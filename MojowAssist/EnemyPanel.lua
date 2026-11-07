-- Nearby display with optional secure Shaman healing. Assist remains independent.
local _, NS = ...
local Panel = {}
Panel.__index = Panel
NS.EnemyPanel = Panel
local WIDTH, ROW_HEIGHT = 238, 38

local function text(parent, x, y, width)
    local label = parent:CreateFontString(nil, 'OVERLAY', 'GameFontHighlightSmall')
    label:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    label:SetWidth(width)
    label:SetJustifyH('LEFT')
    label:SetWordWrap(false)
    return label
end

local function backdrop(frame)
    frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8', edgeFile='Interface\\Buttons\\WHITE8X8', edgeSize=1})
    NS.Appearance:Background(frame,0.025, 0.035, 0.05, 0.94)
    frame:SetBackdropBorderColor(0.23, 0.29, 0.32, 1)
end

function Panel:FinishDrag()
    if InCombatLockdown() then self.dragAnchorPending=true; return false end
    local frame=self.frame
    frame:StopMovingOrSizing(); self.moving=false
    local x=frame:GetCenter()
    local y=type(frame.GetTop)=='function' and frame:GetTop()
    local px,py=UIParent:GetCenter()
    local ratio=UIParent:GetEffectiveScale()/frame:GetEffectiveScale()
    if x and y and px and py then self.addon.db[self.xKey],self.addon.db[self.yKey]=x-px*ratio,y-py*ratio end
    -- WoW's drag operation may replace TOP with CENTER or a screen-edge anchor.
    frame:ClearAllPoints()
    frame:SetPoint('TOP',UIParent,'CENTER',self.addon.db[self.xKey],self.addon.db[self.yKey])
    self.dragAnchorPending=false
    return true
end

function Panel:RowCapacity(baseHeight)
    local frame=self.frame
    if type(frame.GetTop)~='function' or type(UIParent.GetBottom)~='function' then return 12 end
    local top,bottom=frame:GetTop(),UIParent:GetBottom()
    if not top or not bottom then return 12 end
    local ratio=UIParent:GetEffectiveScale()/frame:GetEffectiveScale()
    -- Reserve a small bottom margin; excess rows use the existing scroll paging.
    return math.max(0,math.min(12,math.floor((top-bottom*ratio-8-baseHeight)/ROW_HEIGHT)))
end

function Panel:Includes(section)
    return self.scope=='all' or (self.isGroup and section.key=='group') or (not self.isGroup and section.key~='group')
end

function Panel:Create(addon,scope)
    local self = setmetatable({addon=addon, scope=scope or 'all', isGroup=scope=='group', roster=NS.EnemyRoster:Create(), rows={}, offset=0}, Panel)
    self.xKey,self.yKey,self.scaleKey=self.isGroup and 'groupX' or 'enemyX',self.isGroup and 'groupY' or 'enemyY',self.isGroup and 'groupScale' or 'enemyScale'
    self.visibleKey=self.isGroup and 'enemyShowGroup' or 'enemyVisible'
    self.contentTop=self.isGroup and 27 or 63
    self.healTracePending=false
    self.healsDirty=true
    self.clickHealing=NS.NearbyHealing and NS.NearbyHealing:Enabled() or false
    local frame = CreateFrame('Frame', self.isGroup and 'MojowGroupPanel' or 'MojowEnemyPanel', UIParent, 'BackdropTemplate')
    self.frame = frame
    frame:SetSize(WIDTH, 70)
    frame:SetPoint('TOP', UIParent, 'CENTER', addon.db[self.xKey], addon.db[self.yKey])
    frame:SetScale(addon.db[self.scaleKey])
    frame:SetClampedToScreen(true)
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:EnableMouseWheel(true)
    frame:RegisterForDrag('LeftButton')
    backdrop(frame)
    self.title = text(frame, 9, -8, WIDTH-35)
    self.title:SetTextColor(0.45, 0.95, 0.85)
    self.assistSummary=text(frame,9,-25,WIDTH-18)
    self.assistSummary:SetHeight(30)
    self.assistSummary:SetWordWrap(true)
    self.assistSummary:SetTextColor(0.3,1,0.8)
    if self.isGroup then self.assistSummary:Hide() end
    self.footer = text(frame, 9, -30, WIDTH-18)
    local close = CreateFrame('Button', nil, frame)
    close:SetSize(20,20)
    close:SetPoint('TOPRIGHT', frame, 'TOPRIGHT', -2,-2)
    local closeText = text(close,4,-4,16)
    closeText:SetText('x')
    close:SetScript('OnClick', function() self:SetVisible(false) end)
    frame:SetScript('OnDragStart', function() if not InCombatLockdown() then frame:StartMoving(); self.moving=true end end)
    frame:SetScript('OnDragStop', function() if self:FinishDrag() then self:Refresh() end end)
    frame:SetScript('OnMouseWheel', function(_, delta)
        if self.clickHealing and InCombatLockdown() then return end
        self.offset=math.max(0,math.min(self.maxOffset or 0,self.offset-delta))
        self:Refresh()
    end)
    self.headers={}
    self.sectionBoxes={}
    for i=1,#NS.EnemySections do
        self.headers[i]=text(frame,9,-27,WIDTH-18)
        local color=NS.EnemySections[i].color
        self.headers[i]:SetTextColor(color[1],color[2],color[3])
        local edges={}
        for edge=1,4 do
            local texture=frame:CreateTexture(nil,'ARTWORK')
            texture:SetColorTexture(color[1],color[2],color[3],0.8)
            texture:Hide(); edges[edge]=texture
        end
        self.sectionBoxes[i]=edges
    end
    for i=1,12 do self.rows[i]=self:CreateRow(i) end
    if self.clickHealing and not self.isGroup then
        self.combatRows={}
        for i,unit in ipairs({'focustarget'}) do
            local row=self:CreateRow(12+i)
            row.fixedEnemyUnit=unit
            row.roleLabel=text(frame,9,-66-(i-1)*(ROW_HEIGHT+24),WIDTH-18)
            row.roleLabel:SetText("Focus's target")
            row.roleLabel:SetTextColor(0.45,0.95,0.85)
            row:ClearAllPoints(); row:SetPoint('TOPLEFT',frame,'TOPLEFT',8,-81-(i-1)*(ROW_HEIGHT+24))
            local top=63+(i-1)*(ROW_HEIGHT+24)
            row.sectionBox={}
            for _,box in ipairs({{4,top,WIDTH-8,2},{4,top+ROW_HEIGHT+18,WIDTH-8,2},
                {4,top,2,ROW_HEIGHT+20},{WIDTH-6,top,2,ROW_HEIGHT+20}}) do
                local edge=frame:CreateTexture(nil,'ARTWORK')
                edge:SetColorTexture(0.3,1,0.8,0.8)
                edge:SetPoint('TOPLEFT',frame,'TOPLEFT',box[1],-box[2])
                edge:SetSize(box[3],box[4]); row.sectionBox[#row.sectionBox+1]=edge
            end
            self.combatRows[i]=row
        end
    end
    self.events=CreateFrame('Frame')
    local eventNames={'NAME_PLATE_UNIT_ADDED','NAME_PLATE_UNIT_REMOVED','PLAYER_ENTERING_WORLD','GROUP_ROSTER_UPDATE','PLAYER_REGEN_ENABLED','PLAYER_REGEN_DISABLED','SPELLS_CHANGED','PLAYER_TARGET_CHANGED','PLAYER_FOCUS_CHANGED','RAID_TARGET_UPDATE','UNIT_CONNECTION','UNIT_HEAL_PREDICTION','UNIT_HEALTH','UNIT_FLAGS','UNIT_AURA','QUEST_LOG_UPDATE','UI_ERROR_MESSAGE','ADDON_ACTION_BLOCKED','ADDON_ACTION_FORBIDDEN'}
    for _, event in ipairs(eventNames) do self.events:RegisterEvent(event) end
    self.events:RegisterEvent('UNIT_PET')
    self.events:RegisterEvent('UNIT_TARGET')
    self.events:SetScript('OnEvent',function(_,event,unit,...)
        if event=='UI_ERROR_MESSAGE' and NS.NearbyHealing then NS.NearbyHealing:CaptureHealError(self,...) end
        if event=='UI_ERROR_MESSAGE' or event=='ADDON_ACTION_BLOCKED' or event=='ADDON_ACTION_FORBIDDEN' then
            if self.healTraceUntil and GetTime()<=self.healTraceUntil and self.addon.Say then
                NS.NearbyHealing:TraceEvent(self.addon,event,unit,...)
            end
            return
        end
        if event=='QUEST_LOG_UPDATE' then self.questRevision=(self.questRevision or 0)+1 end
        if event=='NAME_PLATE_UNIT_ADDED' and not self.isGroup then self.roster:Add(unit)
        elseif event=='NAME_PLATE_UNIT_REMOVED' then self.roster:Remove(unit)
        elseif event=='PLAYER_ENTERING_WORLD' or event=='PLAYER_REGEN_ENABLED' then self:Seed() end
        if event=='SPELLS_CHANGED' then self.healsDirty=true end
        if event=='UNIT_AURA' or event=='NAME_PLATE_UNIT_ADDED' or event=='NAME_PLATE_UNIT_REMOVED' then for _,row in ipairs(self.rows) do row.dispelNext=0 end end
        if event=='PLAYER_REGEN_DISABLED' and self.moving and pcall(frame.StopMovingOrSizing,frame) then
            self.moving=false; self.dragAnchorPending=true
        end
        if event=='PLAYER_REGEN_ENABLED' and (self.moving or self.dragAnchorPending) then self:FinishDrag() end
        if frame:IsShown() then self:Refresh() end
    end)
    local elapsed=0
    frame:SetScript('OnUpdate',function(_,delta)
        elapsed=elapsed+delta
        if elapsed>=0.1 then elapsed=0; self:Refresh(); self:RefreshTooltip() end
    end)
    self:Seed()
    self:SetVisible(addon.db[self.visibleKey])
    return self
end

function Panel:RefreshTooltip()
    local row=self.hoveredRow
    if not row or not GameTooltip or type(GameTooltip.IsOwned)~='function' then return end
    if not row:IsShown() then
        if GameTooltip:IsOwned(row) then GameTooltip:Hide() end
        self.hoveredRow=nil; return
    end
    if GameTooltip:IsOwned(row) then
        NS.NearbyHealing:Tooltip(row,self.healLeft,self.healRight,self.roster:IsFriendly(row.boundUnit),self.addon.db)
    end
end

function Panel:Seed()
    self.roster:Clear()
    if self.isGroup then return end
    -- Unit token probes only; never touch forbidden nameplate frames.
    for i=1,200 do
        local unit='nameplate'..i
        if self.roster:Read(UnitExists,unit) then self.roster:Add(unit) end
    end
end

function Panel:SetVisible(visible)
    if self.clickHealing and InCombatLockdown() then
        if self.addon.Say then self.addon:Say('Show or hide '..(self.isGroup and 'Group Members' or 'Extended Targets')..' outside combat.') end
        return false
    end
    self.addon.db[self.visibleKey]=not not visible
    if visible then self:Seed(); self.frame:Show(); self:Refresh()
    else self.frame:Hide() end
    return true
end

function Panel:CreateRow(index)
    local row=CreateFrame(self.clickHealing and 'Button' or 'Frame',nil,self.frame,self.clickHealing and 'SecureActionButtonTemplate,BackdropTemplate' or 'BackdropTemplate')
    row.groupWindow=self.isGroup
    if self.clickHealing then
        row:RegisterForClicks('AnyDown','AnyUp')
        row:SetScript('PreClick',function(_,button,down)
            if (row.targetOnlyUnit or row.enemySelectCast or row.groupSelectUnit) and button=='LeftButton' and down then self.pendingTargetClick=row end
            NS.NearbyHealing:TrackHealClick(self,row,button,down)
            if self.healTracePending and self.addon.Say then
                self.healTraceUntil=GetTime()+2
                self.addon:Say('Heal input: '..button..(down and ' down' or ' up'))
            end
        end)
        row:SetScript('PostClick',function(_,button,down)
            if button=='LeftButton' and not down and self.pendingTargetClick==row then
                self.pendingTargetClick=nil
                if not InCombatLockdown() then self:Refresh() end
            end
            if self.healTracePending and self.addon.Say then
                NS.NearbyHealing:Trace(self.addon,row,button)
                if not down then self.healTracePending=false end
            end
        end)
        row:SetScript('OnEnter',function() self.hoveredRow=row; NS.NearbyHealing:Tooltip(row,self.healLeft,self.healRight,self.roster:IsFriendly(row.boundUnit),self.addon.db) end)
        row:SetScript('OnLeave',function() self.hoveredRow=nil; if GameTooltip then GameTooltip:Hide() end end)
    end
    row:SetSize(WIDTH-16,ROW_HEIGHT-2)
    row:SetPoint('TOPLEFT',self.frame,'TOPLEFT',8,-27-(index-1)*ROW_HEIGHT)
    backdrop(row)
    row.health=CreateFrame('StatusBar',nil,row)
    row.health:SetSize(WIDTH-20,19)
    row.health:SetPoint('TOPLEFT',row,'TOPLEFT',2,-2)
    row.health:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    row.raidIcon=row.health:CreateTexture(nil,'OVERLAY')
    row.raidIcon:SetSize(12,12)
    row.raidIcon:SetPoint('TOPLEFT',row.health,'TOPLEFT',3,-3)
    row.raidIcon:SetTexture('Interface\\TargetingFrame\\UI-RaidTargetingIcons')
    row.raidIcon:Hide()
    row.questIcon=row.health:CreateTexture(nil,'OVERLAY')
    row.questIcon:SetSize(14,14)
    row.questIcon:SetPoint('TOPLEFT',row.health,'TOPLEFT',18,-2)
    row.questIcon:Hide()
    row.name=text(row.health,18,-3,WIDTH-99)
    row.name:SetFont(STANDARD_TEXT_FONT or 'Fonts\\FRIZQT__.TTF',12,'OUTLINE')
    row.value=text(row.health,WIDTH-77,-3,53)
    row.cast=CreateFrame('StatusBar',nil,row)
    row.cast:SetSize(WIDTH-20,12)
    row.cast:SetPoint('TOPLEFT',row,'TOPLEFT',2,-22)
    row.cast:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    row.spell=text(row.cast,4,0,WIDTH-86)
    row.timer=text(row.cast,WIDTH-77,0,53)
    -- Keep native timers separate from legacy numeric bars; hiding a timer must
    -- never leave its engine-driven value attached to a reused legacy row.
    row.nativeCast=CreateFrame('StatusBar',nil,row)
    row.nativeCast:SetSize(WIDTH-20,12)
    row.nativeCast:SetPoint('TOPLEFT',row,'TOPLEFT',2,-22)
    row.nativeCast:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    row.nativeSpell=text(row.nativeCast,4,0,WIDTH-86)
    row.nativeTimer=text(row.nativeCast,WIDTH-77,0,53)
    row.nativeCast:Hide()
    if NS.HealPrediction then NS.HealPrediction:Create(row) end
    return row
end

function Panel:Health(row, unit)
    if NS.HealPrediction then NS.HealPrediction:Clear(row) end
    -- Native widgets accept opaque health values. Never inspect or divide them.
    row.value:SetText('?')
    local ok=pcall(function()
        row.health:SetMinMaxValues(0,UnitHealthMax(unit))
        row.health:SetValue(UnitHealth(unit))
    end)
    if not ok then
        row.health:SetMinMaxValues(0,1)
        row.health:SetValue(0)
        return
    end
    local formatted=false
    if UnitHealthPercent and CurveConstants and CurveConstants.ScaleTo100 then
        formatted=pcall(function()
            row.value:SetFormattedText('%.0f%%',UnitHealthPercent(unit,true,CurveConstants.ScaleTo100))
        end)
    end
    if not formatted then
        pcall(function() row.value:SetFormattedText('%d',UnitHealth(unit)) end)
    end
    if NS.HealPrediction then NS.HealPrediction:Update(row,unit) end
end

function Panel:HasPlayerAggro(unit)
    local r=self.roster
    if r:Read(UnitIsPlayer,unit) and not r:Read(UnitCanAttack,'player',unit) then return false end
    local threat=r:Read(UnitThreatSituation,'player',unit)
    if type(threat)=='number' then return threat==2 or threat==3 end
    return r:Read(UnitAffectingCombat,unit) and r:Read(UnitIsUnit,unit..'target','player') or false
end

function Panel:MobEngaged(unit)
    local r=self.roster
    for _, ally in ipairs({'player','pet'}) do
        local threat=r:Read(UnitThreatSituation,ally,unit)
        if type(threat)=='number' and threat>=0 then return true end
    end
    if not r:Read(UnitAffectingCombat,unit) then return false end
    local target=unit..'target'
    return r:Read(UnitIsUnit,target,'player') or r:Read(UnitIsUnit,target,'pet')
        or r:Read(UnitInParty,target) or r:Read(UnitInRaid,target) or false
end

function Panel:ClassColor(row,unit)
    local r=self.roster
    row.name:SetTextColor(1,1,1)
    local red,green,blue=0.65,0.23,0.18
    if r:Read(UnitReaction,unit,'player')==4 and not self:MobEngaged(unit) then
        red,green,blue=0.78,0.65,0.16
    end
    row.health:SetStatusBarColor(red,green,blue,0.8)
    local player,known=r:Read(UnitIsPlayer,unit)
    if known and not player then return end
    if player then row.health:SetStatusBarColor(0.12,0.38,0.85,0.8) end
    -- Native lookup accepts an opaque class token; never use one as a Lua key.
    if C_ClassColor and C_ClassColor.GetClassColor then
        local canSelect=C_CurveUtil and C_CurveUtil.EvaluateColorFromBoolean and CreateColor
        if player or canSelect then
            local ok=pcall(function()
                local _,class=UnitClass(unit)
                local color=C_ClassColor.GetClassColor(class)
                local barColor=CreateColor and CreateColor(0.12,0.38,0.85,1)
                if canSelect then
                    color=C_CurveUtil.EvaluateColorFromBoolean(UnitIsPlayer(unit),color,CreateColor(1,1,1,1))
                    barColor=C_CurveUtil.EvaluateColorFromBoolean(UnitIsPlayer(unit),barColor,CreateColor(red,green,blue,1))
                end
                row.name:SetTextColor(color:GetRGB())
                if barColor then
                    local br,bg,bb=barColor:GetRGB()
                    row.health:SetStatusBarColor(br,bg,bb,0.8)
                end
            end)
            if ok then self.nativeColorObserved=true; return end
        end
    end
    if player then
        local ok,_,class=pcall(UnitClass,unit)
        if ok and not r:IsSecret(class) and type(class)=='string' then
            local color=RAID_CLASS_COLORS and RAID_CLASS_COLORS[class]
            if color then row.name:SetTextColor(color.r,color.g,color.b) end
        end
    end
end

function Panel:NativeCast(row,cast)
    if not row.nativeCast.SetTimerDuration then return false end
    local ok=pcall(function()
        row.nativeCast:SetStatusBarColor(cast.channel and 0.20 or 0.55,0.40,cast.channel and 0.55 or 0.18,0.9)
        local interpolation=Enum and Enum.StatusBarInterpolation and Enum.StatusBarInterpolation.Immediate or 0
        local direction=Enum and Enum.StatusBarTimerDirection and Enum.StatusBarTimerDirection.RemainingTime or 1
        row.nativeCast:SetTimerDuration(cast.duration,interpolation,direction)
        row.nativeSpell:SetFormattedText(cast.channel and 'Channeling: %s' or 'Casting: %s',cast.name)
    end)
    if not ok then return false end
    row.nativeTimer:SetText('')
    local timerOK=pcall(function() row.nativeTimer:SetFormattedText('%.1fs',cast.duration:GetRemainingDuration()) end)
    if not timerOK then self.nativeTimerFailed=true end
    row.cast:Hide()
    row.nativeCast:Show()
    return true
end

function Panel:RefreshCast(row,unit)
    local cast=self.roster:Cast(unit)
    row.castInfo=cast
    row.nativeCast:Hide()
    row.cast:Show()
    row.cast:SetMinMaxValues(0,1)
    row.cast:SetValue(0)
    row.timer:SetText('')
    row.spell:SetText('')
    if cast and cast.native then
        if self:NativeCast(row,cast) then self.nativeCastObserved=true; return end
        self.nativeCastFailed=true
        cast=self.roster:Cast(unit,true)
        row.castInfo=cast
    end
    if cast and cast.restricted then row.spell:SetText('')
    elseif cast then
        row.cast:SetStatusBarColor(cast.channel and 0.20 or 0.55,0.40,cast.channel and 0.55 or 0.18,0.9)
        row.cast:SetValue(cast.remaining/cast.duration)
        row.spell:SetText((cast.channel and 'Channeling: ' or 'Casting: ')..cast.name)
        row.timer:SetText(string.format('%.1fs',cast.remaining))
        self.legacyCastObserved=true
    end
end

function Panel:Debug()
    self.healTracePending=true
    local say=function(message) self.addon:Say(message) end
    local flag=function(api,...)
        local value,known=self.roster:Read(api,...)
        if not known then return 'unavailable' end
        return value and 'yes' or 'no'
    end
    say('Target: exists='..flag(UnitExists,'target')..', player='..flag(UnitIsPlayer,'target')..', attackable='..flag(UnitCanAttack,'player','target'))
    say('Enemy display: '..#self.roster.order..' nameplate tokens tracked. Healing clicks='..tostring(self.clickHealing))
    say('Cast APIs: casting='..type(UnitCastingDuration)..', channel='..type(UnitChannelDuration)..', widget='..type(self.rows[1].nativeCast.SetTimerDuration))
    say('Class API: '..type(C_ClassColor and C_ClassColor.GetClassColor)..'; native color used='..tostring(not not self.nativeColorObserved))
    say('Since reload: native cast='..tostring(not not self.nativeCastObserved)..', legacy cast='..tostring(not not self.legacyCastObserved)..', native cast error='..tostring(not not self.nativeCastFailed)..', countdown error='..tostring(not not self.nativeTimerFailed))
end

function Panel:DisplayName(row,unit,prefix,levelText,readableName)
    row.name:SetText(prefix..'['..levelText..'] '..(type(readableName)=='string' and readableName or 'Name unavailable'))
    if type(readableName)=='string' then return end
    -- A restricted string may be displayed by native widgets, never inspected,
    -- concatenated, cached as identity, or used to create a targeting macro.
    local ok,raw=pcall(UnitName,unit)
    if ok and self.roster:IsSecret(raw) then
        pcall(row.name.SetFormattedText,row.name,'%s[%s] %s',prefix,levelText,raw)
    end
end

-- Follow the actual secure Assist binding, including native group reorders.
-- This only decorates a row; it never changes click actions or targets.
function Panel:AssistTargetUnit()
    local action=self.addon.action
    local button=action and action.button
    if not button or self.roster:Read(button.GetAttribute,button,'type')~='assist' then return nil,'No leader/focus' end
    local leader=self.roster:Read(button.GetAttribute,button,'unit')
    if type(leader)~='string' or leader=='none' then return nil,'No leader/focus' end
    if self.roster:Read(UnitExists,leader)~=true then return nil,'Leader/focus unavailable' end
    local target=leader..'target'
    local exists=self.roster:Read(UnitExists,target)
    if exists==false then return nil,'No target' end
    if exists~=true then return nil,'Target unavailable' end
    return target
end

function Panel:IsAssistTarget(unit)
    local target=self:AssistTargetUnit()
    return target~=nil and self.roster:Read(UnitIsUnit,unit,target)==true
end

function Panel:RefreshAssistSummary()
    if self.isGroup then return end
    local target,state=self:AssistTargetUnit()
    if not target then self.assistSummary:SetText('Assist: '..state); return end
    local name=self.roster:Read(UnitName,target)
    self.assistSummary:SetText('Assist target: '..(type(name)=='string' and name or 'Name unavailable'))
    if type(name)~='string' then
        local ok,raw=pcall(UnitName,target)
        if ok and self.roster:IsSecret(raw) then
            pcall(self.assistSummary.SetFormattedText,self.assistSummary,'Assist target: %s',raw)
        end
    end
end

function Panel:RefreshRaidIcon(row,unit)
    NS.NativeRaidMarker:Refresh(row.raidIcon,unit)
end

function Panel:RefreshQuestIcon(row,unit)
    row.questIcon:Hide(); row.questTexture=nil; row.questKind=nil
    row.name:ClearAllPoints(); row.name:SetPoint('TOPLEFT',row.health,'TOPLEFT',18,-3)
    row.name:SetWidth(WIDTH-99)
    local questie=Questie
    if type(questie)~='table' or type(questie.API)~='table' or questie.API.isReady~=true
        or type(questie.API.GetQuestObjectiveIconForUnit)~='function' then
        row.questCache=nil; return
    end
    local guid=self.roster:Read(UnitGUID,unit)
    if type(guid)~='string' or not (guid:match('^Creature%-') or guid:match('^Vehicle%-')) then
        row.questCache=nil; return
    end
    local now=GetTime()
    local cache=row.questCache
    if not cache or cache.guid~=guid or cache.revision~=self.questRevision or now>=cache.expires then
        local ok,icon=pcall(questie.API.GetQuestObjectiveIconForUnit,guid)
        if not ok or self.roster:IsSecret(icon) or type(icon)~='string' then icon=nil end
        cache={guid=guid,revision=self.questRevision,expires=now+1,icon=icon}
        row.questCache=cache
    end
    local icons=type(questie.icons)=='table' and questie.icons or {}
    local profile=type(questie.db)=='table' and questie.db.profile
    profile=type(profile)=='table' and profile or {}
    local icon=cache.icon
    -- Mirror Questie's chosen incomplete loot or kill objective, including custom themes.
    if icon and (icon==icons.loot or icon==profile.ICON_LOOT
        or icon==icons.slay or icon==profile.ICON_SLAY) then
        row.questKind=(icon==icons.slay or icon==profile.ICON_SLAY) and 'kill' or 'loot'
        row.questTexture=icon; row.questIcon:SetTexture(icon); row.questIcon:Show()
        row.name:ClearAllPoints(); row.name:SetPoint('TOPLEFT',row.health,'TOPLEFT',34,-3)
        row.name:SetWidth(WIDTH-115)
    end
end

function Panel:RefreshRow(row,unit)
    if NS.HealPrediction then NS.HealPrediction:Clear(row) end
    row:SetAlpha(1)
    row.displayUnavailable=false
    self:RefreshQuestIcon(row,unit)
    if row.nativePoisonReady then row.name:SetWidth(WIDTH-117) end
    self:RefreshRaidIcon(row,unit)
    local groupStatus=self.roster:GroupStatus(unit)
    row.groupStatus=groupStatus
    local name=self.roster:Read(UnitName,unit)
    local level=self.roster:Read(UnitLevel,unit)
    local levelText='?'
    if type(level)=='number' then
        if level==-1 then levelText='??'
        elseif level>0 and level<10000 then levelText=string.format('%d',level) end
    end
    row.tooltipName=type(name)=='string' and name or nil
    row.rangeSource=nil
    local fadeAlpha=1
    local farFriendly=false
    local rangeText
    local friendly=self.roster:IsFriendly(unit)
    if self.clickHealing and friendly then
        local left=NS.NearbyHealing:Range(self.healLeft,unit)
        local right=NS.NearbyHealing:Range(self.healRight,unit)
        local primary=left=='unavailable' and right or left
        fadeAlpha,primary,row.rangeSource=NS.NearbyHealing:RangeFade(self.healLeft or self.healRight,unit,self.roster:IsGroupMember(unit),primary)
        farFriendly=primary=='out'
        rangeText=({['in']='In heal range',out='Too far to heal',unknown='Range unavailable',unavailable='No available heal'})[primary]
        if row.rangeSource=='group' then
            rangeText=primary=='in' and 'Within group range' or primary=='out' and 'Outside group range' or 'Group range unavailable'
        end
        if row.rangeSource~='group' and left~='unavailable' and right~='unavailable' and left~='unknown' and right~='unknown' and left~=right then
            rangeText='Spell ranges differ'
        end
    elseif row.attackUnit then
        local left=NS.NearbyHealing:Range(self.damageLeft,unit)
        local right=NS.NearbyHealing:Range(self.damageRight,unit)
        rangeText=({['in']='In spell range',out='Out of spell range',unknown='Range unavailable',unavailable='No available spell'})[left=='unavailable' and right or left]
    end
    local assistMatch=self:IsAssistTarget(unit)
    local identity
    if assistMatch then
        local action=self.addon.action
        local source=action and self.roster:Read(action.button.GetAttribute,action.button,'unit')
        identity=source=='focus' and "Focus's target" or (self.roster:Read(UnitIsGroupLeader,source)==true and "Leader's target" or "Assist target")
    elseif self.roster:Read(UnitIsUnit,'focus',unit)==true then identity='Your focus'
    elseif self.roster:Read(UnitIsUnit,'target',unit)==true then identity='Your target' end
    row.identityStatus=identity
    if not groupStatus and NS.DispelHelper and self.clickHealing and friendly then
        NS.DispelHelper:Update(row,unit,name,self.dispelCapabilities)
    else row.dispelData=nil; row.dispelNext=0 end
    local dispelMarker=NS.DispelHelper and NS.DispelHelper:Marker(row.dispelData) or ''
    self:DisplayName(row,unit,dispelMarker,levelText,name)
    self:ClassColor(row,unit)
    if groupStatus then row.health:SetStatusBarColor(0.35,0.35,0.35,0.65) end
    row.health:SetAlpha(fadeAlpha)
    local brightness=groupStatus and 0.65 or 1
    row.name:SetAlpha(brightness)
    row.value:SetTextColor(brightness,brightness,brightness)
    NS.Appearance:Background(row,assistMatch and 0.02 or 0.025,assistMatch and 0.14 or 0.035,assistMatch and 0.14 or 0.05,0.94)
    if assistMatch then row:SetBackdropBorderColor(0.2,1,0.8,1)
    elseif self.roster:Read(UnitIsUnit,'target',unit) then row:SetBackdropBorderColor(1,0.82,0.25,1)
    else row:SetBackdropBorderColor(0.23,0.29,0.32,1) end
    if groupStatus then
        row.health:SetMinMaxValues(0,1); row.health:SetValue(0)
        row.value:SetText(groupStatus); row.castInfo=nil
        row.cast:SetMinMaxValues(0,1); row.cast:SetValue(0)
        row.spell:SetText(''); row.timer:SetText(''); row.nativeCast:Hide()
    else
        self:Health(row,unit)
        self:RefreshCast(row,unit)
    end
    self:PlainStatus(row,unit,rangeText,farFriendly,identity)
    if not self.clickHealing or not InCombatLockdown() then row:Show() end
end

function Panel:PlainStatus(row,unit,rangeText,far,identity)
    local primary,detail
    local clickStatus=row.enemySelectCast and 'Select and cast' or (row.targetOnlyUnit and 'Target only' or 'Select normally to cast')
    if row.focusTargetRow and (not row.damageLeft or self.roster:Read(UnitCanAttack,'player',unit)~=true) then
        clickStatus='Target only'; rangeText=nil
    end
    local dispel=row.dispelData
    local cast=row.castInfo
    local aggro=self:HasPlayerAggro(unit)
    row.aggroStatus=aggro and 'Attacking you' or nil
    if row.groupStatus then
        primary=({DEAD='Dead',GHOST='Ghost',OFFLINE='Offline',DOWN='Dead or ghost'})[row.groupStatus]
        detail='Cannot heal'
    elseif dispel and dispel.kind=='found' then
        primary=({Poison='Cure poison',Disease='Cure disease',Curse='Remove curse'})[dispel.dispel]
        detail=far and row.rangeSource~='group' and 'Too far to heal' or rangeText
    elseif far then primary=row.rangeSource=='group' and 'Outside group range' or 'Too far to heal'; detail=identity
    elseif cast and not cast.restricted then
        primary=aggro and 'Attacking you' or identity or (cast.channel and 'Channeling' or 'Casting')
        if cast.interruptible==true then detail='Interruptible'
        elseif cast.interruptible==false then detail='Cannot interrupt'
        else detail='Interrupt info unavailable' end
    elseif aggro then primary='Attacking you'; detail=identity or rangeText
    elseif identity then
        primary=identity
        detail=(cast and cast.restricted and 'Cast info unavailable') or rangeText or (row.enemyRow and clickStatus or nil)
    else
        primary=rangeText or (row.enemyRow and clickStatus or 'Display only')
        if dispel and dispel.kind=='unknown' then detail='Debuff info unavailable'
        elseif cast and cast.restricted then detail='Cast info unavailable' end
    end
    row.statusPrimary,row.statusDetail=primary,detail

end

function Panel:RefreshCombatRows()
    for _,row in ipairs(self.combatRows or {}) do
        local unit=row.fixedEnemyUnit
        if self.roster:Read(UnitExists,unit)==true then
            self:RefreshRow(row,unit)
        else
            row.displayUnavailable=true; if NS.HealPrediction then NS.HealPrediction:Clear(row) end; row.questIcon:Hide(); row.questTexture=nil; row.questKind=nil; row.questCache=nil
            row.castInfo=nil; row.statusPrimary='Focus target unavailable'; row.statusDetail=nil; row.identityStatus=nil
            row.tooltipName=nil; row.aggroStatus=nil; row.rangeSource=nil; row.health:SetAlpha(1)
            row.name:SetText('No focus target'); row.name:SetTextColor(1,1,1); row.value:SetText('')
            row.raidIcon:Hide(); row.groupStatus=nil; row.dispelData=nil
            row.health:SetMinMaxValues(0,1); row.health:SetValue(0)
            row.cast:SetMinMaxValues(0,1); row.cast:SetValue(0)
            row.spell:SetText(''); row.timer:SetText(''); row.nativeCast:Hide()
            row:SetBackdropBorderColor(0.23,0.29,0.32,1)
            NS.Appearance:Background(row,0.025,0.035,0.05,0.94)
        end
    end
end

function Panel:RefreshLocked()
    local inactive=0
    self:RefreshCombatRows()
    for _,row in ipairs(self.rows) do
        if NS.PetBars then NS.PetBars:Update(self,row) end
        if row.boundUnit then
            local sameName=not row.macroName or NS.NearbyHealing:TargetName(row.boundUnit)==row.macroName
            local present=self.roster:Present(row.boundUnit)
            local category=self.roster:Category(row.boundUnit)
            local sameSection=category~=nil and category==row.boundCategory
            local selfAllowed=row.boundUnit=='player' or not self.roster:IsSelf(row.boundUnit)
            if sameName and sameSection and selfAllowed and present then self:RefreshRow(row,row.boundUnit)
            else
                row.displayUnavailable=true; if NS.HealPrediction then NS.HealPrediction:Clear(row) end; row.questIcon:Hide(); row.questTexture=nil; row.questKind=nil; row.questCache=nil
                row.castInfo=nil; row.statusPrimary='Unit unavailable'; row.statusDetail=nil; row.identityStatus=nil
                row.tooltipName=nil; row.aggroStatus=nil; row.rangeSource=nil; row.health:SetAlpha(1)
                row.raidIcon:Hide(); row.groupStatus=nil
                row.dispelData={kind='unknown'}; row.dispelNext=0
                if present and (not sameSection or not selfAllowed) then
                    row.statusPrimary='List updates after combat'
                    row.name:SetText('Waiting for list refresh')
                else row.name:SetText(row.macroName and (row.macroName..' | unavailable') or 'Unit unavailable') end
                if row.boundCategory=='npc' or row.boundCategory=='enemy' then
                    row.name:SetText(''); row:SetAlpha(0.15); inactive=inactive+1
                end
                row.value:SetText('')
                row.health:SetMinMaxValues(0,1); row.health:SetValue(0)
                row.cast:SetMinMaxValues(0,1); row.cast:SetValue(0)
                row.spell:SetText(''); row.timer:SetText(''); row.nativeCast:Hide()
                row:SetBackdropBorderColor(0.23,0.29,0.32,1)
                NS.Appearance:Background(row,0.025,0.035,0.05,0.94)
            end
        end
    end
    self.footer:SetText(inactive>0 and (inactive..' inactive slots | Clears after combat') or 'Combat: rows fixed | Hover for details')
end

function Panel:Refresh()
    if self.moving then return end
    if self.pendingTargetClick then
        if type(IsMouseButtonDown)~='function' or IsMouseButtonDown('LeftButton') then return end
        self.pendingTargetClick=nil
    end
    self:RefreshAssistSummary()
    if self.clickHealing and InCombatLockdown() then self:RefreshLocked(); return end
    if self.clickHealing and self.healsDirty then
        self.healLeft,self.healRight=NS.NearbyHealing:Spells(self.addon.db); self.healsDirty=false
        self.damageLeft,self.damageRight=NS.NearbyHealing:DamageSpells(self.addon.db)
        for _,row in ipairs(self.combatRows or {}) do
            NS.NearbyHealing:Bind(row,row.fixedEnemyUnit,nil,nil,self.damageLeft,self.damageRight,true)
        end
        if NS.DispelHelper then self.dispelCapabilities=NS.DispelHelper:Capabilities() end
        for _,row in ipairs(self.rows) do row.dispelNext=0 end
    end
    self:RefreshCombatRows()
    local units,unknown=self.roster:Snapshot()
    local groups={group={},npc={},enemy={},friendly={}}
    for _,unit in ipairs(units) do
        local category=self.roster:Category(unit)
        if category then table.insert(groups[category],unit) else unknown=unknown+1 end
    end
    local count=0
    for _,section in ipairs(NS.EnemySections) do
        if self:Includes(section) and self.addon.db[section.option] then count=count+#groups[section.key] end
    end
    local baseHeight=self.contentTop+(self.combatRows and #self.combatRows*(ROW_HEIGHT+24) or 0)+26
    for _,section in ipairs(NS.EnemySections) do
        if self:Includes(section) and self.addon.db[section.option] then baseHeight=baseHeight+24 end
    end
    self.rowCapacity=self:RowCapacity(baseHeight)
    self.maxOffset=math.max(0,count-self.rowCapacity)
    self.offset=math.min(self.offset,self.maxOffset)
    self.title:SetText(self.isGroup and 'Mojow Group' or 'Mojow Extended Target List')
    local sections=NS.EnemySections
    local y,index,shown=self.contentTop+(self.combatRows and #self.combatRows*(ROW_HEIGHT+24) or 0),0,0
    for i,section in ipairs(sections) do
        local header=self.headers[i]
        local edges=self.sectionBoxes[i]
        header:Hide()
        for _,edge in ipairs(edges) do edge:Hide() end
        if self:Includes(section) and self.addon.db[section.option] then
            local sectionTop=y
            header:ClearAllPoints()
            header:SetPoint('TOPLEFT',self.frame,'TOPLEFT',9,-y-3)
            header:SetText(section.label..'  '..#groups[section.key])
            header:Show()
            y=y+18
            for _,unit in ipairs(groups[section.key]) do
                index=index+1
                if index>self.offset and shown<self.rowCapacity then
                    shown=shown+1
                    local row=self.rows[shown]
                    row:ClearAllPoints()
                    row:SetPoint('TOPLEFT',self.frame,'TOPLEFT',8,-y)
                    row.boundUnit=unit
                    row.boundCategory=section.key
                    if self.clickHealing then NS.NearbyHealing:Bind(row,unit,self.healLeft,self.healRight,self.damageLeft,self.damageRight) end
                    if NS.PetBars then NS.PetBars:Bind(self,row,unit); NS.PetBars:Update(self,row) end
                    if self.isGroup and self.clickHealing and NS.NativeDispelDisplay then
                        NS.NativeDispelDisplay:Bind(row,unit,self.addon.db.groupNativePoison and self.dispelCapabilities and self.dispelCapabilities.Poison~=nil)
                    end
                    self:RefreshRow(row,unit)
                    y=y+ROW_HEIGHT
                end
            end
            local height=y-sectionTop+2
            local geometry={{4,sectionTop,WIDTH-8,2},{4,y,WIDTH-8,2},
                {4,sectionTop,2,height},{WIDTH-6,sectionTop,2,height}}
            for index,edge in ipairs(edges) do
                local box=geometry[index]
                edge:ClearAllPoints()
                edge:SetPoint('TOPLEFT',self.frame,'TOPLEFT',box[1],-box[2])
                edge:SetSize(box[3],box[4]); edge:Show()
            end
            y=y+6
        end
    end
    for i=shown+1,12 do
        self.rows[i].boundUnit=nil
        self.rows[i].boundCategory=nil
        if self.clickHealing then NS.NearbyHealing:Bind(self.rows[i],nil,nil,nil) end
        if NS.PetBars then NS.PetBars:Bind(self,self.rows[i],nil) end
        if NS.NativeDispelDisplay then NS.NativeDispelDisplay:Bind(self.rows[i],nil,false) end
        self.rows[i]:Hide()
    end
    self.frame:SetHeight(y+26)
    self.footer:ClearAllPoints()
    self.footer:SetPoint('BOTTOMLEFT',self.frame,'BOTTOMLEFT',9,8)
    if count==0 then self.footer:SetText(self.isGroup and 'No group members' or (unknown>0 and 'Some unit information restricted' or 'No units shown | Check filters/nameplates'))
    elseif self.rowCapacity==0 then self.footer:SetText('Move window up to show unit rows')
    elseif count>self.rowCapacity then self.footer:SetText((self.offset+1)..'-'..(self.offset+shown)..' of '..count..(self.clickHealing and ' | Scroll | Click actions' or ' | Scroll | Display only'))
    else self.footer:SetText(unknown>0 and 'Visible only | Some units restricted' or (self.clickHealing and 'Hover for status and click actions' or 'Visible nameplates | Display only')) end
end
