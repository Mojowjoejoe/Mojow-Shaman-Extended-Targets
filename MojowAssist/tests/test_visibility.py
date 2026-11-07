from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class VisibilityTests(unittest.TestCase):
    def test_options_omit_outline_controls_and_keep_tracking(self):
        self.panel.Toggle(self.panel)
        self.assertIsNone(self.panel.outlineModes)
        self.assertIsNone(self.panel.outlineFeedback)
        self.assertEqual(self.panel.frame.height,402)
        self.assertIsNotNone(self.panel.resourceChecks[2])
        self.assertEqual(self.lua.globals().WRITES,0)
        self.assertEqual(self.lua.globals().CVARS.Outline,'2')

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute('''
            CVARS={Outline='2',nameplateShowFriendlyPlayers='0',nameplateShowEnemies='1'}
            WRITES=0; TRACKING={{name='Find Treasure',spellID=2481,active=false}}
            C_CVar={GetCVar=function(k) return CVARS[k] end,
                SetCVar=function(k,v) WRITES=WRITES+1; CVARS[k]=v end}
            C_Minimap={GetNumTrackingTypes=function() return #TRACKING end,
                GetTrackingInfo=function(i) return TRACKING[i] end,
                SetTracking=function(i,on) TRACKING[i].active=on end}
            TEST_ADDON={db={autoFindMinerals=true},Say=function(self,text) self.lastMessage=text end}
        ''')
        self.ns=self.lua.table()
        self.lua.execute((ROOT/'Appearance.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute((ROOT/'VisibilityOptions.lua').read_text(),'MojowAssist',self.ns)
        self.panel=self.ns.VisibilityOptions.Create(self.ns.VisibilityOptions,self.lua.globals().TEST_ADDON)

    def test_open_reads_without_mutating_and_valid_change_reads_back(self):
        self.panel.Toggle(self.panel)
        self.assertEqual(self.lua.globals().WRITES,0)
        self.assertFalse(self.panel.checks.nameplateShowFriendlyPlayers.checked)
        self.assertTrue(self.panel.Set(self.panel,'nameplateShowFriendlyPlayers','1'))
        self.assertTrue(self.panel.checks.nameplateShowFriendlyPlayers.checked)

    def test_rejected_and_unavailable_cvars_are_not_success(self):
        self.assertFalse(self.panel.Set(self.panel,'unsupported','1'))
        self.lua.execute('function C_CVar.SetCVar() end')
        self.assertFalse(self.panel.Set(self.panel,'nameplateShowFriendlyPlayers','1'))
        self.assertIn('did not accept',self.lua.globals().TEST_ADDON.lastMessage)

    def test_resource_re_resolves_index_and_does_not_enable_unknown_spell(self):
        self.assertFalse(self.panel.ToggleTracking(self.panel,2383))
        self.lua.execute("table.insert(TRACKING,1,{name='Other',spellID=999,active=false})")
        self.assertTrue(self.panel.ToggleTracking(self.panel,2481))
        self.assertFalse(self.lua.globals().TRACKING[1].active)
        self.assertTrue(self.lua.globals().TRACKING[2].active)

    def test_combat_changes_are_blocked_without_writes(self):
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.panel.Set(self.panel,'nameplateShowFriendlyPlayers','1'))
        self.assertFalse(self.panel.ToggleTracking(self.panel,2481))
        self.assertEqual(self.lua.globals().WRITES,0)

    def test_rejected_checkbox_click_restores_actual_state(self):
        self.panel.Toggle(self.panel)
        self.lua.execute('COMBAT=true')
        check=self.panel.checks.nameplateShowFriendlyPlayers
        check.checked=True
        check.scripts.OnClick(check)
        self.assertFalse(check.checked)
        resource=self.panel.resourceChecks[3]
        resource.checked=True
        resource.scripts.OnClick(resource)
        self.assertFalse(resource.checked)

    def test_find_minerals_default_waits_for_combat_then_enables_once(self):
        self.lua.execute("TRACKING[1].name='Find Minerals'; TRACKING[1].spellID=2580; COMBAT=true")
        self.assertFalse(self.panel.ApplyTrackingDefaults(self.panel))
        self.assertFalse(self.lua.globals().TRACKING[1].active)
        self.lua.execute('COMBAT=false')
        self.panel.trackingEvents.scripts.OnEvent(self.panel.trackingEvents,'PLAYER_REGEN_ENABLED')
        self.assertTrue(self.lua.globals().TRACKING[1].active)
        self.lua.execute('TRACKING[1].active=false')
        self.panel.trackingEvents.scripts.OnEvent(self.panel.trackingEvents,'MINIMAP_UPDATE_TRACKING')
        self.assertFalse(self.lua.globals().TRACKING[1].active)

    def test_find_minerals_checkbox_saves_off_preference(self):
        self.lua.execute("TRACKING[1].name='Find Minerals'; TRACKING[1].spellID=2580")
        self.panel.ApplyTrackingDefaults(self.panel)
        self.assertTrue(self.lua.globals().TRACKING[1].active)
        self.assertTrue(self.panel.ToggleTracking(self.panel,2580))
        self.assertFalse(self.lua.globals().TEST_ADDON.db.autoFindMinerals)
        fresh=self.ns.VisibilityOptions.Create(self.ns.VisibilityOptions,self.lua.globals().TEST_ADDON)
        fresh.ApplyTrackingDefaults(fresh)
        self.assertFalse(self.lua.globals().TRACKING[1].active)

    def test_default_handles_late_tracking_and_rejected_write_without_loop(self):
        self.lua.execute('TRACKING={}')
        self.assertFalse(self.panel.ApplyTrackingDefaults(self.panel))
        self.lua.execute("TRACKING={{name='Find Minerals',spellID=2580,active=false}}; CALLS=0; function C_Minimap.SetTracking() CALLS=CALLS+1 end")
        self.panel.trackingEvents.scripts.OnEvent(self.panel.trackingEvents,'SPELLS_CHANGED')
        self.assertFalse(self.lua.globals().TRACKING[1].active)
        self.panel.trackingEvents.scripts.OnEvent(self.panel.trackingEvents,'MINIMAP_UPDATE_TRACKING')
        self.assertEqual(self.lua.globals().CALLS,1)

    def test_default_selects_minerals_only_and_preserves_treasure(self):
        self.lua.execute("table.insert(TRACKING,{name='Find Minerals',spellID=2580,active=false})")
        self.assertTrue(self.panel.ApplyTrackingDefaults(self.panel))
        self.assertFalse(self.lua.globals().TRACKING[1].active)
        self.assertTrue(self.lua.globals().TRACKING[2].active)

    def test_manual_minerals_off_wins_over_reentrant_tracking_event(self):
        self.lua.execute("TRACKING={{name='Find Minerals',spellID=2580,active=true}}")
        self.lua.globals().TRACKING_EVENT=self.panel.trackingEvents
        self.lua.execute("function C_Minimap.SetTracking(i,on) TRACKING[i].active=on; TRACKING_EVENT.scripts.OnEvent(TRACKING_EVENT,'MINIMAP_UPDATE_TRACKING') end")
        self.assertTrue(self.panel.ToggleTracking(self.panel,2580))
        self.assertFalse(self.lua.globals().TRACKING[1].active)
        self.assertFalse(self.lua.globals().TEST_ADDON.db.autoFindMinerals)

    def test_friendly_checkbox_uses_current_player_setting_only(self):
        self.lua.execute("CVARS.nameplateShowFriends=nil; CVARS.nameplateShowFriendlyNpcs='0'")
        self.panel.Toggle(self.panel)
        check=self.panel.checks.nameplateShowFriendlyPlayers
        self.assertIsNotNone(check)
        self.assertIsNone(self.panel.checks.nameplateShowFriends)
        check.scripts.OnClick(check)
        self.assertTrue(check.checked)
        self.assertEqual(self.lua.globals().CVARS.nameplateShowFriendlyPlayers,'1')
        self.assertEqual(self.lua.globals().CVARS.nameplateShowFriendlyNpcs,'0')
        self.assertIsNone(self.lua.globals().CVARS.nameplateShowFriends)
        check.scripts.OnClick(check)
        self.assertFalse(check.checked)
        self.assertEqual(self.lua.globals().CVARS.nameplateShowFriendlyPlayers,'0')
