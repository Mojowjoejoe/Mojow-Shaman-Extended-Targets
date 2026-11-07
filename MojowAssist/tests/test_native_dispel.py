from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

NATIVE_FIXTURE="""
            C_UnitAuras=setmetatable({}, {__index=function() error('addon aura reads forbidden') end})
            CustomAuraContainerSlotDefaultOptions={}; NATIVE_CALLS=0; ALLOCATIONS=0
            local original=CreateFrame
            function CreateFrame(kind,...)
                local f=original(kind,...)
                if kind=='AuraContainer' then
                    ALLOCATIONS=ALLOCATIONS+1
                    function f:SetUnit(unit) assert(not COMBAT); NATIVE_CALLS=NATIVE_CALLS+1; self.unit=unit end
                    function f:SetAuraSlotEnabled(key,enabled) assert(not COMBAT); self.enabled=enabled; NATIVE_CALLS=NATIVE_CALLS+1 end
                    function f:AddAuraSlot(key,filter,options)
                        self.filter=filter; self.filters=options.candidateFilters
                        local slot=original('Frame')
                        function slot:SetIcon(icon) self.iconBinding=icon end
                        options.initializeFrame(slot); self.testSlot=slot
                    end
                end
                return f
            end
            ROW=original('Frame'); ROW.groupWindow=true; ROW.health=original('Frame')
        """

class NativeDispelTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.ns=self.lua.table()
        self.lua.execute((ROOT/'NearbyHealing.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute((ROOT/'NativeDispelDisplay.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute(NATIVE_FIXTURE)
        self.row=self.lua.globals().ROW; self.native=self.ns.NativeDispelDisplay

    def test_native_filter_and_unit_are_configured_without_reading_live_auras(self):
        self.assertTrue(self.native.Bind(self.native,self.row,'party1',True))
        c=self.row.nativePoison
        self.assertEqual(c.unit,'party1')
        self.assertEqual(c.filter,'HARMFUL|RAID')
        self.assertTrue(c.filters.includeDispelTypes.Poison)
        self.assertIsNone(c.filters.includeSpellIDs)
        self.assertIsNotNone(c.testSlot.iconBinding)
        self.assertTrue(self.row.nativePoisonReady)
        calls=self.lua.globals().NATIVE_CALLS
        self.assertTrue(self.native.Bind(self.native,self.row,'party1',True))
        self.assertEqual(self.lua.globals().NATIVE_CALLS,calls)
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.native.Bind(self.native,self.row,'party2',True))
        self.assertEqual(c.unit,'party1')
        self.assertEqual(self.lua.globals().NATIVE_CALLS,calls)

    def test_only_stable_group_tokens_and_explicit_enable_allocate(self):
        for unit in ('nameplate1','target','focus','party5','raid41'):
            self.assertFalse(self.native.Bind(self.native,self.row,unit,True))
        self.assertFalse(self.native.Bind(self.native,self.row,'party1',False))
        self.assertEqual(self.lua.globals().ALLOCATIONS,0)
        self.assertTrue(self.native.Bind(self.native,self.row,'raid40',True))
        self.native.Bind(self.native,self.row,None,False)
        self.assertFalse(self.row.nativePoisonReady)
        self.assertFalse(self.row.nativePoison.enabled)

    def test_rebinding_and_failure_disable_old_slot_without_retry_loop(self):
        self.native.Bind(self.native,self.row,'party1',True)
        self.lua.globals().OLD=self.row.nativePoison
        self.lua.execute("function OLD:SetUnit(unit) error('unit unavailable') end")
        self.assertFalse(self.native.Bind(self.native,self.row,'party2',True))
        self.assertFalse(self.row.nativePoisonReady)
        self.assertFalse(self.row.nativePoison.enabled)
        calls=self.lua.globals().NATIVE_CALLS
        self.native.Bind(self.native,self.row,'party2',True)
        self.assertEqual(self.lua.globals().NATIVE_CALLS,calls)
        self.native.Bind(self.native,self.row,None,False)
        self.lua.execute('function OLD:SetUnit(unit) self.unit=unit end')
        self.assertTrue(self.native.Bind(self.native,self.row,'party2',True))

    def test_direct_create_in_combat_does_not_allocate_frames(self):
        self.lua.execute('COMBAT=true')
        result=self.native.Create(self.native,self.row)
        self.assertIsNone(result[0])
        self.assertEqual(self.lua.globals().ALLOCATIONS,0)

    def test_missing_native_api_keeps_rows_usable(self):
        self.lua.execute('CustomAuraContainerSlotDefaultOptions=nil')
        self.assertFalse(self.native.Bind(self.native,self.row,'player',True))
        self.assertIsNone(self.row.nativePoison)
        self.assertIsNotNone(self.row.nativePoisonError)

class GroupPoisonIntegrationTests(unittest.TestCase):
    def setUp(self):
        import test_nearby_healing
        fixture=test_nearby_healing.NearbyHealingTests(); fixture.setUp()
        self.lua,self.ns,self.addon=fixture.lua,fixture.ns,fixture.addon
        for name in ('DispelHelper.lua','NativeDispelDisplay.lua'):
            self.lua.execute((ROOT/name).read_text(),'MojowAssist',self.ns)
        self.lua.execute(NATIVE_FIXTURE)
        self.lua.execute("""
            C_UnitAuras={GetAuraDataByIndex=function() return nil end}
            local previous=C_Spell.GetSpellInfo
            C_Spell.GetSpellInfo=function(id) if id==526 then return {name='Cure Poison'} end return previous(id) end
            function IsSpellKnown(id) return id==331 or id==526 end
            AddUnit('party1',false); UNITS.party1.player=true
        """)
        self.panel=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon,'group')

    def test_opt_in_bind_combat_freeze_and_removed_rows_clear(self):
        self.panel.Refresh(self.panel)
        self.assertEqual(self.lua.globals().ALLOCATIONS,0)
        row=self.panel.rows[1]; before=row.attrs.macrotext1
        self.addon.db.groupNativePoison=True
        self.panel.Refresh(self.panel)
        self.assertTrue(row.nativePoisonReady)
        self.assertEqual(row.nativePoison.unit,'party1')
        self.assertEqual(row.attrs.macrotext1,before)
        calls=self.lua.globals().NATIVE_CALLS
        self.lua.execute("COMBAT=true; C_UnitAuras=setmetatable({}, {__index=function() error('combat addon aura access') end})")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.lua.globals().NATIVE_CALLS,calls)
        self.lua.execute('COMBAT=false; UNITS.party1=nil')
        self.panel.Refresh(self.panel)
        self.assertFalse(row.nativePoisonReady)
        self.assertFalse(row.nativePoison.enabled)

    def test_no_cure_prevents_native_feature_even_if_enabled(self):
        self.addon.db.groupNativePoison=True
        self.lua.execute('function IsSpellKnown(id) return id==331 end')
        self.panel.healsDirty=True; self.panel.Refresh(self.panel)
        self.assertEqual(self.lua.globals().ALLOCATIONS,0)
