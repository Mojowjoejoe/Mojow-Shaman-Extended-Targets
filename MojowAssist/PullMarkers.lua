-- Manual pull marks. Only native SecureActionButtonTemplate executes a mark.
local _,NS=...
local Markers={}
NS.PullMarkers=Markers
local names={[0]='Clear', 'Star','Circle','Diamond','Triangle','Moon','Square','Cross','Skull'}
local function read(fn,...)
    if type(fn)~='function' then return end
    local ok,value=pcall(fn,...)
    if ok and not (issecretvalue and issecretvalue(value)) then return value end
end
local function label(frame,x,y,width,value)
    local text=frame:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    text:SetPoint('TOPLEFT',frame,'TOPLEFT',x,y); text:SetWidth(width); text:SetJustifyH('LEFT'); text:SetWordWrap(false); text:SetText(value)
    return text
end
function Markers:Permission()
    local raid=read(IsInRaid)
    if raid==false then return 'Party / solo: client checks permissions' end
    if raid~=true then return 'Mark permission unavailable' end
    local leader=read(UnitIsGroupLeader,'player')
    local assistant=read(UnitIsGroupAssistant,'player')
    if leader==true or assistant==true then return 'Raid marking permitted' end
    if leader==false and assistant==false then return 'Raid leader or assistant required' end
    return 'Mark permission unavailable'
end
function Markers:Refresh()
    local exists=read(UnitExists,'target')
    local name=exists and read(UnitName,'target')
    self.targetText='Mark target: '..(exists==false and 'No target' or type(name)=='string' and name or 'unavailable')
    local permission=self:Permission()
    local index=read(GetRaidTargetIndex,'target')
    local mark=type(index)=='number' and names[index] or nil
    if not self.available then self.statusText='Markers unavailable on this client'
    elseif exists~=true then self.statusText='Select a target to mark'
    elseif permission=='Raid leader or assistant required' or permission=='Mark permission unavailable' then self.statusText=permission
    else self.statusText='Current mark: '..(mark or 'none / unavailable') end
    for id,button in pairs(self.buttons) do
        local selected=exists==true and mark~=nil and id==index and id~=0
        button:SetBackdropBorderColor(selected and 1 or 0.3,selected and 0.8 or 0.35,selected and 0.2 or 0.4,1)
    end
end
function Markers:Create(addon,parent)
    local self=setmetatable({addon=addon,buttons={},available=type(SetRaidTarget)=='function'},{__index=Markers})
    local frame=CreateFrame('Frame',nil,parent)
    self.frame=frame; frame:SetSize(228,32); frame:SetPoint('TOPLEFT',parent,'TOPLEFT',11,0)
    -- Skull first, then Cross and crowd-control symbols; Clear affects target only.
    local order={8,7,5,6,3,4,2,1,0}
    for pos,id in ipairs(order) do
        local button=CreateFrame('Button',nil,frame,'SecureActionButtonTemplate,BackdropTemplate')
        button:SetSize(24,24); button:SetPoint('TOPLEFT',frame,'TOPLEFT',1+(pos-1)*25,-4)
        button:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
        NS.Appearance:Background(button,0.03,0.04,0.055,0.96)
        if id==0 then label(button,7,-5,16,'X')
        else
            local texture=button:CreateTexture(nil,'ARTWORK'); texture:SetSize(22,22); texture:SetPoint('CENTER',button,'CENTER',0,0)
            texture:SetTexture('Interface\\TargetingFrame\\UI-RaidTargetingIcon_'..id)
        end
        button:RegisterForClicks('AnyDown','AnyUp')
        button:SetAttribute('unit','target')
        button:SetAttribute('harmbutton1','mark')
        button:SetAttribute('helpbutton1','mark')
        button:SetAttribute('type-mark',self.available and 'raidtarget' or nil)
        button:SetAttribute('action-mark',id==0 and 'clear' or 'set')
        button:SetAttribute('marker-mark',id)
        button:SetScript('OnEnter',function()
            if not GameTooltip then return end
            GameTooltip:SetOwner(button,'ANCHOR_RIGHT'); GameTooltip:AddLine(names[id],1,0.85,0.4)
            local targetName=read(UnitName,'target')
            GameTooltip:AddLine('Target: '..(type(targetName)=='string' and targetName or 'unavailable'),0.7,0.9,1,true)
            GameTooltip:AddLine(id==0 and 'Left-click: clear the selected target marker' or 'Left-click: set this mark on your selected target',1,1,1,true)
            self:Refresh()
            GameTooltip:AddLine(self.statusText or '',0.8,0.8,0.8,true)
            GameTooltip:AddLine(self:Permission(),0.8,0.8,0.8,true)
            GameTooltip:AddLine('Select a target, then click a marker. Row healing and spell clicks are unchanged.',0.7,0.9,1,true)
            GameTooltip:Show()
        end)
        button:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
        -- Read back actual native state; do not claim success from the click alone.
        button:SetScript('PostClick',function() self:Refresh() end)
        self.buttons[id]=button
    end
    local events=CreateFrame('Frame');self.events=events
    for _,event in ipairs({'PLAYER_TARGET_CHANGED','RAID_TARGET_UPDATE','GROUP_ROSTER_UPDATE','PARTY_LEADER_CHANGED'}) do events:RegisterEvent(event) end
    events:SetScript('OnEvent',function() self:Refresh() end)
    self:Refresh();return self
end
