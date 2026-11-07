import unittest
import test_nearby_healing

class FocusAnyTargetTests(unittest.TestCase):
    def setUp(self):
        f=test_nearby_healing.NearbyHealingTests(); f.setUp(); f.enable_damage()
        self.lua,self.panel,self.ns,self.addon=f.lua,f.panel,f.ns,f.addon
        self.panel.Refresh(self.panel)

    def test_follows_friendly_player_npc_and_dead_target_in_combat(self):
        row=self.panel.combatRows[1]
        macro=row.attrs.macrotext1
        self.lua.execute('COMBAT=true')
        for flags,name in [('player=true','Friendly Player'),('player=false','Friendly NPC'),('dead=true','Dead Target')]:
            self.lua.execute("AddUnit('focustarget',false); UNITS.focustarget."+flags+"; UNITS.focustarget.name='"+name+"'")
            self.panel.Refresh(self.panel)
            self.assertIn(name,row.name.text)
            self.assertFalse(row.displayUnavailable)
            self.assertEqual(row.attrs.macrotext1,macro)
        self.lua.execute('UNITS.focustarget=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.name.text,'No focus target')
        self.assertTrue(row.displayUnavailable)

    def test_select_any_but_cast_only_on_living_hostile(self):
        row=self.panel.combatRows[1]
        macro=row.attrs.macrotext1
        self.assertTrue(macro.startswith('/cleartarget\n/target [@focustarget,exists]'))
        self.assertIn('/cast [@target,exists,harm,nodead] Lightning Bolt',macro)
        self.assertIsNone(row.attrs.helpbutton1)
        self.assertIsNone(row.attrs.helpbutton2)

    def test_disabled_damage_still_selects_focus_target(self):
        row=self.panel.combatRows[1]
        healing=self.ns.NearbyHealing
        healing.Bind(healing,row,'focustarget',None,None,None,None,True)
        self.assertEqual(row.attrs.macrotext1,'/cleartarget\n/target [@focustarget,exists]')
        self.assertEqual(row.attrs.type1,'macro')
        self.assertEqual(row.attrs['type-damageLeft'],'macro')
        self.assertEqual(row.attrs['macrotext-damageLeft'],row.attrs.macrotext1)
        self.assertIsNone(row.attrs['spell-damageRight'])

    def test_assist_summary_tracks_friendly_target(self):
        self.lua.execute("AddUnit('focus',false); AddUnit('focustarget',false); UNITS.focustarget.player=true; UNITS.focustarget.name='Friend'")
        button=self.lua.globals().CreateFrame('Button')
        button.SetAttribute(button,'type','assist'); button.SetAttribute(button,'unit','focus')
        self.addon.action=self.lua.table_from({'button':button})
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.assistSummary.text,'Assist target: Friend')

    def test_focus_action_flag_clears_on_normal_row_rebind(self):
        row=self.panel.rows[1]
        h=self.ns.NearbyHealing
        h.Bind(h,row,'focustarget',None,None,'Lightning Bolt',None,True)
        self.assertTrue(row.focusTargetRow)
        h.Bind(h,row,None,None,None,None,None)
        self.assertFalse(row.focusTargetRow)
        self.assertIsNone(row.attrs.macrotext1)
