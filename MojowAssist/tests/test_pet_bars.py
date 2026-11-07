import unittest
from pathlib import Path
import test_nearby_healing

ROOT = Path(__file__).resolve().parents[1]

class PetBarTests(unittest.TestCase):
    def setUp(self):
        fixture = test_nearby_healing.NearbyHealingTests()
        fixture.setUp()
        self.lua, self.ns, self.addon = fixture.lua, fixture.ns, fixture.addon
        self.lua.execute((ROOT/'PetBars.lua').read_text(), 'MojowAssist', self.ns)
        self.lua.execute('''
            function RegisterUnitWatch(frame) assert(not COMBAT); frame.unitWatched=true end
            function UnregisterUnitWatch(frame) assert(not COMBAT); frame.unitWatched=false end
            function UnitIsOtherPlayersPet(unit) return UNITS[unit] and UNITS[unit].pet or false end
            function UnitIsOwnerOrControllerOfUnit(owner,unit)
                return UNITS[unit] and UNITS[unit].owner == UNITS[owner]
            end
            function UnitIsDeadOrGhost(unit) return UNITS[unit] and UNITS[unit].dead or false end
            AddUnit('party1',false); UNITS.party1.player=true
            AddUnit('partypet1',false); UNITS.partypet1.pet=true; UNITS.partypet1.owner=UNITS.party1
            UNITS.partypet1.name='Wolf'; UNITS.partypet1.hp=45; UNITS.partypet1.max=100
        ''')
        self.panel = self.ns.EnemyPanel.Create(self.ns.EnemyPanel, self.addon)
        self.panel.Refresh(self.panel)

    @property
    def row(self): return self.panel.rows[1]

    @property
    def pet(self): return self.row.petBar

    def test_exact_pet_click_and_owner_geometry(self):
        self.assertEqual(self.row.boundUnit,'party1')
        self.assertEqual(self.row.width,222)
        self.assertEqual(self.row.height,36)
        self.assertEqual(self.pet.point[1],'TOPLEFT')
        self.assertEqual(self.pet.point[3],'TOPRIGHT')
        self.assertEqual(self.pet.attrs.unit,'partypet1')
        self.assertEqual(self.pet.attrs.helpbutton1,'petLeft')
        self.assertEqual(self.pet.attrs['type-petLeft'],'macro')
        self.assertIn('/cast [@partypet1,exists,help,nodead] Healing Wave',self.pet.attrs['macrotext-petLeft'])
        self.assertNotIn('@target',self.pet.attrs['macrotext-petLeft'])
        self.assertIsNone(self.pet.attrs.type1)
        self.assertIsNone(self.pet.attrs['harmbutton1'])
        self.assertTrue(self.pet.unitWatched)
        self.assertIn('Wolf',self.pet.name.text)
        self.assertEqual(self.pet.health.value,45)
        self.assertEqual(self.row.name.font[3],'OUTLINE')

    def test_mapping_player_party_raid_and_reject_invalid(self):
        for owner,pet in [('player','pet'),('party1','partypet1'),('party4','partypet4'),('raid40','raidpet40')]:
            self.assertEqual(self.ns.PetBars.StablePet(self.ns.PetBars,owner),pet)
        for owner in ['party5','raid41','raid01','target','focus','nameplate1','party1;bad']:
            self.assertIsNone(self.ns.PetBars.StablePet(self.ns.PetBars,owner))

    def test_nameplate_owner_alias_uses_stable_pet(self):
        self.lua.execute("UNITS.nameplate1=UNITS.party1")
        unit,stable=self.ns.PetBars.Find(self.ns.PetBars,self.panel,'nameplate1')
        self.assertEqual(unit,'partypet1'); self.assertTrue(stable)

    def test_nearby_pet_display_only_never_name_targeted(self):
        self.lua.execute("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; AddUnit('nameplate2',false); UNITS.nameplate2.pet=true; UNITS.nameplate2.owner=UNITS.nameplate1")
        self.panel.roster.Add(self.panel.roster,'nameplate2')
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,'nameplate1')
        self.ns.PetBars.Update(self.ns.PetBars,self.panel,self.row)
        self.assertEqual(self.pet.petUnit,'nameplate2')
        self.assertEqual(self.pet.attrs.unit,'none')
        self.assertIsNone(self.pet.attrs['macrotext-petLeft'])
        self.assertEqual(self.pet.status.text,'Pet - display only')

    def test_owner_mismatch_or_secret_does_not_associate(self):
        self.lua.execute("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; AddUnit('nameplate2',false); UNITS.nameplate2.pet=true; UNITS.nameplate2.owner=UNITS.party1")
        self.panel.roster.Add(self.panel.roster,'nameplate2')
        self.assertIsNone(self.ns.PetBars.Find(self.ns.PetBars,self.panel,'nameplate1'))
        self.lua.execute("function UnitIsOwnerOrControllerOfUnit() return {secret=true} end")
        self.assertIsNone(self.ns.PetBars.Find(self.ns.PetBars,self.panel,'nameplate1'))

    def test_combat_updates_health_without_rebinding(self):
        macro=self.pet.attrs['macrotext-petLeft']
        self.lua.execute("COMBAT=true; UNITS.partypet1.hp=20")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.pet.health.value,20)
        self.assertEqual(self.pet.attrs['macrotext-petLeft'],macro)
        self.assertFalse(self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,None))
        self.lua.execute("UNITS.partypet1=nil")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.pet.status.text,'Pet unavailable')
        self.assertEqual(self.pet.health.value,0)

    def test_dead_pet_and_missing_class_data(self):
        self.lua.execute("UNITS.partypet1.dead=true")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.pet.status.text,'Pet - dead')
        self.assertIn('nodead',self.pet.attrs['macrotext-petLeft'])

    def test_reused_owner_row_clears_pet_and_watch(self):
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,None)
        self.assertFalse(self.pet.shown)
        self.assertFalse(self.pet.unitWatched)
        self.assertEqual(self.pet.attrs.unit,'none')
        self.assertIsNone(self.pet.attrs['macrotext-petLeft'])

    def test_disabled_and_changed_heals(self):
        self.panel.healLeft=None; self.panel.healRight='Lesser Healing Wave'
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,'party1')
        self.assertIsNone(self.pet.attrs['type-petLeft'])
        self.assertIn('Lesser Healing Wave',self.pet.attrs['macrotext-petRight'])
        self.assertEqual(self.pet.attrs.helpbutton2,'petRight')

    def test_right_edge_places_pet_on_left(self):
        self.panel.frame.GetRight=self.lua.eval('function() return 950 end')
        self.lua.execute('function UIParent:GetRight() return 1000 end')
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,'party1')
        self.assertEqual(self.pet.point[1],'TOPRIGHT')
        self.assertEqual(self.pet.point[3],'TOPLEFT')

    def test_summoned_group_pet_has_prebound_watch(self):
        self.lua.execute('UNITS.partypet1=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.pet.attrs.unit,'partypet1')
        self.assertTrue(self.pet.unitWatched)
        self.lua.execute("COMBAT=true; AddUnit('partypet1',false); UNITS.partypet1.name='New wolf'")
        self.panel.Refresh(self.panel)
        self.assertIn('New wolf',self.pet.name.text)

    def test_module_creation_is_blocked_in_combat(self):
        self.lua.execute('COMBAT=true')
        self.assertIsNone(self.ns.PetBars.Create(self.ns.PetBars,self.panel,self.lua.table()))

    def test_opaque_health_only_goes_to_native_widgets(self):
        self.lua.execute("UNITS.partypet1.hp={secret=true}; UNITS.partypet1.max={secret=true}; UNITS.partypet1.name={secret=true}")
        self.panel.Refresh(self.panel)
        self.assertTrue(self.pet.health.value.secret)
        self.assertEqual(self.pet.name.text,'Pet')

    def test_nearby_recycled_token_never_gains_action(self):
        self.lua.execute("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; AddUnit('nameplate2',false); UNITS.nameplate2.pet=true; UNITS.nameplate2.owner=UNITS.nameplate1")
        self.panel.roster.Add(self.panel.roster,'nameplate2')
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,'nameplate1')
        self.lua.execute('COMBAT=true; UNITS.nameplate2.owner=UNITS.party1')
        self.ns.PetBars.Update(self.ns.PetBars,self.panel,self.row)
        self.assertEqual(self.pet.status.text,'Pet unavailable')
        self.assertEqual(self.pet.attrs.unit,'none')
        self.assertIsNone(self.pet.attrs['macrotext-petLeft'])

    def test_enemy_owner_has_no_pet_bar_binding(self):
        self.lua.execute("UNITS.party1.enemy=true")
        self.ns.PetBars.Bind(self.ns.PetBars,self.panel,self.row,'party1')
        self.assertEqual(self.pet.attrs.unit,'none')
        self.assertFalse(self.pet.shown)

    def test_hidden_owner_rows_clear_pet_bindings(self):
        old=self.pet
        self.lua.execute('UNITS.party1=nil')
        self.panel.Refresh(self.panel)
        self.assertFalse(old.shown)
        self.assertEqual(old.attrs.unit,'none')

    def test_pet_event_and_full_toc_load(self):
        self.assertTrue(self.panel.events.events['UNIT_PET'])
        toc=(ROOT/'MojowAssist.toc').read_text()
        self.assertLess(toc.index('PetBars.lua'),toc.index('EnemyPanel.lua'))
        from lupa.lua51 import LuaRuntime
        runtime=LuaRuntime(unpack_returned_tuples=True)
        runtime.execute((ROOT/'tests/wow_stub.lua').read_text())
        ns=runtime.table()
        for name in toc.splitlines():
            if name.endswith('.lua'):
                runtime.execute((ROOT/name).read_text(), 'MojowAssist',ns)
        ns.Addon.Initialize(ns.Addon)
