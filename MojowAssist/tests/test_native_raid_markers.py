import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class NativeRaidMarkerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.ns = self.lua.table()
        self.lua.execute((ROOT / 'tests/wow_stub.lua').read_text())
        for name in ('EnemyRoster.lua', 'NativeRaidMarker.lua', 'EnemyPanel.lua'):
            if (ROOT / name).exists():
                self.lua.execute((ROOT / name).read_text(), 'MojowAssist', self.ns)
        self.lua.execute('''
            MARK={secret=true}
            function GetRaidTargetIndex(unit) MARK_UNIT=unit; return MARK end
        ''')
        self.panel = self.lua.table_from({'roster': self.ns.EnemyRoster.Create(self.ns.EnemyRoster)})
        self.row = self.lua.eval('CreateFrame')( 'Button', None, None, 'SecureActionButtonTemplate')
        self.row.raidIcon = self.row.CreateTexture(self.row)
        self.row.raidIcon.SetSpriteSheetCell = self.lua.eval('''function(self,value,rows,columns)
            self.cell=value; self.sheetRows=rows; self.sheetColumns=columns
        end''')
        self.row.raidIcon.SetTexture = self.lua.eval('function(self,path) self.path=path end')

    def refresh(self, unit='nameplate1'):
        self.ns.EnemyPanel.RefreshRaidIcon(self.panel, self.row, unit)

    def test_opaque_marker_goes_directly_to_native_texture_for_each_row_token(self):
        for unit in ('nameplate1', 'focustarget', 'party1'):
            self.refresh(unit)
            self.assertTrue(self.row.raidIcon.shown)
            self.assertTrue(self.lua.eval('rawequal')(self.row.raidIcon.cell, self.lua.globals().MARK))
            self.assertEqual(self.lua.globals().MARK_UNIT, unit)
            self.assertEqual((self.row.raidIcon.sheetRows, self.row.raidIcon.sheetColumns), (4, 4))
            self.assertEqual(self.row.raidIcon.path, r'Interface\TargetingFrame\UI-RaidTargetingIcons')

    def test_opaque_marker_never_reaches_legacy_helper_or_indexed_asset_fallback(self):
        self.row.raidIcon.SetSpriteSheetCell = None
        self.lua.execute('HELPER_CALLS=0; function SetRaidTargetIconTexture() HELPER_CALLS=HELPER_CALLS+1 end')
        self.refresh()
        self.assertFalse(self.row.raidIcon.shown)
        self.assertEqual(self.lua.globals().HELPER_CALLS, 0)

    def test_native_failure_and_removed_marker_clear_previous_display(self):
        self.refresh()
        self.assertTrue(self.row.raidIcon.shown)
        self.row.raidIcon.SetSpriteSheetCell = self.lua.eval('function() error("native unavailable") end')
        self.refresh()
        self.assertFalse(self.row.raidIcon.shown)
        self.lua.execute('MARK=nil')
        self.refresh()
        self.assertFalse(self.row.raidIcon.shown)

    def test_combat_marker_refresh_does_not_change_row_bindings(self):
        self.row.SetAttribute(self.row, 'unit', 'nameplate1')
        self.row.SetAttribute(self.row, 'type1', 'target')
        before = dict(self.row.attrs.items())
        self.lua.execute('COMBAT=true')
        self.refresh()
        self.assertTrue(self.row.raidIcon.shown)
        self.assertEqual(dict(self.row.attrs.items()), before)
