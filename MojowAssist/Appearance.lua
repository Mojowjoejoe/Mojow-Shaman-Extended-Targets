local _,NS=...
local Appearance={surfaces=setmetatable({},{__mode='k'}),transparency=0}
NS.Appearance=Appearance

function Appearance:Apply(surface,entry)
    -- The aura slot becomes restricted after setup. Only change its own
    -- background outside combat; never read native aura/frame state.
    if entry.texture and InCombatLockdown() then self.pending=true; return false end
    local alpha=entry[4]*(1-self.transparency/100)
    local method=entry.texture and surface.SetColorTexture or surface.SetBackdropColor
    local ok=pcall(method,surface,entry[1],entry[2],entry[3],alpha)
    if not ok then self.pending=true end
    return ok
end

function Appearance:Refresh()
    self.pending=false
    for surface,entry in pairs(self.surfaces) do self:Apply(surface,entry) end
end

function Appearance:Background(surface,r,g,b,a,texture)
    local entry=self.surfaces[surface] or {}
    entry[1],entry[2],entry[3],entry[4],entry.texture=r,g,b,a,texture
    self.surfaces[surface]=entry
    self:Apply(surface,entry)
end

function Appearance:Configure(db)
    self.db=db
    if not self.events then
        self.events=CreateFrame('Frame')
        self.events:RegisterEvent('PLAYER_REGEN_ENABLED')
        self.events:SetScript('OnEvent',function() if self.pending then self:Refresh() end end)
    end
    self:SetTransparency(db.windowTransparency or 0)
end

function Appearance:SetTransparency(value)
    if type(value)~='number' or value~=value or value==math.huge or value==-math.huge then return end
    self.transparency=math.max(0,math.min(100,math.floor(value+0.5)))
    if self.db then self.db.windowTransparency=self.transparency end
    self:Refresh()
end
