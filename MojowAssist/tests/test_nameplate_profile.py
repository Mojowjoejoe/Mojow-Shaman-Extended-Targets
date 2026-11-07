import unittest
import test_visibility

class NameplateProfileTests(unittest.TestCase):
    def bitfields(self):
        self.lua.execute('''
            Enum.NamePlateInfoDisplay={CurrentHealthPercent=1}
            Enum.NamePlateCastBarDisplay={SpellName=1,SpellIcon=2}
            Enum.NamePlateThreatDisplay={Progressive=1,Flash=2,HealthBarColor=3}
            CVARS.nameplateInfoDisplay='@D'; CVARS.nameplateCastBarDisplay='@R'; CVARS.nameplateThreatDisplay='@`'
            BITS={nameplateInfoDisplay={[1]=false,[3]=true},
                nameplateCastBarDisplay={[1]=false,[2]=true,[5]=true},
                nameplateThreatDisplay={[1]=false,[2]=false,[3]=false,[6]=true}}
            C_CVar.GetCVarBitfield=function(k,i) if BITS[k] then return BITS[k][i] or false end end
            C_CVar.SetCVarBitfield=function(k,i,v) WRITES=WRITES+1; BITS[k][i]=v end
        ''')

    def test_native_bits_preserve_unrelated_choices_and_restore(self):
        self.bitfields()
        self.profile.Apply(self.profile)
        bits=self.lua.globals().BITS
        self.assertTrue(bits.nameplateInfoDisplay[1])
        self.assertTrue(bits.nameplateCastBarDisplay[1])
        self.assertTrue(bits.nameplateThreatDisplay[3])
        self.assertFalse(bits.nameplateThreatDisplay[2])
        self.assertTrue(bits.nameplateInfoDisplay[3])
        self.assertTrue(bits.nameplateCastBarDisplay[5])
        self.lua.execute('BITS.nameplateThreatDisplay[6]=false')
        self.profile.Restore(self.profile)
        self.assertFalse(bits.nameplateInfoDisplay[1])
        self.assertTrue(bits.nameplateCastBarDisplay[2])
        self.assertFalse(bits.nameplateThreatDisplay[6])

    def test_bit_restore_survives_reload_and_respects_manual_changes(self):
        self.bitfields(); self.profile.Apply(self.profile); self.profile.Apply(self.profile)
        from test_visibility import ROOT
        self.lua.execute((ROOT/'Model.lua').read_text(),'MojowAssist',self.ns)
        db=self.lua.globals().TEST_ADDON.db
        self.lua.globals().TEST_ADDON.db=self.ns.Model.Normalize(self.ns.Model,db)
        self.lua.execute('BITS.nameplateInfoDisplay[1]=false; WRITES=0')
        self.profile.Restore(self.profile)
        self.assertFalse(self.lua.globals().BITS.nameplateInfoDisplay[1])
        self.assertFalse(self.lua.globals().BITS.nameplateCastBarDisplay[1])

    def test_bit_api_missing_or_rejected_reports_and_never_writes_raw_mask(self):
        self.bitfields()
        self.lua.execute('C_CVar.SetCVarBitfield=nil')
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertIn('nameplateInfoDisplay',self.lua.globals().TEST_ADDON.lastMessage)
        self.assertEqual(self.lua.globals().CVARS.nameplateInfoDisplay,'@D')
        self.lua.execute('C_CVar.SetCVarBitfield=function() end')
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertFalse(self.lua.globals().BITS.nameplateInfoDisplay[1])

    def test_bits_missing_enum_and_restricted_read_are_unavailable(self):
        self.bitfields()
        self.lua.execute('Enum.NamePlateInfoDisplay=nil; C_CVar.GetCVarBitfield=function() error("restricted") end')
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertIn('unavailable',self.profile.Status(self.profile))
        self.assertFalse(self.lua.globals().BITS.nameplateInfoDisplay[1])

    def test_partial_restore_then_reapply_retains_original_bit_history(self):
        self.bitfields(); self.profile.Apply(self.profile)
        self.lua.execute('''C_CVar.SetCVarBitfield=function(k,i,v)
            BITS[k][i]=v; error('changed then failed') end''')
        self.assertFalse(self.profile.Restore(self.profile))
        self.lua.execute('C_CVar.SetCVarBitfield=function(k,i,v) BITS[k][i]=v end')
        self.profile.Apply(self.profile)
        self.profile.Restore(self.profile)
        self.assertFalse(self.lua.globals().BITS.nameplateInfoDisplay[1])

    def test_status_fits_single_short_feedback_line(self):
        self.lua.execute('Enum=nil')
        self.assertLessEqual(len(self.profile.Status(self.profile)),49)

    def test_bits_no_startup_status_or_combat_writes(self):
        self.bitfields(); self.profile.Status(self.profile)
        self.assertEqual(self.lua.globals().WRITES,0)
        self.lua.execute('COMBAT=true')
        self.profile.Apply(self.profile); self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().WRITES,0)

    def test_absent_bitfield_cvar_is_not_created(self):
        self.bitfields()
        self.lua.execute('CVARS.nameplateInfoDisplay=nil')
        self.profile.Apply(self.profile)
        self.assertFalse(self.lua.globals().BITS.nameplateInfoDisplay[1])
        self.assertIn('nameplateInfoDisplay',self.lua.globals().TEST_ADDON.lastMessage)
    def setUp(self):
        test_visibility.VisibilityTests.setUp(self)
        from test_visibility import ROOT
        self.lua.execute((ROOT/'NameplateProfile.lua').read_text(),'MojowAssist',self.ns)
        self.lua.execute("TEST_ADDON.db={}; Enum={NamePlateStyle={Block=4},NamePlateSize={Small=1}}; CVARS.nameplateStyle='0'; CVARS.nameplateSize='2'")
        self.profile=self.ns.NameplateProfile.Create(self.ns.NameplateProfile,self.lua.globals().TEST_ADDON,self.panel)

    def test_apply_restore_and_numeric_readback(self):
        self.profile.Apply(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'4')
        self.lua.execute("CVARS.nameplateStyle='4.0'")
        self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'0')

    def test_user_changes_survive_restore(self):
        self.profile.Apply(self.profile)
        self.lua.execute("CVARS.nameplateStyle='3'")
        self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'3')

    def test_repeat_apply_keeps_original_and_combat_no_writes(self):
        self.profile.Apply(self.profile)
        self.profile.Apply(self.profile)
        self.lua.execute('COMBAT=true; WRITES=0')
        self.profile.Restore(self.profile)
        self.profile.Apply(self.profile)
        self.assertEqual(self.lua.globals().WRITES,0)
        self.lua.execute('COMBAT=false')
        self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'0')

    def test_failed_restore_retains_intent_and_reload_retains_backup(self):
        self.profile.Apply(self.profile)
        self.lua.execute('function C_CVar.SetCVar() end')
        self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().TEST_ADDON.db.nameplateRestore.nameplateStyle.before,'0')
        from test_visibility import ROOT
        self.lua.execute((ROOT/'Model.lua').read_text(),'MojowAssist',self.ns)
        normalized=self.ns.Model.Normalize(self.ns.Model,self.lua.globals().TEST_ADDON.db)
        self.assertEqual(normalized.nameplateRestore.nameplateStyle.before,'0')

    def test_no_automatic_writes_and_missing_enum_skips_style(self):
        self.assertEqual(self.lua.globals().WRITES,0)
        self.lua.execute('Enum=nil')
        self.profile.Apply(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'0')

    def test_rejected_write_reports_and_unknown_value_can_retry_restore(self):
        self.lua.execute('function C_CVar.SetCVar() end')
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertIn('rejected', self.lua.globals().TEST_ADDON.lastMessage)
        self.lua.execute('CVARS.nameplateStyle=nil')
        self.assertFalse(self.profile.Restore(self.profile))
        self.assertEqual(self.lua.globals().TEST_ADDON.db.nameplateRestore.nameplateStyle.before,'0')

    def test_ui_opens_without_applying_preset(self):
        self.lua.globals().TEST_ADDON.nameplates=self.profile
        self.panel.Toggle(self.panel)
        self.assertEqual(self.lua.globals().WRITES,0)
        self.assertIn('match',self.panel.plateStatus.text)

    def test_clamped_write_restores_actual_change(self):
        self.lua.execute("function C_CVar.SetCVar(k,v) if k=='nameplateStyle' and v=='4' then CVARS[k]='3' else CVARS[k]=v end end")
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'3')
        self.profile.Restore(self.profile)
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'0')

    def test_missing_enums_report_native_layout_unavailable(self):
        self.lua.execute('Enum=nil')
        self.assertFalse(self.profile.Apply(self.profile))
        self.assertIn('native Block style',self.lua.globals().TEST_ADDON.lastMessage)
        self.assertIn('unavailable',self.profile.Status(self.profile))

    def test_partially_restored_setting_can_retry(self):
        self.profile.Apply(self.profile)
        self.lua.execute("function C_CVar.SetCVar(k,v) if k=='nameplateStyle' then CVARS[k]='2' else CVARS[k]=v end end")
        self.assertFalse(self.profile.Restore(self.profile))
        self.assertEqual(self.lua.globals().TEST_ADDON.db.nameplateRestore.nameplateStyle.applied,'2')
        self.lua.execute('function C_CVar.SetCVar(k,v) CVARS[k]=v end')
        self.assertTrue(self.profile.Restore(self.profile))
        self.assertEqual(self.lua.globals().CVARS.nameplateStyle,'0')

    def test_current_client_preset_has_no_obsolete_friends_requirement(self):
        self.bitfields()
        self.lua.globals().PROFILE=self.profile
        self.lua.execute("""
            for name in pairs(PROFILE:Targets()) do CVARS[name]='0' end
            CVARS.nameplateShowFriends=nil
            local original=C_CVar.SetCVar
            C_CVar.SetCVar=function(name,value)
                assert(name~='nameplateShowFriends','obsolete setting write')
                original(name,value)
            end
        """)
        self.assertTrue(self.profile.Apply(self.profile))
        self.assertEqual(self.profile.Status(self.profile),'19/19 settings match.')
        self.assertEqual(self.lua.globals().CVARS.nameplateShowFriendlyPlayers,'1')
        self.assertTrue(self.profile.Restore(self.profile))
        self.assertEqual(self.lua.globals().CVARS.nameplateShowFriendlyPlayers,'0')
