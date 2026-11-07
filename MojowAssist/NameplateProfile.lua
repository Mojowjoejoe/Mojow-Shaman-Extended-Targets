local _,NS=...
local Profile={}
Profile.__index=Profile
NS.NameplateProfile=Profile
local wanted={
    nameplateShowAll='1',nameplateShowEnemies='1',
    nameplateShowFriendlyPlayers='1',nameplateShowFriendlyNpcs='1',
    nameplateShowOnlyNameForFriendlyPlayerUnits='0',
    nameplateSelectedAlpha='1',nameplateNotSelectedAlpha='1',
    nameplateMinAlpha='1',nameplateMaxAlpha='1',nameplateOccludedAlphaMult='1',
    nameplateShowClassColor='1',nameplateShowFriendlyClassColor='1',
}
-- Forever Nameplates.lua uses enum values as one-based CVar bit indices.
-- These CVars contain encoded strings, not decimal masks. Native bit setters
-- preserve every unrelated preference, including bits added by later clients.
local bitSettings={
    {'nameplateInfoDisplay','NamePlateInfoDisplay','CurrentHealthPercent'},
    {'nameplateCastBarDisplay','NamePlateCastBarDisplay','SpellName'},
    {'nameplateCastBarDisplay','NamePlateCastBarDisplay','SpellIcon'},
    {'nameplateThreatDisplay','NamePlateThreatDisplay','Progressive'},
    {'nameplateThreatDisplay','NamePlateThreatDisplay','HealthBarColor'},
}
local bitByKey={}
for _,setting in ipairs(bitSettings) do bitByKey[setting[1]..setting[3]]=setting end
local function bitIndex(setting)
    local enum=Enum and Enum[setting[2]]
    local index=enum and enum[setting[3]]
    if type(index)=='number' and index>=1 and index<=1530 and index==math.floor(index) then return index end
end
function Profile:ReadBit(setting)
    local index=bitIndex(setting)
    local get=C_CVar and C_CVar.GetCVarBitfield or GetCVarBitfield
    if not index or type(get)~='function' or not self.options:Read(setting[1]) then return end
    local ok,value=pcall(get,setting[1],index)
    if not ok or (issecretvalue and issecretvalue(value)) or type(value)~='boolean' then return end
    return value and '1' or '0'
end
function Profile:WriteBit(setting,value)
    local index=bitIndex(setting)
    local set=C_CVar and C_CVar.SetCVarBitfield or SetCVarBitfield
    return index and type(set)=='function' and pcall(set,setting[1],index,value=='1') and self:ReadBit(setting)==value
end
local function equal(a,b)
    if a==b then return true end
    local x,y=tonumber(a),tonumber(b)
    return x~=nil and y~=nil and x==y
end
function Profile:Create(addon,options)
    addon.db.nameplateRestore=addon.db.nameplateRestore or {}
    return setmetatable({addon=addon,options=options},self)
end
function Profile:Targets()
    local values={}
    for name,value in pairs(wanted) do values[name]=value end
    if Enum and Enum.NamePlateStyle and type(Enum.NamePlateStyle.Block)=='number' then
        values.nameplateStyle=tostring(Enum.NamePlateStyle.Block)
    end
    if Enum and Enum.NamePlateSize and type(Enum.NamePlateSize.Small)=='number' then
        values.nameplateSize=tostring(Enum.NamePlateSize.Small)
    end
    return values
end
function Profile:Write(name,value)
    local set=C_CVar and C_CVar.SetCVar or SetCVar
    return set and pcall(set,name,value) and equal(self.options:Read(name),value)
end
function Profile:Status()
    local matching,total=0,0
    local targets=self:Targets()
    for name,value in pairs(targets) do
        total=total+1
        if equal(self.options:Read(name),value) then matching=matching+1 end
    end
    local unavailable=not targets.nameplateStyle or not targets.nameplateSize
    local bitsUnavailable=false
    for _,setting in ipairs(bitSettings) do
        local current=self:ReadBit(setting)
        total=total+1
        if current=='1' then matching=matching+1 end
        if not current then bitsUnavailable=true end
    end
    return matching..'/'..total..' settings match.'..((unavailable or bitsUnavailable) and ' Some settings unavailable.' or '')
end
function Profile:Apply()
    if InCombatLockdown() then self.addon:Say('Apply nameplates outside combat.'); return false end
    local failed={}
    local targets=self:Targets()
    if not targets.nameplateStyle then failed[#failed+1]='native Block style' end
    if not targets.nameplateSize then failed[#failed+1]='native Small size' end
    for name,value in pairs(targets) do
        local current=self.options:Read(name)
        if not current then failed[#failed+1]=name
        elseif not equal(current,value) then
            -- Save before writing, including when a client partially applies a write.
            local saved=self.addon.db.nameplateRestore
            if not saved[name] then saved[name]={before=current,applied=value} end
            local applied=self:Write(name,value)
            local actual=self.options:Read(name)
            if actual and not equal(actual,current) then saved[name].applied=actual end
            if not applied then failed[#failed+1]=name end
        end
    end
    for _,setting in ipairs(bitSettings) do
        local key=setting[1]..setting[3]
        local current=self:ReadBit(setting)
        if not current then failed[#failed+1]=key
        elseif current~='1' then
            local saved=self.addon.db.nameplateRestore
            -- Numeric strings retain the existing saved-history schema. This
            -- key identifies one native bit, not a CVar to write as a whole.
            if not saved[key] then saved[key]={before=current,applied='1'} end
            local applied=self:WriteBit(setting,'1')
            local actual=self:ReadBit(setting)
            if actual and actual~=current then saved[key].applied=actual end
            if not applied then failed[#failed+1]=key end
        end
    end
    self.addon:Say(self:Status())
    if self.addon.worldBadges then
        self.addon.worldBadges:SetEnabled(true)
        self.addon:Say(self.addon.worldBadges:Status())
    end
    if #failed>0 then self.addon:Say('Unavailable or rejected: '..table.concat(failed,', ')) end
    self.options:Refresh()
    return #failed==0
end
function Profile:Restore()
    if InCombatLockdown() then self.addon:Say('Restore nameplates outside combat.'); return false end
    if self.addon.worldBadges then self.addon.worldBadges:SetEnabled(false) end
    local failed={}
    for name,entry in pairs(self.addon.db.nameplateRestore) do
        local setting=bitByKey[name]
        local current
        if setting then current=self:ReadBit(setting) else current=self.options:Read(name) end
        if not current then failed[#failed+1]=name
        elseif not equal(current,entry.applied) then
            self.addon.db.nameplateRestore[name]=nil
        else
            local restored
            if setting then restored=self:WriteBit(setting,entry.before) else restored=self:Write(name,entry.before) end
            if restored then self.addon.db.nameplateRestore[name]=nil
            else
                local actual
                if setting then actual=self:ReadBit(setting) else actual=self.options:Read(name) end
                if actual then entry.applied=actual end
                failed[#failed+1]=name
            end
        end
    end
    self.addon:Say(#failed==0 and 'Previous nameplate settings restored; later manual changes kept.' or 'Restore pending for: '..table.concat(failed,', '))
    self.options:Refresh()
    return #failed==0
end
