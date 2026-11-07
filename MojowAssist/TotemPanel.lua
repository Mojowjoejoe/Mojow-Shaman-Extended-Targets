local _,NS=...
local Panel={}
Panel.__index=Panel
NS.TotemPanel=Panel

local function text(parent,x,y,width)
    local label=parent:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    label:SetPoint('TOPLEFT',parent,'TOPLEFT',x,y)
    label:SetWidth(width); label:SetJustifyH('LEFT'); label:SetWordWrap(false)
    return label
end

function Panel:Message(message)
    if self.note then self.note:SetText(message) end
    self.addon:Say(message)
end

function Panel:MakeButton(spell)
    local button=CreateFrame('Button',nil,self.frame,'SecureActionButtonTemplate')
    button:SetSize(36,36)
    button:RegisterForClicks('AnyDown','AnyUp')
    button:SetHighlightTexture('Interface\\Buttons\\ButtonHilight-Square','ADD')
    button.icon=button:CreateTexture(nil,'ARTWORK'); button.icon:SetAllPoints()
    button.star=text(button,2,-1,16)
    button.reminder=button:CreateTexture(nil,'OVERLAY',nil,4)
    button.reminder:SetTexture('Interface\\Buttons\\UI-ActionButton-Border')
    button.reminder:SetSize(58,58); button.reminder:SetPoint('CENTER',button,'CENTER',0,0)
    button.reminder:SetVertexColor(1,0.72,0.08,1)
    button.reminder:SetBlendMode('ADD'); button.reminder:Hide()
    -- Texture-only accents keep the secure button's click area unchanged.
    button.reminderEdges={}
    for _,edge in ipairs({{36,3,0,16.5},{36,3,0,-16.5},{3,30,-16.5,0},{3,30,16.5,0}}) do
        local texture=button:CreateTexture(nil,'OVERLAY',nil,5)
        texture:SetColorTexture(1,0.76,0.12,1)
        texture:SetSize(edge[1],edge[2]); texture:SetPoint('CENTER',button,'CENTER',edge[3],edge[4])
        texture:Hide(); button.reminderEdges[#button.reminderEdges+1]=texture
    end
    -- Opaque badge and solid inner edges remain readable even on a transparent panel.
    button.reminderBacking=button:CreateTexture(nil,'ARTWORK',nil,7)
    button.reminderBacking:SetColorTexture(0.08,0.04,0,0.96)
    button.reminderBacking:SetSize(30,12); button.reminderBacking:SetPoint('BOTTOM',button,'BOTTOM',0,3)
    button.reminderBacking:Hide()
    button.reminderLabel=button:CreateFontString(nil,'OVERLAY','GameFontNormalSmall')
    button.reminderLabel:SetPoint('BOTTOM',button,'BOTTOM',0,3)
    button.reminderLabel:SetWidth(30); button.reminderLabel:SetJustifyH('CENTER')
    button.reminderLabel:SetTextColor(1,0.9,0.3,1); button.reminderLabel:SetText('DROP'); button.reminderLabel:Hide()
    button:SetScript('OnUpdate',function()
        if not button.reminderPulse then return end
        button.reminder:SetAlpha(0.65+0.35*(0.5+0.5*math.sin(GetTime()*5)))
    end)
    button:SetScript('PostClick',function(_,mouse,down)
        if mouse=='RightButton' and not down then
            local ok,err=self.model:SetFavorite(button.record.baseID)
            if ok then self:Layout(); self.note:SetText('Favorite: '..button.record.name)
            else self:Message(err) end
        end
    end)
    button:SetScript('OnEnter',function()
        if GameTooltip then
            GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
            GameTooltip:SetSpellByID(button.record.spellID)
            GameTooltip:AddLine('Left-click: summon this totem',1,1,1)
            GameTooltip:AddLine('Right-click: favorite outside combat',1,1,1)
            if self.model.error then GameTooltip:AddLine('Spellbook unavailable; showing last learned choices.',1,0.8,0.1,true) end
            local group=self.groups[button.record.slot]
            if group and group.selected and group.selected.baseID==button.record.baseID then
                if group.activeState=='missing' then GameTooltip:AddLine('DROP: no active totem.',1,0.8,0.1,true)
                elseif group.activeState=='other' then GameTooltip:AddLine('SWAP: replaces the active totem.',1,0.8,0.1,true) end
            end
            GameTooltip:AddLine('Timer tracks this element. Coverage unknown.',0.7,0.9,1,true)
            GameTooltip:Show()
        end
    end)
    button:SetScript('OnLeave',function()
        if GameTooltip then GameTooltip:Hide() end
    end)
    return button
end

function Panel:Layout()
    if not self.frame or InCombatLockdown() then return end
    local expanded=self.addon.db.totemExpanded
    self.frame:SetSize(expanded and 410 or 232,expanded and 440 or 138)
    self.expand:SetText(expanded and 'Compact' or 'Setup')
    for _,widget in ipairs({self.note,self.hint}) do if expanded then widget:Show() else widget:Hide() end end
    for _,widget in ipairs(self.saveButtons) do if expanded then widget:Show() else widget:Hide() end end
    for _,widget in ipairs(self.loadButtons) do if expanded then widget:Show() else widget:Hide() end end
    self.close:ClearAllPoints()
    self.close:SetSize(expanded and 65 or 20,22)
    self.close:SetPoint(expanded and 'BOTTOMRIGHT' or 'TOPRIGHT',self.frame,expanded and 'BOTTOMRIGHT' or 'TOPRIGHT',-5,expanded and 8 or -4)
    self.close:SetText(expanded and 'Hide' or 'x')
    for _,button in pairs(self.buttons) do button:Hide() end
    for row,element in ipairs(NS.TotemModel.elements) do
        local y=-32-(row-1)*72
        local x=10+(row-1)*54
        local ordered=self.model:Ordered(element.slot)
        local group=self.groups[element.slot]
        group.selected=ordered[1]
        group.next:ClearAllPoints()
        group.next:SetPoint('TOPLEFT',self.frame,'TOPLEFT',expanded and 306 or (x+36),expanded and (y-24) or -48)
        if self.model:Next(element.slot) then group.next:Enable() else group.next:Disable() end
        group.heading:ClearAllPoints(); group.heading:SetPoint('TOPLEFT',self.frame,'TOPLEFT',expanded and 10 or x,expanded and y or -28)
        group.timer:ClearAllPoints(); group.timer:SetPoint('TOPLEFT',self.frame,'TOPLEFT',expanded and 325 or x,expanded and y or -86)
        group.timer:SetWidth(expanded and 75 or 50)
        group.empty:ClearAllPoints(); group.empty:SetPoint('TOPLEFT',self.frame,'TOPLEFT',expanded and 10 or x,expanded and (y-30) or -58)
        group.empty:SetWidth(expanded and 380 or 50)
        group.empty:SetText(#ordered==0 and (self.model.error and (expanded and 'Spellbook unavailable' or '?') or (expanded and 'No learned totems for this element' or '--')) or '')
        if expanded then group.status:Show() else group.status:Hide() end
        for index,spell in ipairs(ordered) do
            local button=self.buttons[spell.baseID] or self:MakeButton(spell)
            self.buttons[spell.baseID]=button; button.record=spell
            button:ClearAllPoints(); button:SetPoint('TOPLEFT',self.frame,'TOPLEFT',expanded and (10+(index-1)*42) or x,expanded and (y-22) or -46)
            -- Spell names select the highest learned rank. Right-click has no cast action.
            button:SetAttribute('type1','spell'); button:SetAttribute('spell',spell.name); button:SetAttribute('unit','player')
            button.icon:SetTexture(spell.icon)
            button.star:SetText(self.addon.db.totemFavorites[element.slot]==spell.baseID and '|cffffff00*|r' or '')
            if expanded or index==1 then button:Show() else button:Hide() end
        end
    end
    self:ConfigureSequence()
    for index,button in ipairs(self.loadButtons) do
        if self.addon.db.totemPresets[index] then button:Enable() else button:Disable() end
    end
end

function Panel:Cycle(slot)
    if InCombatLockdown() then self:Message('Change totem choices outside combat.'); return false end
    local nextSpell=self.model:Next(slot)
    if not nextSpell then return false end
    local ok,err=self.model:SetFavorite(nextSpell.baseID)
    if not ok then self:Message(err); return false end
    self:Layout(); self:Update()
    return true
end

function Panel:ConfigureSequence()
    local macro,count=self.model:Sequence()
    self.dropSet:SetAttribute('type1',macro and 'macro' or nil)
    self.dropSet:SetAttribute('macrotext1',macro)
    self.dropSet:SetText(macro and ('Drop set ('..count..' clicks)') or (self.model.error and 'Spellbook unavailable' or (count==0 and 'No learned totems' or 'Use individual totem buttons')))
    if macro then self.dropSet:Enable() else self.dropSet:Disable() end
end

function Panel:UpdateReminder(slot,group)
    local missing=group.activeState=='missing' or group.activeState=='other'
    for _,spell in ipairs(self.model.groups[slot]) do
        local button=self.buttons[spell.baseID]
        if button then
            if group.selected and group.selected.baseID==spell.baseID and missing then
                button.reminderLabel:SetText(group.activeState=='other' and 'SWAP' or 'DROP')
                button.reminderActive=true
                button.reminderPulse=not not InCombatLockdown()
                if not button.reminderPulse then button.reminder:SetAlpha(0.85) end
                button.reminder:Show(); button.reminderBacking:Show(); button.reminderLabel:Show()
                for _,edge in ipairs(button.reminderEdges) do edge:SetAlpha(1); edge:Show() end
            else
                button.reminderActive=false; button.reminderPulse=false
                button.reminder:Hide(); button.reminderBacking:Hide(); button.reminderLabel:Hide()
                for _,edge in ipairs(button.reminderEdges) do edge:Hide() end
            end
        end
    end
end

function Panel:ToggleExpanded()
    if InCombatLockdown() then self:Message('Open totem setup outside combat.'); return false end
    self.addon.db.totemExpanded=not self.addon.db.totemExpanded
    self:Layout()
    return true
end

function Panel:Refresh()
    if not self.frame then return end
    if InCombatLockdown() then self.pending=true; return end
    local ok,err=self.model:Refresh()
    self:Layout()
    if ok then self.note:SetText('Left-click: cast | Right-click: favorite (*)')
    else self.note:SetText('Spellbook unavailable; existing buttons retained.'); self.error=err end
    self.pending=false
    self:Update()
end

function Panel:UpdateGroup(slot,group)
    group.activeState='unknown'; group.rangeState='unknown'
    group.timer:SetText('?')
    group.status:SetText('Status unavailable')
    if type(GetTotemInfo)~='function' then return end
    local ok,have,name,start,duration,icon,modRate,spellID=pcall(GetTotemInfo,slot)
    if not ok then return end
    group.activeState=self.model:ActiveState(group.selected,have,name,start,duration,spellID)
    local secret=function(value) return self.model:Secret(value) end
    if not secret(have) and have==false then group.status:SetText('No active totem'); group.timer:SetText('--'); return end
    if not secret(name) and name=='' then return end
    if secret(name) or type(name)=='string' then pcall(group.status.SetText,group.status,name) end
    if type(GetTotemDuration)=='function' then
        local displayed=pcall(function()
            local object=GetTotemDuration(slot)
            group.timer:SetFormattedText('%.0fs',object:GetRemainingDuration())
        end)
        if displayed then return end
    end
    if not secret(start) and not secret(duration) and type(start)=='number' and type(duration)=='number'
        and start==start and duration==duration and start<math.huge and duration<math.huge then
        group.timer:SetText(string.format('%ds',math.max(0,math.ceil(start+duration-GetTime()))))
    end
end

function Panel:Update()
    if not self.frame then return end
    for slot,group in ipairs(self.groups) do self:UpdateGroup(slot,group); self:UpdateReminder(slot,group) end
end

function Panel:SetVisible(visible)
    if not self.frame then self.addon:Say('Totem controls are available on Shaman characters.'); return false end
    if InCombatLockdown() then self:Message('Show or hide totem controls outside combat.'); return false end
    self.addon.db.totemVisible=not not visible
    if visible then self.frame:Show(); self:Refresh() else self.frame:Hide() end
    return true
end

function Panel:Preset(index,save)
    local ok,message
    if save then ok,message=self.model:SavePreset(index) else ok,message=self.model:LoadPreset(index) end
    if ok then self:Layout() end
    self:Message(message)
end

function Panel:PresetTooltip(button,index,save)
    if not GameTooltip then return end
    GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
    GameTooltip:AddLine((save and 'Save favorites to preset ' or 'Load favorites from preset ')..index)
    local choices=save and self.addon.db.totemFavorites or self.addon.db.totemPresets[index] or {}
    for _,element in ipairs(NS.TotemModel.elements) do
        local spell=self.model.spells[choices[element.slot]]
        GameTooltip:AddLine(element.name..': '..(spell and spell.name or 'None available'),1,1,1)
    end
    GameTooltip:AddLine(save and 'Replaces this saved preset.' or 'Does not summon. Click each totem to cast.',0.45,0.95,0.85)
    GameTooltip:Show()
end

function Panel:Debug()
    if not self.model then self.addon:Say('Totem controls require a Shaman.'); return end
    local count=0; for _ in pairs(self.model.spells) do count=count+1 end
    self.addon:Say('Totems: '..count..' learned types; info API='..type(GetTotemInfo)..', duration API='..type(GetTotemDuration)..', range API=unavailable, pending refresh='..tostring(not not self.pending))
    if self.model.error then self.addon:Say('Totem spellbook: '..self.model.error) end
end

function Panel:FinishDrag()
    if not self.moving or InCombatLockdown() then return end
    self.frame:StopMovingOrSizing(); self.moving=false
    local x,y=self.frame:GetCenter(); local cx,cy=UIParent:GetCenter()
    if not x or not y or not cx or not cy then return end
    self.addon.db.totemX=x-cx-self.frame:GetWidth()/2
    self.addon.db.totemY=y-cy+self.frame:GetHeight()/2
    self.addon.db.totemTopLeft=true
    self.frame:ClearAllPoints()
    self.frame:SetPoint('TOPLEFT',UIParent,'CENTER',self.addon.db.totemX,self.addon.db.totemY)
end

function Panel:Create(addon)
    local self=setmetatable({addon=addon,buttons={},groups={},loadButtons={},saveButtons={}},Panel)
    local ok,_,class=pcall(UnitClass,'player')
    if not ok or (issecretvalue and issecretvalue(class)) or class~='SHAMAN' then return self end
    self.model=NS.TotemModel:Create(addon.db)
    local frame=CreateFrame('Frame','MojowTotemPanel',UIParent,'BackdropTemplate')
    self.frame=frame
    local width,height=addon.db.totemExpanded and 410 or 232,addon.db.totemExpanded and 440 or 138
    frame:SetSize(width,height)
    if not addon.db.totemTopLeft then
        -- Existing saves used the center of the currently selected layout.
        addon.db.totemX=addon.db.totemX-width/2
        addon.db.totemY=addon.db.totemY+height/2
        addon.db.totemTopLeft=true
    end
    frame:SetPoint('TOPLEFT',UIParent,'CENTER',addon.db.totemX,addon.db.totemY)
    frame:SetClampedToScreen(true); frame:SetMovable(true); frame:EnableMouse(true); frame:RegisterForDrag('LeftButton')
    frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    NS.Appearance:Background(frame,0.025,0.035,0.05,0.95); frame:SetBackdropBorderColor(0.3,0.6,0.6,1)
    local title=text(frame,10,-10,126); title:SetText('MOJOW | TOTEMS')
    title:SetTextColor(0.45,0.95,0.85)
    self.expand=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
    self.expand:SetSize(65,22); self.expand:SetPoint('TOPRIGHT',frame,'TOPRIGHT',-30,-4)
    self.expand:SetScript('OnClick',function() self:ToggleExpanded() end)
    for row,element in ipairs(NS.TotemModel.elements) do
        local y=-32-(row-1)*72
        local heading=text(frame,10,y,55); heading:SetText(element.name)
        local slot=element.slot
        local nextButton=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        nextButton:SetSize(16,30); nextButton:SetText('>')
        nextButton:SetScript('OnClick',function() self:Cycle(slot) end)
        nextButton:SetScript('OnEnter',function(button)
            if not GameTooltip then return end
            GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
            local nextSpell=self.model:Next(slot)
            GameTooltip:AddLine(nextSpell and ('Next: '..nextSpell.name) or 'Only one learned choice')
            GameTooltip:AddLine('Click to switch this element outside combat.',1,1,1,true)
            GameTooltip:Show()
        end)
        nextButton:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
        self.groups[slot]={heading=heading,status=text(frame,70,y,245),timer=text(frame,325,y,75),empty=text(frame,10,y-30,380),next=nextButton}
    end
    self.dropSet=CreateFrame('Button',nil,frame,'SecureActionButtonTemplate,UIPanelButtonTemplate')
    self.dropSet:SetSize(200,22); self.dropSet:SetPoint('BOTTOMLEFT',frame,'BOTTOMLEFT',10,8)
    self.dropSet:RegisterForClicks('AnyDown','AnyUp')
    self.dropSet:SetScript('OnEnter',function(button)
        if not GameTooltip then return end
        GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
        GameTooltip:AddLine('One chosen totem per click',1,1,1)
        if self.model.error then GameTooltip:AddLine('Spellbook unavailable; showing last learned choices.',1,0.8,0.1,true) end
        GameTooltip:AddLine('Click again after each global cooldown. Restarts after 6 seconds without a click.',0.7,0.9,1,true)
        for _,element in ipairs(NS.TotemModel.elements) do
            local spell=self.groups[element.slot].selected
            if spell then GameTooltip:AddLine(element.name..': '..spell.name,1,1,1) end
        end
        GameTooltip:AddLine('Cannot summon all elements simultaneously.',1,0.8,0.1,true)
        GameTooltip:Show()
    end)
    self.dropSet:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    self.note=text(frame,10,-326,390)
    for index=1,3 do
        local preset=index
        local save=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        save:SetSize(58,24); save:SetPoint('TOPLEFT',frame,'TOPLEFT',10+(index-1)*132,-350)
        save:SetText('Save '..index); save:SetScript('OnClick',function() self:Preset(preset,true) end)
        save:SetScript('OnEnter',function(button) self:PresetTooltip(button,preset,true) end)
        save:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
        self.saveButtons[index]=save
        local load=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        load:SetSize(58,24); load:SetPoint('TOPLEFT',frame,'TOPLEFT',72+(index-1)*132,-350)
        load:SetText('Load '..index); load:SetScript('OnClick',function() self:Preset(preset,false) end)
        load:SetScript('OnEnter',function(button) self:PresetTooltip(button,preset,false) end)
        load:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
        self.loadButtons[index]=load
    end
    local hint=text(frame,10,-387,305); hint:SetText('Presets save favorites; they do not summon totems.')
    self.hint=hint
    local close=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
    close:SetSize(65,22); close:SetPoint('BOTTOMRIGHT',frame,'BOTTOMRIGHT',-8,8)
    close:SetText('Hide'); close:SetScript('OnClick',function() self:SetVisible(false) end)
    self.close=close
    frame:SetScript('OnDragStart',function() if not InCombatLockdown() then frame:StartMoving(); self.moving=true end end)
    frame:SetScript('OnDragStop',function() self:FinishDrag() end)
    local elapsed=0
    frame:SetScript('OnUpdate',function(_,delta) elapsed=elapsed+delta; if elapsed>=0.25 then elapsed=0; self:Update() end end)
    self.events=CreateFrame('Frame')
    for _,event in ipairs({'SPELLS_CHANGED','PLAYER_REGEN_ENABLED','PLAYER_REGEN_DISABLED','PLAYER_TOTEM_UPDATE'}) do self.events:RegisterEvent(event) end
    self.events:SetScript('OnEvent',function(_,event)
        if event=='PLAYER_REGEN_DISABLED' then
            if self.moving and pcall(frame.StopMovingOrSizing,frame) then self.moving=false end
            self:Update()
        elseif event=='PLAYER_REGEN_ENABLED' then self:FinishDrag(); self:Refresh()
        elseif event=='SPELLS_CHANGED' then self:Refresh()
        else self:Update() end
    end)
    self:SetVisible(addon.db.totemVisible)
    -- Hidden panels still need their learned actions configured before combat.
    if not addon.db.totemVisible then self:Refresh() end
    return self
end
