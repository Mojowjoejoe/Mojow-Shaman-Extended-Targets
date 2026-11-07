from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.ns=self.lua.table()
        self.lua.execute((ROOT/'Appearance.lua').read_text(),'MojowAssist',self.ns)
        self.appearance=self.ns.Appearance

    def test_live_and_future_backgrounds_follow_saved_slider_without_fading_content(self):
        db=self.lua.table_from({'windowTransparency':25})
        self.appearance.Configure(self.appearance,db)
        frame=self.lua.globals().CreateFrame('Button',None,None,'SecureActionButtonTemplate,BackdropTemplate')
        texture=self.lua.globals().CreateFrame('Frame')
        self.appearance.Background(self.appearance,frame,0.1,0.2,0.3,0.94)
        self.appearance.Background(self.appearance,texture,0.1,0.2,0.3,0.94,True)
        self.assertAlmostEqual(frame.fill[4],0.94*0.75)
        self.lua.execute('COMBAT=true')
        self.appearance.SetTransparency(self.appearance,70)
        self.assertEqual(db.windowTransparency,70)
        self.assertAlmostEqual(frame.fill[4],0.94*0.3)
        self.assertAlmostEqual(texture.fill[4],0.94*0.75)
        self.assertTrue(self.appearance.pending)
        self.lua.execute('COMBAT=false')
        self.appearance.events.scripts.OnEvent(self.appearance.events,'PLAYER_REGEN_ENABLED')
        self.assertAlmostEqual(texture.fill[4],0.94*0.3)
        self.assertIsNone(frame.alpha)
        self.appearance.Background(self.appearance,frame,0.2,0.8,0.8,0.94)
        self.assertAlmostEqual(frame.fill[4],0.94*0.3)
        self.appearance.SetTransparency(self.appearance,100)
        self.assertEqual(frame.fill[4],0)
        self.appearance.SetTransparency(self.appearance,0)
        self.assertAlmostEqual(frame.fill[4],0.94)

    def test_one_rejected_background_does_not_abort_others_and_can_retry(self):
        self.appearance.Configure(self.appearance,self.lua.table())
        bad=self.lua.eval("{SetColorTexture=function() error('restricted texture') end}")
        good=self.lua.globals().CreateFrame('Frame')
        self.appearance.Background(self.appearance,bad,0,0,0,1,True)
        self.appearance.Background(self.appearance,good,0,0,0,1)
        self.appearance.SetTransparency(self.appearance,80)
        self.assertAlmostEqual(good.fill[4],0.2)
        self.assertTrue(self.appearance.pending)
        bad.SetColorTexture=self.lua.eval('function(self,r,g,b,a) self.result=a end')
        self.appearance.events.scripts.OnEvent(self.appearance.events,'PLAYER_REGEN_ENABLED')
        self.assertAlmostEqual(bad.result,0.2)
        self.assertFalse(self.appearance.pending)
