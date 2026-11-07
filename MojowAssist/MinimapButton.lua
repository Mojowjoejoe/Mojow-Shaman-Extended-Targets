-- Mojow Assist | 0.2.1-test | By Mojow
local _, NS = ...
local MinimapButton = {}
MinimapButton.__index = MinimapButton
NS.MinimapButton = MinimapButton

function MinimapButton:Create(addon)
    local self = setmetatable({addon=addon}, MinimapButton)
    if not Minimap then return self end
    local button = CreateFrame('Button', 'MojowAssistMinimapButton', Minimap)
    self.button = button
    button:SetSize(31, 31)
    button:SetFrameStrata('MEDIUM')
    button:SetHighlightTexture(136477) -- UI-Minimap-ZoomButton-Highlight
    local background = button:CreateTexture(nil, 'BACKGROUND')
    background:SetSize(24, 24)
    background:SetTexture(136467) -- UI-Minimap-Background
    background:SetPoint('CENTER', button, 'CENTER')
    local border = button:CreateTexture(nil, 'OVERLAY')
    border:SetSize(50, 50)
    border:SetTexture(136430) -- MiniMap-TrackingBorder
    border:SetPoint('TOPLEFT', button, 'TOPLEFT')
    local text = button:CreateFontString(nil, 'OVERLAY', 'GameFontNormalLarge')
    text:SetPoint('CENTER', button, 'CENTER', 0, 0)
    text:SetText('M')
    text:SetTextColor(0.45, 0.95, 0.85, 1)
    button:RegisterForClicks('LeftButtonUp','RightButtonUp')
    button:RegisterForDrag('LeftButton')
    button:SetScript('OnClick', function(_,mouseButton)
        if not self.dragging and (not self.suppressUntil or GetTime() > self.suppressUntil) then
            if mouseButton=='RightButton' then self:ToggleMenu() else addon.panel:OpenSettings() end
        end
    end)
    button:SetScript('OnDragStart', function()
        self.dragging = true
        if GameTooltip then GameTooltip:Hide() end
        button:SetScript('OnUpdate', function() self:Drag() end)
    end)
    button:SetScript('OnDragStop', function()
        self:Drag()
        self.dragging = false
        self.suppressUntil = GetTime() + 0.15
        button:SetScript('OnUpdate', nil)
    end)
    button:SetScript('OnHide', function() self.dragging=false; button:SetScript('OnUpdate',nil) end)
    button:SetScript('OnEnter', function()
        if GameTooltip and not self.dragging then
            GameTooltip:SetOwner(button, 'ANCHOR_LEFT')
            GameTooltip:AddLine('Mojow Assist')
            GameTooltip:AddLine('Click: Settings', 1, 1, 1)
            GameTooltip:AddLine('Right-click: Controls and unit filters', 1, 1, 1)
            GameTooltip:AddLine('Drag: move around minimap', 1, 1, 1)
            GameTooltip:Show()
        end
    end)
    button:SetScript('OnLeave', function() if GameTooltip then GameTooltip:Hide() end end)
    self:Position()
    return self
end

function MinimapButton:ToggleMenu()
    if not self.menu then
        local menu=CreateFrame('Frame',nil,UIParent,'BackdropTemplate')
        self.menu=menu
        menu:SetSize(220,356)
        menu:EnableMouse(true)
        menu:SetFrameStrata('DIALOG')
        menu:SetClampedToScreen(true)
        menu:SetPoint('TOPRIGHT',self.button,'BOTTOMLEFT',0,-4)
        menu:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
        NS.Appearance:Background(menu,0.025,0.035,0.05,0.98)
        menu:SetBackdropBorderColor(0.45,0.95,0.85,1)
        local title=menu:CreateFontString(nil,'OVERLAY','GameFontNormal')
        title:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-10)
        title:SetText('Mojow controls')
        self.menuOptions={}
        for i,section in ipairs(NS.EnemySections) do
            local option=section.option
            local check=CreateFrame('CheckButton',nil,menu,'UICheckButtonTemplate')
            check:SetSize(24,24)
            check:SetPoint('TOPLEFT',menu,'TOPLEFT',8,-28-(i-1)*26)
            local label=check:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
            label:SetPoint('LEFT',check,'RIGHT',3,0)
            label:SetText(section.key=='group' and 'Group window' or section.label)
            check:SetScript('OnClick',function()
                if option=='enemyShowGroup' and self.addon.groupMembers then
                    self.addon.groupMembers:SetVisible(not self.addon.db[option])
                else
                    self.addon.db[option]=not self.addon.db[option]
                    self.addon.enemies.offset=0
                    self.addon.enemies:Refresh()
                end
                check:SetChecked(self.addon.db[option])
            end)
            self.menuOptions[i]=check
        end
        local visibility=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        visibility:SetSize(200,24)
        visibility:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-136)
        visibility:SetText('Nameplates / tracking')
        visibility:SetScript('OnClick',function() menu:Hide(); self.addon.visibility:Toggle() end)
        local totems=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        totems:SetSize(200,24)
        totems:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-166)
        self.totemMenuButton=totems
        totems:SetScript('OnClick',function()
            menu:Hide()
            if self.addon.totems then self.addon.totems:SetVisible(not self.addon.db.totemVisible)
            else self.addon:Say('Totem controls did not initialize.') end
        end)
        local healing=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        healing:SetSize(200,24); healing:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-196)
        healing:SetText('Healing click settings')
        healing:SetScript('OnClick',function() menu:Hide(); NS.HealingSettings:Open(self.addon.enemies) end)
        local attacks=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        attacks:SetSize(200,24); attacks:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-226)
        attacks:SetText('Enemy click settings')
        attacks:SetScript('OnClick',function() menu:Hide(); NS.HealingSettings:Open(self.addon.enemies,true) end)
        self.poisonCheck=CreateFrame('CheckButton',nil,menu,'UICheckButtonTemplate')
        self.poisonCheck:SetSize(24,24)
        self.poisonCheck:SetPoint('TOPLEFT',menu,'TOPLEFT',8,-256)
        local poisonLabel=self.poisonCheck:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
        poisonLabel:SetPoint('LEFT',self.poisonCheck,'RIGHT',3,0)
        poisonLabel:SetText('Group poison (trial)')
        self.poisonCheck:SetScript('OnClick',function()
            if InCombatLockdown() then self.addon:Say('Change Group poison icons outside combat.')
            else
                self.addon.db.groupNativePoison=not self.addon.db.groupNativePoison
                if self.addon.groupMembers then self.addon.groupMembers:Refresh() end
            end
            self.poisonCheck:SetChecked(self.addon.db.groupNativePoison)
        end)
        self.poisonCheck:SetScript('OnEnter',function()
            if GameTooltip then
                GameTooltip:SetOwner(self.poisonCheck,'ANCHOR_RIGHT')
                GameTooltip:AddLine('Removable poison in Group')
                GameTooltip:AddLine('Green-bordered icons use the game aura display, including combat when supported.',1,1,1,true)
                GameTooltip:AddLine('Requires a learned poison cure.',1,1,1,true)
                GameTooltip:AddLine('Trial: live validation pending. Does not change click spells.',0.7,0.7,0.7,true)
                GameTooltip:Show()
            end
        end)
        self.poisonCheck:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
        local marks=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        self.markerMenuButton=marks
        marks:SetSize(200,24); marks:SetPoint('TOPLEFT',menu,'TOPLEFT',10,-286)
        marks:SetScript('OnClick',function()
            menu:Hide()
            if self.addon.markerBar then self.addon.markerBar:SetVisible(not self.addon.db.markerBarVisible) end
        end)
        local close=CreateFrame('Button',nil,menu,'UIPanelButtonTemplate')
        close:SetSize(65,22)
        close:SetPoint('BOTTOMRIGHT',menu,'BOTTOMRIGHT',-8,8)
        close:SetText('Close')
        close:SetScript('OnClick',function() menu:Hide() end)
        menu:Hide()
    end
    if self.menu:IsShown() then self.menu:Hide(); return end
    for i,section in ipairs(NS.EnemySections) do self.menuOptions[i]:SetChecked(self.addon.db[section.option]) end
    self.poisonCheck:SetChecked(self.addon.db.groupNativePoison)
    self.markerMenuButton:SetText(self.addon.db.markerBarVisible and 'Hide marker bar' or 'Show marker bar')
    self.totemMenuButton:SetText(self.addon.db.totemVisible and 'Hide totems' or 'Show totems')
    self.menu:Show()
end

function MinimapButton:Position()
    if not self.button then return end
    local angle = math.rad(self.addon.db.minimapAngle)
    local x = math.cos(angle) * (Minimap:GetWidth()/2 + 10)
    local y = math.sin(angle) * (Minimap:GetHeight()/2 + 10)
    self.button:ClearAllPoints()
    self.button:SetPoint('CENTER', Minimap, 'CENTER', x, y)
end

function MinimapButton:Drag()
    local x, y = GetCursorPosition()
    local cx, cy = Minimap:GetCenter()
    if not cx or not cy then return end
    local scale = Minimap:GetEffectiveScale()
    local dx, dy = x/scale - cx, y/scale - cy
    if dx == 0 and dy == 0 then return end
    self.addon.db.minimapAngle = math.deg(math.atan2(dy, dx)) % 360
    self:Position()
end
