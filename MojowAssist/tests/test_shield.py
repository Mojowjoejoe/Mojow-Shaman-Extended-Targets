from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class ShieldTests(unittest.TestCase):
    def native_fixture(self):
        self.lua.execute('''
            CustomAuraContainerSlotDefaultOptions={}
            local original=CreateFrame
            function CreateFrame(kind,...)
                local frame=original(kind,...)
                if kind=='AuraContainer' then
                    function frame:SetUnit(unit) self.configuredUnit=unit end
                    function frame:SetAuraSlotCandidateFilters(key,filters) self.filters=filters end
                    function frame:AddAuraSlot(key,filter,options)
                        self.key=key; self.filter=filter; self.filters=options.candidateFilters
                        local slot=original('Frame')
                        function slot:SetIcon(texture) self.iconBinding=texture end
                        function slot:SetDurationCooldown(cooldown) self.cooldownBinding=cooldown end
                        function slot:SetDurationText(label) self.durationBinding=label end
                        function slot:SetApplicationCount(label) self.countBinding=label end
                        options.initializeFrame(slot)
                        self.testSlot=slot
                    end
                end
                return frame
            end
        ''')

    def test_native_display_configures_bindings_and_no_combat_reads(self):
        self.native_fixture()
        self.helper.Configure(self.helper)
        native=self.helper.nativeDisplay
        self.assertEqual(native.configuredUnit,'player')
        self.assertEqual(native.filter,'HELPFUL')
        self.assertTrue(native.filters.includeSpellIDs[324])
        self.assertIsNotNone(native.testSlot.iconBinding)
        self.assertIsNotNone(native.testSlot.cooldownBinding)
        self.assertIsNotNone(native.testSlot.durationBinding)
        self.assertIsNotNone(native.testSlot.countBinding)
        self.lua.execute('''
            COMBAT=true
            C_UnitAuras=setmetatable({}, {__index=function() error('combat aura reads forbidden') end})
        ''')
        self.helper.Update(self.helper)
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Live shield icon shown above')
        self.assertEqual(self.helper.button.attrs.type1,'spell')

    def test_native_creation_failure_preserves_cast_button(self):
        self.lua.execute('''
            CustomAuraContainerSlotDefaultOptions={}
            local original=CreateFrame
            function CreateFrame(kind,...)
                if kind=='AuraContainer' then error('Unsupported container') end
                return original(kind,...)
            end
        ''')
        self.helper.Configure(self.helper)
        self.assertIsNone(self.helper.nativeDisplay)
        self.assertIn('Unsupported container',self.helper.nativeError)
        self.assertEqual(self.helper.button.attrs.type1,'spell')

    def test_debug_reports_restrictions_without_printing_secret_fields(self):
        self.lua.globals().testAddon=self.addon
        self.lua.execute('''
            OUTPUT={}
            function testAddon:Say(message) table.insert(OUTPUT,message) end
            function C_UnitAuras.GetAuraDataByIndex(unit,index)
                if index==1 then return {name={secret=true},spellId={secret=true}} end
            end
        ''')
        self.helper.Debug(self.helper)
        lines=self.lua.globals().OUTPUT
        self.assertIn('0 readable names, 0 readable spell IDs',lines[len(lines)])

    def test_readable_name_lookup_nil_can_use_known_aura_instance(self):
        self.lua.execute('AURA={auraInstanceID=77,applications=3}')
        self.helper.Update(self.helper)
        self.lua.execute('''
            COMBAT=false
            function C_UnitAuras.GetAuraDataBySpellName() return nil end
            function C_UnitAuras.GetAuraDataByAuraInstanceID(unit,id)
                assert(unit=='player' and id==77)
                return {auraInstanceID=77,applications=2}
            end
        ''')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active | 2 charges')

    def test_combat_nil_without_readable_scan_is_unknown(self):
        self.lua.execute('COMBAT=true; AURA=nil')
        self.helper.Update(self.helper)
        self.assertIn('hidden in combat',self.helper.status.text)

    def test_removed_cached_aura_does_not_stay_active(self):
        self.lua.execute('AURA={auraInstanceID=77,applications=1}')
        self.helper.Update(self.helper)
        self.lua.execute('''
            COMBAT=false; AURA=nil
            function C_UnitAuras.GetAuraDataByAuraInstanceID() return nil end
            function C_UnitAuras.GetAuraDataByIndex() return nil end
        ''')
        self.helper.Update(self.helper)
        self.assertIn('MISSING',self.helper.status.text)
        self.assertIsNone(self.helper.auraInstances['Lightning Shield'])

    def test_scan_detects_shield_when_name_query_omits_it(self):
        self.lua.execute('''
            COMBAT=false
            function C_UnitAuras.GetAuraDataByIndex(unit,index,filter)
                if index==1 then return {name='Lightning Shield',applications=2} end
            end
        ''')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active | 2 charges')

    def test_readable_empty_scan_confirms_missing_outside_combat(self):
        self.lua.execute('function C_UnitAuras.GetAuraDataByIndex() return nil end')
        self.helper.Update(self.helper)
        self.assertIn('MISSING',self.helper.status.text)

    def test_restricted_scan_never_claims_missing(self):
        self.lua.execute('''
            COMBAT=false
            function C_UnitAuras.GetAuraDataByIndex(unit,index)
                if index==1 then return {name={secret=true}} end
            end
        ''')
        self.helper.Update(self.helper)
        self.assertIn('unavailable',self.helper.status.text)

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute('''
            function UnitClass() return 'Shaman','SHAMAN' end
            KNOWN=true; AURA=nil; WATER=nil
            function IsSpellKnown(id) return KNOWN end
            function GetTime() return 100 end
            C_Spell={GetSpellInfo=function(id)
                return {name=(id==52127 or id==24398) and 'Water Shield' or 'Lightning Shield',iconID=123}
            end}
            C_UnitAuras={GetAuraDataBySpellName=function(unit,name,filter)
                assert(unit=='player' and filter=='HELPFUL')
                if name=='Water Shield' then return WATER end
                return AURA
            end}
        ''')
        self.ns=self.lua.table()
        self.lua.execute((ROOT/'Appearance.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute((ROOT/'Model.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute((ROOT/'NativeShieldDisplay.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute((ROOT/'ShieldHelper.lua').read_text(),'MojowAssist',self.ns)
        self.addon=self.lua.table(db=self.ns.Model.Normalize(self.ns.Model,self.lua.table()))
        self.helper=self.ns.ShieldHelper.Create(self.ns.ShieldHelper,self.addon)

    def test_missing_and_secure_self_cast(self):
        self.assertEqual(self.helper.button.attrs.type1,'spell')
        self.assertIsNone(self.helper.button.attrs.type)
        self.assertEqual(self.helper.button.attrs.unit,'player')
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')
        self.assertIn('MISSING',self.helper.status.text)

    def test_active_charges_time_then_expired(self):
        self.lua.execute('AURA={applications=3,expirationTime=225}')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active | 3 charges | 2:05')
        self.lua.execute('AURA=nil')
        self.helper.Update(self.helper)
        self.assertIn('MISSING',self.helper.status.text)

    def test_combat_updates_do_not_reconfigure_secure_button(self):
        self.lua.execute('COMBAT=true; KNOWN=false; AURA={applications=2}')
        self.helper.Configure(self.helper)
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.button.attrs.type1,'spell')
        self.assertEqual(self.helper.status.text,'Shield status hidden in combat')
        self.lua.execute('COMBAT=false')
        self.helper.Configure(self.helper)
        self.assertIsNone(self.helper.button.attrs.type1)
        self.assertEqual(self.helper.status.text,'Learn Lightning Shield')

    def test_unavailable_aura_does_not_report_missing(self):
        self.lua.execute("function C_UnitAuras.GetAuraDataBySpellName() error('unavailable') end")
        self.helper.Update(self.helper)
        self.assertIn('unavailable',self.helper.status.text)

    def test_secret_fields_not_used_in_arithmetic(self):
        self.lua.execute('AURA={applications={secret=true},expirationTime={secret=true}}')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active')

    def test_water_shield_suppresses_missing_warning(self):
        self.lua.execute('WATER={applications=3}')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Water Shield active')

    def test_learned_higher_rank_by_localized_name(self):
        self.lua.execute('''
            KNOWN=false
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=1,offSpecID=0} end,
                GetSpellBookItemInfo=function() return {spellID=325,itemType=1} end}
        ''')
        self.helper.Configure(self.helper)
        self.assertTrue(self.helper.known)
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')
        self.assertTrue(self.helper.shieldSpellIDs[325])

    def test_non_shaman_has_no_button(self):
        self.lua.execute("function UnitClass() return 'Mage','MAGE' end")
        other=self.ns.ShieldHelper.Create(self.ns.ShieldHelper,self.addon)
        self.assertIsNone(other.button)

    def test_drag_cleanup_retries_after_combat(self):
        self.helper.button.scripts.OnDragStart()
        self.assertTrue(self.helper.moving)
        self.lua.execute('COMBAT=true')
        self.helper.events.scripts.OnEvent(self.helper.events,'PLAYER_REGEN_DISABLED')
        self.assertTrue(self.helper.moving)
        self.lua.execute('COMBAT=false')
        self.helper.events.scripts.OnEvent(self.helper.events,'PLAYER_REGEN_ENABLED')
        self.assertFalse(self.helper.moving)
        self.assertFalse(self.helper.button.moving)

    def test_water_selection_persists_and_native_filter_and_title_follow(self):
        self.native_fixture()
        self.helper.Configure(self.helper)
        self.assertTrue(self.helper.Cycle(self.helper))
        self.assertEqual(self.addon.db.shieldSpellID,52127)
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')
        self.assertIn('Water Shield',self.helper.title.text)
        self.assertTrue(self.helper.nativeDisplay.filters.includeSpellIDs[52127])
        self.assertIsNone(self.helper.nativeDisplay.filters.includeSpellIDs[324])
        self.assertEqual(self.helper.nativeDisplay.shieldTitle.text,'Water Shield')
        self.lua.execute('WATER={applications=3,expirationTime=200}')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active | 3 charges | 1:40')
        normalized=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual(normalized.shieldSpellID,52127)

    def test_shield_switch_ignores_combat_unlearned_and_drag(self):
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.helper.Cycle(self.helper))
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')
        self.lua.execute('COMBAT=false; function IsSpellKnown(id) return id==324 end')
        self.helper.Configure(self.helper)
        self.assertFalse(self.helper.Cycle(self.helper))
        self.lua.execute('function IsSpellKnown() return true end')
        self.helper.Configure(self.helper)
        b=self.helper.button
        b.scripts.OnMouseDown(b,'RightButton')
        b.scripts.OnDragStart()
        b.scripts.OnDragStop()
        b.scripts.OnMouseUp(b,'RightButton')
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')
        b.scripts.OnMouseDown(b,'RightButton')
        b.scripts.OnMouseUp(b,'RightButton')
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')

    def test_water_higher_ranks_refresh_after_training(self):
        self.addon.db.shieldSpellID=52127
        self.lua.execute("""
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_Spell.GetSpellInfo=function(id)
                return {name=(id==324 and 'Lightning Shield' or 'Water Shield'),iconID=123}
            end
            RANKID=52127
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=1,offSpecID=0} end,
                GetSpellBookItemInfo=function() return {spellID=RANKID,itemType=1} end}
        """)
        self.helper.Configure(self.helper)
        self.lua.execute('RANKID=52129; COMBAT=true')
        self.helper.events.scripts.OnEvent(self.helper.events,'SPELLS_CHANGED')
        self.assertIsNone(self.helper.shieldSpellIDs[52129])
        self.lua.execute('COMBAT=false')
        self.helper.events.scripts.OnEvent(self.helper.events,'PLAYER_REGEN_ENABLED')
        self.assertTrue(self.helper.shieldSpellIDs[52129])
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')

    def test_saved_water_choice_restores_and_reports_other_shield(self):
        self.addon.db.shieldSpellID=52127
        helper=self.ns.ShieldHelper.Create(self.ns.ShieldHelper,self.addon)
        self.assertEqual(helper.button.attrs.spell,'Water Shield')
        self.lua.execute('AURA={applications=3}')
        helper.Update(helper)
        self.assertEqual(helper.status.text,'Lightning Shield active')

    def test_failed_native_filter_change_hides_previous_shield(self):
        self.native_fixture(); self.helper.Configure(self.helper)
        native=self.helper.nativeDisplay
        self.lua.globals().TESTNATIVE=native
        self.lua.execute("function TESTNATIVE:SetAuraSlotCandidateFilters() error('blocked') end")
        self.assertTrue(self.helper.Cycle(self.helper))
        self.assertFalse(native.shown)
        self.assertIsNone(self.helper.nativeDisplay)
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')

    def test_classic_water_id_without_newer_spell_metadata_switches(self):
        self.lua.execute("""
            C_Spell.GetSpellInfo=function(id)
                if id==324 then return {name='Lightning Shield',iconID=1} end
                if id==24398 then return {name='Water Shield',iconID=2} end
            end
            function IsSpellKnown(id) return id==324 or id==24398 end
        """)
        self.assertTrue(self.helper.Cycle(self.helper))
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')
        self.assertTrue(self.helper.shieldSpellIDs[24398])
        self.assertEqual(self.addon.db.shieldSpellID,52127)
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')

    def test_visible_switch_reports_failure_and_success_without_casting(self):
        self.lua.globals().TEST_ADDON=self.addon
        self.lua.execute("function TEST_ADDON:Say(text) self.lastMessage=text end; function IsSpellKnown(id) return id==324 end")
        switch=self.helper.switch
        self.assertIsNotNone(switch)
        switch.scripts.OnClick(switch)
        self.assertIn('not learned',self.addon.lastMessage)
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')
        self.lua.execute('function IsSpellKnown() return true end')
        switch.scripts.OnClick(switch)
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')
        self.assertIn('Water Shield',self.addon.lastMessage)
        self.assertIsNone(switch.attrs.type1)
        self.lua.execute('COMBAT=true')
        switch.scripts.OnClick(switch)
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')
        self.assertIn('outside combat',self.addon.lastMessage)

    def test_water_discovered_from_spellbook_when_both_base_ids_are_missing(self):
        self.lua.execute("""
            function GetLocale() return 'enUS' end
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_Spell.GetSpellInfo=function(id) if id==324 then return {name='Lightning Shield',iconID=1} end end
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=2,offSpecID=0} end,
                GetSpellBookItemInfo=function(i) return {spellID=90000+i,itemType=1} end,
                GetSpellBookItemName=function(i) return i==1 and 'Water Shield' or 'Water Walking','Rank 1' end,
                GetSpellBookItemTexture=function() return 456 end}
        """)
        self.assertTrue(self.helper.Cycle(self.helper))
        self.assertEqual(self.helper.button.attrs.spell,'Water Shield')
        self.assertTrue(self.helper.shieldSpellIDs[90001])
        self.assertIsNone(self.helper.shieldSpellIDs[90002])
        self.helper.Configure(self.helper)
        self.assertTrue(self.helper.known)

    def test_spellbook_future_or_passive_water_is_not_learned(self):
        self.lua.execute("""
            function GetLocale() return 'enUS' end
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_Spell.GetSpellInfo=function(id) if id==324 then return {name='Lightning Shield',iconID=1} end end
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=2,offSpecID=0} end,
                GetSpellBookItemInfo=function(i) return {spellID=90000+i,itemType=i==1 and 2 or 1,isPassive=i==2} end,
                GetSpellBookItemName=function() return 'Water Shield','Rank 1' end}
        """)
        self.assertFalse(self.helper.Cycle(self.helper))
        self.assertEqual(self.helper.button.attrs.spell,'Lightning Shield')

    def test_spellbook_exact_localized_name_works_without_item_metadata(self):
        self.lua.execute("""
            function GetLocale() return 'deDE' end
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_Spell.GetSpellInfo=function(id) if id==52127 then return {name='Wasserschild',iconID=1} end end
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=1,offSpecID=0} end,
                GetSpellBookItemInfo=function() return {actionID=90001,itemType=1} end,
                GetSpellBookItemName=function() return 'Wasserschild','Rank 1' end}
        """)
        self.assertTrue(self.helper.Cycle(self.helper))
        self.assertEqual(self.helper.button.attrs.spell,'Wasserschild')
        self.assertTrue(self.helper.shieldSpellIDs[90001])
