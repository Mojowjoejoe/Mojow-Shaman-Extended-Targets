from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
class DispelTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.ns=self.lua.table()
        self.lua.execute("C_UnitAuras={}; AURAS={}; CALLS=0; function C_UnitAuras.GetAuraDataByIndex(u,i,f) CALLS=CALLS+1; assert(f=='HARMFUL'); return AURAS[i] end")
        self.lua.execute((ROOT/'DispelHelper.lua').read_text(),'MojowAssist',self.ns)
        self.helper=self.ns.DispelHelper
        self.caps=self.lua.table_from({'Poison':self.lua.table_from({'id':526,'name':'Cure Poison'})})
    def test_readable_matching_type(self):
        self.lua.execute("AURAS={{dispelName='Magic'},{dispelName='Poison'}}")
        result=self.helper.Scan(self.helper,'party1',self.caps)
        self.assertEqual(result.kind,'found'); self.assertEqual(result.dispel,'Poison')
        self.assertEqual(result.spell.id,526)
    def test_combat_never_queries_restricted_auras(self):
        self.lua.execute('COMBAT=true')
        self.assertEqual(self.helper.Scan(self.helper,'party1',self.caps).kind,'unknown')
        self.assertEqual(self.lua.globals().CALLS,0)
    def test_nil_end_clear_but_error_or_secret_unknown(self):
        self.assertEqual(self.helper.Scan(self.helper,'party1',self.caps).kind,'clear')
        for code in ("AURAS={{dispelName={secret=true}}}","AURAS={{secret=true}}", "function C_UnitAuras.GetAuraDataByIndex() error('restricted') end"):
            self.lua.execute(code)
            self.assertEqual(self.helper.Scan(self.helper,'party1',self.caps).kind,'unknown')
    def test_no_known_cure_and_bounded_scan(self):
        self.assertEqual(self.helper.Scan(self.helper,'party1',self.lua.table()).kind,'none')
        self.lua.execute("function C_UnitAuras.GetAuraDataByIndex() CALLS=CALLS+1; return {dispelName='Magic'} end")
        self.assertEqual(self.helper.Scan(self.helper,'party1',self.caps).kind,'unknown')
        self.assertLessEqual(self.lua.globals().CALLS,40)

    def test_cache_never_carries_clean_state_into_combat_or_reused_name(self):
        row=self.lua.table()
        self.lua.execute('NOW=1; function GetTime() return NOW end')
        self.assertEqual(self.helper.Update(self.helper,row,'party1','First',self.caps).kind,'clear')
        self.lua.execute("AURAS={{dispelName='Poison'}}")
        self.assertEqual(self.helper.Update(self.helper,row,'party1','Second',self.caps).kind,'found')
        self.lua.execute('COMBAT=true')
        calls=self.lua.globals().CALLS
        self.assertEqual(self.helper.Update(self.helper,row,'party1','Second',self.caps).kind,'unknown')
        self.assertEqual(self.lua.globals().CALLS,calls)
        self.lua.execute('COMBAT=false')
        self.assertEqual(self.helper.Update(self.helper,row,'party1',None,self.caps).kind,'unknown')

    def test_tooltip_matches_configured_cure_click(self):
        self.lua.execute("LINES={}; GameTooltip={AddLine=function(self,s) table.insert(LINES,s) end}")
        data=self.lua.table_from({'kind':'found','dispel':'Poison','spell':self.caps.Poison})
        self.helper.Tooltip(self.helper,self.lua.table_from({'dispelData':data}),self.lua.table_from({'healLeftID':331,'healRightID':526}))
        self.assertIn('Shift-right click',self.lua.globals().LINES[1])
