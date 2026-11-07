import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True); self.ns=self.lua.table()
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute("""
            MINE=25; OTHER=90; MAX=100; DEAD=false; FRIEND=true; EXISTS=true
            Enum=Enum or {}; Enum.UnitIncomingHealClampMode={MissingHealth=2}
            function UnitExists() return EXISTS end
            function UnitCanAssist() return FRIEND end
            function UnitIsDeadOrGhost() return DEAD end
            function CreateUnitHealPredictionCalculator()
                return {SetIncomingHealClampMode=function(self,x) self.clamp=x end,
                    SetIncomingHealOverflowPercent=function(self,x) self.overflow=x end,
                    GetMaximumHealth=function() return MAX end,
                    GetIncomingHeals=function() return OTHER,MINE,0,false end}
            end
            function UnitGetDetailedHealPrediction(unit,healer,c) LAST_UNIT=unit; LAST_HEALER=healer end
            ROW={health=CreateFrame('StatusBar'),value=CreateFrame('Frame')}
            ROW.health:SetSize(200,19); TEX={}
            function ROW.health:SetStatusBarTexture(path) self.statusTexturePath=path end
            local originalCreateFrame=CreateFrame
            function CreateFrame(...)
                local frame=originalCreateFrame(...)
                function frame:SetStatusBarTexture(path) self.statusTexturePath=path end
                return frame
            end
            function ROW.health:GetStatusBarTexture() return TEX end
        """)
        self.lua.execute((ROOT/'HealPrediction.lua').read_text(),'MojowAssist',self.ns)
        self.p=self.ns.HealPrediction; self.row=self.lua.globals().ROW; self.p.Create(self.p,self.row)
    def update(self): self.p.Update(self.p,self.row,'party1')
    def test_own_estimate_and_native_clamp_config(self):
        self.update(); e=self.row.incomingHeal
        self.assertEqual(e.bar.value,25); self.assertEqual(self.row.value.format,'+%.0f'); self.assertEqual(self.row.value.formattedValue,25)
        self.assertEqual(e.calculator.clamp,2); self.assertEqual(e.calculator.overflow,1)
        self.assertEqual(self.lua.globals().LAST_HEALER,'player')
        self.assertEqual(self.lua.globals().LAST_UNIT,'party1')
    def test_visible_texture_uses_valid_asset_path(self):
        self.assertEqual(self.row.incomingHeal.bar.statusTexturePath, r'Interface\Buttons\WHITE8X8')
    def test_cancel_or_zero_clears(self):
        self.update(); self.lua.execute('MINE=0'); self.update(); self.assertFalse(self.row.incomingHeal.bar.shown)
    def test_unavailable_dead_or_hostile_clears(self):
        for code in ['DEAD=true','FRIEND=false','EXISTS=false']:
            self.lua.execute('DEAD=false; FRIEND=true; EXISTS=true'); self.update()
            self.lua.execute(code); self.update(); self.assertFalse(self.row.incomingHeal.bar.shown)
    def test_restricted_amount_forwarded_without_numeric_label(self):
        self.lua.execute('MINE={secret=true}; MAX={secret=true}; ROW.value:SetText("50%")')
        self.update(); self.assertTrue(self.row.incomingHeal.bar.shown)
        self.assertTrue(self.row.incomingHeal.bar.value.secret); self.assertEqual(self.row.value.text,'50%')
        self.assertIsNone(self.row.incomingHealAmount)
    def test_failure_clears_previous_heal(self):
        self.update(); self.lua.execute('UnitGetDetailedHealPrediction=function() error("unavailable") end')
        self.update(); self.assertFalse(self.row.incomingHeal.bar.shown)
    def test_combat_updates_without_click_changes(self):
        self.lua.execute('COMBAT=true'); self.update(); self.assertTrue(self.row.incomingHeal.bar.shown)
    def test_no_calculator_has_no_fake_estimate(self):
        self.lua.execute('CreateUnitHealPredictionCalculator=nil')
        other=self.lua.table(); self.p.Create(self.p,other); self.assertIsNone(other.incomingHeal)
