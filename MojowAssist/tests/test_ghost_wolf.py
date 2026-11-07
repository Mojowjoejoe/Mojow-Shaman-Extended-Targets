from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

class GhostWolfTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute("""
            function UnitClass() return 'Shaman','SHAMAN' end
            KNOWN=true; FORM=0
            function IsSpellKnown(id) return KNOWN and id==2645 end
            function GetShapeshiftFormID() return FORM end
            C_Spell={GetSpellInfo=function(id) if id==2645 then return {name='Ghost Wolf',iconID=123} end end}
        """)
        self.ns=self.lua.table()
        for name in ['Appearance.lua','NearbyHealing.lua','GhostWolf.lua']:
            self.lua.execute((ROOT/name).read_text(),'MojowAssist',self.ns)
        self.addon=self.lua.table(db=self.lua.table())
        self.anchor=self.lua.globals().CreateFrame('Frame')
        self.helper=self.ns.GhostWolf.Create(self.ns.GhostWolf,self.addon,self.anchor)

    def test_secure_toggle_and_anchor(self):
        self.assertEqual(self.helper.button.attrs.type1,'spell')
        self.assertEqual(self.helper.button.attrs.spell,'Ghost Wolf')
        self.assertEqual(self.helper.button.attrs.unit,'player')
        self.assertEqual(self.helper.button.point[1],'LEFT')
        self.assertEqual(self.helper.status.text,'Click to transform')

    def test_active_unknown_and_combat_do_not_mutate_binding(self):
        self.lua.execute('FORM=16; COMBAT=true')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Active - click to exit')
        self.lua.execute('KNOWN=false; FORM={secret=true}')
        self.helper.events.scripts.OnEvent(self.helper.events,'SPELLS_CHANGED')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.button.attrs.type1,'spell')
        self.assertEqual(self.helper.status.text,'Status unavailable')
        self.lua.execute('COMBAT=false; FORM=0')
        self.helper.events.scripts.OnEvent(self.helper.events,'PLAYER_REGEN_ENABLED')
        self.assertIsNone(self.helper.button.attrs.type1)
        self.assertEqual(self.helper.status.text,'Not learned')

    def test_training_enables_button(self):
        self.lua.execute('KNOWN=false')
        self.helper.Configure(self.helper)
        self.assertIsNone(self.helper.button.attrs.type1)
        self.lua.execute('KNOWN=true')
        self.helper.events.scripts.OnEvent(self.helper.events,'SPELLS_CHANGED')
        self.assertEqual(self.helper.button.attrs.type1,'spell')

    def test_unavailable_form_api_never_claims_inactive(self):
        self.lua.execute('GetShapeshiftFormID=nil')
        self.helper.Update(self.helper)
        self.assertEqual(self.helper.status.text,'Status unavailable')
        self.assertEqual(self.helper.button.attrs.type1,'spell')

    def test_lookup_error_clears_action_without_claiming_unlearned(self):
        self.lua.execute("function IsSpellKnown() error('temporarily unavailable') end")
        self.helper.Configure(self.helper)
        self.assertIsNone(self.helper.button.attrs.type1)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.lua.execute('COMBAT=true; KNOWN=true')
        self.helper.Configure(self.helper)
        self.assertIsNone(self.helper.button.attrs.type1)

    def test_missing_metadata_is_unknown_and_recovers(self):
        self.lua.execute('C_Spell.GetSpellInfo=function() return nil end')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.assertIsNone(self.helper.button.attrs.type1)
        self.lua.execute("C_Spell.GetSpellInfo=function() return {name='Ghost Wolf',iconID=123} end")
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.button.attrs.type1,'spell')
        self.assertEqual(self.helper.status.text,'Click to transform')

    def test_clamp_reserves_wolf_width_and_preserves_other_insets(self):
        self.lua.globals().ANCHOR=self.anchor
        self.lua.execute('''
            function ANCHOR:GetClampRectInsets() return -3,0,42,-4 end
            function ANCHOR:SetClampRectInsets(...) assert(not COMBAT); self.insets={...} end
        ''')
        self.helper.Configure(self.helper)
        self.assertIsNotNone(self.anchor.insets)
        self.assertEqual(tuple(self.anchor.insets.values()),(-3,180,42,-4))
        self.lua.execute('COMBAT=true')
        self.helper.Configure(self.helper)
        self.assertEqual(tuple(self.anchor.insets.values()),(-3,180,42,-4))

    def test_absent_discovery_api_is_unknown(self):
        self.lua.execute('IsSpellKnown=nil')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.assertIsNone(self.helper.button.attrs.type1)

    def test_nil_known_result_is_unavailable_not_unlearned(self):
        self.lua.execute('IsSpellKnown=function() return nil end')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.assertIsNone(self.helper.button.attrs.type1)

    def test_incomplete_book_is_unavailable_and_complete_negative_is_unlearned(self):
        self.lua.execute('''
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return nil end}
        ''')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.lua.execute('''
            C_SpellBook.GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=1} end
            C_SpellBook.GetSpellBookItemInfo=function() return nil end
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
        ''')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Lookup unavailable')
        self.lua.execute('C_SpellBook.GetNumSpellBookSkillLines=function() return 0 end')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.status.text,'Not learned')
        self.assertIsNone(self.helper.button.attrs.type1)
        self.lua.execute('''
            C_SpellBook.GetNumSpellBookSkillLines=function() return 1 end
            C_SpellBook.GetSpellBookItemInfo=function() return {itemType=1,spellID=2645} end
        ''')
        self.helper.Configure(self.helper)
        self.assertEqual(self.helper.button.attrs.spell,'Ghost Wolf')
