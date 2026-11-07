-- Decorations for public native nameplates only. Never request forbidden frames.
local _,NS=...
local Badges={}
Badges.__index=Badges
NS.WorldNameplateBadges=Badges

local function secret(value) return issecretvalue and issecretvalue(value) or false end
local function read(fn,...)
    if type(fn)~='function' then return end
    local ok,value=pcall(fn,...)
    if ok and not secret(value) then return value end
end
local function accessible(frame)
    if not frame then return false end
    local ok,allowed=pcall(function() return not frame:IsForbidden() and not frame:IsProtected() end)
    return ok and allowed==true
end
local function readableFrame(frame)
    if not frame then return false end
    local ok,allowed=pcall(function() return not frame:IsForbidden() end)
    return ok and allowed==true
end
local function finite(value)
    return not secret(value) and type(value)=='number' and value==value and value~=math.huge and value~=-math.huge
end
local function token(unit)
    if secret(unit) or type(unit)~='string' then return end
    local n=tonumber(unit:match('^nameplate(%d+)$'))
    return n and n>=1 and n<=200 and unit=='nameplate'..n and unit or nil
end
local function hide(entry)
    if not entry then return end
    for _,frame in ipairs({entry.classBadge,entry.levelBadge}) do
        if accessible(frame) then pcall(frame.Hide,frame) end
    end
end
local function badge(entry,key,parent,side,relative,x)
    local frame=CreateFrame('Frame',nil,parent,'BackdropTemplate')
    entry[key]=frame
    frame:Hide()
    frame:SetSize(20,20); frame:SetPoint(side,parent,relative,x,0)
    frame:EnableMouse(false)
    frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    frame:SetBackdropColor(0.04,0.04,0.04,0.94); frame:SetBackdropBorderColor(0.16,0.16,0.16,1)
    frame:Hide()
    return frame
end
local function label(frame)
    local text=frame:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    text:SetPoint('CENTER',frame,'CENTER',0,0); text:SetWidth(18)
    text:SetJustifyH('CENTER'); text:SetWordWrap(false)
    text:SetFont(STANDARD_TEXT_FONT or 'Fonts\\FRIZQT__.TTF',11,'OUTLINE')
    return text
end

function Badges:CreateEntry(plate,health,unit)
    if InCombatLockdown() or not readableFrame(plate) or not readableFrame(health) then return end
    local entry={plate=plate,health=health,overlay=not accessible(plate) or not accessible(health)}
    local parent=entry.overlay and UIParent or health
    -- Keep partial construction tracked so a refused method cannot strand a badge.
    self.cache[plate]=entry
    self.entries[unit]=entry
    badge(entry,'classBadge',parent,'RIGHT','LEFT',-1)
    badge(entry,'levelBadge',parent,'LEFT','RIGHT',1)
    if entry.overlay then entry.classBadge:SetFrameStrata('LOW'); entry.levelBadge:SetFrameStrata('LOW') end
    entry.icon=entry.classBadge:CreateTexture(nil,'ARTWORK')
    entry.icon:SetSize(18,18); entry.icon:SetPoint('CENTER',entry.classBadge,'CENTER',0,0)
    entry.icon:SetTexture('Interface\\GLUES\\CHARACTERCREATE\\UI-CHARACTERCREATE-CLASSES')
    entry.unknownClass=label(entry.classBadge); entry.unknownClass:SetText('?')
    entry.level=label(entry.levelBadge); entry.level:SetTextColor(1,0.82,0.39)
    entry.ready=true
    return entry
end

function Badges:AnchorToNative(entry)
    if entry.nativeAnchored then return true end
    if entry.anchorBlocked or InCombatLockdown() then return false end
    if not accessible(entry.classBadge) or not accessible(entry.levelBadge) then return false end
    hide(entry)
    local ok,err=pcall(function()
        entry.classBadge:ClearAllPoints(); entry.levelBadge:ClearAllPoints()
        entry.classBadge:SetPoint('RIGHT',entry.health,'LEFT',-1,0)
        entry.levelBadge:SetPoint('LEFT',entry.health,'RIGHT',1,0)
    end)
    if ok and accessible(entry.classBadge) and accessible(entry.levelBadge) then
        entry.nativeAnchored=true
        self.anchorResult='accepted; using native layout'
        return true
    end
    entry.anchorBlocked=true
    -- The frames are still hidden from before the attempted attachment.
    self.anchorResult=ok and 'badge became protected; left hidden' or 'client rejected attachment'
    if not ok and not secret(err) and type(err)=='string' then
        self.anchorResult=self.anchorResult..': '..err:gsub('[%c]',' '):sub(1,150)
    end
    return false
end

function Badges:Position(entry)
    if not entry.overlay then return true end
    if not readableFrame(entry.plate) or not readableFrame(entry.health) then return false end
    if read(entry.health.IsVisible,entry.health)~=true then return false end
    if entry.nativeAnchored then return true end
    local ok,x,y=pcall(entry.health.GetCenter,entry.health)
    local width=read(entry.health.GetWidth,entry.health)
    local scale=read(entry.health.GetEffectiveScale,entry.health)
    local uiScale=read(UIParent.GetEffectiveScale,UIParent)
    if not ok or not finite(x) or not finite(y) or not finite(width) or not finite(scale) or not finite(uiScale)
        or width<=0 or scale<=0 or uiScale<=0 then return self:AnchorToNative(entry) end
    local ratio=scale/uiScale
    -- Numeric screen anchors only: no parenting/anchoring to protected frames.
    entry.classBadge:ClearAllPoints(); entry.levelBadge:ClearAllPoints()
    entry.classBadge:SetPoint('RIGHT',UIParent,'BOTTOMLEFT',(x-width/2)*ratio-1,y*ratio)
    entry.levelBadge:SetPoint('LEFT',UIParent,'BOTTOMLEFT',(x+width/2)*ratio+1,y*ratio)
    return true
end

function Badges:Render(entry,unit)
    local unknown=false
    if entry.nativeLevel and read(entry.nativeLevel.IsShown,entry.nativeLevel)==true then
        -- Forever already supplies a right-side level badge, including native
        -- restricted-value handling. Keep it intact instead of drawing over it.
        entry.levelBadge:Hide()
    else
        local level=read(UnitLevel,unit)
        if type(level)=='number' and level==-1 then entry.level:SetText('??')
        elseif type(level)=='number' and level>=1 and level<=999 and level==math.floor(level) then entry.level:SetText(tostring(level))
        else entry.level:SetText('?'); unknown=true end
        entry.levelBadge:Show()
    end
    if read(UnitIsPlayer,unit)==true then
        local ok,_,class=pcall(UnitClass,unit)
        local coords=ok and not secret(class) and type(class)=='string' and CLASS_ICON_TCOORDS and CLASS_ICON_TCOORDS[class]
        if type(coords)=='table' then
            entry.icon:SetTexCoord(coords[1],coords[2],coords[3],coords[4])
            entry.icon:Show(); entry.unknownClass:Hide()
        else entry.icon:Hide(); entry.unknownClass:Show(); unknown=true end
        entry.classBadge:Show()
    else entry.classBadge:Hide() end
    return unknown
end

function Badges:Remove(unit)
    unit=token(unit); if not unit then return end
    hide(self.entries[unit]); self.entries[unit]=nil; self.tokens[unit]=nil
end

function Badges:RefreshUnit(unit)
    local plate=read(C_NamePlate and C_NamePlate.GetNamePlateForUnit,unit)
    if not readableFrame(plate) then return 'unavailable' end
    local ok,health,nativeLevel=pcall(function()
        -- Plater owns a separate lower-case unitFrame; do not double-skin it.
        if plate.unitFrame then return end
        local frame=plate.UnitFrame
        if not readableFrame(frame) then return end
        return frame.HealthBarsContainer and frame.HealthBarsContainer.healthBar,frame.PlayerLevelDiffFrame
    end)
    if not ok or not health then return 'unsupported' end
    if not readableFrame(health) then return 'unavailable' end
    if nativeLevel and not readableFrame(nativeLevel) then return 'unavailable' end
    if read(health.IsShown,health)~=true then return 'unsupported' end
    local old=self.entries[unit]
    if old and (old.plate~=plate or old.health~=health) then hide(old); self.entries[unit]=nil end
    local entry=self.cache[plate]
    if entry and entry.failed then return 'errors' end
    if entry and (entry.health~=health or not entry.ready) then hide(entry); self.cache[plate]=nil; entry=nil end
    if not entry then
        if InCombatLockdown() then return 'deferred' end
        entry=self:CreateEntry(plate,health,unit)
    end
    if not entry or not accessible(entry.classBadge) or not accessible(entry.levelBadge) then return 'unavailable' end
    self.entries[unit]=entry
    entry.nativeLevel=nativeLevel
    if not self:Position(entry) then return 'position' end
    return 'decorated',self:Render(entry,unit)
end

function Badges:Refresh()
    local counts={visible=0,decorated=0,unavailable=0,unsupported=0,deferred=0,errors=0,unknown=0,position=0}
    self.counts=counts
    if not self.enabled then return end
    for unit in pairs(self.tokens) do
        if read(UnitExists,unit)==true then
            counts.visible=counts.visible+1
            local ok,status,unknown=pcall(self.RefreshUnit,self,unit)
            if not ok then
                status='errors'
                if self.entries[unit] then self.entries[unit].failed=true end
            end
            counts[status]=counts[status]+1
            if unknown then counts.unknown=counts.unknown+1 end
            if status~='decorated' then hide(self.entries[unit]); self.entries[unit]=nil end
        else self:Remove(unit) end
    end
end

function Badges:Seed()
    for i=1,200 do
        local unit='nameplate'..i
        if read(UnitExists,unit)==true then self.tokens[unit]=true end
    end
end

function Badges:SetEnabled(enabled)
    if InCombatLockdown() then self.addon:Say('Change DogHouse badges outside combat.'); return false end
    self.enabled=not not enabled; self.addon.db.nameplateBadges=self.enabled
    if not self.enabled then
        for unit in pairs(self.entries) do self:Remove(unit) end
        for plate,entry in pairs(self.cache) do
            hide(entry)
            if entry.failed or entry.anchorBlocked then self.cache[plate]=nil end
        end
    else self:Seed() end
    self:Refresh()
    return true
end

-- Read-only diagnostic; normal public pool only, no frame mutation.
function Badges:GeometryProbe()
    local function value(v)
        if secret(v) then return 'restricted' end
        if v==nil then return 'nil' end
        if type(v)=='boolean' then return v and 'yes' or 'no' end
        if finite(v) then return 'number' end
        return type(v)
    end
    local function field(frame,method,two)
        if not frame then return 'no-frame' end
        local ok,a,b=pcall(function()
            if type(frame[method])~='function' then return 'no-method' end
            return frame[method](frame)
        end)
        if not ok then return 'API-error' end
        if not secret(a) and a=='no-method' then return a end
        return value(a)..(two and '/'..value(b) or '')
    end
    local function geometry(frame)
        return 'visible='..field(frame,'IsVisible')..', center='..field(frame,'GetCenter',true)..', width='..field(frame,'GetWidth')..', scale='..field(frame,'GetEffectiveScale')
    end
    local lines={}; local seen={}
    for i=1,200 do
        local unit='nameplate'..i
        if read(UnitExists,unit)==true then
            local kind=read(UnitIsPlayer,unit)==true and 'player' or 'NPC'
            if not seen[kind] then
                local plate=read(C_NamePlate and C_NamePlate.GetNamePlateForUnit,unit)
                if readableFrame(plate) then
                    local ok,health=pcall(function() return plate.UnitFrame and plate.UnitFrame.HealthBarsContainer and plate.UnitFrame.HealthBarsContainer.healthBar end)
                    lines[#lines+1]='Geometry '..kind..': plate '..geometry(plate)..' | health '..geometry(ok and health or nil)..' | UI scale='..field(UIParent,'GetEffectiveScale')
                    seen[kind]=true
                end
            end
        end
    end
    return lines
end

function Badges:Probe()
    local c={players=0,npcs=0,missing=0,forbidden=0,protected=0,layout=0,plater=0,ready=0,errors=0}
    local function gate(frame)
        if not frame then return 'missing' end
        if frame:IsForbidden() then return 'forbidden' end
        if frame:IsProtected() then return 'protected' end
    end
    for i=1,200 do
        local unit='nameplate'..i
        if read(UnitExists,unit)==true then
            local player=read(UnitIsPlayer,unit)
            if player==true then c.players=c.players+1 elseif player==false then c.npcs=c.npcs+1 end
            local ok,reason=pcall(function()
                if not C_NamePlate or type(C_NamePlate.GetNamePlateForUnit)~='function' then return 'errors' end
                local plate=C_NamePlate.GetNamePlateForUnit(unit)
                local denied=gate(plate); if denied then return denied end
                if plate.unitFrame then return 'plater' end
                local frame=plate.UnitFrame
                if not frame then return 'layout' end
                denied=gate(frame); if denied then return denied end
                local health=frame.HealthBarsContainer and frame.HealthBarsContainer.healthBar
                if not health then return 'layout' end
                denied=gate(health); if denied then return denied end
                return 'ready'
            end)
            local key=ok and reason or 'errors'; c[key]=c[key]+1
        end
    end
    return string.format('Badge probe: players %d, NPCs %d | missing public frame %d, forbidden %d, protected %d, other layout %d, Plater %d, ready %d, errors %d',
        c.players,c.npcs,c.missing,c.forbidden,c.protected,c.layout,c.plater,c.ready,c.errors)
end

function Badges:Status()
    local c=self.counts
    if not self.enabled then return 'DogHouse badges: off' end
    return string.format('DogHouse badges: visible %d, decorated %d, unavailable %d, unsupported %d, deferred %d, errors %d, unknown %d, unreadable position %d',
        c.visible,c.decorated,c.unavailable,c.unsupported,c.deferred,c.errors,c.unknown,c.position)
end

function Badges:Create(addon)
    local self=setmetatable({addon=addon,enabled=addon.db.nameplateBadges==true,tokens={},entries={},cache=setmetatable({},{__mode='k'})},Badges)
    self.events=CreateFrame('Frame')
    for _,event in ipairs({'NAME_PLATE_UNIT_ADDED','NAME_PLATE_UNIT_REMOVED','PLAYER_ENTERING_WORLD','PLAYER_REGEN_ENABLED'}) do self.events:RegisterEvent(event) end
    self.events:SetScript('OnEvent',function(_,event,unit)
        if event=='NAME_PLATE_UNIT_REMOVED' then self:Remove(unit)
        elseif event=='NAME_PLATE_UNIT_ADDED' then unit=token(unit); if unit then self.tokens[unit]=true end
        elseif self.enabled then self:Seed() end
        self:Refresh()
    end)
    local elapsed,positionElapsed=0,0
    self.events:SetScript('OnUpdate',function(_,delta)
        if not self.enabled then return end
        positionElapsed=positionElapsed+delta
        if positionElapsed>=0.03 then
            positionElapsed=0
            for _,entry in pairs(self.entries) do
                if entry.overlay then
                    local ok,positioned=pcall(self.Position,self,entry)
                    if not ok or not positioned then hide(entry) end
                end
            end
        end
        elapsed=elapsed+delta
        if elapsed>=0.25 then elapsed=0; self:Refresh() end
    end)
    if self.enabled then self:Seed() end
    self:Refresh()
    return self
end
