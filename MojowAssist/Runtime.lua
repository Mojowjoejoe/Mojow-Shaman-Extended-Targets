-- Mojow Assist | 0.2.1-test | By Mojow
local addonName, NS = ...
local Addon = {version = '0.9.44-test', prefix = 'MOJOWASSIST', roster = {}}
NS.Addon = Addon

function Addon:IsSecret(value)
    return issecretvalue and issecretvalue(value) or false
end

function Addon:Say(text)
    print('|cff71d7cdMojow Assist:|r ' .. text)
end

function Addon:FullName(unit)
    local name, realm = UnitFullName(unit)
    if self:IsSecret(name) or self:IsSecret(realm) then return nil end
    if not name then return nil end
    if not realm or realm == '' then realm = GetNormalizedRealmName() end
    if not realm then return nil end
    local full = name .. '-' .. realm:gsub('%s', '')
    if NS.Model:ValidateName(full) then return full end
end

function Addon:Channel()
    if IsInGroup(LE_PARTY_CATEGORY_INSTANCE) then return 'INSTANCE_CHAT' end
    if IsInRaid() then return 'RAID' end
    if IsInGroup() then return 'PARTY' end
end

function Addon:Reconcile()
    if InCombatLockdown() then self.rosterDirty = true; return end
    self.roster, self.leader = {}, nil
    local units = {'player'}
    if IsInRaid() then
        for i = 1, GetNumGroupMembers() do units[#units + 1] = 'raid' .. i end
    elseif IsInGroup() then
        for i = 1, GetNumSubgroupMembers() do units[#units + 1] = 'party' .. i end
    end
    if IsInGroup() then
        for _, unit in ipairs(units) do
            local name = self:FullName(unit)
            if name then
                self.roster[name] = unit
                local leader = UnitIsGroupLeader(unit)
                if not self:IsSecret(leader) and leader then self.leader = name end
            end
        end
    end
    self.rosterDirty = false
    self:Apply()
end

function Addon:Apply()
    if not self.ready or InCombatLockdown() then self.pendingLayout = true; return end
    local master = self.db.master
    if self.db.mode == 'auto' then master = self.leader end
    self.effectiveMode = (self.db.mode == 'focus' or (self.db.mode == 'auto' and not IsInGroup())) and 'focus' or 'group'
    self.displayUnit = self.effectiveMode == 'focus' and 'focus' or (master and self.roster[master] or nil)
    self.action:Configure(self.displayUnit, self.effectiveMode)
    self.activeMaster = self.displayUnit and master or nil
    self.panel.frame:SetScale(self.db.scale)
    self.panel.frame:ClearAllPoints()
    self.panel.frame:SetPoint('CENTER', UIParent, 'CENTER', self.db.x, self.db.y)
    if self.db.visible then self.panel.frame:Show() else self.panel.frame:Hide() end
    self.pendingLayout = false
    self.panel:Refresh()
end

function Addon:SelectMaster(name, remote)
    if not NS.Model:ValidateName(name) or not self.roster[name] then
        self:Say('Choose a current group member from Settings.'); return false
    end
    self.pendingMode = nil
    if not remote then self.db.followLeader = false end
    if InCombatLockdown() then
        self.pendingMaster = name
        self:Say('Master change queued until combat ends.')
        self.panel:Refresh(); return true
    end
    self.db.mode = 'group'
    self.db.master = name
    self.pendingMaster = nil
    self:Apply()
    self:Say('Assist master: ' .. name)
    return true
end

function Addon:SetMode(mode)
    if mode ~= 'auto' and mode ~= 'focus' and mode ~= 'group' then return end
    self.pendingMaster = nil
    self.pendingMode = nil
    if mode == 'focus' then self.db.followLeader = false end
    if mode == self.db.mode then self.panel:Refresh(); return end
    if InCombatLockdown() then
        self.pendingMode = mode
        self:Say('Assist mode change queued until combat ends.')
        self.panel:Refresh(); return
    end
    self.db.mode = mode
    self:Reconcile()
end

function Addon:SetOption(key, value)
    if key ~= 'visible' and key ~= 'locked' and key ~= 'scale' and key ~= 'followLeader' then return end
    self.db[key] = value
    local normalized = NS.Model:Normalize(self.db)
    self.db[key] = normalized[key]
    if InCombatLockdown() then self.pendingLayout = true; self:Say('Settings queued until combat ends.') end
    self:Apply()
    self.panel:Refresh()
end

function Addon:Bind(key)
    if InCombatLockdown() then self:Say('Set the keybind after combat.'); return false end
    if type(key) ~= 'string' or key == '' then return false end
    local action = 'CLICK MojowAssistButton:LeftButton'
    local existing = GetBindingAction(key)
    local previous = {GetBindingKey(action)}
    local ok = SetBindingClick(key, 'MojowAssistButton', 'LeftButton')
    if not ok then self:Say('Could not set that key; previous binding kept.'); return false end
    for _, oldKey in ipairs(previous) do
        if oldKey ~= key then
            if not SetBinding(oldKey) then
                self:Say('New key set, but an older key could not be cleared. Check WoW Key Bindings.')
            end
        end
    end
    if existing and existing ~= '' and existing ~= action then
        self:Say(key .. ' reassigned from ' .. existing .. ' to Mojow Assist.')
    end
    if ok then SaveBindings(GetCurrentBindingSet()); self:Say('Assist bound to ' .. key .. '.'); self.panel:Refresh() end
    return not not ok
end

function Addon:Share()
    if self.db.mode ~= 'group' then self:Say('Select a group master before sharing. Focus is local to you.'); return false end
    if InCombatLockdown() then self:Say('Share the master after combat.'); return false end
    self:Reconcile()
    if self:FullName('player') ~= self.leader then self:Say('Only the current group leader can share. Friends can select the same master manually.'); return false end
    local message = NS.Model:Encode(self.db.master)
    local channel = self:Channel()
    if not message or not self.roster[self.db.master] or not channel then self:Say('Select a group member first.'); return false end
    if not self.syncAvailable then self:Say('Group sharing unavailable on this client. Select the master manually.'); return false end
    local now = GetTime()
    if self.lastShare and now - self.lastShare < 2 then self:Say('Wait two seconds before sharing again.'); return false end
    local ok, result = pcall(C_ChatInfo.SendAddonMessage, self.prefix, message, channel)
    local success = Enum and Enum.SendAddonMessageResult and Enum.SendAddonMessageResult.Success
    if not ok or not (result == true or (success ~= nil and result == success)) then
        self:Say('The client did not accept sharing. Friends can choose the master manually.'); return false
    end
    self.lastShare = now
    self:Say('Master sent. Friends must enable Follow group leader; players in combat need you to share again afterward.')
    return true
end

function Addon:Receive(prefix, message, channel, sender)
    if InCombatLockdown() or self.db.mode ~= 'group' or not self.db.followLeader then return end
    if self:IsSecret(prefix) or self:IsSecret(message) or self:IsSecret(channel) or self:IsSecret(sender) then return end
    if prefix ~= self.prefix or channel ~= self:Channel() or type(sender) ~= 'string' then return end
    self:Reconcile()
    if not sender:find('-', 1, true) then sender = sender .. '-' .. GetNormalizedRealmName() end
    local master = NS.Model:Decode(message, sender, self.leader, self.roster)
    if master and master ~= self.db.master then self:SelectMaster(master, true) end
end

function Addon:Debug()
    local version, build, date, interface = GetBuildInfo()
    self:Say('v' .. self.version .. ' | client ' .. tostring(version) .. ' | build ' .. tostring(build) .. ' | interface ' .. tostring(interface))
    self:Say('Master: ' .. (self.db.master or 'none') .. ' | active: ' .. (self.activeMaster or 'none') .. ' | sharing: ' .. tostring(self.syncAvailable) .. ' | combat: ' .. tostring(InCombatLockdown()))
    if not InCombatLockdown() then
        local unit = self.panel.assist:GetAttribute('unit')
        local kind = self.panel.assist:GetAttribute('type')
        if not self:IsSecret(unit) and not self:IsSecret(kind) then
            local exists = unit and UnitExists(unit)
            local existsText = self:IsSecret(exists) and 'restricted' or tostring(exists)
            self:Say('Action: ' .. tostring(kind) .. ' | unit: ' .. tostring(unit) .. ' | exists: ' .. existsText .. ' | click handler: ' .. tostring(self.panel.assist:GetScript('OnClick') ~= nil))
        end
    end
    self:Say('Experimental: actual secure clicks and battleground behavior need in-game verification.')
end

function Addon:Command(input)
    local command, rest = (input or ''):match('^(%S*)%s*(.-)%s*$')
    command = command:lower()
    if command == 'debug' then self:Debug()
    elseif command == 'help' then
        self:Say('/mja attacks: choose enemy click spells')
        self:Say('/mja heals: healing clicks | /mja enemies: Extended Targets | /mja groupwindow: Group Members')
        self:Say('/mja totems: totem controls | /mja visibility: nameplates and tracking')
        self:Say('/mja plates on: native preset | /mja plates restore: undo preset')
        self:Say('Minimap: left-click Settings; right-click Controls and unit filters.')
        self:Say('Hover rows for status, spell and range details.')
    elseif command == 'attacks' then NS.HealingSettings:Open(self.enemies,true)
    elseif command == 'heals' then NS.HealingSettings:Open(self.enemies)
    elseif command == 'plates' then
        if rest=='on' then self.nameplates:Apply()
        elseif rest=='restore' then self.nameplates:Restore()
        elseif rest=='debug' and self.worldBadges then self.worldBadges:Refresh(); self:Say(self.worldBadges:Status()); self:Say(self.worldBadges:Probe()); self:Say('Badge anchor: '..(self.worldBadges.anchorResult or 'not attempted')); for _,line in ipairs(self.worldBadges:GeometryProbe()) do self:Say(line) end
        elseif rest=='badges' and self.worldBadges then self.worldBadges:SetEnabled(not self.worldBadges.enabled); self:Say(self.worldBadges:Status())
        else self:Say(self.nameplates:Status()); self.visibility:Toggle() end
    elseif command == 'visibility' then self.visibility:Toggle()
    elseif command == 'marks' or command == 'markers' then
        if self.markerBar then self.markerBar:SetVisible(rest~='hide')
        else self:Say('Marker bar did not initialize.') end
    elseif command == 'totems' then
        if not self.totems then self:Say('Totem controls did not initialize.')
        elseif rest=='debug' then self.totems:Debug()
        elseif rest=='hide' then self.totems:SetVisible(false)
        else self.totems:SetVisible(true) end
    elseif command == 'shield' then
        if self.shield then self.shield:Debug() else self:Say('Shield helper did not initialize.') end
    elseif command == 'groupwindow' then
        if rest=='debug' then self.groupMembers:Debug(); return end
        if rest=='reset' then
            if InCombatLockdown() then self:Say('Reset Group Members outside combat.'); return end
            self.db.groupX,self.db.groupY,self.db.groupScale=50,100,1
            self.groupMembers.frame:ClearAllPoints()
            self.groupMembers.frame:SetPoint('TOP',UIParent,'CENTER',50,100)
            self.groupMembers.frame:SetScale(1)
        end
        self.groupMembers:SetVisible(rest~='hide')
    elseif command == 'enemies' then
        if rest == 'debug' then self.enemies:Debug()
        elseif rest == 'reset' then
            if InCombatLockdown() then self:Say('Reset nearby units outside combat.'); return end
            self.db.enemyX, self.db.enemyY, self.db.enemyScale = 300, 100, 1
            self.enemies.frame:ClearAllPoints()
            self.enemies.frame:SetPoint('TOP', UIParent, 'CENTER', 300, 100)
            self.enemies.frame:SetScale(1)
            self.enemies:SetVisible(true)
        elseif rest == 'hide' then self.enemies:SetVisible(false)
        else self.enemies:SetVisible(true) end
    elseif command == 'show' then self:SetOption('visible', true)
    elseif command == 'hide' then self:SetOption('visible', false)
    elseif command == 'share' then self:Share()
    elseif command == 'auto' then self:SetMode('auto')
    elseif command == 'focus' then self:SetMode('focus')
    elseif command == 'group' then self:SetMode('group')
    elseif command == 'master' then self:SelectMaster(rest)
    elseif command == 'reset' then
        self.db.x, self.db.y, self.db.scale, self.db.visible = 0, 160, 0.7, true
        self.db.minimapAngle = 225; self.minimap:Position()
        self:Apply()
    else self.panel:OpenSettings() end
end

function Addon:Initialize()
    if self.ready or InCombatLockdown() then return end
    self.db = NS.Model:Normalize(MojowAssistDB)
    MojowAssistDB = self.db
    NS.Appearance:Configure(self.db)
    self.panel = NS.Panel:Create(self)
    self.action = NS.AssistAction:Create(self, self.panel.assist)
    self.minimap = NS.MinimapButton:Create(self)
    self.visibility = NS.VisibilityOptions:Create(self)
    self.visibility:ApplyTrackingDefaults()
    self.nameplates = NS.NameplateProfile:Create(self,self.visibility)
    if NS.WorldNameplateBadges then self.worldBadges=NS.WorldNameplateBadges:Create(self) end
    if NS.MarkerBar then self.markerBar=NS.MarkerBar:Create(self) end
    self.enemies = NS.EnemyPanel:Create(self,'targets')
    self.groupMembers = NS.EnemyPanel:Create(self,'group')
    local shieldOK,shield=pcall(NS.ShieldHelper.Create,NS.ShieldHelper,self)
    if shieldOK then self.shield=shield else self:Say('Shield helper could not start: '..tostring(shield)) end
    local wolfOK,wolf=pcall(NS.GhostWolf.Create,NS.GhostWolf,self,self.shield and self.shield.button)
    if wolfOK then self.ghostWolf=wolf else self:Say('Ghost Wolf button could not start: '..tostring(wolf)) end
    local totemOK,totems=pcall(NS.TotemPanel.Create,NS.TotemPanel,self)
    if totemOK then self.totems=totems else self:Say('Totem controls could not start: '..tostring(totems)) end
    self.ready = true
    if C_ChatInfo and C_ChatInfo.RegisterAddonMessagePrefix and C_ChatInfo.SendAddonMessage then
        local ok, result = pcall(C_ChatInfo.RegisterAddonMessagePrefix, self.prefix)
        local success = Enum and Enum.RegisterAddonMessagePrefixResult and Enum.RegisterAddonMessagePrefixResult.Success
        self.syncAvailable = ok and (result == true or (success ~= nil and result == success))
    end
    SLASH_MOJOWASSIST1 = '/mja'
    SLASH_MOJOWASSIST2 = '/mojowassist'
    SlashCmdList.MOJOWASSIST = function(input) self:Command(input) end
    self:Reconcile()
    self:Say('v' .. self.version .. ' loaded. /mja opens Settings; /mja debug shows beta build details.')
end

function Addon:OnEvent(event, ...)
    if event == 'ADDON_LOADED' then
        local name = ...
        if name == addonName then self.loaded = true; self:Initialize() end
        return
    end
    if not self.ready then
        if self.loaded and (event == 'PLAYER_REGEN_ENABLED' or event == 'PLAYER_ENTERING_WORLD') then self:Initialize() end
        return
    end
    if event == 'PLAYER_REGEN_ENABLED' then
        self.panel:FinishDrag()
        self:Reconcile()
        if self.pendingMaster then
            local name = self.pendingMaster; self.pendingMaster = nil
            self:SelectMaster(name)
        end
        if self.pendingMode then
            local mode = self.pendingMode; self.pendingMode = nil
            self:SetMode(mode)
        end
        self:Apply()
    elseif event == 'GROUP_ROSTER_UPDATE' or event == 'PARTY_LEADER_CHANGED' or event == 'PLAYER_ENTERING_WORLD' then
        self:Reconcile(); self.panel:Refresh()
    elseif event == 'CHAT_MSG_ADDON' then self:Receive(...)
    elseif event == 'PLAYER_FOCUS_CHANGED' then self.panel:Refresh()
    elseif event == 'UPDATE_BINDINGS' or event == 'PLAYER_REGEN_DISABLED' then self.panel:Refresh() end
end

BINDING_HEADER_MOJOWASSIST = 'Mojow Assist'
_G['BINDING_NAME_CLICK MojowAssistButton:LeftButton'] = 'Assist selected master'
local events = CreateFrame('Frame')
Addon.events = events
for _, event in ipairs({'ADDON_LOADED', 'PLAYER_ENTERING_WORLD', 'GROUP_ROSTER_UPDATE', 'PARTY_LEADER_CHANGED', 'PLAYER_REGEN_ENABLED', 'PLAYER_REGEN_DISABLED', 'CHAT_MSG_ADDON', 'UPDATE_BINDINGS', 'PLAYER_FOCUS_CHANGED'}) do
    events:RegisterEvent(event)
end
events:SetScript('OnEvent', function(_, event, ...) Addon:OnEvent(event, ...) end)
