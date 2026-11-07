from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

class EnemyTests(unittest.TestCase):
    def test_self_alias_category_uses_identity_not_npc_flag_or_name(self):
        self.runlua("AddUnit('player',false); UNITS.player.player=false; UNITS.target=UNITS.player")
        self.assertIsNone(self.roster.Category(self.roster,'target'))
        self.runlua('function IsInGroup() return true end')
        self.assertEqual(self.roster.Category(self.roster,'player'),'group')
        self.runlua("AddUnit('nameplate1',true); UNITS.nameplate1.name=UNITS.player.name")
        self.assertEqual(self.roster.Category(self.roster,'nameplate1'),'npc')

    def test_friendly_players_included_but_not_friendly_npcs_or_self(self):
        self.runlua("""
            AddUnit('nameplate1',false); UNITS.nameplate1.player=true
            AddUnit('nameplate2',false)
            AddUnit('nameplate3',false); UNITS.nameplate3.player=true
            UNITS.player=UNITS.nameplate3; UNITS.target=UNITS.nameplate1
        """)
        for unit in ('nameplate1','nameplate2','nameplate3'): self.roster.Add(self.roster,unit)
        self.assertEqual(len(self.rows()[0]),1)
        self.assertEqual(self.rows()[0][1],'nameplate1')

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.ns = self.lua.table()
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute((ROOT/'Appearance.lua').read_text(), 'MojowAssist', self.ns)
        self.lua.execute('''
            UNITS = {}; NOW = 10
            function IsInGroup() return false end
            function GetTime() return NOW end
            function UnitExists(u) return UNITS[u] ~= nil end
            function UnitCanAttack(_,u) return UNITS[u] and UNITS[u].enemy end
            function UnitIsDeadOrGhost(u) return UNITS[u] and UNITS[u].dead end
            function UnitIsUnit(a,b) return UNITS[a] and UNITS[a] == UNITS[b] end
            function UnitName(u) return UNITS[u] and UNITS[u].name end
            function UnitHealth(u) return UNITS[u].hp end
            function UnitHealthMax(u) return UNITS[u].max end
            function UnitIsPlayer(u) return UNITS[u].player end
            function UnitClass(u) return 'Class',UNITS[u].class end
            function UnitCastingInfo(u)
                local x=UNITS[u]; if x.cast then return x.cast,nil,nil,x.startMS,x.endMS end
            end
            function UnitChannelInfo(u)
                local x=UNITS[u]; if x.channel then return x.channel,nil,nil,x.startMS,x.endMS end
            end
            function AddUnit(u, enemy)
                UNITS[u]={name=u,enemy=enemy,hp=70,max=100}
            end
        ''')
        self.lua.execute((ROOT/'EnemyRoster.lua').read_text(), 'MojowAssist', self.ns)
        self.roster = self.ns.EnemyRoster.Create(self.ns.EnemyRoster)

    def runlua(self, code):
        self.lua.execute(code)

    def rows(self):
        return self.roster.Snapshot(self.roster)

    def test_group_members_without_nameplates_and_deduplication(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; AddUnit('party2',false); UNITS.party2.player=true; UNITS.nameplate1=UNITS.party1")
        self.roster.Add(self.roster,'nameplate1')
        rows,_=self.rows()
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1],'party1')
        self.assertEqual(rows[2],'party2')

    def test_group_tokens_classify_even_when_player_flag_restricted(self):
        self.runlua("AddUnit('raid1',false); UNITS.raid1.player={secret=true}")
        self.assertEqual(self.roster.Category(self.roster,'raid1'),'group')
        rows,_=self.rows()
        self.assertEqual(rows[1],'raid1')

    def test_guid_merges_group_nameplate_when_unit_comparison_fails(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            AddUnit('nameplate1',false); UNITS.nameplate1.player=true
            function UnitIsUnit() return false end
            GUIDS={party1='Player-1-123',nameplate1='Player-1-123'}
        """)
        self.roster.Add(self.roster,'nameplate1')
        rows,_=self.rows()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[1],'party1')

    def test_secret_guids_and_similar_names_are_not_identity_keys(self):
        self.runlua("""
            AddUnit('party1',false); UNITS.party1.player=true
            AddUnit('nameplate1',false); UNITS.nameplate1.player=true
            UNITS.party1.name='Same'; UNITS.nameplate1.name='Same'
            function UnitIsUnit() return false end
            GUIDS={party1={secret=true},nameplate1={secret=true}}
        """)
        self.roster.Add(self.roster,'nameplate1')
        rows,_=self.rows()
        self.assertEqual(len(rows),2)

    def test_hostiles_only_and_remove(self):
        self.runlua("AddUnit('nameplate1',true); AddUnit('nameplate2',false)")
        for u in ('nameplate1','nameplate2'): self.roster.Add(self.roster,u)
        self.assertEqual(len(self.rows()[0]),1)
        self.roster.Remove(self.roster,'nameplate1')
        self.assertEqual(len(self.rows()[0]),0)

    def test_token_reuse_and_unknown_hostility(self):
        self.runlua("AddUnit('nameplate1',true)")
        self.roster.Add(self.roster,'nameplate1')
        self.assertEqual(len(self.rows()[0]),1)
        self.roster.Remove(self.roster,'nameplate1')
        self.runlua("AddUnit('nameplate1',{secret=true})")
        self.roster.Add(self.roster,'nameplate1')
        rows, unknown = self.rows()
        self.assertEqual(len(rows),0)
        self.assertEqual(unknown,1)

    def test_target_and_focus_deduplicate(self):
        self.runlua("AddUnit('nameplate1',true); UNITS.target=UNITS.nameplate1; UNITS.focus=UNITS.target")
        self.roster.Add(self.roster,'nameplate1')
        self.assertEqual(len(self.rows()[0]),1)

    def test_dead_and_changed_friendly_disappear(self):
        self.runlua("AddUnit('nameplate1',true)")
        self.roster.Add(self.roster,'nameplate1')
        self.runlua("UNITS.nameplate1.dead=true")
        self.assertEqual(len(self.rows()[0]),0)
        self.runlua("UNITS.nameplate1.dead=false; UNITS.nameplate1.enemy=false")
        self.assertEqual(len(self.rows()[0]),0)

    def test_cast_channel_and_secret_timing(self):
        self.runlua("AddUnit('target',true); UNITS.target.cast='Bolt'; UNITS.target.startMS=9000; UNITS.target.endMS=12000")
        cast = self.roster.Cast(self.roster,'target')
        self.assertEqual(cast.remaining,2)
        self.assertFalse(cast.channel)
        self.runlua("UNITS.target.cast=nil; UNITS.target.channel='Drain'")
        self.assertTrue(self.roster.Cast(self.roster,'target').channel)
        self.runlua("UNITS.target.endMS={secret=true}")
        self.assertTrue(self.roster.Cast(self.roster,'target').restricted)

    def test_expired_and_invalid_cast(self):
        self.runlua("AddUnit('target',true); UNITS.target.cast='Bolt'; UNITS.target.startMS=9000; UNITS.target.endMS=10000")
        self.assertIsNone(self.roster.Cast(self.roster,'target'))
        self.runlua("UNITS.target.endMS=math.huge")
        self.assertTrue(self.roster.Cast(self.roster,'target').restricted)

    def test_invalid_tokens_ignored(self):
        for token in ('player', 'party1', 'nameplate99999', 'nameplate0'):
            self.roster.Add(self.roster,token)
        self.assertEqual(len(self.roster.order),0)

    def test_stable_order_and_clear(self):
        for n in (3,1,2):
            u=f'nameplate{n}'
            self.runlua(f"AddUnit('{u}',true)")
            self.roster.Add(self.roster,u)
            self.roster.Add(self.roster,u)
        self.assertEqual([self.rows()[0][i] for i in (1,2,3)],['nameplate3','nameplate1','nameplate2'])
        self.roster.Clear(self.roster)
        self.assertEqual(len(self.rows()[0]),0)

class EnemyPanelTests(EnemyTests):
    def test_sections_filter_and_restore(self):
        self.runlua("""
            AddUnit('nameplate1',false); UNITS.nameplate1.player=true
            AddUnit('nameplate2',true); UNITS.nameplate2.player=true
            AddUnit('nameplate3',true)
        """)
        for unit in ('nameplate1','nameplate2','nameplate3'): self.roster.Add(self.roster,unit)
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].name.text,'[?] nameplate3')
        self.assertEqual(self.panel.rows[2].name.text,'[?] nameplate2')
        self.assertEqual(self.panel.rows[3].name.text,'[?] nameplate1')
        self.addon.db.enemyShowFriendlyPlayers=False
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[3].shown)
        self.assertFalse(self.panel.headers[4].shown)
        self.addon.db.enemyShowNPCs=False
        self.addon.db.enemyShowEnemyPlayers=False
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[1].shown)
        self.addon.db.enemyShowFriendlyPlayers=True
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].name.text,'[?] nameplate1')

    def test_friendly_player_class_health_and_no_false_aggro(self):
        self.runlua("""
            AddUnit('target',false); UNITS.target.player=true; UNITS.target.class='MAGE'
            AddUnit('player',false); UNITS.targettarget=UNITS.player
            RAID_CLASS_COLORS={MAGE={r=.4,g=.8,b=1}}
            function UnitAffectingCombat() return true end
        """)
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.rows[1].shown)
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.85)
        self.assertEqual(self.panel.rows[1].health.value,70)
        self.assertEqual(self.panel.rows[1].name.text,'[?] target')

    def test_personal_aggro_marker_and_clear(self):
        self.runlua("""
            AddUnit('target',true); AddUnit('player',false)
            function UnitThreatSituation() return THREAT end
            function UnitAffectingCombat() return COMBAT end
        """)
        for status, marked in [('0',False),('1',False),('2',True),('3',True),('nil',False),('{secret=true}',False)]:
            self.runlua('THREAT='+status)
            self.panel.Refresh(self.panel)
            self.assertEqual((self.panel.rows[1].statusPrimary=='Attacking you'),marked)
        self.runlua('COMBAT=true; UNITS.targettarget=UNITS.player')
        self.panel.Refresh(self.panel)
        self.assertTrue((self.panel.rows[1].statusPrimary=='Attacking you'))
        self.runlua('COMBAT=false; UNITS.targettarget=nil')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].name.text,'[?] target')

    def test_neutral_aggro_and_reset_colors(self):
        self.runlua("""
            AddUnit('target',true)
            REACTION=4; THREAT=nil; COMBAT=false; GROUP=false
            function UnitReaction() return REACTION end
            function UnitThreatSituation(ally) if ally=='player' then return THREAT end end
            function UnitAffectingCombat() return COMBAT end
            function UnitInParty() return GROUP end
        """)
        for state, green in [('THREAT=nil',.65), ('THREAT=0',.23),
                             ('THREAT=nil; COMBAT=true; GROUP=true',.23),
                             ('GROUP=false',.65), ('REACTION=3',.23),
                             ('REACTION={secret=true}',.23)]:
            self.runlua(state)
            self.panel.Refresh(self.panel)
            self.assertAlmostEqual(self.panel.rows[1].health.color[2],green)

    def test_level_labels_and_reused_row(self):
        self.runlua("AddUnit('target',true); function UnitLevel(u) return UNITS[u].level end")
        for value, label in [('12','12'), ('-1','??'), ('nil','?'), ('{secret=true}','?'), ('0','?')]:
            self.runlua('UNITS.target.level='+value)
            self.panel.Refresh(self.panel)
            self.assertEqual(self.panel.rows[1].name.text, '['+label+'] target')

    def setUp(self):
        super().setUp()
        self.lua.execute((ROOT/'NativeRaidMarker.lua').read_text(), 'MojowAssist', self.ns)
        self.lua.execute((ROOT/'EnemyPanel.lua').read_text(), 'MojowAssist', self.ns)
        self.lua.execute((ROOT/'Model.lua').read_text(), 'MojowAssist', self.ns)
        self.addon=self.lua.table()
        self.addon.db=self.ns.Model.Normalize(self.ns.Model,self.lua.table())
        self.panel=self.ns.EnemyPanel.Create(self.ns.EnemyPanel,self.addon)
        self.roster=self.panel.roster

    def test_restricted_name_forwarded_only_to_native_text(self):
        self.runlua("AddUnit('target',true); SECRETNAME={secret=true}; UNITS.target.name=SECRETNAME")
        row=self.panel.rows[1]
        row.name.SetFormattedText=self.lua.eval("function(self,fmt,prefix,level,name) assert(name==SECRETNAME); self.nativeName=name end")
        self.panel.Refresh(self.panel)
        self.assertTrue(row.name.nativeName.secret)
        self.assertIsNone(row.macroName)

    def test_party_section_precedes_crowded_npc_rows(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true")
        for index in range(1,14):
            self.runlua("AddUnit('nameplate%d',true)" % index)
            self.roster.Add(self.roster,'nameplate%d' % index)
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].boundUnit,'party1')
        self.assertIn('Group Members',self.panel.headers[1].text)

    def test_group_and_ungrouped_have_separate_sections_and_filters(self):
        self.runlua("AddUnit('party1',false); UNITS.party1.player=true; AddUnit('nameplate1',false); UNITS.nameplate1.player=true")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.headers[1].text,'Group Members  1')
        self.assertEqual(self.panel.headers[4].text,'Nearby Friendly Players  1')
        self.assertEqual(self.panel.rows[1].boundUnit,'party1')
        self.addon.db.enemyShowFriendlyPlayers=False
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].boundUnit,'party1')
        self.assertFalse(self.panel.rows[2].shown)
        self.addon.db.enemyShowGroup=False
        self.addon.db.enemyShowFriendlyPlayers=True
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].boundUnit,'nameplate1')

    def native_setup(self, channel=False):
        self.runlua("""
            AddUnit('target',true)
            SECRET={secret=true}
            DURATION={GetRemainingDuration=function() return SECRET end}
            Enum.StatusBarInterpolation={Immediate=0}
            Enum.StatusBarTimerDirection={RemainingTime=1,ElapsedTime=0}
            function UnitCastingDuration() return DURATION end
            function UnitChannelDuration() return nil end
            UNITS.target.cast=SECRET
        """)
        if channel:
            self.runlua("function UnitCastingDuration() return nil end; function UnitChannelDuration() return DURATION end; UNITS.target.cast=nil; UNITS.target.channel=SECRET")

    def test_native_timer_clears_on_nameplate_reuse(self):
        self.native_setup()
        self.runlua("UNITS.nameplate1=UNITS.target; UNITS.target=nil; function UnitCastingDuration(u) if u=='nameplate1' then return DURATION end end")
        self.roster.Add(self.roster,'nameplate1')
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.rows[1].nativeCast.shown)
        self.panel.events.scripts.OnEvent(self.panel.events,'NAME_PLATE_UNIT_REMOVED','nameplate1')
        self.runlua("AddUnit('nameplate1',true); function UnitCastingDuration() return nil end")
        self.panel.events.scripts.OnEvent(self.panel.events,'NAME_PLATE_UNIT_ADDED','nameplate1')
        self.assertFalse(self.panel.rows[1].nativeCast.shown)
        self.assertEqual(self.panel.rows[1].spell.text,'')

    def test_class_api_failure_resets_previous_color(self):
        self.runlua("AddUnit('target',true); UNITS.target.player=true; UNITS.target.class={secret=true}; C_ClassColor={GetClassColor=function() error('unavailable') end}")
        self.panel.rows[1].health.SetStatusBarColor(self.panel.rows[1].health,1,1,1)
        self.panel.Refresh(self.panel)
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.85)
        self.assertEqual(self.panel.rows[1].name.textColor[1],1)

    def test_countdown_failure_is_reported_separately(self):
        self.native_setup()
        self.runlua("function DURATION:GetRemainingDuration() error('unavailable') end")
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.nativeTimerFailed)
        self.assertTrue(self.panel.rows[1].nativeCast.shown)

    def test_native_cast_opaque_name_and_countdown(self):
        self.native_setup()
        self.panel.Refresh(self.panel)
        row=self.panel.rows[1]
        self.assertTrue(row.nativeCast.shown)
        self.assertTrue(row.nativeSpell.formattedValue.secret)
        self.assertTrue(row.nativeTimer.formattedValue.secret)
        self.assertEqual(row.nativeCast.direction,1)
        self.assertFalse(row.cast.shown)

    def test_native_channel_and_stop_clear(self):
        self.native_setup(channel=True)
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.rows[1].nativeCast.shown)
        self.runlua("function UnitChannelDuration() return nil end; UNITS.target.channel=nil")
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[1].nativeCast.shown)
        self.assertEqual(self.panel.rows[1].spell.text,'')

    def test_native_failure_can_use_readable_legacy_cast(self):
        self.native_setup()
        self.lua.globals().badrow=self.panel.rows[1]
        self.runlua("function badrow.nativeCast:SetTimerDuration() error('unsupported') end; UNITS.target.cast='Bolt'; UNITS.target.startMS=9000; UNITS.target.endMS=12000")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].spell.text,'Casting: Bolt')
        self.assertEqual(self.panel.rows[1].timer.text,'2.0s')

    def test_native_color_selects_opaque_player_flag(self):
        self.runlua("""
            AddUnit('target',true); UNITS.target.player={secret=true}; UNITS.target.class={secret=true}
            C_ClassColor={GetClassColor=function() return {GetRGB=function() return 0.1,0.2,0.9 end} end}
            function CreateColor(r,g,b,a) return {GetRGB=function() return r,g,b end} end
            C_CurveUtil={EvaluateColorFromBoolean=function(flag,yes,no) assert(flag==UNITS.target.player); return yes end}
        """)
        self.panel.ClassColor(self.panel,self.panel.rows[1],'target')
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.85)
        self.assertAlmostEqual(self.panel.rows[1].name.textColor[3],0.9)

    def test_restricted_player_category_is_reported_not_guessed(self):
        self.runlua("AddUnit('target',true); UNITS.target.player={secret=true}")
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[1].shown)
        self.assertIn('restricted',self.panel.footer.text)

    def test_enemy_faction_player_not_attackable_still_enemy_section(self):
        self.runlua("AddUnit('target',false); UNITS.target.player=true; function UnitIsEnemy() return true end")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.headers[3].text,'Enemy Players  1')
        self.assertEqual(self.panel.headers[4].text,'Nearby Friendly Players  0')

    def test_native_failure_shows_unavailable(self):
        self.native_setup()
        self.lua.globals().badrow=self.panel.rows[1]
        self.runlua("function badrow.nativeCast:SetTimerDuration() error('blocked') end")
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[1].nativeCast.shown)
        self.assertEqual(self.panel.rows[1].spell.text,'')

    def test_native_class_color_opaque_class_token(self):
        self.runlua("""
            AddUnit('target',true); UNITS.target.player=true; UNITS.target.class={secret=true}
            C_ClassColor={GetClassColor=function(class)
                assert(class==UNITS.target.class)
                return {GetRGB=function() return 0.1,0.4,0.9 end}
            end}
        """)
        self.panel.Refresh(self.panel)
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.85)
        self.assertAlmostEqual(self.panel.rows[1].name.textColor[3],0.9)

    def test_legacy_player_class_and_npc_reset(self):
        self.runlua("AddUnit('target',true); UNITS.target.player=true; UNITS.target.class='MAGE'; RAID_CLASS_COLORS={MAGE={r=0.4,g=0.8,b=1}}")
        self.panel.Refresh(self.panel)
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.85)
        self.assertAlmostEqual(self.panel.rows[1].name.textColor[1],0.4)
        self.assertAlmostEqual(self.panel.rows[1].name.textColor[2],0.8)
        self.runlua("UNITS.target.player=false")
        self.panel.Refresh(self.panel)
        self.assertAlmostEqual(self.panel.rows[1].health.color[3],0.18)
        self.assertEqual(self.panel.rows[1].name.textColor[1],1)

    def test_health_passes_opaque_values_directly(self):
        self.runlua("AddUnit('target',true); UNITS.target.hp={secret=true}; UNITS.target.max={secret=true}")
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.rows[1].health.value.secret)
        self.assertTrue(self.panel.rows[1].health.maximum.secret)
        self.assertTrue(self.panel.rows[1].value.formattedValue.secret)

    def test_percent_uses_native_curve_and_formatter(self):
        self.runlua("AddUnit('target',true); CurveConstants={ScaleTo100={}}; function UnitHealthPercent(u,p,c) assert(c==CurveConstants.ScaleTo100); return {secret=true} end")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].value.format, '%.0f%%')
        self.assertTrue(self.panel.rows[1].value.formattedValue.secret)

    def test_health_api_failure_clears_previous_bar(self):
        self.runlua("AddUnit('target',true)")
        self.panel.Refresh(self.panel)
        self.runlua("function UnitHealth() error('unavailable') end")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].health.value,0)
        self.assertEqual(self.panel.rows[1].value.text,'?')

    def test_header_anchor_stays_at_top(self):
        self.assertEqual(self.panel.frame.point[1], 'TOP')

    def test_defaults_and_persistence(self):
        self.assertTrue(self.addon.db.enemyVisible)
        self.addon.db.enemyX=121
        self.addon.db.enemyVisible=False
        saved=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual(saved.enemyX,121)
        self.assertFalse(saved.enemyVisible)

    def test_overflow_scroll_and_combat_removal(self):
        for i in range(1,16):
            u=f'nameplate{i}'
            self.runlua(f"AddUnit('{u}',true)")
            self.roster.Add(self.roster,u)
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.maxOffset,3)
        self.panel.frame.scripts.OnMouseWheel(self.panel.frame,-3)
        self.assertEqual(self.panel.rows[1].name.text,'[?] nameplate4')
        self.runlua('COMBAT=true')
        for i in range(1,16): self.roster.Remove(self.roster,f'nameplate{i}')
        self.panel.Refresh(self.panel)
        self.assertFalse(self.panel.rows[1].shown)
        self.assertEqual(self.panel.offset,0)

    def test_secret_health_and_cast_do_not_crash(self):
        self.runlua("AddUnit('target',true); UNITS.target.hp={secret=true}; UNITS.target.cast={secret=true}")
        self.panel.Refresh(self.panel)
        self.assertTrue(self.panel.rows[1].value.formattedValue.secret)
        self.assertEqual(self.panel.rows[1].spell.text,'')

    def test_cast_clears_when_token_reused(self):
        self.runlua("AddUnit('nameplate1',true); UNITS.nameplate1.cast='Bolt'; UNITS.nameplate1.startMS=9000; UNITS.nameplate1.endMS=12000")
        self.roster.Add(self.roster,'nameplate1')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rows[1].spell.text,'Casting: Bolt')
        self.panel.events.scripts.OnEvent(self.panel.events,'NAME_PLATE_UNIT_REMOVED','nameplate1')
        self.runlua("AddUnit('nameplate1',true)")
        self.panel.events.scripts.OnEvent(self.panel.events,'NAME_PLATE_UNIT_ADDED','nameplate1')
        self.assertEqual(self.panel.rows[1].spell.text,'')

    def test_drag_restores_top_anchor_before_roster_growth(self):
        self.panel.frame.GetTop=self.lua.eval('function() return 740 end')
        self.panel.frame.GetCenter=self.lua.eval('function() return 620,500 end')
        self.panel.frame.scripts.OnDragStart()
        self.panel.frame.SetPoint(self.panel.frame,'BOTTOM',self.lua.globals().UIParent,'BOTTOM',0,0)
        self.panel.frame.scripts.OnDragStop()
        self.assertEqual(self.panel.frame.point[1],'TOP')
        self.assertEqual(self.addon.db.enemyX,120)
        self.assertEqual(self.addon.db.enemyY,240)
        self.runlua("AddUnit('nameplate1',true)")
        self.roster.Add(self.roster,'nameplate1'); self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.frame.point[1],'TOP')
        self.assertEqual(self.panel.frame.point[5],240)

    def test_visible_row_capacity_uses_space_below_top(self):
        self.panel.frame.GetTop=self.lua.eval('function() return 300 end')
        self.lua.execute('function UIParent:GetBottom() return 0 end')
        for i in range(1,8):
            unit='nameplate'+str(i)
            self.runlua("AddUnit('"+unit+"',true)")
            self.roster.Add(self.roster,unit)
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.rowCapacity,2)
        self.assertEqual(self.panel.maxOffset,5)
        self.assertIn('1-2 of 7',self.panel.footer.text)
        self.panel.frame.scripts.OnMouseWheel(self.panel.frame,-1)
        self.assertIn('2-3 of 7',self.panel.footer.text)

if __name__ == '__main__': unittest.main()

