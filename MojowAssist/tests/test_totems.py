from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class TotemTests(unittest.TestCase):
    def test_full_addon_shaman_initialization_preserves_other_modules(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        lua.execute('''
            function UnitClass() return 'Shaman','SHAMAN' end
            C_Spell={GetSpellInfo=function(id)
                if id==8071 then return {name='Stone Skin',iconID=id} end
                if id==324 then return {name='Lightning Shield',iconID=id} end
            end}
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {itemIndexOffset=0,numSpellBookItems=2,offSpecID=0} end,
                GetSpellBookItemInfo=function(i) return {itemType=1,spellID=i==1 and 8071 or 324} end}
        ''')
        ns=lua.table()
        for name in (ROOT/'MojowAssist.toc').read_text().splitlines():
            if name.strip().endswith('.lua'): lua.execute((ROOT/name.strip()).read_text(),'MojowAssist',ns)
        ns.Addon.Initialize(ns.Addon)
        self.assertTrue(ns.Addon.ready)
        self.assertEqual(lua.globals().SLASH_MOJOWASSIST1,"/mja")
        self.assertEqual(lua.globals().SLASH_MOJOWASSIST2,"/mojowassist")
        ns.Addon.minimap.ToggleMenu(ns.Addon.minimap)
        self.assertEqual(ns.Addon.minimap.totemMenuButton.text,'Hide totems')
        ns.Addon.minimap.ToggleMenu(ns.Addon.minimap)
        ns.Addon.db.totemVisible=False
        ns.Addon.minimap.ToggleMenu(ns.Addon.minimap)
        self.assertEqual(ns.Addon.minimap.totemMenuButton.text,'Show totems')
        self.assertIsNotNone(ns.Addon.panel)
        self.assertIsNotNone(ns.Addon.enemies)
        self.assertEqual(ns.Addon.enemies.scope,'targets')
        self.assertEqual(ns.Addon.groupMembers.scope,'group')
        self.assertIsNone(ns.Addon.groupMembers.combatRows)
        self.assertTrue(ns.Addon.groupMembers.frame.shown)
        ns.Addon.minimap.menuOptions[1].scripts.OnClick()
        self.assertFalse(ns.Addon.groupMembers.frame.shown)
        self.assertTrue(ns.Addon.enemies.frame.shown)
        ns.Addon.minimap.menuOptions[1].scripts.OnClick()
        self.assertTrue(ns.Addon.groupMembers.frame.shown)
        ns.Addon.Command(ns.Addon,'groupwindow hide')
        self.assertFalse(ns.Addon.groupMembers.frame.shown)
        self.assertTrue(ns.Addon.enemies.frame.shown)
        ns.Addon.Command(ns.Addon,'groupwindow reset')
        self.assertTrue(ns.Addon.groupMembers.frame.shown)
        self.assertEqual((ns.Addon.db.groupX,ns.Addon.db.groupY),(50,100))
        original=ns.Addon.SetMode
        lua.globals().ROUTE_ADDON=ns.Addon
        lua.execute('function ROUTE_ADDON:SetMode(mode) self.routedMode=mode end')
        ns.Addon.Command(ns.Addon,'group')
        self.assertEqual(ns.Addon.routedMode,'group')
        ns.Addon.SetMode=original
        lua.execute('COMBAT=true')
        ns.Addon.minimap.menuOptions[1].scripts.OnClick()
        self.assertTrue(ns.Addon.groupMembers.frame.shown)
        self.assertTrue(ns.Addon.db.enemyShowGroup)
        lua.execute('COMBAT=false')
        self.assertTrue(ns.Addon.shield.known)
        self.assertEqual(ns.Addon.totems.buttons[8071].attrs.spell,'Stone Skin')

    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/wow_stub.lua').read_text())
        self.lua.execute('''
            function UnitClass() return 'Shaman','SHAMAN' end
            function GetTime() return 100 end
            BOOK={8071,8072,8075,3599,5675}
            NAMES={[8071]='Stone Skin',[8072]='Stone Skin',[8075]='Strength',[3599]='Searing',[5675]='Mana Spring'}
            C_Spell={GetSpellInfo=function(id) if NAMES[id] then return {name=NAMES[id],iconID=id} end end}
            Enum.SpellBookSpellBank={Player=0}; Enum.SpellBookItemType={Spell=1}
            C_SpellBook={GetNumSpellBookSkillLines=function() return 1 end,
                GetSpellBookSkillLineInfo=function() return {offSpecID=0,itemIndexOffset=0,numSpellBookItems=#BOOK} end,
                GetSpellBookItemInfo=function(index) return {spellID=BOOK[index],itemType=1} end,
                GetSpellBookItemName=function(index) return NAMES[BOOK[index]],BOOK[index]==8072 and 'Rank 2' or 'Rank 1' end}
            function GetTotemInfo() return false,'',0,0 end
            TEST_ADDON={Say=function(self,message) self.message=message end}
        ''')
        self.ns=self.lua.table()
        for name in ('Appearance.lua','Model.lua','TotemModel.lua','TotemPanel.lua'):
            self.lua.execute((ROOT/name).read_text(),'MojowAssist',self.ns)
        self.addon=self.lua.globals().TEST_ADDON
        self.addon.db=self.ns.Model.Normalize(self.ns.Model,self.lua.table())
        self.panel=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.model=self.panel.model

    def test_learned_only_rank_dedup_and_secure_self_actions(self):
        self.assertEqual(len(list(self.model.spells.items())),4)
        self.assertEqual(len(self.model.groups[2]),2)
        self.assertIsNone(self.panel.buttons[8072])
        self.assertIsNone(self.panel.buttons[8177])
        button=self.panel.buttons[8071]
        self.assertEqual(button.attrs.type1,'spell')
        self.assertEqual(button.attrs.spell,'Stone Skin')
        self.assertEqual(button.attrs.unit,'player')
        self.assertIsNone(button.attrs.type2)
        self.assertEqual(self.panel.groups[4].empty.text,'--')
        self.assertEqual(button.record.spellID,8072)

    def test_tooltip_rank_does_not_depend_on_book_order(self):
        self.lua.execute('BOOK={8072,8071}')
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.buttons[8071].record.spellID,8072)
        self.assertEqual(self.panel.buttons[8071].attrs.spell,'Stone Skin')

    def test_right_click_favorite_moves_first_without_cast_action(self):
        self.panel.ToggleExpanded(self.panel)
        button=self.panel.buttons[8075]
        button.scripts.PostClick(button,'RightButton',False)
        self.assertEqual(self.addon.db.totemFavorites[2],8075)
        self.assertEqual(self.model.Ordered(self.model,2)[1].baseID,8075)
        self.assertIn('*',button.star.text)
        self.assertIsNone(button.attrs.type2)
        self.panel.ToggleExpanded(self.panel)
        self.assertTrue(button.shown)
        self.assertFalse(self.panel.buttons[8071].shown)

    def test_compact_setup_and_combat_lock(self):
        self.assertFalse(self.addon.db.totemExpanded)
        self.assertEqual((self.panel.frame.width,self.panel.frame.height),(232,138))
        self.assertTrue(self.panel.buttons[8071].shown)
        self.assertFalse(self.panel.buttons[8075].shown)
        self.assertFalse(self.panel.saveButtons[1].shown)
        self.assertTrue(self.panel.ToggleExpanded(self.panel))
        self.assertTrue(self.panel.buttons[8075].shown)
        self.assertTrue(self.panel.saveButtons[1].shown)
        self.assertEqual(self.panel.groups[4].empty.text,'No learned totems for this element')
        restored=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertTrue(restored.totemExpanded)
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.panel.ToggleExpanded(self.panel))
        self.assertTrue(self.addon.db.totemExpanded)
        self.assertTrue(self.panel.buttons[8075].shown)

    def test_preset_copies_and_reload_persistence(self):
        self.model.SetFavorite(self.model,8071)
        self.model.SetFavorite(self.model,3599)
        self.assertTrue(self.model.SavePreset(self.model,1)[0])
        self.model.SetFavorite(self.model,8075)
        self.assertEqual(self.addon.db.totemPresets[1][2],8071)
        self.assertTrue(self.model.LoadPreset(self.model,1)[0])
        self.addon.db.totemFavorites[2]=8075
        self.assertEqual(self.addon.db.totemPresets[1][2],8071)
        restored=self.ns.Model.Normalize(self.ns.Model,self.addon.db)
        self.assertEqual(restored.totemFavorites[2],8075)
        self.assertEqual(restored.totemPresets[1][2],8071)

    def test_unavailable_preset_is_atomic_and_missing_preset_rejected(self):
        self.model.SetFavorite(self.model,8071)
        self.addon.db.totemPresets[1]=self.lua.table_from({2:8075,4:8177})
        self.assertFalse(self.model.LoadPreset(self.model,1)[0])
        self.assertEqual(self.addon.db.totemFavorites[2],8071)
        self.assertFalse(self.model.LoadPreset(self.model,3)[0])

    def test_combat_buttons_favorites_visibility_and_presets_stay_fixed(self):
        self.model.SetFavorite(self.model,8071)
        self.model.SavePreset(self.model,1)
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.model.SetFavorite(self.model,8075)[0])
        self.assertFalse(self.model.LoadPreset(self.model,1)[0])
        self.assertFalse(self.model.SavePreset(self.model,2)[0])
        self.assertFalse(self.panel.SetVisible(self.panel,False))
        self.panel.Layout(self.panel)
        button=self.panel.buttons[8075]
        button.scripts.PostClick(button,'RightButton',False)
        self.assertEqual(self.addon.db.totemFavorites[2],8071)
        self.assertTrue(self.panel.frame.shown)
        self.assertEqual(button.attrs.spell,'Strength')

    def test_learning_in_combat_defers_refresh_until_safe(self):
        self.lua.execute("COMBAT=true; NAMES[8177]='Grounding'; table.insert(BOOK,8177)")
        self.panel.events.scripts.OnEvent(self.panel.events,'SPELLS_CHANGED')
        self.assertTrue(self.panel.pending)
        self.assertIsNone(self.panel.buttons[8177])
        self.lua.execute('COMBAT=false')
        self.panel.events.scripts.OnEvent(self.panel.events,'PLAYER_REGEN_ENABLED')
        self.assertFalse(self.panel.pending)
        self.assertEqual(self.panel.buttons[8177].attrs.spell,'Grounding')

    def test_totem_active_empty_and_error_clear_stale_status(self):
        self.lua.execute("function GetTotemInfo() return true,'Stone Skin',90,120 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.groups[2].status.text,'Stone Skin')
        self.assertEqual(self.panel.groups[2].timer.text,'110s')
        self.lua.execute("function GetTotemInfo() error('restricted') end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.groups[2].status.text,'Status unavailable')
        self.assertEqual(self.panel.groups[2].timer.text,'?')
        self.lua.execute("function GetTotemInfo() return true,'',0,0 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.groups[2].status.text,'Status unavailable')
        self.assertEqual(self.panel.groups[2].timer.text,'?')

    def test_native_secret_totem_data_is_only_forwarded_for_display(self):
        self.lua.execute('''
            COMBAT=true; SECRET={secret=true}
            function GetTotemInfo() return SECRET,SECRET,SECRET,SECRET end
            function GetTotemDuration() return {GetRemainingDuration=function() return SECRET end} end
        ''')
        self.panel.Update(self.panel)
        self.assertTrue(self.panel.groups[2].status.text.secret)
        self.assertTrue(self.panel.groups[2].timer.formattedValue.secret)

    def test_spellbook_failure_preserves_configured_actions(self):
        self.lua.execute("function C_SpellBook.GetSpellBookItemInfo() error('unavailable') end")
        self.panel.Refresh(self.panel)
        self.assertEqual(self.panel.buttons[8071].attrs.spell,'Stone Skin')
        self.assertIn('unavailable',self.panel.note.text)

    def test_nil_metadata_and_unreadable_book_preserve_previous_controls(self):
        self.model.SetFavorite(self.model,8075)
        self.lua.execute('''
            C_Spell.GetSpellInfo=function() return nil end
            C_SpellBook.GetSpellBookItemName=function() return nil end
        ''')
        self.panel.Refresh(self.panel)
        self.assertEqual(len(list(self.model.spells.items())),4)
        self.assertEqual(self.model.spells[8071].spellID,8072)
        self.assertEqual(self.addon.db.totemFavorites[2],8075)
        self.assertEqual(self.panel.buttons[8075].attrs.spell,'Strength')
        self.assertIn('unavailable',self.panel.note.text)

    def test_book_names_recover_missing_rank_and_base_metadata(self):
        self.lua.execute('C_Spell.GetSpellInfo=function() return nil end; BOOK={8072,8071,8075,3599,5675}')
        self.assertEqual(self.model.Refresh(self.model),True)
        self.assertEqual(len(list(self.model.spells.items())),4)
        self.assertEqual(self.model.spells[8071].spellID,8072)
        self.assertEqual(self.model.spells[8071].name,'Stone Skin')

    def test_new_talent_totem_uses_book_name_without_spell_metadata(self):
        self.lua.execute("NAMES[16190]='Mana Tide'; table.insert(BOOK,16190); OLD_INFO=C_Spell.GetSpellInfo; C_Spell.GetSpellInfo=function(id) if id~=16190 then return OLD_INFO(id) end end")
        self.panel.Refresh(self.panel)
        self.assertIsNotNone(self.model.spells[16190])
        self.assertEqual(self.model.spells[16190].spellID,16190)
        self.assertEqual(self.panel.buttons[16190].attrs.spell,'Mana Tide')

    def test_complete_empty_book_clears_controls_even_without_metadata(self):
        self.lua.execute('BOOK={}; C_Spell.GetSpellInfo=function() return nil end')
        self.panel.Refresh(self.panel)
        self.assertEqual(len(list(self.model.spells.items())),0)
        self.assertFalse(self.panel.buttons[8071].shown)
        self.assertIsNone(self.model.error)

    def test_missing_book_item_cannot_commit_partial_discovery(self):
        self.lua.execute('OLD_ITEM=C_SpellBook.GetSpellBookItemInfo; C_SpellBook.GetSpellBookItemInfo=function(i) if i~=3 then return OLD_ITEM(i) end end')
        result=self.model.Refresh(self.model)
        self.assertIsInstance(result,tuple)
        self.assertFalse(result[0])
        self.assertEqual(len(list(self.model.spells.items())),4)

    def test_unreadable_book_item_type_cannot_erase_controls(self):
        for kind in ('nil','{secret=true}'):
            with self.subTest(kind=kind):
                self.lua.execute('C_SpellBook.GetSpellBookItemInfo=function(i) return {spellID=BOOK[i],itemType='+kind+'} end')
                result=self.model.Refresh(self.model)
                self.assertIsInstance(result,tuple)
                self.assertFalse(result[0])
                self.assertEqual(len(list(self.model.spells.items())),4)

    def test_readable_nonspell_item_types_are_still_excluded(self):
        self.lua.execute('C_SpellBook.GetSpellBookItemInfo=function(i) return {spellID=BOOK[i],itemType=99} end')
        self.assertEqual(self.model.Refresh(self.model),True)
        self.assertEqual(len(list(self.model.spells.items())),0)

    def test_readable_book_names_recover_missing_rank_metadata_on_first_load(self):
        self.lua.execute('OLD_INFO=C_Spell.GetSpellInfo; C_Spell.GetSpellInfo=function(id) if id~=8072 then return OLD_INFO(id) end end')
        fresh=self.ns.TotemModel.Create(self.ns.TotemModel,self.addon.db)
        self.assertEqual(fresh.Refresh(fresh),True)
        self.assertEqual(fresh.spells[8071].spellID,8072)

    def test_unknown_catalog_with_nonempty_book_is_unavailable_not_empty(self):
        self.lua.execute('C_Spell.GetSpellInfo=function() return nil end; BOOK={8072}')
        fresh=self.ns.TotemModel.Create(self.ns.TotemModel,self.addon.db)
        result=fresh.Refresh(fresh)
        self.assertIsInstance(result,tuple)
        self.assertFalse(result[0])

    def test_hidden_panel_and_non_shaman(self):
        self.panel.SetVisible(self.panel,False)
        self.assertFalse(self.addon.db.totemVisible)
        self.assertFalse(self.panel.frame.shown)
        self.lua.execute("function UnitClass() return 'Mage','MAGE' end")
        other=self.ns.TotemPanel.Create(self.ns.TotemPanel,self.addon)
        self.assertIsNone(other.frame)

    def test_corrupt_saved_settings_are_sanitized(self):
        saved=self.lua.table_from({'totemFavorites':self.lua.table_from({1:'bad',2:8071,3:float('inf')}),
                                  'totemPresets':self.lua.table_from({1:'bad',2:self.lua.table_from({4:8177})})})
        restored=self.ns.Model.Normalize(self.ns.Model,saved)
        self.assertIsNone(restored.totemFavorites[1])
        self.assertEqual(restored.totemFavorites[2],8071)
        self.assertIsNone(restored.totemFavorites[3])
        self.assertIsNone(restored.totemPresets[1])
        self.assertEqual(restored.totemPresets[2][4],8177)

    def test_combat_reminder_only_for_selected_missing_totem(self):
        self.lua.execute('COMBAT=true')
        self.panel.Update(self.panel)
        self.assertTrue(self.panel.buttons[8071].reminder.shown)
        self.assertFalse(self.panel.buttons[8075].reminder.shown)
        self.lua.execute("function GetTotemInfo() return true,'Stone Skin',90,120 end")
        self.panel.Update(self.panel)
        self.assertFalse(self.panel.buttons[8071].reminder.shown)
        self.lua.execute("function GetTotemInfo() return true,'Strength',90,120 end")
        self.panel.Update(self.panel)
        self.assertTrue(self.panel.buttons[8071].reminder.shown)
        self.lua.execute('COMBAT=false')
        self.panel.Update(self.panel)
        self.assertTrue(self.panel.buttons[8071].reminder.shown)
        self.assertFalse(self.panel.buttons[8071].reminderPulse)

    def test_secret_and_failed_state_never_glow_as_missing(self):
        self.lua.execute('COMBAT=true')
        self.panel.Update(self.panel)
        self.lua.execute("SECRET={secret=true}; function GetTotemInfo() return SECRET,SECRET,SECRET,SECRET end")
        self.panel.Update(self.panel)
        self.assertFalse(self.panel.buttons[8071].reminder.shown)
        self.assertEqual(self.panel.groups[2].activeState,'unknown')
        self.lua.execute("function GetTotemInfo() error('restricted') end")
        self.panel.Update(self.panel)
        self.assertFalse(self.panel.buttons[8071].reminder.shown)

    def test_quick_cycle_stable_order_and_combat_lock(self):
        self.assertTrue(self.panel.Cycle(self.panel,2))
        self.assertEqual(self.addon.db.totemFavorites[2],8075)
        self.assertTrue(self.panel.buttons[8075].shown)
        self.assertTrue(self.panel.Cycle(self.panel,2))
        self.assertEqual(self.addon.db.totemFavorites[2],8071)
        self.lua.execute('COMBAT=true')
        self.assertFalse(self.panel.Cycle(self.panel,2))
        self.assertEqual(self.addon.db.totemFavorites[2],8071)

    def test_shared_sequence_is_one_per_click_and_follows_selection(self):
        button=self.panel.dropSet
        self.assertEqual(button.attrs.type1,'macro')
        self.assertEqual(button.attrs.macrotext1,'/castsequence reset=6 Stone Skin, Searing, Mana Spring')
        self.assertEqual(button.text,'Drop set (3 clicks)')
        self.panel.Cycle(self.panel,2)
        self.assertEqual(button.attrs.macrotext1,'/castsequence reset=6 Strength, Searing, Mana Spring')
        before=button.attrs.macrotext1
        self.lua.execute('COMBAT=true')
        self.panel.Layout(self.panel)
        self.panel.Update(self.panel)
        self.assertEqual(button.attrs.macrotext1,before)

    def test_no_learned_totems_disables_shared_action(self):
        self.lua.execute('BOOK={}')
        self.panel.Refresh(self.panel)
        self.assertIsNone(self.panel.dropSet.attrs.type1)
        self.assertIsNone(self.panel.dropSet.attrs.macrotext1)
        self.assertEqual(self.panel.dropSet.text,'No learned totems')

    def test_expired_totem_glows_but_live_totem_range_is_unknown(self):
        self.lua.execute("COMBAT=true; function GetTotemInfo() return true,'Stone Skin',1,20 end")
        self.panel.Update(self.panel)
        self.assertTrue(self.panel.buttons[8071].reminder.shown)
        self.lua.execute("function GetTotemInfo() return true,'Stone Skin',90,120 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.groups[2].rangeState,'unknown')
        self.assertEqual(self.panel.groups[2].activeState,'active')
        self.assertFalse(self.panel.buttons[8071].reminder.shown)

    def test_known_missing_selected_totem_has_static_preparation_cue(self):
        button=self.panel.buttons[8071]
        self.assertTrue(button.reminder.shown)
        self.assertTrue(button.reminderLabel.shown)
        self.assertEqual(button.reminderLabel.text,'DROP')
        self.assertTrue(button.reminderBacking.shown)
        self.assertFalse(button.reminderPulse)
        self.assertFalse(self.panel.buttons[8075].reminderLabel.shown)
        for _,edge in button.reminderEdges.items():
            self.assertTrue(edge.shown)
            self.assertEqual(edge.alpha,1)

    def test_combat_pulse_does_not_fade_label_or_static_edges(self):
        button=self.panel.buttons[8071]
        self.lua.execute('COMBAT=true')
        self.panel.Update(self.panel)
        self.assertTrue(button.reminderPulse)
        self.lua.execute('function GetTime() return 0 end')
        button.scripts.OnUpdate(button)
        first=button.reminder.alpha
        self.lua.execute('function GetTime() return 0.3 end')
        button.scripts.OnUpdate(button)
        self.assertNotEqual(first,button.reminder.alpha)
        self.assertTrue(button.reminderLabel.shown)
        for _,edge in button.reminderEdges.items(): self.assertEqual(edge.alpha,1)
        self.lua.execute('COMBAT=false')
        self.panel.Update(self.panel)
        self.assertFalse(button.reminderPulse)
        self.assertEqual(button.reminder.alpha,0.85)

    def test_unknown_present_empty_name_does_not_claim_missing(self):
        self.lua.execute("function GetTotemInfo() return true,'',0,0 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.groups[2].activeState,'unknown')
        self.assertFalse(self.panel.buttons[8071].reminder.shown)
        self.assertFalse(self.panel.buttons[8071].reminderLabel.shown)
        self.assertFalse(self.panel.buttons[8071].reminderBacking.shown)

    def test_failed_or_secret_scan_clears_all_preparation_artwork(self):
        button=self.panel.buttons[8071]
        self.assertTrue(button.reminderLabel.shown)
        self.lua.execute("function GetTotemInfo() error('restricted') end")
        self.panel.Update(self.panel)
        self.assertFalse(button.reminder.shown)
        self.assertFalse(button.reminderLabel.shown)
        self.assertFalse(button.reminderBacking.shown)
        for _,edge in button.reminderEdges.items(): self.assertFalse(edge.shown)

    def test_cue_switch_does_not_change_actions_in_combat(self):
        button=self.panel.buttons[8071]
        original=dict(button.attrs.items())
        self.lua.execute("COMBAT=true; function GetTotemInfo() return true,'Stone Skin',90,120 end")
        self.panel.Update(self.panel)
        self.assertFalse(button.reminderLabel.shown)
        self.lua.execute("function GetTotemInfo() return false,'',0,0 end")
        self.panel.Update(self.panel)
        self.assertTrue(button.reminderLabel.shown)
        self.assertEqual(dict(button.attrs.items()),original)

    def test_replacement_cue_says_swap_and_missing_cue_says_drop(self):
        self.lua.execute("function GetTotemInfo() return true,'Strength',90,120 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.buttons[8071].reminderLabel.text,'SWAP')
        self.lua.execute("function GetTotemInfo() return false,'',0,0 end")
        self.panel.Update(self.panel)
        self.assertEqual(self.panel.buttons[8071].reminderLabel.text,'DROP')

    def test_totem_tooltip_keeps_native_spell_without_radius_diagram(self):
        self.lua.execute("""
            GameTooltip=CreateFrame('Frame')
            function GameTooltip:SetOwner(owner) self.owner=owner; self.lines={} end
            function GameTooltip:SetSpellByID(id) self.spellID=id end
            function GameTooltip:AddLine(line) table.insert(self.lines,line) end
        """)
        button=self.panel.buttons[8071]
        original=dict(button.attrs.items())
        self.lua.execute('COMBAT=true')
        button.scripts.OnEnter()
        tooltip=self.lua.globals().GameTooltip
        self.assertEqual(tooltip.spellID,8072)
        lines=list(tooltip.lines.values())
        self.assertEqual(lines[0],'Left-click: summon this totem')
        self.assertEqual(lines[1],'Right-click: favorite outside combat')
        self.assertLessEqual(len(lines),4)
        self.assertFalse(any(not x.strip() for x in lines))
        self.assertIsNone(self.panel.rangeGuide)
        self.assertEqual(dict(button.attrs.items()),original)
        button.scripts.OnLeave()
        self.assertFalse(tooltip.shown)
