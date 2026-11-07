-- Observable attackable NPCs and other players. No protected actions or restricted-value ranking.
local _, NS = ...
local Roster = {}
Roster.__index = Roster
NS.EnemyRoster = Roster
NS.EnemySections = {
    {key='group', option='enemyShowGroup', label='Group Members', color={0.40,0.90,0.50}},
    {key='npc', option='enemyShowNPCs', label='NPCs', color={1,0.73,0.30}},
    {key='enemy', option='enemyShowEnemyPlayers', label='Enemy Players', color={1,0.38,0.38}},
    {key='friendly', option='enemyShowFriendlyPlayers', label='Nearby Friendly Players', color={0.38,0.72,1}},
}

function Roster:IsGroupToken(unit)
    if type(unit)~='string' then return false end
    local party=tonumber(unit:match('^party(%d+)$'))
    local raid=tonumber(unit:match('^raid(%d+)$'))
    return (party and party>=1 and party<=4) or (raid and raid>=1 and raid<=40) or false
end

function Roster:IsGroupMember(unit)
    return self:IsGroupToken(unit) or (unit=='player' and self:Read(IsInGroup)==true)
end

function Roster:Present(unit)
    if self:Read(UnitExists,unit)==true then return true end
    -- Disconnected group members can retain a readable roster name without a world unit.
    if self:IsGroupToken(unit) and self:Read(UnitIsConnected,unit)==false then
        local name=self:Read(UnitName,unit)
        return type(name)=='string' and name~=''
    end
    return false
end

function Roster:GroupStatus(unit)
    if not self:IsGroupMember(unit) then return nil end
    if self:Read(UnitIsConnected,unit)==false then return 'OFFLINE' end
    local ghost=self:Read(UnitIsGhost,unit)
    if ghost==true then return 'GHOST' end
    if self:Read(UnitIsDead,unit)==true then return 'DEAD' end
    if self:Read(UnitIsDeadOrGhost,unit)==true then return ghost==false and 'DEAD' or 'DOWN' end
end

function Roster:IsSelf(unit)
    if unit=='player' or self:Read(UnitIsUnit,unit,'player')==true then return true end
    local guid=self:Read(UnitGUID,unit)
    local playerGUID=self:Read(UnitGUID,'player')
    return type(guid)=='string' and guid~='' and type(playerGUID)=='string' and guid==playerGUID
end

function Roster:Category(unit)
    -- Never let a self alias become an NPC or nearby stranger.
    if self:IsSelf(unit) then return self:Read(IsInGroup)==true and 'group' or nil end
    -- Group tokens identify players independently of nameplate visibility.
    if self:IsGroupMember(unit) and self:Present(unit) then
        return self:Read(UnitCanAttack,'player',unit) and 'enemy' or 'group'
    end
    local player,known=self:Read(UnitIsPlayer,unit)
    if not known then return nil end
    if not player then return 'npc' end
    local enemy,enemyKnown=self:Read(UnitIsEnemy,'player',unit)
    if enemyKnown and enemy then return 'enemy' end
    local friend,friendKnown=self:Read(UnitIsFriend,'player',unit)
    if friendKnown and friend then return 'friendly' end
    local attackable,attackKnown=self:Read(UnitCanAttack,'player',unit)
    if attackKnown and attackable then return 'enemy' end
    -- On clients without relationship APIs, use the readable attackability flag.
    if type(UnitIsEnemy)~='function' and type(UnitIsFriend)~='function' and attackKnown then return 'friendly' end
end

function Roster:IsFriendly(unit)
    local category=self:Category(unit)
    return category=='group' or category=='friendly'
end

function Roster:Create()
    return setmetatable({order={}, present={}}, self)
end

function Roster:IsSecret(value)
    return issecretvalue and issecretvalue(value) or false
end

function Roster:Read(api, ...)
    if type(api) ~= 'function' then return nil, false end
    local ok, value = pcall(api, ...)
    if not ok or self:IsSecret(value) then return nil, false end
    return value, true
end

function Roster:Add(unit)
    if self:IsSecret(unit) or type(unit) ~= 'string' then return end
    local n = tonumber(unit:match('^nameplate(%d+)$'))
    if not n or n < 1 or n > 200 or self.present[unit] then return end
    self.present[unit] = true
    self.order[#self.order+1] = unit
end

function Roster:Remove(unit)
    if self:IsSecret(unit) or type(unit) ~= 'string' then return end
    self.present[unit] = nil
    for i = #self.order, 1, -1 do
        if self.order[i] == unit then table.remove(self.order, i) end
    end
end

function Roster:Clear()
    self.order, self.present = {}, {}
end

function Roster:Snapshot()
    local rows, unknown = {}, 0
    local seenGUIDs={}
    local selfGUID=self:Read(UnitGUID,'player')
    if type(selfGUID)~='string' or selfGUID=='' then selfGUID=nil end
    local function consider(unit,includeSelf)
        local exists = self:Present(unit)
        if not exists then return end
        local player = self:IsGroupMember(unit) or self:Read(UnitIsPlayer, unit)
        local hostile, known = self:Read(UnitCanAttack, 'player', unit)
        if not player and not known then unknown = unknown + 1; return end
        if (not hostile and not player) or (not self:IsGroupMember(unit) and self:Read(UnitIsDeadOrGhost, unit)) then return end
        local guid=self:Read(UnitGUID,unit)
        if type(guid)~='string' or guid=='' then guid=nil end
        if not includeSelf and (self:Read(UnitIsUnit,unit,'player') or (guid and guid==selfGUID)) then return end
        if guid and seenGUIDs[guid] then return end
        for _, previous in ipairs(rows) do
            if self:Read(UnitIsUnit, unit, previous) or self:Read(UnitIsUnit, previous, unit) then return end
        end
        rows[#rows+1] = unit
        if guid then seenGUIDs[guid]=true end
    end
    -- Show self first only while grouped, then merge other stable group tokens.
    if self:Read(IsInGroup)==true then consider('player',true) end
    for i=1,4 do consider('party'..i) end
    for i=1,40 do consider('raid'..i) end
    for _, unit in ipairs(self.order) do consider(unit) end
    consider('target')
    consider('focus')
    return rows, unknown
end

local function finite(n)
    return type(n) == 'number' and n == n and n > -math.huge and n < math.huge
end

function Roster:Interruptible(value)
    if not self:IsSecret(value) and type(value)=='boolean' then return not value end
end

function Roster:NativeCast(unit, channel)
    local api = channel and UnitChannelDuration or UnitCastingDuration
    if type(api) ~= 'function' then return nil end
    local ok, duration = pcall(api, unit)
    if not ok then return nil end
    if not self:IsSecret(duration) and duration == nil then return nil end
    local nameAPI = channel and UnitChannelInfo or UnitCastingInfo
    local nameOK, name, _, _, _, _, _, channelFlag, castFlag = pcall(nameAPI, unit)
    if not nameOK or (not self:IsSecret(name) and name == nil) then
        name = channel and 'Channeling' or 'Casting'
    end
    local flag=castFlag
    if channel then flag=channelFlag end
    return {native=true, duration=duration, name=name, channel=channel, interruptible=self:Interruptible(flag)}
end

function Roster:Cast(unit, legacyOnly)
    if not legacyOnly then
        local native = self:NativeCast(unit, false) or self:NativeCast(unit, true)
        if native then return native end
    end
    local function read(api)
        if type(api) ~= 'function' then return false end
        return pcall(api, unit)
    end
    local channel = false
    local ok, name, _, _, startMS, endMS, _, channelFlag, castFlag = read(UnitCastingInfo)
    if not ok or self:IsSecret(name) then return {restricted=true} end
    if not name then
        channel = true
        ok, name, _, _, startMS, endMS, _, channelFlag, castFlag = read(UnitChannelInfo)
    end
    if not ok or self:IsSecret(name) or self:IsSecret(startMS) or self:IsSecret(endMS) then
        return {restricted=true}
    end
    if not name then return nil end
    if type(name) ~= 'string' or not finite(startMS) or not finite(endMS) or endMS <= startMS then
        return {restricted=true}
    end
    local remaining = endMS / 1000 - GetTime()
    if remaining <= 0 or GetTime() < startMS / 1000 then return nil end
    local flag=castFlag
    if channel then flag=channelFlag end
    return {name=name, remaining=remaining, duration=(endMS-startMS)/1000, channel=channel, interruptible=self:Interruptible(flag)}
end
