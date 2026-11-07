import test_enemies
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class NearbyHealingTests(unittest.TestCase):
    def runlua(self, code):
        self.lua.execute(code)

    def setUp(self):
        fixture=test_enemies.EnemyPanelTests()
        fixture.setUp()
        self.__dict__.update({k:v for k,v in fixture.__dict__.items() if k in ('lua','ns','addon','panel','roster')})
        self.runlua("""
            function UnitClass(u) if u=='player' then return 'Shaman','SHAMAN' end return 'Mage','MAGE' end
            C_Spell={GetSpellInfo=function(id) if id==331 then return {name='Healing Wave'} elseif id==8004 then return {name='Lesser Healing Wave'} end end}
            function IsSpellKnown(id) return id==331 end
        """)
        if (ROOT/'NearbyHealing.lua').exists():
            self.lua.execute((ROOT/'NearbyHealing.lua').read_text(),'MojowAssist',self.ns)
        self.panel=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon)
        self.roster=self.panel.roster

    def test_heal_binding_and_unlearned_right_click(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs.unit,'party1')
        self.assertEqual(row.attrs.helpbutton1,'healLeft')
        self.assertEqual(row.attrs['type-healLeft'],'spell')
        self.assertEqual(row.attrs['spell-healLeft'],'Healing Wave')
        self.assertIsNone(row.attrs.type1)
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')

    def test_combat_freezes_binding_and_clears_missing_unit(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua("COMBAT=true; UNITS.nameplate1=nil; UNITS.party1=nil; AddUnit('nameplate2',false); UNITS.nameplate2.player=true; UNITS.party2=UNITS.nameplate2")
        self.roster.Remove(self.roster,'nameplate1'); self.roster.Add(self.roster,'nameplate2')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.unit,'party1')
        self.assertEqual(row.name.text,'Unit unavailable')
        self.assertFalse(self.panel.SetVisible(self.panel,False))
        self.assertTrue(self.panel.frame.shown)
        self.runlua('COMBAT=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_ENABLED')
        self.assertEqual(row.attrs.unit,'party2')

    def test_learning_and_scroll_wait_for_combat_end(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua('COMBAT=true; function IsSpellKnown() return true end')
        self.panel.events.scripts.OnEvent(self.panel.events,'SPELLS_CHANGED')
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')
        self.panel.frame.scripts.OnMouseWheel(self.panel.frame,-1)
        self.assertEqual(self.panel.offset,0)
        self.runlua('COMBAT=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_ENABLED')
        self.assertEqual(row.attrs['spell-healRight'],'Lesser Healing Wave')

    def test_recycled_token_display_matches_bound_action(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.runlua("COMBAT=true; AddUnit('nameplate1',true); UNITS.nameplate1.name='New enemy'")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIn('nameplate1',row.name.text)
        self.assertEqual(row.attrs.unit,'party1')
        self.assertIsNone(row.attrs.type1)
        self.assertIsNone(row.attrs.harmbutton1)

    def test_reset_command_rejected_before_protected_mutation(self):
        self.lua.execute((ROOT/'Runtime.lua').read_text(),'MojowAssist',self.ns)
        addon=self.ns.Addon
        addon.db=self.addon.db
        addon.enemies=self.panel
        self.runlua('COMBAT=true')
        before=self.addon.db.enemyX
        addon.Command(addon,'enemies reset')
        self.assertEqual(self.addon.db.enemyX,before)

    def test_failed_drag_stop_retried_after_combat(self):
        self.panel.moving=True
        self.runlua('COMBAT=true')
        self.panel.frame.StopMovingOrSizing=self.lua.eval("function() if COMBAT then error('protected') end end")
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_DISABLED')
        self.assertTrue(self.panel.moving)
        self.runlua('COMBAT=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_ENABLED')
        self.assertFalse(self.panel.moving)

    def test_trace_handles_restricted_values_without_changing_action(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1; function UnitCanAssist() return {secret=true} end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.addon.Say=self.lua.eval('function(self,msg) self.message=msg end')
        row=self.panel.rows[1]
        self.runlua('COMBAT=true')
        self.ns.NearbyHealing.Trace(self.ns.NearbyHealing,self.addon,row,'LeftButton')
        self.assertEqual(row.attrs.unit,'party1')
        self.assertEqual(row.attrs['spell-healLeft'],'Healing Wave')

    def test_unmatched_nearby_player_uses_exact_name_macro(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIsNone(row.attrs.unit)
        self.assertEqual(row.attrs.type1,'macro')
        self.assertEqual(row.attrs.macrotext1,'/cleartarget\n/target nameplate1\n/cast [@target,exists,help,nodead] Healing Wave')
        self.assertIsNone(row.attrs.helpbutton1)
        self.assertIsNone(row.attrs.type2)

    def test_target_alias_available_and_secret_match_rejected(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.target=UNITS.nameplate1")
        self.assertEqual(self.ns.NearbyHealing.Resolve(self.ns.NearbyHealing,'nameplate1'),'target')
        self.runlua('function UnitIsUnit() return {secret=true} end')
        self.assertIsNone(self.ns.NearbyHealing.Resolve(self.ns.NearbyHealing,'nameplate1'))

    def test_macro_pins_name_when_nameplate_recycled_in_combat(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.nameplate1.name='Friend'")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]; original=row.attrs.macrotext1
        self.runlua("COMBAT=true; UNITS.nameplate1.name='SomeoneElse'")
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.macrotext1,original)
        self.assertIn('Friend',row.name.text)
        self.assertNotIn('SomeoneElse',row.name.text)
        self.assertEqual(row.health.value,0)

    def test_macro_rejects_injection_and_nonplayer(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1')
        for name in ('Friend\n/logout','[help] Friend','Friend;Enemy','Friend|cffff0000'):
            self.lua.globals().UNITS.nameplate1.name=name
            self.panel.Refresh(self.panel)
            self.assertIsNone(self.panel.rows[1].attrs.type1)
        self.runlua("UNITS.nameplate1.name='Friend'; UNITS.nameplate1.player=false")
        self.assertIsNone(self.ns.NearbyHealing.TargetName(self.ns.NearbyHealing,'nameplate1'))

    def test_macro_to_direct_and_back_clears_previous_actions(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs.type1,'macro')
        self.runlua('UNITS.party1=UNITS.nameplate1')
        self.panel.Refresh(self.panel)
        self.assertIsNone(row.attrs.type1)
        self.assertIsNone(row.attrs.macrotext1)
        self.assertEqual(row.attrs['type-healLeft'],'spell')
        self.runlua('UNITS.party1=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.type1,'macro')
        self.assertIsNone(row.attrs.helpbutton1)
        self.assertIsNone(row.attrs['type-healLeft'])

    def test_macro_preserves_full_player_realm(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; function UnitName() return 'Friend','OtherRealm' end")
        self.assertEqual(self.ns.NearbyHealing.TargetName(self.ns.NearbyHealing,'nameplate1'),'Friend-OtherRealm')

    def test_macro_diagnostic_and_blocked_event_are_read_only(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.addon.Say=self.lua.eval('function(self,msg) self.message=msg end')
        row=self.panel.rows[1]; before=row.attrs.macrotext1
        self.runlua('COMBAT=true')
        self.panel.healTracePending=True
        row.scripts.PreClick(row,'LeftButton',True)
        self.panel.events.scripts.OnEvent(self.panel.events,'ADDON_ACTION_BLOCKED','MojowAssist','RunMacroText')
        self.assertIn('RunMacroText',self.addon.message)
        row.scripts.PostClick(row,'LeftButton',False)
        self.assertFalse(self.panel.healTracePending)
        self.assertEqual(row.attrs.macrotext1,before)
        self.panel.healTraceUntil=0
        previous=self.addon.message
        self.panel.events.scripts.OnEvent(self.panel.events,'UI_ERROR_MESSAGE',1,'unrelated')
        self.assertEqual(self.addon.message,previous)

    def test_macro_uses_confirmed_short_name_target_command(self):
        macro=self.ns.NearbyHealing.Macro(self.ns.NearbyHealing,'Becat-Docrime','Healing Wave')
        self.assertEqual(macro,'/cleartarget\n/target Becat\n/cast [@target,exists,help,nodead] Healing Wave')
        self.assertIsNone(self.ns.NearbyHealing.Macro(self.ns.NearbyHealing,'-Docrime','Healing Wave'))

    def test_custom_binding_saved_and_applied_to_macro(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',331))
        self.assertIn('Healing Wave',self.panel.rows[1].attrs['macrotext2'])
        self.assertEqual(self.addon.db.healRightID,331)
        restored=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual(restored.healRightID,331)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'left',0))
        self.assertIsNone(self.panel.rows[1].attrs.type1)
        self.assertEqual(self.ns.NearbyHealing.BindingLabel(self.ns.NearbyHealing,self.addon.db,'left'),'Disabled')

    def test_binding_rejects_unknown_spell_and_combat_changes(self):
        self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',8004))
        self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',9999))
        self.runlua('COMBAT=true')
        self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',331))
        self.assertEqual(self.addon.db.healRightID,8004)

    def test_debug_is_opt_in_and_invalid_saved_binding_defaults(self):
        self.assertFalse(self.panel.healTracePending)
        restored=self.ns.Model.Normalize(self.ns.Model,self.lua.table_from({'healLeftID':'bad','healRightID':9999}))
        self.assertEqual(restored.healLeftID,331)
        self.assertEqual(restored.healRightID,8004)

    def test_settings_lists_learned_choices_and_applies_click(self):
        self.lua.execute((ROOT/'HealingSettings.lua').read_text(),'MojowAssist',self.ns)
        self.addon.Say=self.lua.eval('function(self,msg) self.message=msg end')
        self.assertTrue(self.ns.HealingSettings.Open(self.ns.HealingSettings,self.panel))
        view=self.panel.healingSettings
        self.assertEqual(len(view.buttons),4)
        right=next(b for _,b in view.buttons.items() if b.side=='right' and b.spellID==331)
        right.scripts.OnClick(right)
        self.assertEqual(self.addon.db.healRightID,331)
        self.assertEqual(view.current[2].text,'Healing Wave')
        self.runlua('COMBAT=true')
        disabled=next(b for _,b in view.buttons.items() if b.side=='right' and b.spellID==0)
        disabled.scripts.OnClick(disabled)
        self.assertEqual(self.addon.db.healRightID,331)
        self.assertIn('outside combat',self.addon.message)

    def test_disabling_both_clicks_clears_direct_actions(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        for side in ('left','right'):
            self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,side,0)
        row=self.panel.rows[1]
        self.assertIsNone(row.attrs['type-healLeft'])
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')
        self.assertFalse(row.hasHealingAction)

    def test_range_reports_unknown_for_missing_secret_and_errors(self):
        healing=self.ns.NearbyHealing
        for expression in ('nil','{secret=true}'):
            self.runlua('C_Spell.IsSpellInRange=function() return '+expression+' end')
            self.assertEqual(healing.Range(healing,'Healing Wave','nameplate1'),'unknown')
        self.runlua("C_Spell.IsSpellInRange=function() error('restricted') end")
        self.assertEqual(healing.Range(healing,'Healing Wave','nameplate1'),'unknown')
        self.assertEqual(healing.Range(healing,None,'nameplate1'),'unavailable')

    def test_range_marker_changes_without_mutating_combat_actions(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; C_Spell.IsSpellInRange=function() return true end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]; before=row.attrs.macrotext1
        self.assertIn('In heal range',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.runlua('COMBAT=true; C_Spell.IsSpellInRange=function() return false end')
        self.panel.Refresh(self.panel)
        self.assertIn('Too far to heal',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.assertEqual(row.attrs.macrotext1,before)
        self.runlua('C_Spell.IsSpellInRange=function() return nil end')
        self.panel.Refresh(self.panel)
        self.assertIn('Range unavailable',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())

    def test_different_click_ranges_and_legacy_fallback(self):
        self.runlua("C_Spell.IsSpellInRange=nil; function IsSpellInRange(spell,unit) return spell=='Healing Wave' and 1 or 0 end")
        healing=self.ns.NearbyHealing
        self.assertEqual(healing.Range(healing,'Healing Wave','party1'),'in')
        self.assertEqual(healing.Range(healing,'Lesser Healing Wave','party1'),'out')
        self.assertIn('[MIX]',healing.RangeMarker(healing,'in','out'))
        self.assertIn('[?]',healing.RangeMarker(healing,'in','unknown'))
        self.assertIn('[IN]',healing.RangeMarker(healing,'in','unavailable'))

    def test_cleanse_indicator_updates_and_combat_replaces_it_with_unknown(self):
        self.lua.execute((ROOT/'DispelHelper.lua').read_text(),'MojowAssist',self.ns)
        self.runlua("""
            local previous=C_Spell.GetSpellInfo
            C_Spell.GetSpellInfo=function(id) if id==526 then return {name='Cure Poison'} end return previous(id) end
            function IsSpellKnown(id) return id==331 or id==526 end
            AddUnit('nameplate1',false); UNITS.nameplate1.player=true
            AURACALLS=0; POISON=true
            C_UnitAuras={GetAuraDataByIndex=function(u,i) AURACALLS=AURACALLS+1; if POISON and i==1 then return {dispelName='Poison'} end end}
        """)
        self.panel.healsDirty=True
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIn('Cure poison',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.assertIn('|cff55ff88[Poison]|r ',row.name.text)
        self.runlua('COMBAT=true')
        calls=self.lua.globals().AURACALLS
        self.panel.Refresh(self.panel)
        self.assertIn('Debuff info unavailable',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.assertEqual(self.lua.globals().AURACALLS,calls)
        self.assertNotIn('[Poison]',row.name.text)
        self.runlua('COMBAT=false; POISON=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'UNIT_AURA','nameplate1')
        self.assertNotIn('Cure poison',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.assertNotIn('[Poison]',row.name.text)
        self.assertNotIn('Debuff info unavailable',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())

    def test_out_of_range_group_health_greys_and_recovers_in_combat(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; C_Spell.IsSpellInRange=function() return false end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.assertAlmostEqual(row.health.alpha,0.35)
        before=row.attrs['spell-healLeft']
        self.runlua('COMBAT=true; C_Spell.IsSpellInRange=function() return nil end')
        self.panel.Refresh(self.panel)
        self.assertNotAlmostEqual(row.health.alpha,0.35)
        self.assertEqual(row.attrs['spell-healLeft'],before)
        self.runlua('C_Spell.IsSpellInRange=function() return true end')
        self.panel.Refresh(self.panel)
        self.assertNotAlmostEqual(row.health.alpha,0.35)

    def test_nearby_players_grey_but_primary_in_range_stays_colored(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; C_Spell.IsSpellInRange=function() return false end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertAlmostEqual(self.panel.rows[1].health.alpha,0.35)
        self.runlua("UNITS.party1=UNITS.nameplate1; function IsSpellKnown() return true end; C_Spell.IsSpellInRange=function(spell) return spell=='Healing Wave' end")
        self.panel.healsDirty=True; self.panel.Refresh(self.panel)
        self.assertIn('Spell ranges differ',self.panel.rows[1].statusPrimary)
        self.assertNotAlmostEqual(self.panel.rows[1].health.alpha,0.35)

    def enable_damage(self):
        self.runlua("""
            local oldInfo=C_Spell.GetSpellInfo
            C_Spell.GetSpellInfo=function(id)
                if id==403 then return {name='Lightning Bolt'} end
                if id==8042 then return {name='Earth Shock'} end
                return oldInfo(id)
            end
            function IsSpellKnown(id) return id==331 or id==403 or id==8042 end
        """)
        self.panel.healsDirty=True

    def test_enemy_target_clicks_are_harm_only_and_friend_reuse_clears_them(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs.unit,'target')
        self.assertEqual(row.attrs.harmbutton1,'damageLeft')
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')
        self.assertEqual(row.attrs['spell-damageRight'],'Earth Shock')
        self.assertIsNone(row.attrs.helpbutton1)
        self.assertIsNone(row.attrs.type1)
        self.runlua("UNITS.nameplate1.enemy=false; UNITS.nameplate1.player=true")
        self.panel.Refresh(self.panel)
        self.assertIsNone(row.attrs.harmbutton1)
        self.assertIsNone(row.attrs['spell-damageLeft'])
        self.assertEqual(row.attrs['spell-healLeft'],'Healing Wave')

    def test_nameplate_only_enemy_does_not_target_ambiguous_name(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); AddUnit('nameplate2',true); UNITS.nameplate1.name='Wolf'; UNITS.nameplate2.name='Wolf'")
        self.roster.Add(self.roster,'nameplate1'); self.roster.Add(self.roster,'nameplate2'); self.panel.Refresh(self.panel)
        for index in (1,2):
            row=self.panel.rows[index]
            self.assertEqual(row.attrs.type1,'macro')
            self.assertEqual(row.attrs.unit,'nameplate'+str(index))
            self.assertIn('/target [@nameplate'+str(index)+',exists,harm,nodead]',row.attrs.macrotext1)
            self.assertNotIn('Wolf',row.attrs.macrotext1)
            self.assertIsNone(row.attrs.harmbutton1)
            self.assertNotIn('[TARGET]',row.name.text)
            self.assertIn('Select and cast',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())

    def test_enemy_alias_display_tracks_current_target_in_combat(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua("COMBAT=true; AddUnit('nameplate2',true); UNITS.nameplate2.name='New Target'; UNITS.target=UNITS.nameplate2")
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.unit,'target')
        self.assertEqual(row.boundUnit,'target')
        self.assertIn('New Target',row.name.text)
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')

    def test_damage_unlearned_and_secret_relationship_are_not_bound(self):
        self.enable_damage()
        self.runlua("function IsSpellKnown(id) return id==331 end; AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIsNone(row.attrs['type-damageLeft'])
        self.assertIsNone(row.attrs['type-damageRight'])
        self.runlua('function UnitCanAttack() return {secret=true} end')
        self.ns.NearbyHealing.Bind(self.ns.NearbyHealing,row,'nameplate1','Healing Wave',None,'Lightning Bolt','Earth Shock')
        self.assertIsNone(row.attrs.harmbutton1)

    def test_enemy_choices_persist_separately_and_disable_clears_cast(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'left',8042,True))
        self.assertEqual(self.panel.rows[1].attrs['spell-damageLeft'],'Earth Shock')
        self.assertEqual(self.addon.db.healLeftID,331)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',0,True))
        self.assertIsNone(self.panel.rows[1].attrs['type-damageRight'])
        saved=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual(saved.enemyLeftID,8042)
        self.assertEqual(saved.enemyRightID,0)

    def test_enemy_choices_reject_unlearned_heals_and_combat(self):
        self.enable_damage()
        for spell in (331,8050,9999):
            self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'left',spell,True))
        self.runlua('COMBAT=true')
        self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'left',8042,True))

    def test_enemy_settings_view_is_separate_from_healing(self):
        self.enable_damage()
        self.lua.execute((ROOT/'HealingSettings.lua').read_text(),'MojowAssist',self.ns)
        self.assertTrue(self.ns.HealingSettings.Open(self.ns.HealingSettings,self.panel,True))
        view=self.panel.enemySettings
        self.assertEqual(view.current[1].text,'Lightning Bolt')
        self.assertEqual(view.current[2].text,'Earth Shock')
        self.assertIsNone(self.panel.healingSettings)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',0,True))
        self.ns.HealingSettings.Refresh(self.ns.HealingSettings,self.panel,True)
        self.assertEqual(view.current[2].text,'Disabled')

    def test_shift_player_menu_uses_secure_action_and_right_heal_stays_separate(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1; function IsSpellKnown() return true end; function UnitPopup_OpenMenu() error('insecure menu call') end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.healsDirty=True; self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu' if row.menuUnit else '')
        self.assertEqual(row.attrs.unit2,'party1')
        row.scripts.PostClick(row,'RightButton',False)
        self.assertIsNone(self.ns.NearbyHealing.OpenPlayerMenu)

    def test_enemy_row_clears_menu_modifiers(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIsNone(row.attrs['shift-type-healRight'])
        self.assertIsNone(row.attrs['shift-macrotext2'])
        self.assertIsNone(row.attrs.unit2)
        self.assertIsNone(row.attrs.type2)
        self.assertEqual(row.attrs['type-damageRight'],'spell')

    def test_ungrouped_menu_token_and_disabled_shift_noop(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertIsNone(row.attrs.type2)
        self.assertIsNone(row.attrs.unit2)
        self.assertEqual(row.attrs['shift-type2'],'')

    def test_restricted_group_flags_preserve_right_heal(self):
        self.runlua("AddUnit('nameplate1',false); UNITS.nameplate1.player=true; UNITS.party1=UNITS.nameplate1; function IsSpellKnown() return true end; function UnitIsPlayer() return {secret=true} end")
        row=self.panel.rows[1]
        self.ns.NearbyHealing.Bind(self.ns.NearbyHealing,row,'party1','Healing Wave','Lesser Healing Wave')
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu' if row.menuUnit else '')
        self.assertEqual(row.attrs['type-healRight'],'spell')

    def test_assist_marker_tracks_native_leader_target_in_combat(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); AddUnit('nameplate2',true); AddUnit('party1',false); UNITS.party1target=UNITS.nameplate1")
        button=self.lua.globals().CreateFrame('Button')
        button.SetAttribute(button,'type','assist'); button.SetAttribute(button,'unit','party1')
        self.addon.action=self.lua.table_from({'button':button})
        self.roster.Add(self.roster,'nameplate1'); self.roster.Add(self.roster,'nameplate2'); self.panel.Refresh(self.panel)
        self.assertIn('target',self.panel.rows[2].identityStatus)
        self.assertIsNone(self.panel.rows[3].identityStatus)
        self.runlua('COMBAT=true; UNITS.party1target=UNITS.nameplate2')
        self.panel.Refresh(self.panel)
        self.assertIsNone(self.panel.rows[2].identityStatus)
        self.assertIn('target',self.panel.rows[3].identityStatus)
        self.assertEqual(self.panel.rows[3].attrs.type1,'macro')

    def test_focus_assist_marker_clears_when_missing_or_secret(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); AddUnit('focus',false); UNITS.focustarget=UNITS.nameplate1")
        button=self.lua.globals().CreateFrame('Button')
        button.SetAttribute(button,'type','assist'); button.SetAttribute(button,'unit','focus')
        self.addon.action=self.lua.table_from({'button':button})
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertIn('target',self.panel.rows[1].identityStatus)
        self.runlua('UNITS.focustarget=nil')
        self.panel.Refresh(self.panel)
        self.assertIsNone(self.panel.rows[1].identityStatus)
        button.SetAttribute(button,'unit',self.lua.table_from({'secret':True}))
        self.panel.Refresh(self.panel)
        self.assertIsNone(self.panel.rows[1].identityStatus)

    def test_raid_marker_changes_and_clears_during_combat(self):
        self.runlua("AddUnit('nameplate1',true); MARK=8; function GetRaidTargetIndex() return MARK end; function SetRaidTargetIconTexture(icon,index) icon.testIndex=index end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertTrue(row.raidIcon.shown)
        self.assertEqual(row.raidIcon.testIndex,8)
        self.runlua('COMBAT=true; MARK=4')
        self.panel.events.scripts.OnEvent(self.panel.events,'RAID_TARGET_UPDATE')
        self.assertEqual(row.raidIcon.testIndex,4)
        self.runlua('MARK=nil')
        self.panel.Refresh(self.panel)
        self.assertFalse(row.raidIcon.shown)

    def test_raid_marker_hides_for_restricted_invalid_and_missing_units(self):
        self.runlua("AddUnit('nameplate1',true); MARK=8; function GetRaidTargetIndex() return MARK end; function SetRaidTargetIconTexture(icon,index) icon.testIndex=index end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        for value in ('{secret=true}','0','9','1.5'):
            self.runlua('MARK='+value)
            self.panel.Refresh(self.panel)
            self.assertFalse(row.raidIcon.shown)
        self.runlua('MARK=8'); self.panel.Refresh(self.panel)
        self.runlua('COMBAT=true; UNITS.nameplate1=nil'); self.panel.Refresh(self.panel)
        self.assertFalse(row.raidIcon.shown)

    def test_group_death_ghost_offline_and_recovery_remain_visible(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; CONNECTED=true; GHOST=false; function UnitIsConnected() return CONNECTED end; function UnitIsGhost() return GHOST end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua('UNITS.party1.dead=true')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.value.text,'DEAD')
        self.assertEqual(row.boundUnit,'party1')
        self.runlua('COMBAT=true; GHOST=true'); self.panel.Refresh(self.panel)
        self.assertEqual(row.value.text,'GHOST')
        self.runlua('CONNECTED=false'); self.panel.Refresh(self.panel)
        self.assertEqual(row.value.text,'OFFLINE')
        self.runlua('CONNECTED=true; GHOST=false; UNITS.party1.dead=false'); self.panel.Refresh(self.panel)
        self.assertNotIn(row.value.text,('DEAD','GHOST','OFFLINE'))
        self.assertEqual(row.attrs['spell-healLeft'],'Healing Wave')

    def test_target_focus_markers_follow_identity_and_clear(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); AddUnit('nameplate2',true); UNITS.target=UNITS.nameplate1; UNITS.focus=UNITS.nameplate2")
        self.roster.Add(self.roster,'nameplate1'); self.roster.Add(self.roster,'nameplate2'); self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].identityStatus,'Your target')
        self.assertEqual(self.panel.rows[2].identityStatus,'Your focus')
        self.runlua('UNITS.target=nil; UNITS.focus=nil'); self.panel.Refresh(self.panel)
        for i in (1,2):
            self.assertNotEqual(self.panel.rows[i].identityStatus,'Your target')
            self.assertNotEqual(self.panel.rows[i].identityStatus,'Your focus')

    def test_unknown_group_status_is_not_reported_as_offline(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; function UnitIsConnected() return {secret=true} end; function UnitIsGhost() error('restricted') end; function UnitIsDeadOrGhost() return {secret=true} end")
        self.panel.Refresh(self.panel)
        self.assertNotIn(self.panel.rows[1].value.text,('DEAD','GHOST','OFFLINE'))

    def test_offline_member_without_world_unit_stays_until_roster_departure(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; local oldExists=UnitExists; function UnitExists(u) if u=='party1' then return false end return oldExists(u) end; function UnitIsConnected(u) return u~='party1' end")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].value.text,'OFFLINE')
        self.assertEqual(self.panel.rows[1].boundUnit,'party1')
        self.runlua('UNITS.party1=nil'); self.panel.Refresh(self.panel)
        self.assertIsNone(self.panel.rows[1].boundUnit)

    def test_assist_summary_names_target_even_when_not_in_visible_rows(self):
        self.runlua("AddUnit('focus',false); AddUnit('focustarget',true); UNITS.focustarget.name='Leader Enemy'")
        button=self.lua.globals().CreateFrame('Button')
        button.SetAttribute(button,'type','assist'); button.SetAttribute(button,'unit','focus')
        self.addon.action=self.lua.table_from({'button':button})
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.assistSummary.text,'Assist target: Leader Enemy')
        self.runlua("UNITS.nameplate1=UNITS.focustarget")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertAlmostEqual(row.border[2],1)
        self.runlua("COMBAT=true; AddUnit('focustarget',true); UNITS.focustarget.name='Different Enemy'")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.assistSummary.text,'Assist target: Different Enemy')
        self.assertAlmostEqual(row.border[2],0.29)
        self.assertAlmostEqual(row.fill[2],0.035)
        self.runlua('UNITS.focustarget=nil'); self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.assistSummary.text,'Assist: No target')

    def test_focus_cast_row_binds_without_target_then_follows_it(self):
        self.enable_damage(); self.panel.Refresh(self.panel)
        self.assertEqual(len(self.panel.combatRows),1)
        focus=self.panel.combatRows[1]
        self.assertEqual(focus.attrs.unit,'focustarget')
        self.assertEqual(focus.attrs['spell-damageRight'],'Earth Shock')
        self.assertEqual(focus.roleLabel.text,"Focus's target")
        self.runlua("COMBAT=true; AddUnit('focustarget',true); UNITS.focustarget.name='Focus Mob'")
        self.panel.Refresh(self.panel)
        self.assertIn('Focus Mob',focus.name.text)
        self.assertEqual(focus.attrs.unit,'focustarget')
        self.runlua('UNITS.focustarget.enemy=false')
        self.panel.Refresh(self.panel)
        self.assertIn('Focus Mob',focus.name.text)
        self.assertEqual(focus.attrs.type1,'macro')
        self.assertIsNone(focus.attrs.helpbutton1)

    def test_focus_cast_row_is_distinct_from_selected_assist_leader(self):
        self.enable_damage()
        self.runlua("""
            AddUnit('party1',false); AddUnit('party1target',true)
            UNITS.party1target.name='Leader Mob'
            AddUnit('focus',false); AddUnit('focustarget',true)
            UNITS.focustarget.name='Focus Mob'
        """)
        button=self.lua.globals().CreateFrame('Button')
        button.SetAttribute(button,'type','assist'); button.SetAttribute(button,'unit','party1')
        self.addon.action=self.lua.table_from({'button':button})
        self.panel.Refresh(self.panel)
        focus=self.panel.combatRows[1]
        self.assertEqual(self.panel.assistSummary.text,'Assist target: Leader Mob')
        self.assertEqual(focus.roleLabel.text,"Focus's target")
        self.assertIn('Focus Mob',focus.name.text)
        self.assertEqual(focus.attrs.unit,'focustarget')
        macro=focus.attrs['macrotext-damageLeft']
        self.assertIn('/target [@focustarget,exists]',macro)
        self.runlua("COMBAT=true; UNITS.party1target.name='New Leader Mob'")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.assistSummary.text,'Assist target: New Leader Mob')
        self.assertEqual(focus.roleLabel.text,"Focus's target")
        self.assertIn('Focus Mob',focus.name.text)
        self.assertEqual(focus.attrs['macrotext-damageLeft'],macro)

    def test_combat_cast_rows_respect_disabled_choice_and_combat_lock(self):
        self.enable_damage(); self.panel.Refresh(self.panel)
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',0,True))
        self.assertIsNone(self.panel.combatRows[1].attrs['type-damageRight'])
        self.runlua('COMBAT=true')
        self.assertFalse(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'right',8042,True))

    def test_primary_range_controls_grey_with_secondary_fallback(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; function IsSpellKnown() return true end; C_Spell.IsSpellInRange=function(spell) return spell~='Healing Wave' end")
        self.panel.healsDirty=True; self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.assertIn('Too far to heal',((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip())
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,self.panel,'left',0))
        self.assertNotAlmostEqual(row.health.alpha,0.35)
        self.runlua('COMBAT=true; C_Spell.IsSpellInRange=function() return false end')
        self.panel.Refresh(self.panel)
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.runlua('C_Spell.IsSpellInRange=function() return {secret=true} end')
        self.panel.Refresh(self.panel)
        self.assertNotAlmostEqual(row.health.alpha,0.35)

    def test_compact_rows_and_faded_class_color(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; C_Spell.IsSpellInRange=function() return false end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.height,36)
        self.assertEqual(((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip(),'Too far to heal')
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.assertNotAlmostEqual(row.health.color[2],0.35)
        self.runlua('COMBAT=true; C_Spell.IsSpellInRange=function() return true end')
        self.panel.Refresh(self.panel)
        self.assertEqual(((row.statusPrimary or '')+' '+(row.statusDetail or '')).strip(),'In heal range')
        self.assertEqual(row.health.alpha,1)

    def test_group_self_first_once_with_heal_and_menu_and_dead_status(self):
        self.runlua("AddUnit('player',false); UNITS.player.player=true; UNITS.player.name='Me'; AddUnit('party1',false); UNITS.party1.player=true; UNITS.raid1=UNITS.player; UNITS.nameplate1=UNITS.player; function IsInGroup() return true end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.boundUnit,'player')
        self.assertEqual(row.attrs.unit,'player')
        self.assertEqual(row.attrs['spell-healLeft'],'Healing Wave')
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')
        self.assertEqual(self.panel.headers[1].text,'Group Members  2')
        self.runlua('UNITS.player.dead=true; function UnitIsGhost() return false end')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].value.text,'DEAD')
        self.runlua('function IsInGroup() return false end')
        self.panel.Refresh(self.panel)
        self.assertNotEqual(self.panel.rows[1].boundUnit,'player')

    def test_plain_cast_status_interruptibility_and_secret_flags(self):
        self.enable_damage()
        self.runlua("AddUnit('target',true); BLOCK=false; function UnitCastingInfo() return 'Fireball',nil,nil,9000,12000,false,'cast-id',BLOCK end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.name.text,'[?] target')
        self.assertEqual(row.spell.text,'Casting: Fireball')
        self.assertEqual(row.statusPrimary,'Your target')
        self.assertEqual(row.statusDetail,'Interruptible')
        self.runlua('BLOCK=true'); self.panel.Refresh(self.panel)
        self.assertEqual(row.statusDetail,'Cannot interrupt')
        self.runlua('BLOCK={secret=true}'); self.panel.Refresh(self.panel)
        self.assertEqual(row.statusDetail,'Interrupt info unavailable')
        self.runlua("function UnitCastingInfo() end; function UnitChannelInfo() return 'Drain',nil,nil,9000,12000,false,false end")
        self.panel.Refresh(self.panel)
        self.assertEqual(row.spell.text,'Channeling: Drain')
        self.assertEqual(row.statusDetail,'Interruptible')
        self.runlua('function UnitChannelInfo() end'); self.panel.Refresh(self.panel)
        self.assertNotEqual(row.statusDetail,'Interruptible')

    def test_plain_status_keeps_cure_urgent_and_names_clean(self):
        self.lua.execute((ROOT/'DispelHelper.lua').read_text(),'MojowAssist',self.ns)
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; C_Spell.IsSpellInRange=function() return false end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        row.dispelData=self.lua.table_from({'kind':'found','dispel':'Poison'})
        self.panel.PlainStatus(self.panel,row,'party1','Too far to heal',True,'Your focus')
        self.assertEqual(row.statusPrimary,'Cure poison')
        self.assertEqual(row.statusDetail,'Too far to heal')
        self.assertNotIn('[F]',row.name.text)
        self.assertNotIn('[FAR]',row.name.text)

    def test_group_fade_falls_back_only_when_spell_range_unknown(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; C_Spell.IsSpellInRange=function() end; function UnitInRange() return false,true end")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        before=row.attrs['spell-healLeft']
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.assertEqual(row.rangeSource,'group')
        self.assertEqual(row.statusPrimary,'Outside group range')
        self.assertIsNone(row.statusText)
        self.runlua('COMBAT=true; function UnitInRange() return true,true end')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)
        self.assertEqual(row.attrs['spell-healLeft'],before)
        self.runlua('function UnitInRange() return false,false end')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)
        self.assertEqual(row.statusPrimary,'Range unavailable')
        self.runlua('C_Spell.IsSpellInRange=function() return true end; function UnitInRange() error("must not override spell range") end')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)
        self.assertEqual(row.rangeSource,'spell')

    def test_secret_range_is_forwarded_to_native_alpha_without_text_inference(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            SECRET_RANGE={secret=true}; SECRET_ALPHA={secret=true}; SEEN=0
            C_Spell.IsSpellInRange=function() return SECRET_RANGE end
            C_CurveUtil={EvaluateColorValueFromBoolean=function(value,yes,no)
                assert(value==SECRET_RANGE); assert(yes==1 and no==0.35)
                SEEN=SEEN+1; return SECRET_ALPHA
            end}
        """)
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertTrue(row.health.alpha.secret)
        self.assertEqual(row.rangeSource,'native spell')
        self.assertEqual(row.statusPrimary,'Range unavailable')
        self.assertGreater(self.lua.globals().SEEN,0)
        self.runlua('C_Spell.IsSpellInRange=function() return nil end; C_CurveUtil=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)

    def test_secret_group_range_respects_native_checked_flag(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            C_Spell.IsSpellInRange=function() end
            CHECKED=true; CLOSE=false
            function UnitInRange() return {secret=true,value=CLOSE},{secret=true,value=CHECKED} end
            C_CurveUtil={EvaluateColorValueFromBoolean=function(value,yes,no)
                if type(value)=='table' then value=value.value end
                return value and yes or no
            end}
        """)
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertAlmostEqual(row.health.alpha,0.35)
        self.assertEqual(row.rangeSource,'native group')
        self.assertEqual(row.statusPrimary,'Range unavailable')
        self.runlua('COMBAT=true; CHECKED=false')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)
        self.runlua('CHECKED=true; CLOSE=true')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.health.alpha,1)

    def test_hover_details_include_cast_even_when_range_is_primary(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            C_Spell.IsSpellInRange=function() return false end
            function UnitCastingInfo() return 'Healing Wave',nil,nil,9000,12000,false,'id',true end
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertIn('Too far to heal',lines)
        self.assertIn('Casting: Healing Wave',lines)
        self.assertIn('Cannot interrupt',lines)
        self.assertIsNone(row.statusText)
        self.assertEqual(row.height,36)

    def test_combat_npc_target_slot_does_not_display_self_after_target_change(self):
        self.enable_damage()
        self.runlua("AddUnit('target',true); UNITS.target.name='Boar'; AddUnit('player',false); UNITS.player.player=true; UNITS.player.name='Mojow'")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        action=row.attrs['spell-damageLeft']
        self.assertEqual(self.panel.headers[2].text,'NPCs  1')
        self.runlua('COMBAT=true; UNITS.target=UNITS.player')
        self.panel.Refresh(self.panel)
        self.assertNotIn('Mojow',row.name.text)
        self.assertEqual(row.value.text,'')
        self.assertEqual(row.attrs['spell-damageLeft'],action)
        self.assertEqual(row.attrs.unit,'target')
        self.runlua('COMBAT=false')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.headers[2].text,'NPCs  0')
        self.assertFalse(row.shown)

    def test_combat_target_slot_waits_on_category_change_then_recovers(self):
        self.enable_damage()
        self.runlua("AddUnit('target',true); UNITS.target.name='Boar'")
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua("COMBAT=true; AddUnit('target',false); UNITS.target.player=true; UNITS.target.name='Friend'")
        self.panel.Refresh(self.panel)
        self.assertNotIn('Friend',row.name.text)
        self.assertEqual(row.value.text,'')
        self.runlua("AddUnit('target',true); UNITS.target.name='Another boar'")
        self.panel.Refresh(self.panel)
        self.assertIn('Another boar',row.name.text)

    def readiness_tooltip(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            C_Spell.IsSpellInRange=function() return true end
            C_Spell.IsSpellUsable=function() return true,false end
            C_Spell.GetSpellCooldown=function() return {startTime=0,duration=0,isEnabled=true,modRate=1} end
            LINES={}; GameTooltip={SetOwner=function(self,row) self.owner=row; LINES={} end,
                IsOwned=function(self,row) return self.owner==row end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end,
                Hide=function(self) self.owner=nil end}
        """)
        self.panel.Refresh(self.panel)
        return self.panel.rows[1]

    def test_heal_tooltip_ready_mana_and_cooldown_without_click_mutation(self):
        row=self.readiness_tooltip(); before=row.attrs['spell-healLeft']
        row.scripts.OnEnter()
        self.assertTrue(any('Ready by current checks' in x for x in self.lua.globals().LINES.values()))
        self.runlua('COMBAT=true; C_Spell.IsSpellUsable=function() return false,true end')
        row.scripts.OnEnter()
        self.assertTrue(any('Not enough mana' in x for x in self.lua.globals().LINES.values()))
        self.runlua('C_Spell.IsSpellUsable=function() return true,false end; C_Spell.GetSpellCooldown=function() return {startTime=9,duration=4,isEnabled=true,modRate=1} end')
        row.scripts.OnEnter()
        self.assertTrue(any('Cooldown: 3.0s' in x for x in self.lua.globals().LINES.values()))
        self.assertEqual(row.attrs['spell-healLeft'],before)

    def test_heal_tooltip_restricted_data_never_claims_ready(self):
        row=self.readiness_tooltip()
        for code in ("C_Spell.IsSpellUsable=function() return {secret=true},{secret=true} end",
                     "C_Spell.GetSpellCooldown=function() return {secret=true} end",
                     "C_Spell.GetSpellCooldown=function() error('restricted') end"):
            self.runlua('C_Spell.IsSpellUsable=function() return true,false end'); self.runlua(code); row.scripts.OnEnter()
            lines=list(self.lua.globals().LINES.values())
            self.assertFalse(any('Ready by current checks' in x for x in lines))
            self.assertTrue(any('unavailable' in x for x in lines))

    def test_hover_readiness_refreshes_without_stealing_other_tooltip(self):
        row=self.readiness_tooltip(); row.scripts.OnEnter()
        self.runlua('C_Spell.IsSpellInRange=function() return false end')
        self.panel.frame.scripts.OnUpdate(self.panel.frame,0.3)
        self.assertTrue(any('Out of range' in x for x in self.lua.globals().LINES.values()))
        self.runlua("GameTooltip.owner={}; LINES={'other tooltip'}")
        self.panel.frame.scripts.OnUpdate(self.panel.frame,0.3)
        self.assertEqual(self.lua.globals().LINES[1],'other tooltip')

    def test_quest_bag_mirrors_questie_and_clears_on_completion_or_reuse(self):
        self.runlua("""
            AddUnit('target',true); GUID='Creature-0-1-2-3-100-0001'
            function UnitGUID(u) if u=='target' then return GUID end end
            CALLS=0; ICON='bag'
            Questie={icons={loot='bag'},db={profile={}},API={isReady=true,
                GetQuestObjectiveIconForUnit=function(guid) CALLS=CALLS+1; return ICON end}}
        """)
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertTrue(row.questIcon.shown)
        self.assertEqual(row.questTexture,'bag')
        calls=self.lua.globals().CALLS
        self.panel.Refresh(self.panel)
        self.assertEqual(self.lua.globals().CALLS,calls)
        self.runlua('ICON=nil')
        self.panel.events.scripts.OnEvent(self.panel.events,'QUEST_LOG_UPDATE')
        self.assertFalse(row.questIcon.shown)
        self.runlua("ICON='bag'; GUID='Creature-0-1-2-3-101-0002'")
        self.panel.Refresh(self.panel)
        self.assertTrue(row.questIcon.shown)
        self.runlua("GUID={secret=true}")
        self.panel.Refresh(self.panel)
        self.assertFalse(row.questIcon.shown)
        self.assertIsNone(row.questTexture)

    def test_quest_badge_ignores_unrelated_icons_and_unready_questie(self):
        self.runlua("""
            AddUnit('target',true)
            function UnitGUID(u) if u=='target' then return 'Creature-0-1-2-3-100-0001' end end
            Questie={icons={loot='bag'},db={profile={ICON_LOOT='custombag'}},API={isReady=true,
                GetQuestObjectiveIconForUnit=function() return 'talk' end}}
        """)
        self.panel.Refresh(self.panel); row=self.panel.rows[1]
        self.assertFalse(row.questIcon.shown)
        self.runlua("Questie.API.GetQuestObjectiveIconForUnit=function() return 'custombag' end")
        self.panel.events.scripts.OnEvent(self.panel.events,'QUEST_LOG_UPDATE')
        self.assertTrue(row.questIcon.shown)
        self.runlua('Questie.API.isReady=false')
        self.panel.Refresh(self.panel)
        self.assertFalse(row.questIcon.shown)

    def test_quest_swords_follow_default_and_custom_icons_and_clear(self):
        self.runlua("""
            AddUnit('target',true)
            function UnitGUID(u) if u=='target' then return 'Creature-0-1-2-3-100-0001' end end
            ICON='swords'
            Questie={icons={loot='bag',slay='swords'},db={profile={ICON_SLAY='customswords'}},
                API={isReady=true,GetQuestObjectiveIconForUnit=function() return ICON end}}
        """)
        self.panel.Refresh(self.panel); row=self.panel.rows[1]
        self.assertTrue(row.questIcon.shown)
        self.assertEqual(row.questTexture,'swords')
        for icon in ('customswords','bag','swords'):
            self.runlua("ICON='"+icon+"'")
            self.panel.events.scripts.OnEvent(self.panel.events,'QUEST_LOG_UPDATE')
            self.assertTrue(row.questIcon.shown)
            self.assertEqual(row.questTexture,icon)
        self.runlua('ICON=nil')
        self.panel.events.scripts.OnEvent(self.panel.events,'QUEST_LOG_UPDATE')
        self.assertFalse(row.questIcon.shown)
        self.assertIsNone(row.questTexture)

    def test_recent_heal_error_is_shown_only_on_clicked_identity_and_expires(self):
        row=self.readiness_tooltip()
        row.scripts.PreClick(row,'LeftButton',True)
        self.panel.events.scripts.OnEvent(self.panel.events,'UI_ERROR_MESSAGE',57,"I can't do that while moving")
        row.scripts.OnEnter()
        self.assertTrue(any("I can't do that while moving" in x for x in self.lua.globals().LINES.values()))
        self.runlua("UNITS.party1.name='Different player'")
        self.panel.Refresh(self.panel); row.scripts.OnEnter()
        self.assertFalse(any("I can't do that while moving" in x for x in self.lua.globals().LINES.values()))
        self.runlua('NOW=20')
        row.scripts.OnEnter()
        self.assertFalse(any('Game message after' in x for x in self.lua.globals().LINES.values()))

    def test_disabled_heal_click_does_not_capture_unrelated_game_error(self):
        row=self.readiness_tooltip()
        self.panel.healLeft=None
        row.scripts.PreClick(row,'LeftButton',True)
        self.panel.events.scripts.OnEvent(self.panel.events,'UI_ERROR_MESSAGE',1,'Unrelated error')
        self.assertIsNone(row.lastHealError)

    def test_literal_enemy_alias_binds_without_identity_self_comparison(self):
        self.enable_damage()
        self.runlua("AddUnit('target',true); function UnitIsUnit() return {secret=true} end")
        row=self.panel.rows[1]
        self.ns.NearbyHealing.Bind(self.ns.NearbyHealing,row,'target',None,None,'Lightning Bolt','Earth Shock')
        self.assertEqual(row.attrs.unit,'target')
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')

    def test_select_cast_macro_cannot_rebind_during_same_mouse_click(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true)")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs.type1,'macro')
        row.scripts.PreClick(row,'LeftButton',True)
        self.runlua('UNITS.target=UNITS.nameplate1')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.type1,'macro')
        row.scripts.PostClick(row,'LeftButton',False)
        self.assertEqual(row.attrs.unit,'target')
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')

    def test_select_cast_combat_binding_stays_exact_and_stale_slot_is_quiet(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true)")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua('COMBAT=true; UNITS.target=UNITS.nameplate1')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.type1,'macro')
        self.assertEqual(row.attrs.unit,'nameplate1')
        self.runlua('UNITS.nameplate1=nil; UNITS.target=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(row.name.text,'')
        self.assertAlmostEqual(row.alpha,0.15)
        self.assertIn('1 inactive',self.panel.footer.text)
        self.runlua("AddUnit('nameplate1',true)")
        self.panel.Refresh(self.panel)
        self.assertEqual(row.alpha,1)

    def test_right_release_cannot_clear_pending_left_target_click(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); HELD=true; function IsMouseButtonDown() return HELD end")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        row.scripts.PreClick(row,'LeftButton',True)
        self.runlua('UNITS.target=UNITS.nameplate1')
        row.scripts.PostClick(row,'RightButton',False)
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs.type1,'macro')
        self.runlua('HELD=false')
        row.scripts.PostClick(row,'LeftButton',False)
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')

    def test_inactive_target_only_tooltip_does_not_offer_selection(self):
        self.enable_damage()
        self.runlua("""
            AddUnit('nameplate1',true)
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.runlua('COMBAT=true; UNITS.nameplate1=nil')
        self.panel.Refresh(self.panel); row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertIn('Inactive slot; list refreshes after combat.',lines)
        self.assertFalse(any('Left-click: target' in x for x in lines))

    def test_enemy_tooltip_distinguishes_select_cast_from_direct_spell_clicks(self):
        self.enable_damage()
        self.runlua("""
            AddUnit('nameplate1',true)
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
            C_Spell.IsSpellInRange=function() return true end
            C_Spell.IsSpellUsable=function() return true,false end
            C_Spell.GetSpellCooldown=function() return {startTime=0,duration=0,isEnabled=true} end
        """)
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]; row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertIn('Left: select and cast Lightning Bolt',lines)
        self.assertIn('Right: no supported spell target',lines)
        self.assertTrue(any('Left: Ready by current checks' in x for x in lines))
        self.runlua('UNITS.target=UNITS.nameplate1')
        self.panel.Refresh(self.panel); row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertIn('Left: Lightning Bolt',lines)
        self.assertTrue(any('Left: Ready by current checks' in x for x in lines))
        self.assertTrue(any('Right: Ready by current checks' in x for x in lines))
        self.runlua('COMBAT=true; C_Spell.IsSpellInRange=function() return false end')
        self.panel.Refresh(self.panel); row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertTrue(any('Out of range' in x for x in lines))
        self.assertFalse(any('Ready by current checks' in x for x in lines))
        self.assertEqual(row.attrs['spell-damageLeft'],'Lightning Bolt')
        self.assertEqual(row.attrs['spell-damageRight'],'Earth Shock')
        self.runlua('C_Spell.IsSpellInRange=function() return true end; C_Spell.IsSpellUsable=function() return {secret=true}, {secret=true} end')
        row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertFalse(any('Ready by current checks' in x for x in lines))
        self.assertTrue(any('Mana check unavailable' in x for x in lines))

    def test_kill_objective_hover_is_not_described_as_loot(self):
        self.enable_damage()
        self.runlua("""
            AddUnit('target',true)
            function UnitGUID(u) if u=='target' then return 'Creature-0-1-2-3-100-0001' end end
            ICON='swords'
            Questie={icons={loot='bag',slay='swords'},API={isReady=true,
                GetQuestObjectiveIconForUnit=function() return ICON end}}
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        self.panel.Refresh(self.panel); row=self.panel.rows[1]; row.scripts.OnEnter()
        self.assertIn('Questie: unfinished kill objective',list(self.lua.globals().LINES.values()))
        self.runlua("ICON='bag'")
        self.panel.events.scripts.OnEvent(self.panel.events,'QUEST_LOG_UPDATE'); row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertIn('Questie: active quest-item or object objective',lines)
        self.assertNotIn('Questie: unfinished kill objective',lines)

    def test_enemy_macro_exact_token_guards_and_no_current_target_clear(self):
        healing=self.ns.NearbyHealing
        for unit in ('nameplate1','nameplate200','focus','focustarget'):
            macro=healing.EnemyMacro(healing,unit,'Lightning Bolt')
            self.assertEqual(macro.splitlines(),[
                '/cleartarget',
                '/target [@'+unit+',exists,harm,nodead]',
                '/cast [@target,exists,harm,nodead] Lightning Bolt'])
        for unit in ('target','Goblin Craftsman','nameplate1; /target enemy','party1',None):
            self.assertIsNone(healing.EnemyMacro(healing,unit,'Lightning Bolt'))
        for spell in ('Lightning Bolt\n/startattack','[harm] Lightning Bolt',None,'X'*161):
            self.assertIsNone(healing.EnemyMacro(healing,'nameplate200',spell))

    def test_enemy_macro_cleared_when_row_reused_for_friend_and_disabled_left(self):
        self.enable_damage()
        self.runlua("AddUnit('nameplate1',true); UNITS.focus=UNITS.nameplate1")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertEqual(row.attrs['type-damageLeft'],'macro')
        self.assertIn('/target [@focus,',row.attrs['macrotext-damageLeft'])
        self.assertEqual(row.attrs['type-damageRight'],'spell')
        self.assertFalse(row.hasHealingAction)
        self.runlua('COMBAT=true')
        before=row.attrs['macrotext-damageLeft']
        self.panel.Refresh(self.panel)
        self.assertEqual(row.attrs['macrotext-damageLeft'],before)
        self.runlua('COMBAT=false; UNITS.nameplate1.enemy=false; UNITS.nameplate1.player=true')
        self.panel.Refresh(self.panel)
        self.assertIsNone(row.attrs['macrotext-damageLeft'])
        self.assertIsNone(row.attrs.macrotext1)
        self.assertEqual(row.attrs['type-healLeft'],'spell')
        self.runlua('UNITS.nameplate1.enemy=true; UNITS.nameplate1.player=false; UNITS.focus=nil')
        self.addon.db.enemyLeftID=0; self.panel.healsDirty=True
        self.panel.Refresh(self.panel)
        self.assertFalse(row.enemySelectCast)
        self.assertIsNone(row.attrs.macrotext1)
        self.assertEqual(row.attrs.type1,'target')

    def test_drag_interrupted_by_combat_reanchors_top_after_combat(self):
        self.panel.frame.GetTop=self.lua.eval('function() return 740 end')
        self.panel.frame.scripts.OnDragStart()
        self.panel.frame.SetPoint(self.panel.frame,'CENTER',self.lua.globals().UIParent,'CENTER',0,0)
        self.runlua('COMBAT=true')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_DISABLED')
        self.assertEqual(self.panel.frame.point[1],'CENTER')
        self.assertTrue(self.panel.moving or self.panel.dragAnchorPending)
        self.runlua('COMBAT=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_ENABLED')
        self.assertEqual(self.panel.frame.point[1],'TOP')
        self.assertEqual(self.addon.db.enemyY,240)
        self.assertFalse(self.panel.moving)
        self.assertFalse(self.panel.dragAnchorPending)

    def split_panels(self):
        self.runlua("""
            function IsInGroup() return true end
            AddUnit('player',false); UNITS.player.player=true
            AddUnit('party1',false); UNITS.party1.player=true
            AddUnit('nameplate1',true)
            AddUnit('nameplate2',false); UNITS.nameplate2.player=true
            C_Spell.IsSpellInRange=function() return false end
        """)
        targets=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon,'targets')
        group=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon,'group')
        self.addon.enemies=targets; self.addon.groupMembers=group
        return targets,group

    def test_split_group_window_has_own_rows_and_preserves_heal_fade(self):
        targets,group=self.split_panels()
        self.assertEqual(group.title.text,'Mojow Group')
        self.assertEqual(targets.title.text,'Mojow Extended Target List')
        self.assertEqual(group.rows[1].boundUnit,'player')
        self.assertEqual(group.rows[2].boundUnit,'party1')
        self.assertEqual(group.rows[2].attrs['spell-healLeft'],'Healing Wave')
        self.assertAlmostEqual(group.rows[2].health.alpha,0.35)
        self.assertEqual(targets.rows[1].boundUnit,'nameplate1')
        self.assertEqual(targets.rows[2].boundUnit,'nameplate2')
        self.assertFalse(targets.headers[1].shown)
        self.assertFalse(group.headers[2].shown)
        self.assertIsNone(group.combatRows)
        self.assertIsNotNone(targets.combatRows[1])
        self.assertFalse(group.assistSummary.shown)

    def test_split_windows_hide_and_move_independently(self):
        targets,group=self.split_panels()
        targets.SetVisible(targets,False)
        self.assertTrue(group.frame.shown)
        self.assertTrue(self.addon.db.enemyShowGroup)
        self.runlua('UNITS.party1.hp=42')
        group.frame.scripts.OnUpdate(group.frame,0.2)
        self.assertEqual(group.rows[2].health.value,42)
        old_x=self.addon.db.enemyX; old_y=self.addon.db.enemyY
        group.frame.GetTop=self.lua.eval('function() return 800 end')
        group.frame.GetCenter=self.lua.eval('function() return 600,500 end')
        group.frame.scripts.OnDragStart(); group.frame.scripts.OnDragStop()
        self.assertEqual((self.addon.db.groupX,self.addon.db.groupY),(100,300))
        self.assertEqual((self.addon.db.enemyX,self.addon.db.enemyY),(old_x,old_y))
        self.assertEqual(group.frame.point[1],'TOP')
        group.SetVisible(group,False)
        self.assertFalse(self.addon.db.enemyShowGroup)
        targets.SetVisible(targets,True)
        self.assertFalse(group.frame.shown)
        saved=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual((saved.groupX,saved.groupY),(100,300))
        self.assertFalse(saved.enemyShowGroup)

    def test_split_group_bindings_freeze_in_combat_and_refresh_after(self):
        targets,group=self.split_panels()
        self.runlua("COMBAT=true; AddUnit('party2',false); UNITS.party2.player=true")
        group.events.scripts.OnEvent(group.events,'GROUP_ROSTER_UPDATE')
        self.assertEqual(group.rows[2].attrs.unit,'party1')
        self.assertFalse(group.rows[3].shown)
        self.assertFalse(group.SetVisible(group,False))
        self.assertTrue(group.frame.shown)
        self.runlua('COMBAT=false')
        group.events.scripts.OnEvent(group.events,'PLAYER_REGEN_ENABLED')
        self.assertEqual(group.rows[3].attrs.unit,'party2')
        self.assertEqual(group.rows[3].attrs['spell-healLeft'],'Healing Wave')

    def test_healing_choice_updates_both_split_windows(self):
        targets,group=self.split_panels()
        self.runlua('function IsSpellKnown() return true end')
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,targets,'left',8004,False))
        self.assertEqual(group.rows[2].attrs['spell-healLeft'],'Lesser Healing Wave')
        self.assertIn('Lesser Healing Wave',targets.rows[2].attrs.macrotext1)

    def test_group_left_click_selects_then_heals_exact_group_token(self):
        targets,group=self.split_panels()
        row=group.rows[2]
        self.assertEqual(row.attrs['type-healLeft'],'macro')
        self.assertEqual(row.attrs['macrotext-healLeft'],
            '/target [@party1,exists]\n/cast [@party1,exists,help,nodead] Healing Wave')
        self.assertEqual(group.rows[1].attrs['macrotext-healLeft'],
            '/target [@player,exists]\n/cast [@player,exists,help,nodead] Healing Wave')
        self.assertEqual(row.attrs['type-healRight'],'spell' if row.attrs['spell-healRight'] else None)
        self.assertEqual(row.attrs['shift-type-healRight'],'togglemenu')
        before=row.attrs['macrotext-healLeft']
        self.runlua('COMBAT=true')
        group.Refresh(group)
        self.assertEqual(row.attrs['macrotext-healLeft'],before)
        self.assertEqual(row.attrs.unit,'party1')
        self.runlua('COMBAT=false')
        self.assertTrue(self.ns.NearbyHealing.Choose(self.ns.NearbyHealing,targets,'left',0,False))
        self.assertEqual(row.attrs.type1,'target')
        self.assertEqual(row.attrs['type-healLeft'],'target')
        self.assertIsNone(row.attrs['macrotext-healLeft'])
        self.assertIsNone(row.attrs.macrotext1)

    def test_group_target_heal_macro_rejects_non_group_tokens(self):
        healing=self.ns.NearbyHealing
        self.assertIn('[@raid40,exists]',healing.GroupMacro(healing,'raid40','Healing Wave'))
        for unit in ('party5','raid41','target','nameplate1','Lost','party1; /target Other'):
            self.assertIsNone(healing.GroupMacro(healing,unit,'Healing Wave'))
        self.assertIsNone(healing.GroupMacro(healing,'party1','Healing Wave\n/startattack'))

    def test_group_selection_tooltip_and_row_reuse_clear_macro(self):
        targets,group=self.split_panels()
        self.runlua("""
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        row=group.rows[2]; row.scripts.OnEnter()
        self.assertIn('Left: select and heal with Healing Wave',list(self.lua.globals().LINES.values()))
        self.ns.NearbyHealing.Bind(self.ns.NearbyHealing,row,None,None,None)
        self.assertIsNone(row.attrs['macrotext-healLeft'])
        self.assertIsNone(row.attrs.macrotext1)
        self.assertIsNone(row.groupSelectUnit)

    def test_group_binding_never_adds_damage_for_hostile_roster_token(self):
        targets,group=self.split_panels()
        self.runlua('UNITS.party1.enemy=true')
        row=group.rows[2]
        self.ns.NearbyHealing.Bind(self.ns.NearbyHealing,row,'party1','Healing Wave',None,'Lightning Bolt','Earth Shock')
        self.assertEqual(row.attrs.unit,'party1')
        self.assertEqual(row.attrs.type1,'macro')
        self.assertIn('/target [@party1,exists]',row.attrs.macrotext1)
        self.assertIn('/cast [@party1,exists,help,nodead]',row.attrs.macrotext1)
        self.assertIsNone(row.attrs.harmbutton1)
        self.assertIsNone(row.attrs['spell-damageLeft'])

    def test_group_tooltip_puts_clicks_before_status_and_quest_details(self):
        targets,group=self.split_panels()
        self.runlua("""
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        row=group.rows[2]; row.questTexture='swords'; row.questKind='kill'
        row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertEqual(lines[0],'party1')
        self.assertEqual(lines[1],'Left: select and heal with Healing Wave')
        self.assertTrue(lines[2].startswith('Right:'))
        self.assertEqual(lines[3],'Shift-right-click: player menu')
        self.assertGreater(lines.index('Questie: unfinished kill objective'),3)
        self.assertGreater(lines.index('Too far to heal'),3)

    def test_inactive_tooltip_does_not_repeat_stale_details(self):
        targets,group=self.split_panels()
        self.runlua("""
            LINES={}; GameTooltip={SetOwner=function() LINES={} end,
                AddLine=function(self,line) table.insert(LINES,line) end,Show=function() end}
        """)
        row=group.rows[2]; row.displayUnavailable=True
        row.questTexture='swords'; row.questKind='kill'
        row.scripts.OnEnter()
        lines=list(self.lua.globals().LINES.values())
        self.assertEqual(len(lines),2)
        self.assertEqual(lines[1],'Inactive slot; list refreshes after combat.')

    def test_group_poison_label_requires_learned_cure_and_keeps_heal_action(self):
        self.lua.execute((ROOT/'DispelHelper.lua').read_text(),'MojowAssist',self.ns)
        self.runlua("""
            local previous=C_Spell.GetSpellInfo
            C_Spell.GetSpellInfo=function(id) if id==526 then return {name='Cure Poison'} end return previous(id) end
            CUREKNOWN=false
            function IsSpellKnown(id) return id==331 or (id==526 and CUREKNOWN) end
            AddUnit('party1',false); UNITS.party1.player=true
            C_UnitAuras={GetAuraDataByIndex=function(u,i) if i==1 then return {dispelName='Poison'} end end}
        """)
        panel=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon,'group')
        panel.Refresh(panel)
        row=panel.rows[1]
        self.assertNotIn('[Poison]',row.name.text)
        before=row.attrs.macrotext1
        self.runlua('CUREKNOWN=true')
        panel.healsDirty=True; panel.Refresh(panel)
        self.assertIn('[Poison]',row.name.text)
        self.assertEqual(row.attrs.macrotext1,before)
        self.runlua("C_UnitAuras.GetAuraDataByIndex=function() error('restricted') end")
        row.dispelNext=0; panel.Refresh(panel)
        self.assertNotIn('[Poison]',row.name.text)
        self.assertEqual(row.dispelData.kind,'unknown')
