import unittest
import test_totems


class TotemLayoutTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_totems.TotemTests()
        self.fixture.setUp()
        self.lua=self.fixture.lua
        self.ns=self.fixture.ns
        self.addon=self.fixture.addon
        self.panel=self.fixture.panel

    def point(self):
        p=self.panel.frame.point
        return p[1],p[3],p[4],p[5]

    def test_legacy_compact_center_migrates_once_and_keeps_top_left(self):
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-366,69))
        self.assertTrue(self.addon.db.totemTopLeft)
        self.panel.ToggleExpanded(self.panel)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-366,69))
        self.panel.ToggleExpanded(self.panel)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-366,69))
        saved=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.addon.db=saved
        self.panel=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-366,69))

    def test_expanded_migration_uses_expanded_dimensions(self):
        self.addon.db=self.ns.Model.Normalize(self.ns.Model,self.lua.table(totemX=100,totemY=50,totemExpanded=True))
        self.panel=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-105,270))
        self.panel.ToggleExpanded(self.panel)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-105,270))

    def test_drag_reanchors_and_persists_top_left_after_reload(self):
        self.panel.ToggleExpanded(self.panel)
        self.panel.moving=True
        self.panel.FinishDrag(self.panel)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-205,220))
        self.assertEqual((self.addon.db.totemX,self.addon.db.totemY),(-205,220))
        self.panel.ToggleExpanded(self.panel)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-205,220))
        self.addon.db=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.panel=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.assertEqual(self.point(),('TOPLEFT','CENTER',-205,220))

    def test_combat_resize_and_drag_do_not_move_or_save(self):
        before=self.point()
        self.lua.execute('COMBAT=true')
        self.panel.moving=True
        self.panel.FinishDrag(self.panel)
        self.assertFalse(self.panel.ToggleExpanded(self.panel))
        self.assertEqual(self.point(),before)

    def test_failed_first_discovery_has_visible_compact_feedback(self):
        self.lua.execute('C_SpellBook.GetSpellBookSkillLineInfo=function() return nil end')
        self.panel=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.assertEqual(self.panel.dropSet.text,'Spellbook unavailable')
        self.assertTrue(self.panel.dropSet.shown)
        self.assertFalse(self.panel.note.shown)

    def test_retained_choice_hover_explains_discovery_failure(self):
        self.lua.execute('''
            GameTooltip=CreateFrame('Frame')
            function GameTooltip:SetOwner() self.lines={} end
            function GameTooltip:SetSpellByID() end
            function GameTooltip:AddLine(line) table.insert(self.lines,line) end
            C_SpellBook.GetSpellBookSkillLineInfo=function() return nil end
        ''')
        self.panel.Refresh(self.panel)
        self.panel.buttons[8071].scripts.OnEnter()
        self.assertIn('Spellbook unavailable; showing last learned choices.',list(self.lua.globals().GameTooltip.lines.values()))
