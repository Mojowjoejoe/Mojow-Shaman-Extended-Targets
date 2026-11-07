-- Mojow Assist | 0.2.1-test | By Mojow
local _, NS = ...
local Panel = {}
Panel.__index = Panel
NS.Panel = Panel

local function label(parent, text, x, y, width, font)
    local out = parent:CreateFontString(nil, 'OVERLAY', font or 'GameFontHighlightSmall')
    out:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    if width then out:SetWidth(width) end
    out:SetJustifyH('LEFT')
    out:SetText(text)
    return out
end

local function button(parent, text, x, y, width, action)
    local out = CreateFrame('Button', nil, parent, 'UIPanelButtonTemplate')
    out:SetSize(width, 24)
    out:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    out:SetText(text)
    out:SetScript('OnClick', action)
    return out
end

local function backdrop(frame, edgeSize)
    frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8', edgeFile='Interface\\Buttons\\WHITE8X8', edgeSize=edgeSize or 1})
    NS.Appearance:Background(frame,0.035, 0.055, 0.08, 0.95)
    frame:SetBackdropBorderColor(0.22, 0.64, 0.60, 1)
end

local function portrait(parent, x, y, size)
    local ring = parent:CreateTexture(nil, 'ARTWORK')
    ring:SetSize(size + 4, size + 4)
    ring:SetPoint('TOPLEFT', parent, 'TOPLEFT', x - 2, y + 2)
    ring:SetTexture('Interface\\Buttons\\WHITE8X8')
    ring:SetVertexColor(0.70, 0.56, 0.28)
    local mask = parent:CreateMaskTexture()
    mask:SetTexture('Interface\\CHARACTERFRAME\\TempPortraitAlphaMask', 'CLAMPTOBLACKADDITIVE', 'CLAMPTOBLACKADDITIVE')
    mask:SetAllPoints(ring)
    ring:AddMaskTexture(mask)
    local face = parent:CreateTexture(nil, 'OVERLAY')
    face:SetSize(size, size)
    face:SetPoint('TOPLEFT', parent, 'TOPLEFT', x, y)
    local faceMask = parent:CreateMaskTexture()
    faceMask:SetTexture('Interface\\CHARACTERFRAME\\TempPortraitAlphaMask', 'CLAMPTOBLACKADDITIVE', 'CLAMPTOBLACKADDITIVE')
    faceMask:SetAllPoints(face)
    face:AddMaskTexture(faceMask)
    return face
end

local function updatePortrait(texture, unit)
    texture:SetTexture('Interface\\Icons\\INV_Misc_QuestionMark')
    if unit then pcall(SetPortraitTexture, texture, unit) end
end

function Panel:Create(addon)
    local self = setmetatable({addon=addon, page=1}, Panel)
    local frame = CreateFrame('Frame', 'MojowAssistPanel', UIParent, 'BackdropTemplate')
    self.frame = frame
    frame:SetSize(420, 206)
    frame:SetMovable(true)
    frame:SetClampedToScreen(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag('LeftButton')
    backdrop(frame)
    frame:SetBackdropBorderColor(0.25, 0.28, 0.32, 1)
    frame:SetScript('OnDragStart', function()
        if not InCombatLockdown() and not addon.db.locked then self.dragging = true; frame:StartMoving() end
    end)
    frame:SetScript('OnDragStop', function() self:FinishDrag() end)
    label(frame, 'MOJOW ASSIST', 12, -10, 180, 'GameFontNormal')
    self.mode = label(frame, '', 204, -12, 204)
    self.autoModeButton = button(frame, 'Auto Leader', 12, -32, 194, function() addon:SetMode('auto') end)
    self.focusModeButton = button(frame, 'Focus', 214, -32, 194, function() addon:SetMode('focus') end)
    local masterCard = CreateFrame('Frame', nil, frame, 'BackdropTemplate')
    self.masterCard = masterCard
    masterCard:SetSize(194, 70)
    masterCard:SetPoint('TOPLEFT', frame, 'TOPLEFT', 12, -62)
    backdrop(masterCard, 2)
    self.masterAccent = masterCard:CreateTexture(nil, 'OVERLAY')
    self.masterAccent:SetTexture('Interface\\Buttons\\WHITE8X8')
    self.masterAccent:SetSize(4, 62)
    self.masterAccent:SetPoint('LEFT', masterCard, 'LEFT', 2, 0)
    self.masterPortrait = portrait(masterCard, 8, -11, 48)
    self.master = label(masterCard, 'Set a focus', 64, -12, 122, 'GameFontHighlight')
    self.master:SetHeight(30)
    label(masterCard, 'ASSIST LEADER', 64, -49, 122, 'GameFontNormalSmall')
    local assist = CreateFrame('Button', 'MojowAssistButton', frame, 'SecureActionButtonTemplate,BackdropTemplate')
    self.assist = assist
    assist:SetSize(194, 70)
    assist:SetPoint('TOPLEFT', frame, 'TOPLEFT', 214, -62)
    backdrop(assist, 2)
    local hover = assist:CreateTexture(nil, 'HIGHLIGHT')
    hover:SetAllPoints(assist)
    hover:SetTexture('Interface\\Buttons\\WHITE8X8')
    hover:SetVertexColor(1, 1, 1, 0.06)
    assist:SetHighlightTexture(hover)
    self.targetHover = hover
    self.targetAccent = assist:CreateTexture(nil, 'OVERLAY')
    self.targetAccent:SetTexture('Interface\\Buttons\\WHITE8X8')
    self.targetAccent:SetSize(4, 62)
    self.targetAccent:SetPoint('LEFT', assist, 'LEFT', 2, 0)
    self.targetPortrait = portrait(assist, 8, -11, 48)
    self.target = label(assist, 'No target', 64, -12, 122, 'GameFontHighlight')
    self.target:SetHeight(30)
    self.assistCaption = label(assist, 'CLICK TO ASSIST', 64, -49, 122, 'GameFontNormalSmall')
    self.castBar = CreateFrame('StatusBar', nil, assist)
    self.castBar:SetSize(122, 16)
    self.castBar:SetPoint('TOPLEFT', assist, 'TOPLEFT', 64, -47)
    self.castBar:EnableMouse(false)
    self.castBar:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    self.castBar:SetStatusBarColor(0.15, 0.45, 0.48, 0.9)
    self.castName = label(self.castBar, '', 2, -2, 84)
    self.castName:SetWordWrap(false)
    self.castTime = label(self.castBar, '', 87, -2, 34)
    self.castBar:Hide()
    assist:RegisterForClicks('AnyUp', 'AnyDown')
    assist:SetAttribute('unit', 'none')
    assist:SetAttribute('toggleForVehicle', false)
    local focus = CreateFrame('Button', nil, frame, 'SecureActionButtonTemplate,BackdropTemplate')
    self.setFocus = focus
    focus:SetSize(112, 24)
    focus:SetPoint('TOPLEFT', frame, 'TOPLEFT', 12, -140)
    backdrop(focus)
    focus:SetBackdropBorderColor(0.35, 0.38, 0.42, 1)
    label(focus, 'Set Focus', 24, -6, 84)
    focus:SetHighlightTexture('Interface\\QuestFrame\\UI-QuestTitleHighlight')
    focus:RegisterForClicks('AnyUp', 'AnyDown')
    focus:SetAttribute('type', 'focus')
    focus:SetAttribute('unit', 'target')
    focus:SetAttribute('useOnKeyDown', false)
    focus:SetScript('PostClick', function(_, _, down)
        if not down then addon:SetMode('focus') end
    end)
    local settingsButton = CreateFrame('Button', nil, frame, 'BackdropTemplate')
    settingsButton:SetSize(80, 24)
    settingsButton:SetPoint('TOPLEFT', frame, 'TOPLEFT', 328, -140)
    backdrop(settingsButton)
    settingsButton:SetBackdropBorderColor(0.35, 0.38, 0.42, 1)
    label(settingsButton, 'Settings', 13, -6, 64)
    settingsButton:SetHighlightTexture('Interface\\QuestFrame\\UI-QuestTitleHighlight')
    settingsButton:SetScript('OnClick', function() self:OpenSettings() end)
    self.key = label(frame, 'Key: not bound', 136, -147, 180)
    self.status = label(frame, '', 12, -169, 396)
    self.pending = label(frame, '', 12, -187, 396)
    self.pulseEdges = {}
    for _, edge in ipairs({'TOP', 'BOTTOM', 'LEFT', 'RIGHT'}) do
        local t = assist:CreateTexture(nil, 'OVERLAY')
        t:SetTexture('Interface\\Buttons\\WHITE8X8')
        t:SetVertexColor(1, 0.85, 0.4)
        if edge == 'TOP' or edge == 'BOTTOM' then
            t:SetSize(190, 2)
        else t:SetSize(2, 66) end
        t:SetPoint(edge, assist, edge, 0, 0)
        t:SetAlpha(0)
        self.pulseEdges[#self.pulseEdges + 1] = t
    end
    -- Read-only display refresh. No targeting action executes in this callback.
    local elapsed, castElapsed = 0, 0
    frame:SetScript('OnUpdate', function(_, delta)
        self:AnimatePulse()
        elapsed = elapsed + delta
        castElapsed = castElapsed + delta
        if castElapsed >= 0.05 then
            castElapsed = 0
            local unit = addon.displayUnit
            if addon.rosterDirty and addon.effectiveMode ~= 'focus' then unit = nil end
            self:RefreshCast(unit)
        end
        if elapsed >= 0.25 then elapsed = 0; self:RefreshTarget() end
    end)
    self:CreateSettings()
    return self
end

function Panel:FinishDrag()
    if not self.dragging or InCombatLockdown() then return end
    self.frame:StopMovingOrSizing()
    self.dragging = false
    local cx, cy = self.frame:GetCenter()
    local px, py = UIParent:GetCenter()
    local ratio = UIParent:GetEffectiveScale() / self.frame:GetEffectiveScale()
    if cx and px then self.addon.db.x, self.addon.db.y = cx - px * ratio, cy - py * ratio end
end

function Panel:ColorCard(card, unit, accent)
    local r, g, b = 0.42, 0.43, 0.46
    if unit then
        local ok, player = pcall(UnitIsPlayer, unit)
        if ok and not self.addon:IsSecret(player) and player then
            local classOK, _, class = pcall(UnitClass, unit)
            if classOK and not self.addon:IsSecret(class) and type(class) == 'string' then
                local color = RAID_CLASS_COLORS and RAID_CLASS_COLORS[class]
                if color then r, g, b = color.r, color.g, color.b end
            end
        end
    end
    if accent then accent:SetVertexColor(r, g, b, 1) end
    card:SetBackdropBorderColor(r, g, b, 1)
    NS.Appearance:Background(card,r * 0.28, g * 0.28, b * 0.28, 0.96)
end

-- Never inspect secret API results or turn missing data into a target match.
function Panel:ReadUnit(api, ...)
    if type(api) ~= 'function' then return nil, false end
    local ok, value = pcall(api, ...)
    if not ok or self.addon:IsSecret(value) then return nil, false end
    return value, true
end

function Panel:AnimatePulse()
    local age = self.pulseStart and (GetTime() - self.pulseStart)
    local alpha = 0
    if age and age >= 0 and age < 1.2 then
        alpha = 0.65 * math.sin(math.pi * age / 1.2)
    end
    for _, edge in ipairs(self.pulseEdges) do edge:SetAlpha(alpha) end
end

function Panel:RefreshIndicator(display)
    local a = self.addon
    local state = 'TARGET INFO UNAVAILABLE'
    local enemy, leaderGUID, targetGUID
    if a.rosterDirty and a.effectiveMode ~= 'focus' then display = nil end
    if not display then
        if not a.rosterDirty then state = a.effectiveMode == 'focus' and 'NO FOCUS' or 'NO ASSIST LEADER' end
    else
        local exists, readable = self:ReadUnit(UnitExists, display)
        if readable and not exists then
            state = a.effectiveMode == 'focus' and 'NO FOCUS' or 'TARGET INFO UNAVAILABLE'
        elseif readable and exists then
            local visible, visibilityKnown = self:ReadUnit(UnitIsVisible, display)
            if visibilityKnown and visible then
                enemy = display .. 'target'
                local hasTarget, known = self:ReadUnit(UnitExists, enemy)
                if known and not hasTarget then state = 'NO ENEMY TARGET'
                elseif known and hasTarget then
                    local attackable, attackKnown = self:ReadUnit(UnitCanAttack, 'player', enemy)
                    if attackKnown and not attackable then state = 'NO ENEMY TARGET'
                    elseif attackKnown and attackable then
                        local same, sameKnown = self:ReadUnit(UnitIsUnit, 'target', enemy)
                        if sameKnown then state = same and 'SAME TARGET' or 'ASSIST NEEDED' end
                        leaderGUID = self:ReadUnit(UnitGUID, display)
                        targetGUID = self:ReadUnit(UnitGUID, enemy)
                    end
                end
            end
        end
    end
    -- Only compare consecutive observable identities for the same leader.
    if type(leaderGUID) == 'string' and type(targetGUID) == 'string' then
        local now = GetTime()
        if self.lastLeaderGUID ~= leaderGUID then self.pulseStart = nil end
        if self.lastLeaderGUID == leaderGUID and self.lastTargetGUID and self.lastTargetGUID ~= targetGUID then
            if not self.lastPulse or now - self.lastPulse >= 3 then
                self.pulseStart, self.lastPulse = now, now
            end
        end
        self.lastLeaderGUID, self.lastTargetGUID = leaderGUID, targetGUID
    else
        self.lastLeaderGUID, self.lastTargetGUID, self.pulseStart = nil, nil, nil
    end
    if state ~= 'SAME TARGET' and state ~= 'ASSIST NEEDED' then self.pulseStart = nil end
    if self.pulseStart and GetTime() - self.pulseStart < 1.2 then
        state = state == 'SAME TARGET' and 'TARGET CHANGED | SAME TARGET' or 'TARGET CHANGED'
    end
    self.indicatorState = state
    local matched = state == 'SAME TARGET' or state == 'TARGET CHANGED | SAME TARGET'
    self.status:SetText((matched and '|TInterface\\RaidFrame\\ReadyCheck-Ready:12|t ' or '') .. state)
    self.status:SetTextColor(matched and 0.35 or 1, matched and 1 or 0.82, matched and 0.5 or 0.4)
    self:AnimatePulse()
end

function Panel:RefreshCast(display)
    self.castBar:Hide()
    self.assistCaption:Show()
    self.assistCaption:SetText('CLICK TO ASSIST')
    self.castName:SetText('')
    self.castTime:SetText('')
    if not display then return end
    local visible, known = self:ReadUnit(UnitIsVisible, display)
    if not known or not visible then return end
    local unit = display .. 'target'
    local exists, existsKnown = self:ReadUnit(UnitExists, unit)
    if not existsKnown or not exists then return end
    local function read(api)
        if type(api) ~= 'function' then return false end
        return pcall(api, unit)
    end
    local ok, name, _, _, startMS, endMS = read(UnitCastingInfo)
    local a = self.addon
    if not ok or a:IsSecret(name) then self.assistCaption:SetText('CAST UNAVAILABLE'); return end
    if not name then
        ok, name, _, _, startMS, endMS = read(UnitChannelInfo)
    end
    if not ok or a:IsSecret(name) or a:IsSecret(startMS) or a:IsSecret(endMS) then
        self.assistCaption:SetText('CAST UNAVAILABLE'); return
    end
    if not name then return end
    if type(name) ~= 'string' or type(startMS) ~= 'number' or type(endMS) ~= 'number'
        or startMS ~= startMS or endMS ~= endMS or endMS == math.huge or startMS == -math.huge or endMS <= startMS then
        self.assistCaption:SetText('CAST UNAVAILABLE'); return
    end
    local now = GetTime()
    local startTime, endTime = startMS / 1000, endMS / 1000
    if now >= endTime or now < startTime then return end
    local remaining = endTime - now
    self.castBar:SetMinMaxValues(0, endTime - startTime)
    self.castBar:SetValue(remaining)
    self.castName:SetText(name)
    self.castTime:SetText(string.format('%.1fs', remaining))
    self.assistCaption:Hide()
    self.castBar:Show()
end

function Panel:RefreshTarget()
    local a = self.addon
    self.pending:SetText((a.pendingMode or a.pendingMaster or a.pendingLayout) and 'Changes queued until combat ends' or ((a.db.mode == 'auto' and a.rosterDirty) and 'Leader update pending until combat ends' or ''))
    local display = a.displayUnit
    if a.rosterDirty and a.effectiveMode ~= 'focus' then display = nil end
    self:RefreshCast(display)
    self:RefreshIndicator(display)
    self:ColorCard(self.masterCard, display, self.masterAccent)
    self:ColorCard(self.assist, display and (display .. 'target'), self.targetAccent)
    if a.rosterDirty and a.effectiveMode ~= 'focus' then
        updatePortrait(self.masterPortrait); updatePortrait(self.targetPortrait)
        self.target:SetText('Roster changed'); return
    end
    updatePortrait(self.masterPortrait, a.displayUnit)
    updatePortrait(self.targetPortrait, a.displayUnit and (a.displayUnit .. 'target'))
    if a.effectiveMode == 'focus' then
        local ok, name = pcall(UnitName, 'focus')
        if ok and a:IsSecret(name) then self.master:SetText(name)
        elseif ok and name then self.master:SetText(name)
        else self.master:SetText('Set a focus') end
    end
    if not a.displayUnit then self.target:SetText('No master'); return end
    local ok, name = pcall(UnitName, a.displayUnit .. 'target')
    if not ok then self.target:SetText('Unavailable'); return end
    -- Secret text may go straight to a font string; never inspect or concatenate it.
    if a:IsSecret(name) then self.target:SetText(name)
    elseif name then self.target:SetText(name)
    else self.target:SetText('No target') end
end

function Panel:Refresh()
    local a = self.addon
    self.master:SetText('Master: ' .. (a.activeMaster or a.db.master or 'not selected'))
    local caption = a.db.mode == 'auto' and (a.effectiveMode == 'focus' and 'AUTO: SOLO FOCUS' or 'AUTO: GROUP LEADER') or (a.db.mode == 'focus' and 'FOCUS' or 'MANUAL GROUP')
    self.mode:SetText(caption)
    self.autoModeButton:SetText(a.db.mode == 'auto' and '|cff55ff88[Auto Leader]|r' or 'Auto Leader')
    self.focusModeButton:SetText(a.db.mode == 'focus' and '|cff55ff88[Focus]|r' or 'Focus')
    local key = GetBindingKey('CLICK MojowAssistButton:LeftButton')
    self.key:SetText('Key: ' .. (key or 'not bound'))
    self:RefreshTarget()
    if self.settings and self.settings:IsShown() then self:RefreshSettings() end
end

function Panel:OpenSettings()
    self.settings:Show()
    if not InCombatLockdown() then self.addon:Reconcile() end
    self:RefreshSettings()
end

function Panel:CreateSettings()
    local a = self.addon
    local settings = CreateFrame('Frame', 'MojowAssistSettings', UIParent, 'BackdropTemplate')
    self.settings = settings
    settings:SetSize(410, 610)
    settings:SetPoint('CENTER', UIParent, 'CENTER', 0, 0)
    settings:SetFrameStrata('DIALOG')
    settings:SetMovable(true)
    settings:SetClampedToScreen(true)
    settings:EnableMouse(true)
    settings:RegisterForDrag('LeftButton')
    settings:SetScript('OnDragStart', function() settings:StartMoving() end)
    settings:SetScript('OnDragStop', function() settings:StopMovingOrSizing() end)
    backdrop(settings)
    label(settings, 'Mojow Assist ' .. a.version, 16, -16, 330, 'GameFontNormalLarge')
    button(settings, 'X', 368, -10, 26, function() settings:Hide() end)
    label(settings, 'Choose a master (your party / current raid)', 16, -48, 376)
    self.rows = {}
    for i = 1, 6 do
        local row = button(settings, '', 16, -68 - (i-1)*27, 378, function() end)
        row:SetScript('OnClick', function() if row.member then a:SelectMaster(row.member) end end)
        self.rows[i] = row
    end
    self.pageLabel = label(settings, '', 100, -239, 205)
    button(settings, '<', 16, -230, 60, function() self.page=math.max(1,self.page-1); self:RefreshSettings() end)
    button(settings, '>', 334, -230, 60, function() self.page=self.page+1; self:RefreshSettings() end)
    self.follow = CreateFrame('CheckButton', nil, settings, 'UICheckButtonTemplate')
    self.follow:SetSize(24,24); self.follow:SetPoint('TOPLEFT',settings,'TOPLEFT',16,-264)
    label(settings, 'Follow group leader\'s shared selection', 44, -270, 344)
    self.follow:SetScript('OnClick', function(f) a:SetOption('followLeader', not not f:GetChecked()) end)
    button(settings, 'Share master', 16, -296, 180, function() a:Share() end)
    self.bind = button(settings, 'Set assist key', 210, -296, 184, function()
        if InCombatLockdown() then a:Say('Set the keybind after combat.'); return end
        a:Say('Press a key to assign to Mojow Assist. Its current action will be replaced; Esc cancels.')
        self.capture = true; self.bind:SetText('Press key (Esc cancels)'); settings:EnableKeyboard(true)
    end)
    settings:EnableKeyboard(false)
    settings:SetScript('OnKeyDown', function(_, key)
        if not self.capture then return end
        if key=='LSHIFT' or key=='RSHIFT' or key=='LCTRL' or key=='RCTRL' or key=='LALT' or key=='RALT' then return end
        self.capture=false; settings:EnableKeyboard(false); self.bind:SetText('Set assist key')
        if key=='ESCAPE' then return end
        local binding = (IsControlKeyDown() and 'CTRL-' or '') .. (IsAltKeyDown() and 'ALT-' or '') .. (IsShiftKeyDown() and 'SHIFT-' or '') .. key
        a:Bind(binding)
    end)
    settings:SetScript('OnHide', function() self.capture=false; settings:EnableKeyboard(false); self.bind:SetText('Set assist key') end)
    self.lock = button(settings, '', 16, -332, 180, function() a:SetOption('locked', not a.db.locked) end)
    self.visible = button(settings, '', 210, -332, 184, function() a:SetOption('visible', not a.db.visible) end)
    button(settings, 'Smaller', 16, -368, 105, function() a:SetOption('scale',a.db.scale-0.1) end)
    self.scale = label(settings, '', 143, -375, 130)
    button(settings, 'Larger', 289, -368, 105, function() a:SetOption('scale',a.db.scale+0.1) end)
    button(settings, 'Use focus mode', 16, -404, 180, function() a:SetMode('focus') end)
    button(settings, 'Use group mode', 210, -404, 184, function() a:SetMode('group') end)
    self.enemyToggle = button(settings, 'Nearby units', 16, -438, 180, function()
        a.enemies:SetVisible(not a.db.enemyVisible)
        self:RefreshSettings()
    end)
    button(settings, 'Reset nearby window', 210, -438, 184, function() a:Command('enemies reset') end)
    self.transparencyLabel=label(settings,'',16,-480,378)
    local slider=CreateFrame('Slider','MojowWindowTransparencySlider',settings,'OptionsSliderTemplate')
    self.transparency=slider
    slider:SetSize(350,18); slider:SetPoint('TOPLEFT',settings,'TOPLEFT',26,-506)
    slider:SetMinMaxValues(0,100); slider:SetValueStep(1); slider:SetObeyStepOnDrag(true)
    if slider.Low then slider.Low:SetText('Solid') end
    if slider.High then slider.High:SetText('Clear') end
    slider:SetScript('OnValueChanged',function(_,value)
        NS.Appearance:SetTransparency(value)
        self.transparencyLabel:SetText('All window backgrounds: '..NS.Appearance.transparency..'% transparent')
    end)
    slider:SetValue(a.db.windowTransparency or 0)
    self.transparencyLabel:SetText('All window backgrounds: '..(a.db.windowTransparency or 0)..'% transparent')
    label(settings, 'Master/layout changes wait until combat ends.\nRight-click minimap icon: nearby unit sections.\n/mja enemies: show roster. /mja enemies hide: hide.', 16, -552, 378)
    table.insert(UISpecialFrames, 'MojowAssistSettings')
    settings:Hide()
end

function Panel:RefreshSettings()
    local a = self.addon
    self.transparency:SetValue(a.db.windowTransparency or 0)
    local names = {}
    for name in pairs(a.roster) do names[#names+1] = name end
    table.sort(names)
    local pages = math.max(1, math.ceil(#names/6))
    self.page = math.max(1, math.min(pages, self.page))
    for i, row in ipairs(self.rows) do
        local name = names[(self.page-1)*6+i]
        row.member = name
        if name then row:SetText((name == a.db.master and '* ' or '') .. name); row:Show()
        else row:Hide() end
    end
    self.pageLabel:SetText(#names==0 and 'Join a party or raid first' or ('Page ' .. self.page .. ' / ' .. pages))
    self.follow:SetChecked(a.db.followLeader)
    self.lock:SetText(a.db.locked and 'Unlock panel' or 'Lock panel')
    self.visible:SetText(a.db.visible and 'Hide panel' or 'Show panel')
    self.scale:SetText(string.format('Scale: %.0f%%', a.db.scale*100))
    self.enemyToggle:SetText(a.db.enemyVisible and 'Hide nearby units' or 'Show nearby units')
end
