from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'MojowAssist' if (ROOT / 'MojowAssist').is_dir() else ROOT

class ModelTests(unittest.TestCase):
    def test_totem_anchor_migration_flag_is_explicit_and_persists(self):
        self.assertFalse(self.model.Normalize(self.model,self.lua.table()).totemTopLeft)
        saved=self.lua.table_from({'totemTopLeft':True,'totemX':-120,'totemY':230})
        loaded=self.model.Normalize(self.model,saved)
        self.assertTrue(loaded.totemTopLeft)
        self.assertEqual(loaded.totemX,-120)
        self.assertEqual(loaded.totemY,230)
        self.assertFalse(self.model.Normalize(self.model,self.lua.table_from({'totemTopLeft':'true'})).totemTopLeft)

    def test_section_options_persist(self):
        keys=('enemyShowGroup','enemyShowNPCs','enemyShowEnemyPlayers','enemyShowFriendlyPlayers')
        defaults=self.model.Normalize(self.model,self.lua.table())
        for key in keys: self.assertTrue(defaults[key])
        saved=self.lua.table_from({key:False for key in keys})
        normalized=self.model.Normalize(self.model,saved)
        reloaded=self.model.Normalize(self.model,normalized)
        for key in keys: self.assertFalse(reloaded[key])

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.ns = self.lua.table()
        source = ADDON / 'Model.lua'
        self.assertTrue(source.exists(), 'Model implementation is missing')
        self.lua.execute(source.read_text(), 'MojowAssist', self.ns)
        self.model = self.ns.Model

    def test_auto_default_preserves_legacy_manual_master(self):
        self.assertEqual(self.model.Normalize(self.model,self.lua.table()).mode,'auto')
        self.assertEqual(self.model.Normalize(self.model,self.lua.table_from({'master':'Lead-Realm'})).mode,'group')

    def test_corrupt_preferences_are_normalized(self):
        s = self.model.Normalize(self.model, self.lua.table_from({'scale': 'bad', 'x': float('inf'), 'locked': 'yes'}))
        self.assertEqual(s.scale, 0.7)
        self.assertEqual(s.x, 0)
        self.assertTrue(s.locked)
        self.assertTrue(s.visible)

    def test_appearance_clamps_and_preserves_false(self):
        s = self.model.Normalize(self.model, self.lua.table_from({'scale': 9, 'x': -99999, 'visible': False, 'followLeader': False}))
        self.assertEqual(s.scale, 1.6)
        self.assertEqual(s.x, -4000)
        self.assertFalse(s.visible)
        self.assertFalse(s.followLeader)

    def test_find_minerals_defaults_on_and_saved_off_survives_normalization(self):
        self.assertTrue(self.model.Normalize(self.model,self.lua.table()).autoFindMinerals)
        result=self.model.Normalize(self.model,self.lua.table_from({'autoFindMinerals':False}))
        self.assertFalse(self.model.Normalize(self.model,result).autoFindMinerals)

    def test_window_transparency_saved_clamped_and_nan_rejected(self):
        for value,expected in ((45,45),(200,100),(-5,0),(float('nan'),0),('bad',0)):
            normalized=self.model.Normalize(self.model,self.lua.table_from({'windowTransparency':value}))
            self.assertEqual(normalized.windowTransparency,expected)
            self.assertEqual(self.model.Normalize(self.model,normalized).windowTransparency,expected)

    def test_requires_full_name_and_rejects_control_or_delimiter(self):
        for bad in ['', 'Bob', 'Bob-Realm|X', 'Bob-Realm\n', 'party1', 'Bob Realm', 'x'*201, 'Bob--Realm']:
            self.assertFalse(self.model.ValidateName(self.model, bad), bad)
        self.assertTrue(self.model.ValidateName(self.model, 'Mójow-Area52'))

    def test_protocol_accepts_only_leader_and_known_master(self):
        roster = self.lua.table_from({'Lead-Realm': 'party1', 'Friend-Realm': 'party2'})
        self.assertEqual(self.model.Decode(self.model, '1|SET|Friend-Realm', 'Lead-Realm', 'Lead-Realm', roster), 'Friend-Realm')
        for msg,sender in [('1|SET|Friend-Realm','Other-Realm'), ('2|SET|Friend-Realm','Lead-Realm'), ('1|SET|Missing-Realm','Lead-Realm'), ('1|SET|Friend-Realm|extra','Lead-Realm'), ('X'*256,'Lead-Realm')]:
            self.assertIsNone(self.model.Decode(self.model, msg, sender, 'Lead-Realm', roster))

    def test_minimap_angle_survives_saved_settings_reload(self):
        s = self.model.Normalize(self.model, self.lua.table_from({'minimapAngle':90}))
        self.assertEqual(s.minimapAngle,90)
        self.assertEqual(self.model.Normalize(self.model,self.lua.table()).minimapAngle,225)

    def test_realm_punctuation_is_supported(self):
        self.assertTrue(self.model.ValidateName(self.model, "Mojow-Quel'Thalas"))
        self.assertTrue(self.model.ValidateName(self.model, 'Mojow-Azjol-Nerub'))
        self.assertFalse(self.model.ValidateName(self.model, 'Mojow-Realm|SET'))

    def test_encode_rejects_invalid_names(self):
        self.assertEqual(self.model.Encode(self.model, 'Friend-Realm'), '1|SET|Friend-Realm')
        self.assertIsNone(self.model.Encode(self.model, 'party1'))


class RuntimeTests(unittest.TestCase):
    def test_group_poison_trial_toggle_defaults_off_and_rejects_combat(self):
        self.assertFalse(self.app.db.groupNativePoison)
        self.app.minimap.ToggleMenu(self.app.minimap)
        check=self.app.minimap.poisonCheck
        check.scripts.OnClick(check)
        self.assertTrue(self.app.db.groupNativePoison)
        self.lua.execute('COMBAT=true')
        check.checked=False
        check.scripts.OnClick(check)
        self.assertTrue(self.app.db.groupNativePoison)
        self.assertTrue(check.checked)
        self.lua.execute('COMBAT=false')
        check.scripts.OnClick(check)
        self.assertFalse(self.app.db.groupNativePoison)

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute("MojowAssistDB={mode='group'}")
        self.ns = self.lua.table()
        for name in ['Appearance.lua', 'Model.lua', 'Panel.lua', 'AssistAction.lua', 'MinimapButton.lua', 'EnemyRoster.lua', 'NativeRaidMarker.lua', 'EnemyPanel.lua', 'NativeShieldDisplay.lua', 'ShieldHelper.lua', 'GhostWolf.lua', 'VisibilityOptions.lua', 'NameplateProfile.lua', 'TotemModel.lua', 'TotemPanel.lua', 'Runtime.lua']:
            path=ADDON/name
            self.assertTrue(path.exists(), name+' implementation is missing')
            self.lua.execute(path.read_text(), 'MojowAssist', self.ns)
        self.app=self.ns.Addon
        self.app.Initialize(self.app)

    def test_transparency_slider_updates_existing_and_later_windows_in_combat(self):
        slider=self.app.panel.transparency
        original=self.app.panel.assist.attrs.unit
        self.lua.execute('COMBAT=true')
        slider.scripts.OnValueChanged(slider,60)
        self.assertEqual(self.app.db.windowTransparency,60)
        self.assertEqual(self.lua.globals().MojowAssistDB.windowTransparency,60)
        self.assertAlmostEqual(self.app.panel.frame.fill[4],0.95*0.4)
        self.assertAlmostEqual(self.app.panel.settings.fill[4],0.95*0.4)
        self.assertAlmostEqual(self.app.enemies.frame.fill[4],0.94*0.4)
        self.assertEqual(self.app.panel.assist.attrs.unit,original)
        self.assertIn('60%',self.app.panel.transparencyLabel.text)
        self.app.visibility.Toggle(self.app.visibility)
        self.assertAlmostEqual(self.app.visibility.frame.fill[4],0.98*0.4)
        self.app.panel.Refresh(self.app.panel)
        self.assertAlmostEqual(self.app.panel.masterCard.fill[4],0.96*0.4)

    def test_select_builds_native_unit_action(self):
        self.assertTrue(self.app.SelectMaster(self.app,'Friend-Realm'))
        self.assertEqual(self.app.panel.assist.attrs.unit, 'party2')
        self.assertEqual(self.app.panel.assist.attrs.type, 'assist')

    def test_combat_selection_waits_for_combat_end(self):
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.lua.globals().COMBAT=True
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.assertEqual(self.app.panel.assist.attrs.unit, 'party1')
        self.assertEqual(self.app.pendingMaster, 'Friend-Realm')
        self.lua.globals().COMBAT=False
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.app.panel.assist.attrs.unit, 'party2')

    def test_roster_reorder_does_not_change_assist_identity(self):
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.lua.execute("COMBAT=true; ROSTER.party1={'Other','Realm'}; ROSTER.party2={'Lead','Realm'}")
        self.app.OnEvent(self.app,'GROUP_ROSTER_UPDATE')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')
        self.assertTrue(self.app.rosterDirty)
        self.lua.globals().COMBAT=False
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.app.displayUnit,'party2')

    def test_missing_master_disables_action_outside_combat(self):
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.lua.execute('ROSTER.party2=nil')
        self.app.OnEvent(self.app,'GROUP_ROSTER_UPDATE')
        self.assertIsNone(self.app.panel.assist.attrs.type)

    def test_selected_conflicting_key_is_reassigned(self):
        self.lua.execute("BINDINGS.F='INTERACTTARGET'")
        self.assertTrue(self.app.Bind(self.app,'F'))
        self.assertEqual(self.lua.globals().BINDINGS.F,'CLICK MojowAssistButton:LeftButton')
        self.assertTrue(self.app.Bind(self.app,'F8'))
        self.assertEqual(self.lua.globals().BINDINGS.F8,'CLICK MojowAssistButton:LeftButton')

    def test_leader_messages_and_manual_override(self):
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Friend-Realm','PARTY','Lead-Realm')
        self.assertEqual(self.app.db.master,'Friend-Realm')
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Friend-Realm','PARTY','Lead-Realm')
        self.assertEqual(self.app.db.master,'Lead-Realm')

    def test_untrusted_and_combat_messages_are_ignored(self):
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Friend-Realm','PARTY','Friend-Realm')
        self.assertIsNone(self.app.db.master)
        self.lua.globals().COMBAT=True
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Friend-Realm','PARTY','Lead-Realm')
        self.assertIsNone(self.app.db.master)

    def test_only_leader_can_share_and_never_in_combat(self):
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.assertFalse(self.app.Share(self.app))
        self.lua.globals().LEADER='player'
        self.app.Reconcile(self.app)
        self.assertTrue(self.app.Share(self.app))
        self.assertEqual(len(self.lua.globals().SENT),1)
        self.lua.globals().COMBAT=True
        self.assertFalse(self.app.Share(self.app))
        self.assertEqual(len(self.lua.globals().SENT),1)

    def test_settings_defer_protected_layout(self):
        self.lua.globals().COMBAT=True
        self.app.SetOption(self.app,'visible',False)
        self.app.SetOption(self.app,'scale',1.4)
        self.assertTrue(self.app.panel.frame.shown)
        self.lua.globals().COMBAT=False
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertFalse(self.app.panel.frame.shown)
        self.assertEqual(self.app.panel.frame.scale,1.4)

    def test_changed_leader_invalidates_old_authority(self):
        self.lua.globals().LEADER='party2'
        self.app.OnEvent(self.app,'PARTY_LEADER_CHANGED')
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Lead-Realm','PARTY','Lead-Realm')
        self.assertIsNone(self.app.db.master)
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Lead-Realm','PARTY','Friend-Realm')
        self.assertEqual(self.app.db.master,'Lead-Realm')

    def test_unknown_send_result_does_not_claim_success(self):
        self.lua.execute("LEADER='player'; Enum.SendAddonMessageResult=nil; C_ChatInfo.SendAddonMessage=function() return nil end")
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.assertFalse(self.app.Share(self.app))

    def test_secret_target_text_is_passed_to_display_without_inspection(self):
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.lua.execute("SECRET={secret=true}; UnitName=function() return SECRET end")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertTrue(self.app.panel.target.text.secret)

    def test_settings_can_open_during_combat(self):
        self.lua.globals().COMBAT=True
        self.app.panel.OpenSettings(self.app.panel)
        self.assertTrue(self.app.panel.settings.shown)

    def test_pending_master_who_left_is_not_applied(self):
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.lua.globals().COMBAT=True
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.lua.execute('ROSTER.party2=nil; COMBAT=false')
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')
        self.assertIsNone(self.app.pendingMaster)

    def test_drag_released_in_combat_finishes_after_combat(self):
        self.app.SetOption(self.app,'locked',False)
        self.app.panel.frame.scripts.OnDragStart()
        self.lua.globals().COMBAT=True
        self.app.panel.frame.scripts.OnDragStop()
        self.lua.globals().COMBAT=False
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertFalse(self.app.panel.frame.moving)

    def test_assist_dispatch_uses_existing_group_unit(self):
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.assertTrue(self.lua.globals().NativeDispatch(self.app.panel.assist))
        self.assertEqual(self.lua.globals().ASSISTED_UNIT,'party2')

    def test_native_roster_update_retargets_secure_action_in_combat(self):
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.lua.execute("COMBAT=true; ROSTER.party1={'Other','Realm'}; ROSTER.party2={'Lead','Realm'}")
        self.lua.globals().UpdateNativeHeader(self.app.action.header)
        self.assertEqual(self.app.panel.assist.attrs.unit,'party2')
        self.lua.execute('ROSTER.party2=nil')
        self.lua.globals().UpdateNativeHeader(self.app.action.header)
        self.assertEqual(self.app.panel.assist.attrs.unit,'none')
        self.assertIsNone(self.app.panel.assist.attrs.type)

    def test_minimap_click_opens_settings(self):
        self.app.panel.settings.Hide(self.app.panel.settings)
        self.app.minimap.button.scripts.OnClick(self.app.minimap.button,'LeftButton')
        self.assertTrue(self.app.panel.settings.shown)

    def test_minimap_right_click_toggles_sections_in_combat(self):
        self.app.panel.settings.Hide(self.app.panel.settings)
        self.app.minimap.button.scripts.OnClick(self.app.minimap.button,'RightButton')
        self.assertTrue(self.app.minimap.menu.shown)
        self.assertFalse(self.app.panel.settings.shown)
        self.lua.globals().COMBAT=True
        for index,key in enumerate(('enemyShowGroup','enemyShowNPCs','enemyShowEnemyPlayers','enemyShowFriendlyPlayers'),1):
            check=self.app.minimap.menuOptions[index]
            check.scripts.OnClick(check)
            self.assertFalse(self.app.db[key])
            self.assertFalse(check.checked)
        self.app.minimap.button.scripts.OnClick(self.app.minimap.button,'RightButton')
        self.assertFalse(self.app.minimap.menu.shown)

    def test_minimap_drag_saves_angle_and_moves_button(self):
        self.lua.execute('CURSOR_X=500; CURSOR_Y=600')
        self.app.minimap.button.scripts.OnDragStart()
        self.app.minimap.button.scripts.OnUpdate(self.app.minimap.button,0.1)
        self.app.minimap.button.scripts.OnDragStop()
        self.assertAlmostEqual(self.app.db.minimapAngle,90)
        self.assertAlmostEqual(self.app.minimap.button.point[4],0,places=6)
        self.assertGreater(self.app.minimap.button.point[5],0)

    def test_focus_assist_works_without_group(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.lua.execute("ROSTER.party1=nil; ROSTER.party2=nil; ROSTER.focus={'Stranger','Elsewhere'}")
        self.app.SetMode(self.app,'focus')
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.assertTrue(self.lua.globals().NativeDispatch(self.app.panel.assist))
        self.assertEqual(self.lua.globals().ASSISTED_UNIT,'focus')

    def test_set_focus_button_uses_native_focus_action(self):
        self.assertIsNotNone(self.app.panel.setFocus,'Set Focus button missing')
        self.assertEqual(self.app.panel.setFocus.attrs.type,'focus')
        self.assertEqual(self.app.panel.setFocus.attrs.unit,'target')
        self.app.panel.setFocus.scripts.PostClick(self.app.panel.setFocus,'LeftButton',False)
        self.assertEqual(self.app.db.mode,'focus')

    def test_group_tracker_cannot_overwrite_focus_action_in_combat(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.app.SetMode(self.app,'focus')
        self.lua.globals().COMBAT=True
        self.lua.globals().UpdateNativeHeader(self.app.action.header)
        self.app.OnEvent(self.app,'GROUP_ROSTER_UPDATE')
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.assertEqual(self.app.panel.assist.attrs.type,'assist')

    def test_group_selection_exits_focus(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.app.SetMode(self.app,'focus')
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.assertEqual(self.app.db.mode,'group')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party2')

    def test_latest_queued_mode_choice_wins(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.app.SelectMaster(self.app,'Lead-Realm')
        self.lua.globals().COMBAT=True
        self.app.SelectMaster(self.app,'Friend-Realm')
        self.app.SetMode(self.app,'focus')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')
        self.lua.globals().COMBAT=False
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.assertIsNone(self.app.pendingMaster)

    def test_focus_portraits_track_focus_and_its_target(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.lua.execute("ROSTER.focus={'Stranger','Elsewhere'}")
        self.app.SetMode(self.app,'focus')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.masterPortrait.unit,'focus')
        self.assertEqual(self.app.panel.targetPortrait.unit,'focustarget')

    def test_missing_focus_never_falls_back_to_current_target(self):
        self.assertIsNotNone(self.app.SetMode,'Focus mode API missing')
        self.app.SetMode(self.app,'focus')
        self.lua.execute("ROSTER.focus=nil; ROSTER.target={'Other','Realm'}")
        self.assertFalse(self.lua.globals().NativeDispatch(self.app.panel.assist))
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')

    def test_class_colors_reset_for_npcs_and_restricted_data(self):
        self.lua.execute("PLAYER_UNITS={focus=true}; ROSTER.focus={'Mage','Realm'}")
        self.app.SetMode(self.app,'focus')
        self.assertAlmostEqual(self.app.panel.masterCard.border[1],0.25)
        self.assertAlmostEqual(self.app.panel.assist.border[1],0.42)
        self.lua.execute("UnitIsPlayer=function() return {secret=true} end")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertAlmostEqual(self.app.panel.masterCard.border[1],0.42)

    def test_saved_scale_preserved_and_reset_uses_seventy_percent(self):
        self.app.SetOption(self.app,'scale',1.2)
        self.assertAlmostEqual(self.app.db.scale,1.2)
        self.app.Command(self.app,'reset')
        self.assertAlmostEqual(self.app.db.scale,0.7)

    def test_legacy_marker_button_absent_and_marking_never_called_from_lua(self):
        self.assertIsNone(self.app.MarkSkull)
        self.assertIsNone(self.app.panel.markSkull)
        for path in ADDON.glob('*.lua'):
            self.assertNotRegex(path.read_text(), r'\bSetRaidTarget\s*\(')
        self.assertNotIn('Skull', (ADDON/'Bindings.xml').read_text())

    def setup_indicator(self):
        self.lua.execute("ROSTER.focus={'Lead','Realm'}; ROSTER.focustarget={'Enemy','Realm'}; GUIDS={focus='leader',focustarget='enemy1',target='enemy1'}")
        self.app.SetMode(self.app,'focus')

    def test_indicator_match_and_different_target(self):
        self.setup_indicator()
        self.assertEqual(self.app.panel.indicatorState,'SAME TARGET')
        self.lua.execute("GUIDS.target='other'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'ASSIST NEEDED')

    def test_indicator_distinguishes_missing_and_unavailable(self):
        self.app.SetMode(self.app,'focus')
        self.assertEqual(self.app.panel.indicatorState,'NO FOCUS')
        self.setup_indicator()
        self.lua.execute('DISTANT=true; ROSTER.focustarget=nil')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'TARGET INFO UNAVAILABLE')
        self.lua.execute('DISTANT=false')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'NO ENEMY TARGET')

    def test_restricted_comparison_never_shows_match(self):
        self.setup_indicator()
        self.lua.execute('UnitIsUnit=function() return {secret=true} end')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'TARGET INFO UNAVAILABLE')

    def test_change_pulse_fades_and_throttles(self):
        self.setup_indicator()
        self.assertIsNone(self.app.panel.pulseStart)
        self.lua.execute("GUIDS.focustarget='enemy2'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'TARGET CHANGED')
        self.lua.execute('GetTime=function() return 100.6 end')
        self.app.panel.AnimatePulse(self.app.panel)
        self.assertGreater(self.app.panel.pulseEdges[1].alpha,0)
        self.lua.execute("GetTime=function() return 102 end; GUIDS.focustarget='enemy3'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.indicatorState,'ASSIST NEEDED')
        self.assertEqual(self.app.panel.pulseEdges[1].alpha,0)
        self.assertEqual(self.app.panel.lastPulse,100)

    def test_recovery_and_leader_change_do_not_flash(self):
        self.setup_indicator()
        self.lua.execute('DISTANT=true')
        self.app.panel.RefreshTarget(self.app.panel)
        self.lua.execute("DISTANT=false; GUIDS.focustarget='enemy2'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertIsNone(self.app.panel.pulseStart)
        self.lua.execute("GUIDS.focus='newleader'; GUIDS.focustarget='enemy3'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertIsNone(self.app.panel.pulseStart)

    def test_indicator_refresh_in_combat_keeps_secure_action(self):
        self.setup_indicator()
        self.lua.execute("COMBAT=true; GUIDS.focustarget='enemy2'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.assertEqual(self.app.panel.assist.attrs.type,'assist')

    def test_leader_switch_clears_active_pulse_and_pending_notice_survives(self):
        self.setup_indicator()
        self.lua.execute("GUIDS.focustarget='enemy2'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertIsNotNone(self.app.panel.pulseStart)
        self.lua.execute("GUIDS.focus='leader2'")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertIsNone(self.app.panel.pulseStart)
        self.lua.execute('COMBAT=true')
        self.app.SetMode(self.app,'group')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.pending.text,'Changes queued until combat ends')

    def test_class_accent_and_neutral_hover_remain_distinct(self):
        self.lua.execute("PLAYER_UNITS={focus=true,focustarget=true}; ROSTER.focus={'Mage','Realm'}")
        self.app.SetMode(self.app,'focus')
        panel=self.app.panel
        self.assertAlmostEqual(panel.targetAccent.vertexColor[3],0.92)
        self.assertAlmostEqual(panel.assist.fill[3],0.92*0.28)
        self.assertEqual(panel.targetHover.vertexColor[1],panel.targetHover.vertexColor[3])
        self.assertAlmostEqual(panel.targetHover.vertexColor[4],0.06)
        self.lua.execute('PLAYER_UNITS={}')
        panel.RefreshTarget(panel)
        self.assertAlmostEqual(panel.targetAccent.vertexColor[1],0.42)

    def test_rebinding_replaces_old_key_and_updates_display(self):
        self.assertTrue(self.app.Bind(self.app,'F8'))
        self.assertTrue(self.app.Bind(self.app,'F9'))
        self.assertIsNone(self.lua.globals().BINDINGS['F8'])
        self.assertEqual(self.lua.globals().BINDINGS['F9'],'CLICK MojowAssistButton:LeftButton')
        self.assertEqual(self.app.panel.key.text,'Key: F9')

    def test_normal_assist_key_replaces_previous_addon_key(self):
        self.app.Bind(self.app,'F8')
        self.lua.execute("BINDINGS.F9='ASSISTTARGET'; BINDINGS.SPACE='JUMP'")
        self.assertTrue(self.app.Bind(self.app,'F9'))
        self.assertIsNone(self.lua.globals().BINDINGS['F8'])
        self.assertEqual(self.lua.globals().BINDINGS['F9'],'CLICK MojowAssistButton:LeftButton')
        self.assertEqual(self.lua.globals().BINDINGS.SPACE,'JUMP')

    def test_auto_party_leader_and_focus_override(self):
        self.app.SetMode(self.app,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')
        self.app.SetMode(self.app,'focus')
        self.lua.execute("LEADER='party2'")
        self.app.OnEvent(self.app,'PARTY_LEADER_CHANGED')
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.app.SetMode(self.app,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party2')

    def test_auto_solo_fallback_and_return_to_party(self):
        self.lua.execute('ROSTER.party1=nil; ROSTER.party2=nil')
        self.app.SetMode(self.app,'auto')
        self.assertEqual(self.app.db.mode,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'focus')
        self.lua.execute("ROSTER.party1={'Lead','Realm'}")
        self.app.OnEvent(self.app,'GROUP_ROSTER_UPDATE')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')

    def test_auto_leadership_change_waits_during_combat(self):
        self.app.SetMode(self.app,'auto')
        self.lua.execute("COMBAT=true; LEADER='party2'")
        self.app.OnEvent(self.app,'PARTY_LEADER_CHANGED')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party1')
        self.assertIn('pending',self.app.panel.pending.text)
        self.lua.execute('COMBAT=false')
        self.app.OnEvent(self.app,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.app.panel.assist.attrs.unit,'party2')

    def test_auto_raid_leader(self):
        self.lua.execute("ROSTER={raid1={'Me','Realm'},raid2={'Raidlead','Realm'},raid3={'Friend','Realm'}}; LEADER='raid2'; IsInRaid=function() return true end; IsInGroup=function() return true end; GetRaidRosterInfo=function(i) return ROSTER['raid'..i][1] end")
        self.app.SetMode(self.app,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'raid2')

    def test_auto_local_leader_and_remote_selection_ignored(self):
        self.lua.execute("LEADER='player'")
        self.app.SetMode(self.app,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'player')
        self.app.OnEvent(self.app,'CHAT_MSG_ADDON','MOJOWASSIST','1|SET|Friend-Realm','PARTY','Me-Realm')
        self.assertEqual(self.app.db.mode,'auto')
        self.assertEqual(self.app.panel.assist.attrs.unit,'player')

    def test_cast_bar_countdown_and_stop(self):
        self.setup_indicator()
        self.lua.execute("CAST={'Fireball','Fireball',1,99000,102000}")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertTrue(self.app.panel.castBar.shown)
        self.assertEqual(self.app.panel.castTime.text,'2.0s')
        self.assertEqual(self.app.panel.castBar.value,2)
        self.lua.execute('CAST=nil')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertFalse(self.app.panel.castBar.shown)
        self.assertTrue(self.app.panel.assistCaption.shown)

    def test_channel_and_secret_cast_fallback(self):
        self.setup_indicator()
        self.lua.execute("CHANNEL={'Channel','Channel',1,99000,103000}")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertEqual(self.app.panel.castTime.text,'3.0s')
        self.lua.execute('CHANNEL[4]={secret=true}')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertFalse(self.app.panel.castBar.shown)
        self.assertEqual(self.app.panel.assistCaption.text,'CAST UNAVAILABLE')

    def test_cast_clears_on_distance_and_combat_roster_change(self):
        self.setup_indicator()
        self.lua.execute("CAST={'Spell','Spell',1,99000,102000}; COMBAT=true")
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertTrue(self.app.panel.castBar.shown)
        self.lua.execute('DISTANT=true')
        self.app.panel.RefreshTarget(self.app.panel)
        self.assertFalse(self.app.panel.castBar.shown)

if __name__ == '__main__': unittest.main()
