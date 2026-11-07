-- Mojow Assist | 0.2.1-test | By Mojow
local _, NS = ...
local AssistAction = {}
AssistAction.__index = AssistAction
NS.AssistAction = AssistAction

function AssistAction:Create(addon, button)
    local self = setmetatable({addon=addon, button=button}, AssistAction)
    -- Always visible to the native roster updater, independent of the user panel.
    -- Transparent, non-interactive one-pixel bookkeeping frame.
    local header = CreateFrame('Frame', 'MojowAssistRosterHeader', UIParent, 'SecureGroupHeaderTemplate')
    self.header = header
    header:SetPoint('TOPLEFT', UIParent, 'TOPLEFT', 0, 0)
    header:SetSize(1, 1)
    header:SetAlpha(0)
    header:EnableMouse(false)
    header:SetAttribute('template', 'SecureHandlerAttributeTemplate')
    header:SetAttribute('templateType', 'Frame')
    header:SetAttribute('initialConfigFunction', 'self:SetWidth(1); self:SetHeight(1)')
    header:SetAttribute('showParty', true)
    header:SetAttribute('showRaid', true)
    header:SetAttribute('showPlayer', true)
    header:SetAttribute('showSolo', false)
    header:SetAttribute('point', 'TOP')
    header:SetAttribute('nameList', '__MojowAssistNoSelection__')
    header:Show()
    -- Native configureChildren creates child1 even when the matching list is empty.
    local child = header:GetAttribute('child1')
    self.child = child
    if not child then
        addon:Say('Secure group tracker unavailable. Assist remains disabled; send /mja debug output.')
        return self
    end
    SecureHandlerSetFrameRef(child, 'assist', button)
    child:SetAttribute('_onattributechanged', [[
        if name == 'unit' and self:GetAttribute('groupEnabled') then
            local button = self:GetFrameRef('assist')
            if button then
                button:SetAttribute('type', nil)
                button:SetAttribute('unit', value or 'none')
                if value then button:SetAttribute('type', 'assist') end
            end
        end
    ]])
    return self
end

function AssistAction:Configure(unit, mode)
    if InCombatLockdown() then return end
    self.button:SetAttribute('type', nil)
    self.button:SetAttribute('unit', 'none')
    if self.child then self.child:SetAttribute('groupEnabled', false) end
    if mode == 'focus' then
        self.header:SetAttribute('nameList', '__MojowAssistNoSelection__')
        self.button:SetAttribute('unit', 'focus')
        self.button:SetAttribute('type', 'assist')
        return
    end
    if not self.child then return end
    self.child:SetAttribute('groupEnabled', true)
    local rawName
    if unit then
        -- Match exactly how Blizzard GetGroupRosterInfo constructs the filter key.
        local raidIndex = unit:match('^raid(%d+)$')
        if raidIndex then rawName = GetRaidRosterInfo(tonumber(raidIndex))
        else
            local name, server = UnitName(unit)
            if not self.addon:IsSecret(name) and not self.addon:IsSecret(server) and name then
                rawName = name
                if server and server ~= '' then rawName = name .. '-' .. server end
            end
        end
    end
    if self.addon:IsSecret(rawName) then rawName = nil end
    self.header:SetAttribute('nameList', rawName or '__MojowAssistNoSelection__')
    -- If the native unit did not change, its attribute handler may not fire again.
    local resolved = self.child:GetAttribute('unit')
    if self.addon:IsSecret(resolved) then return end
    if resolved then
        self.button:SetAttribute('unit', resolved)
        self.button:SetAttribute('type', 'assist')
    end
end
