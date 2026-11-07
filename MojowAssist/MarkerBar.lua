local _,NS=...
local Panel={}
NS.MarkerBar=Panel
function Panel:Refresh()
    if not self.frame then return end
    if self.markers then self.markers:Refresh() end
    if InCombatLockdown() then return end
    if self.addon.db.markerBarVisible then self.frame:Show() else self.frame:Hide() end
end
function Panel:SetVisible(visible)
    if InCombatLockdown() then self.addon:Say('Show or hide the marker bar outside combat.'); return false end
    self.addon.db.markerBarVisible=not not visible
    self:Refresh(); return true
end
function Panel:FinishDrag()
    if InCombatLockdown() or not (self.moving or self.dragPending) then return end
    self.frame:StopMovingOrSizing(); self.moving=false; self.dragPending=false
    local x,y=self.frame:GetCenter(); local cx,cy=UIParent:GetCenter()
    if type(x)=='number' and type(y)=='number' and type(cx)=='number' and type(cy)=='number' then
        self.addon.db.markerBarX,self.addon.db.markerBarY=x-cx,y-cy
        self.frame:ClearAllPoints(); self.frame:SetPoint('CENTER',UIParent,'CENTER',x-cx,y-cy)
    end
end
function Panel:Create(addon)
    local self=setmetatable({addon=addon},{__index=Panel})
    local frame=CreateFrame('Frame','MojowAssistMarkerBar',UIParent,'BackdropTemplate')
    self.frame=frame
    frame:SetSize(242,32); frame:SetPoint('CENTER',UIParent,'CENTER',addon.db.markerBarX,addon.db.markerBarY)
    frame:SetMovable(true); frame:SetClampedToScreen(true)
    frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    NS.Appearance:Background(frame,0.025,0.035,0.05,0.90); frame:SetBackdropBorderColor(0.3,0.38,0.42,0.9)
    local grip=CreateFrame('Frame',nil,frame); self.grip=grip
    grip:SetSize(10,24); grip:SetPoint('TOPLEFT',frame,'TOPLEFT',1,-4)
    grip:EnableMouse(true); grip:RegisterForDrag('LeftButton')
    local dots=grip:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall'); dots:SetPoint('CENTER',grip,'CENTER',0,0); dots:SetText(':')
    grip:SetScript('OnDragStart',function() if not InCombatLockdown() then self.moving=true; frame:StartMoving() end end)
    grip:SetScript('OnDragStop',function() self:FinishDrag() end)
    grip:SetScript('OnEnter',function()
        if not GameTooltip then return end
        GameTooltip:SetOwner(grip,'ANCHOR_RIGHT'); GameTooltip:AddLine('Mojow marks')
        GameTooltip:AddLine('Drag here outside combat. Click an icon to mark your selected target.',1,1,1,true); GameTooltip:Show()
    end)
    grip:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    local events=CreateFrame('Frame'); self.events=events
    for _,event in ipairs({'PLAYER_REGEN_ENABLED','PLAYER_REGEN_DISABLED','PLAYER_ENTERING_WORLD'}) do events:RegisterEvent(event) end
    events:SetScript('OnEvent',function(_,event)
        if event=='PLAYER_REGEN_DISABLED' and self.moving and pcall(frame.StopMovingOrSizing,frame) then
            self.moving=false; self.dragPending=true
        end
        if event=='PLAYER_REGEN_ENABLED' then self:FinishDrag() end
        self:Refresh()
    end)
    if NS.PullMarkers then self.markers=NS.PullMarkers:Create(addon,frame) end
    self:Refresh(); return self
end
