local _,NS=...
local Options={}
Options.__index=Options
NS.VisibilityOptions=Options
local resources={{2383,'Find Herbs'},{2580,'Find Minerals'},{2481,'Find Treasure'}}

function Options:Read(name)
    local get=C_CVar and C_CVar.GetCVar or GetCVar
    if not get then return nil end
    local ok,value=pcall(get,name)
    if ok and not (issecretvalue and issecretvalue(value)) and type(value)=='string' and value~='' then return value end
end

function Options:Set(name,value)
    if InCombatLockdown() then self.addon:Say('Change visibility settings outside combat.'); return false end
    local set=C_CVar and C_CVar.SetCVar or SetCVar
    if not set or not self:Read(name) then self.addon:Say('This client does not expose '..name..'.'); return false end
    local ok=pcall(set,name,tostring(value))
    local applied=ok and self:Read(name)==tostring(value)
    if not applied then self.addon:Say('The client did not accept '..name..' = '..tostring(value)..'.') end
    self:Refresh()
    return applied
end

function Options:Tracking(spellID)
    if not C_Minimap or not C_Minimap.GetNumTrackingTypes or not C_Minimap.GetTrackingInfo then return nil end
    local ok,count=pcall(C_Minimap.GetNumTrackingTypes)
    if not ok or type(count)~='number' then return nil end
    local localized
    if C_Spell and C_Spell.GetSpellInfo then
        local found,info=pcall(C_Spell.GetSpellInfo,spellID)
        if found and info then localized=info.name end
    end
    for index=1,math.min(count,200) do
        local found,entry=pcall(C_Minimap.GetTrackingInfo,index)
        if found and type(entry)=='table' and (entry.spellID==spellID or (localized and entry.name==localized)) then
            return entry,index
        end
    end
end

function Options:ToggleTracking(spellID)
    if InCombatLockdown() then self.addon:Say('Change resource tracking outside combat.'); return false end
    local entry,index=self:Tracking(spellID)
    if not entry or not C_Minimap.SetTracking then self.addon:Say('That tracking ability is not available to this character.'); return false end
    local desired=not entry.active
    -- A tracking event may fire inside SetTracking; explicit clicks win over defaults.
    if spellID==2580 then self.mineralsDefaultAttempted=true end
    local ok=pcall(C_Minimap.SetTracking,index,desired)
    local updated=self:Tracking(spellID)
    local applied=ok and updated and updated.active==desired
    if not applied then self.addon:Say('Tracking did not change. Check the game minimap tracking menu.'); end
    if spellID==2580 then
        self.mineralsDefaultApplied=not not applied
        if applied and self.addon.db then self.addon.db.autoFindMinerals=desired end
    end
    self:Refresh()
    return not not applied
end

local function label(parent,text,y)
    local value=parent:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    value:SetPoint('TOPLEFT',parent,'TOPLEFT',12,y)
    value:SetWidth(326)
    value:SetJustifyH('LEFT')
    value:SetText(text)
    return value
end

function Options:Create(addon)
    local self=setmetatable({addon=addon},Options)
    self.trackingEvents=CreateFrame('Frame')
    for _,event in ipairs({'PLAYER_ENTERING_WORLD','SPELLS_CHANGED','MINIMAP_UPDATE_TRACKING','PLAYER_REGEN_ENABLED'}) do
        self.trackingEvents:RegisterEvent(event)
    end
    self.trackingEvents:SetScript('OnEvent',function() self:ApplyTrackingDefaults() end)
    return self
end

function Options:ApplyTrackingDefaults()
    if self.mineralsDefaultAttempted then return self.mineralsDefaultApplied or false end
    if not self.addon.db or self.addon.db.autoFindMinerals==false then
        self.mineralsDefaultAttempted=true; self.mineralsDefaultApplied=true; return true
    end
    if InCombatLockdown() then return false end
    local entry=self:Tracking(2580)
    if not entry then return false end -- Wait for the learned tracking list to load.
    self.mineralsDefaultAttempted=true -- Set before the write can emit a tracking event.
    if entry.active then self.mineralsDefaultApplied=true; return true end
    self.mineralsDefaultApplied=self:ToggleTracking(2580)
    return self.mineralsDefaultApplied
end

function Options:Toggle()
    if self.frame and self.frame:IsShown() then self.frame:Hide(); return end
    if not self.frame then
        local frame=CreateFrame('Frame',nil,UIParent,'BackdropTemplate')
        self.frame=frame
        frame:SetSize(350,402)
        frame:SetPoint('CENTER',UIParent,'CENTER',0,0)
        frame:SetFrameStrata('DIALOG')
        frame:SetClampedToScreen(true)
        frame:EnableMouse(true)
        frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
        NS.Appearance:Background(frame,0.025,0.035,0.05,0.98)
        frame:SetBackdropBorderColor(0.45,0.95,0.85,1)
        label(frame,'Mojow | Nameplates and tracking',-12)
        self.checks={}
        local settings={{'nameplateShowEnemies','Enemy nameplates'},{'nameplateShowFriendlyPlayers','Friendly player nameplates'}}
        for i,setting in ipairs(settings) do
            local cvar=setting[1]
            local check=CreateFrame('CheckButton',nil,frame,'UICheckButtonTemplate')
            check:SetSize(24,24)
            check:SetPoint('TOPLEFT',frame,'TOPLEFT',10,-40-(i-1)*26)
            local text=check:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
            text:SetPoint('LEFT',check,'RIGHT',4,0); text:SetText(setting[2])
            check:SetScript('OnClick',function()
                self:Set(cvar,self:Read(cvar)=='1' and '0' or '1')
                self:Refresh()
            end)
            self.checks[cvar]=check
        end
        label(frame,'Resource tracking (learned abilities)',-106)
        self.resourceChecks={}
        for i,resource in ipairs(resources) do
            local id=resource[1]
            local check=CreateFrame('CheckButton',nil,frame,'UICheckButtonTemplate')
            check:SetSize(24,24)
            check:SetPoint('TOPLEFT',frame,'TOPLEFT',10,-128-(i-1)*26)
            check.label=check:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
            check.label:SetPoint('LEFT',check,'RIGHT',4,0)
            check:SetScript('OnClick',function() self:ToggleTracking(id); self:Refresh() end)
            self.resourceChecks[i]=check
        end
        label(frame,'Find Minerals defaults on; uncheck here to keep it off.',-208)
        label(frame,'Resource tracking adds minimap dots.\nQuestie handles quest map markers.',-222)
        local apply=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        apply:SetSize(206,24); apply:SetPoint('TOPLEFT',frame,'TOPLEFT',12,-274)
        apply:SetText('Apply DogHouse plates + badges')
        apply:SetScript('OnClick',function() if self.addon.nameplates then self.addon.nameplates:Apply() end end)
        local restore=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        restore:SetSize(110,24); restore:SetPoint('LEFT',apply,'RIGHT',8,0)
        restore:SetText('Restore previous')
        restore:SetScript('OnClick',function() if self.addon.nameplates then self.addon.nameplates:Restore() end end)
        self.plateStatus=label(frame,'Native horizontal bars, class colors and visibility.',-308)
        label(frame,'Changes apply outside combat. Restore keeps later manual edits.',-330)
        local close=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        close:SetSize(70,24); close:SetPoint('BOTTOMRIGHT',frame,'BOTTOMRIGHT',-12,10)
        close:SetText('Close'); close:SetScript('OnClick',function() frame:Hide() end)
        frame:RegisterEvent('MINIMAP_UPDATE_TRACKING')
        frame:RegisterEvent('CVAR_UPDATE')
        frame:SetScript('OnEvent',function() if frame:IsShown() then self:Refresh() end end)
    end
    self:Refresh()
    self.frame:Show()
end

function Options:Refresh()
    if not self.frame then return end
    if self.plateStatus and self.addon.nameplates then self.plateStatus:SetText(self.addon.nameplates:Status()) end
    for cvar,check in pairs(self.checks) do
        local current=self:Read(cvar)
        check:SetChecked(current=='1')
        if current then check:Enable() else check:Disable() end
    end
    for i,resource in ipairs(resources) do
        local entry=self:Tracking(resource[1])
        local check=self.resourceChecks[i]
        check:SetChecked(entry and entry.active or false)
        check.label:SetText(entry and entry.name or resource[2]..' (not available)')
        if entry then check:Enable() else check:Disable() end
    end
end
