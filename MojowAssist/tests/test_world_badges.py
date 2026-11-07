import unittest
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]

class WorldBadgeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.ns=self.lua.table()
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute('''
            U={nameplate1={player=true,class='MAGE',level=22}}; PLATES={}; CVAR_WRITES=0
            function UnitExists(u) return U[u]~=nil end
            function UnitIsPlayer(u) return U[u].player end
            function UnitClass(u) return 'class',U[u].class end
            function UnitLevel(u) return U[u].level end
            C_CVar={SetCVar=function() CVAR_WRITES=CVAR_WRITES+1 end}
            CLASS_ICON_TCOORDS={MAGE={0.25,0.5,0,0.25}}
            function NativeFrame()
                local f=CreateFrame('Frame')
                function f:IsForbidden() return self.forbidden or false end
                function f:IsProtected() return self.protected or false end
                return f
            end
            local old=CreateFrame
            function CreateFrame(...)
                local f=old(...)
                function f:IsForbidden() return self.forbidden or false end
                function f:IsProtected() return self.protected or false end
                return f
            end
            function Plate()
                local p=NativeFrame(); p.UnitFrame=NativeFrame()
                p.UnitFrame.HealthBarsContainer={healthBar=NativeFrame()}
                return p
            end
            PLATES.nameplate1=Plate()
            C_NamePlate={GetNamePlateForUnit=function(unit,forbidden)
                assert(forbidden~=true,'must not request forbidden frames'); return PLATES[unit]
            end}
            ADDON={db={},Say=function(self,message) self.message=message end}
        ''')
        self.lua.execute((ROOT/'WorldNameplateBadges.lua').read_text(),'MojowAssist',self.ns)
        self.skin=self.ns.WorldNameplateBadges.Create(self.ns.WorldNameplateBadges,self.lua.globals().ADDON)

    def enable(self): self.skin.SetEnabled(self.skin,True)

    def test_native_bar_kept_with_left_class_and_right_level(self):
        self.enable()
        entry=self.skin.entries.nameplate1
        self.assertIsNotNone(entry)
        self.assertEqual(entry.classBadge.width,20)
        self.assertEqual(entry.icon.width,18)
        self.assertEqual(entry.classBadge.point[1],'RIGHT')
        self.assertEqual(entry.classBadge.point[3],'LEFT')
        self.assertEqual(entry.levelBadge.point[1],'LEFT')
        self.assertEqual(entry.levelBadge.point[3],'RIGHT')
        self.assertEqual(entry.level.text,'22')
        self.assertTrue(entry.classBadge.shown)
        self.assertEqual(self.lua.globals().CVAR_WRITES,0)

    def test_npc_has_level_without_class_badge(self):
        self.lua.execute('U.nameplate1.player=false')
        self.enable(); e=self.skin.entries.nameplate1
        self.assertFalse(e.classBadge.shown)
        self.assertTrue(e.levelBadge.shown)
        self.assertEqual(e.level.text,'22')

    def test_forbidden_skips_and_protected_needs_position(self):
        for flag in ['forbidden','protected']:
            self.lua.execute('PLATES.nameplate1.'+flag+'=true')
            self.enable()
            self.assertIsNone(self.skin.entries.nameplate1)
            self.assertEqual(self.skin.counts.unavailable if flag=='forbidden' else self.skin.counts.position,1)
            self.lua.execute('PLATES.nameplate1.'+flag+'=false')
        self.lua.execute('PLATES.nameplate1.UnitFrame.HealthBarsContainer.healthBar.protected=true')
        self.skin.Refresh(self.skin)
        self.assertIsNone(self.skin.entries.nameplate1)

    def test_inaccessible_api_keeps_native_fallback(self):
        self.lua.execute('C_NamePlate.GetNamePlateForUnit=function() error("blocked") end')
        self.enable()
        self.assertEqual(self.skin.counts.unavailable,1)
        self.assertIsNone(self.skin.entries.nameplate1)

    def test_new_decoration_defers_in_combat(self):
        self.enable(); self.skin.SetEnabled(self.skin,False)
        self.lua.execute("PLATES.nameplate1=Plate(); COMBAT=true")
        self.assertFalse(self.skin.SetEnabled(self.skin,True))
        self.lua.execute('COMBAT=false'); self.enable()
        self.lua.execute("COMBAT=true; U.nameplate2={player=true,class='MAGE',level=23}; PLATES.nameplate2=Plate()")
        self.skin.tokens.nameplate2=True; self.skin.Refresh(self.skin)
        self.assertIsNone(self.skin.entries.nameplate2)
        self.assertEqual(self.skin.counts.deferred,1)

    def test_existing_decorations_update_without_recreation_in_combat(self):
        self.enable(); before=self.skin.entries.nameplate1
        self.lua.execute('COMBAT=true; U.nameplate1.level=25; U.nameplate1.player=false')
        self.skin.Refresh(self.skin)
        self.assertEqual(before.level.text,'25')
        self.assertFalse(before.classBadge.shown)

    def test_restricted_class_and_level_have_no_fabricated_identity(self):
        self.enable()
        self.lua.execute('U.nameplate1.class={secret=true}; U.nameplate1.level={secret=true}')
        self.skin.Refresh(self.skin)
        e=self.skin.entries.nameplate1
        self.assertEqual(e.level.text,'?')
        self.assertFalse(e.icon.shown)
        self.assertEqual(e.unknownClass.text,'?')

    def test_remove_and_reuse_resets_class_and_level(self):
        self.enable(); e=self.skin.entries.nameplate1
        self.skin.Remove(self.skin,'nameplate1')
        self.assertFalse(e.levelBadge.shown)
        self.assertFalse(e.classBadge.shown)
        self.lua.execute('U.nameplate1.player=false; U.nameplate1.level=-1')
        self.skin.tokens.nameplate1=True; self.skin.Refresh(self.skin)
        self.assertEqual(self.skin.entries.nameplate1.level.text,'??')
        self.assertFalse(self.skin.entries.nameplate1.classBadge.shown)

    def test_disabled_at_start_and_explicit_disable_hides_all(self):
        self.assertIsNone(self.skin.entries.nameplate1)
        self.enable(); e=self.skin.entries.nameplate1
        self.skin.SetEnabled(self.skin,False)
        self.assertFalse(e.levelBadge.shown)
        self.assertFalse(self.lua.globals().ADDON.db.nameplateBadges)

    def test_unsupported_layout_is_counted(self):
        self.lua.execute('PLATES.nameplate1.UnitFrame=nil')
        self.enable()
        self.assertEqual(self.skin.counts.unsupported,1)

    def test_status_and_secret_event_tokens_are_safe(self):
        self.enable()
        self.assertIn('decorated 1',self.skin.Status(self.skin))
        self.skin.events.scripts.OnEvent(self.skin.events,'NAME_PLATE_UNIT_ADDED',self.lua.table_from({'secret':True}))
        self.assertEqual(self.skin.counts.decorated,1)

    def test_saved_flag_survives_model_normalization(self):
        self.lua.execute((ROOT/'Model.lua').read_text(),'MojowAssist',self.ns)
        saved=self.lua.table_from({'nameplateBadges':True})
        self.assertTrue(self.ns.Model.Normalize(self.ns.Model,saved).nameplateBadges)

    def test_third_party_plate_is_not_decorated_twice(self):
        self.lua.execute('PLATES.nameplate1.unitFrame=NativeFrame()')
        self.enable()
        self.assertIsNone(self.skin.entries.nameplate1)
        self.assertEqual(self.skin.counts.unsupported,1)

    def test_hidden_native_health_bar_is_not_reported_decorated(self):
        self.lua.execute('PLATES.nameplate1.UnitFrame.HealthBarsContainer.healthBar:Hide()')
        self.enable()
        self.assertEqual(self.skin.counts.unsupported,1)

    def test_native_preset_apply_and_restore_control_badges(self):
        self.lua.execute((ROOT/'NameplateProfile.lua').read_text(),'MojowAssist',self.ns)
        addon=self.lua.globals().ADDON; addon.worldBadges=self.skin
        options=self.lua.eval("{Read=function() return nil end,Refresh=function() end}")
        profile=self.ns.NameplateProfile.Create(self.ns.NameplateProfile,addon,options)
        profile.Apply(profile)
        self.assertTrue(self.skin.enabled)
        profile.Restore(profile)
        self.assertFalse(self.skin.enabled)

    def test_readable_class_changes_update_icon_coordinates(self):
        self.enable()
        self.lua.execute("CLASS_ICON_TCOORDS.WARRIOR={0,0.25,0,0.25}; U.nameplate1.class='WARRIOR'")
        self.skin.Refresh(self.skin)
        self.assertEqual(self.skin.entries.nameplate1.icon.texCoord[1],0)

    def test_frame_replacement_hides_previous_badges(self):
        self.enable(); old=self.skin.entries.nameplate1
        self.lua.execute('PLATES.nameplate1=Plate()')
        self.skin.Refresh(self.skin)
        self.assertFalse(old.classBadge.shown)
        self.assertFalse(old.levelBadge.shown)

    def test_partial_construction_failure_is_hidden_and_not_retried_each_tick(self):
        self.lua.execute('''
            MADE={}; local create=CreateFrame
            function CreateFrame(kind,name,parent,template)
                local frame=create(kind,name,parent,template)
                if template=='BackdropTemplate' then
                    MADE[#MADE+1]=frame
                    function frame:SetBackdropColor() error('refused style') end
                end
                return frame
            end
        ''')
        self.enable()
        for _ in range(3): self.skin.Refresh(self.skin)
        self.assertEqual(len(self.lua.globals().MADE),1)
        self.assertFalse(self.lua.globals().MADE[1].shown)
        self.assertEqual(self.skin.counts.errors,1)
        self.skin.SetEnabled(self.skin,False)
        self.assertFalse(self.lua.globals().MADE[1].shown)

    def test_existing_native_level_badge_is_reused_without_overlap_or_mutation(self):
        self.lua.execute('PLATES.nameplate1.UnitFrame.PlayerLevelDiffFrame=NativeFrame()')
        native=self.lua.globals().PLATES.nameplate1.UnitFrame.PlayerLevelDiffFrame
        self.enable()
        self.assertFalse(self.skin.entries.nameplate1.levelBadge.shown)
        self.assertTrue(native.shown)
        self.skin.SetEnabled(self.skin,False)
        self.assertTrue(native.shown)

    def protected_geometry(self):
        self.lua.execute("""
            local p=PLATES.nameplate1; local h=p.UnitFrame.HealthBarsContainer.healthBar
            p.protected=true; p.UnitFrame.protected=true; h.protected=true
            local oldCreate=CreateFrame
            function CreateFrame(kind,name,parent,template) local f=oldCreate(kind,name,parent,template); f.testParent=parent; return f end
            X=200; Y=100; VISIBLE=true
            function h:GetCenter() return X,Y end
            function h:GetWidth() return 100 end
            function h:GetEffectiveScale() return 2 end
            function UIParent:GetEffectiveScale() return 1 end
            function h:IsVisible() return VISIBLE end
            for _,f in ipairs({p,p.UnitFrame,h}) do
                for _,name in ipairs({'SetPoint','SetParent','ClearAllPoints','SetSize','Hide','Show','SetAttribute'}) do
                    f[name]=function() error('native mutation forbidden') end
                end
            end
        """)

    def test_protected_native_overlay_is_independent_and_moves_in_combat(self):
        self.protected_geometry(); self.enable()
        e=self.skin.entries.nameplate1
        self.assertTrue(e.overlay); self.assertEqual(self.skin.counts.decorated,1)
        self.lua.globals().E=e
        self.assertTrue(self.lua.eval('E.classBadge.testParent==UIParent'))
        self.lua.execute('COMBAT=true; X=250')
        self.skin.events.scripts.OnUpdate(self.skin.events,0.04)
        self.assertTrue(e.classBadge.shown)
        self.skin.Position(self.skin,e)
        self.assertEqual(e.classBadge.point[4],399)
        self.assertEqual(e.classBadge.point[5],200)
        self.skin.Remove(self.skin,'nameplate1'); self.assertFalse(e.classBadge.shown)

    def test_hidden_or_secret_position_clears_overlay(self):
        self.protected_geometry(); self.enable(); e=self.skin.entries.nameplate1
        original=e.classBadge.SetPoint
        e.classBadge.SetPoint=self.lua.eval('function() error("anchor rejected") end')
        self.lua.execute('X={secret=true}')
        self.skin.events.scripts.OnUpdate(self.skin.events,0.04)
        self.assertFalse(e.classBadge.shown)
        self.skin.Refresh(self.skin); self.assertEqual(self.skin.counts.position,1)
        e.classBadge.SetPoint=original
        self.lua.execute('X=200; VISIBLE=true'); self.skin.Refresh(self.skin)
        self.assertTrue(e.classBadge.shown)
        self.lua.execute('VISIBLE=false'); self.skin.Refresh(self.skin)
        self.assertFalse(e.classBadge.shown)

    def test_native_anchor_works_when_center_reads_fail_without_native_mutation(self):
        self.protected_geometry()
        self.lua.execute("PLATES.nameplate1.UnitFrame.HealthBarsContainer.healthBar.GetCenter=function() error('restricted position') end")
        self.enable(); e=self.skin.entries.nameplate1
        self.assertTrue(e.nativeAnchored); self.assertTrue(e.classBadge.shown)
        self.assertIn('accepted',self.skin.anchorResult)
        self.lua.globals().E=e
        self.assertTrue(self.lua.eval('E.classBadge.point[2]==E.health'))
        e.classBadge.SetPoint=self.lua.eval('function() error("must not reanchor during combat") end')
        self.lua.execute('COMBAT=true')
        self.skin.Refresh(self.skin); self.assertEqual(self.skin.counts.decorated,1)
        self.skin.events.scripts.OnUpdate(self.skin.events,0.04)
        self.assertTrue(e.classBadge.shown)
        self.lua.execute('VISIBLE=false'); self.skin.events.scripts.OnUpdate(self.skin.events,0.04)
        self.assertFalse(e.classBadge.shown)

    def test_rejected_anchor_reports_error_and_leaves_frames_hidden(self):
        self.protected_geometry(); self.enable(); e=self.skin.entries.nameplate1
        self.lua.execute("PLATES.nameplate1.UnitFrame.HealthBarsContainer.healthBar.GetCenter=function() error('restricted') end")
        e.classBadge.SetPoint=self.lua.eval('function() error("Cannot anchor to restricted frame") end')
        self.skin.Refresh(self.skin)
        self.assertFalse(e.classBadge.shown); self.assertTrue(e.anchorBlocked)
        self.assertIn('Cannot anchor',self.skin.anchorResult)
        self.assertIsNone(self.skin.entries.nameplate1)

    def test_anchor_inherited_protection_never_shows_badge(self):
        self.protected_geometry(); self.enable(); e=self.skin.entries.nameplate1
        self.lua.execute("PLATES.nameplate1.UnitFrame.HealthBarsContainer.healthBar.GetCenter=function() error('restricted') end")
        e.classBadge.SetPoint=self.lua.eval('function(self) self.protected=true end')
        self.skin.Refresh(self.skin)
        self.assertFalse(e.classBadge.shown); self.assertTrue(e.anchorBlocked)
        self.assertIn('became protected',self.skin.anchorResult)
