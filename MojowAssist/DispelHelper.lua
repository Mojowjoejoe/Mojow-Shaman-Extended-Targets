local _,NS=...
local Dispel={}
NS.DispelHelper=Dispel
-- Conservative cross-client coverage; do not infer talent-dependent magic cures.
local cures={{526,'Poison'},{2870,'Disease'},{51886,'Curse'}}
local function secret(value) return issecretvalue and issecretvalue(value) end

function Dispel:Capabilities()
    local result={}
    for _,entry in ipairs(cures) do
        local ok,name=pcall(NS.NearbyHealing.Learned,NS.NearbyHealing,entry[1])
        if ok and name then result[entry[2]]={id=entry[1],name=name}
        elseif not ok then result._unknown=true end
    end
    return result
end

function Dispel:Scan(unit,capabilities)
    if not capabilities or not next(capabilities) then return {kind='none'} end
    if InCombatLockdown() then return {kind='unknown'} end
    local api=C_UnitAuras and C_UnitAuras.GetAuraDataByIndex
    if type(api)~='function' then return {kind='unknown'} end
    for index=1,40 do
        local ok,aura=pcall(api,unit,index,'HARMFUL')
        if not ok or secret(aura) then return {kind='unknown'} end
        if aura==nil then return {kind=capabilities._unknown and 'unknown' or 'clear'} end
        local readable,kind=pcall(function() return aura.dispelName end)
        if not readable or secret(kind) then return {kind='unknown'} end
        if type(kind)=='string' and capabilities[kind] then
            return {kind='found',dispel=kind,spell=capabilities[kind]}
        end
    end
    return {kind='unknown'}
end

function Dispel:Update(row,unit,name,capabilities)
    if type(name)~='string' or name=='' then
        row.dispelData={kind='unknown'}; row.dispelNext=0
        return row.dispelData
    end
    local now=GetTime()
    if InCombatLockdown() or row.dispelUnit~=unit or row.dispelName~=name
        or not row.dispelNext or now>=row.dispelNext then
        row.dispelData=self:Scan(unit,capabilities)
        row.dispelUnit,row.dispelName=unit,name
        -- Combat never caches an earlier clean/positive result into the next update.
        row.dispelNext=InCombatLockdown() and 0 or now+0.5
    end
    return row.dispelData
end

function Dispel:Marker(data)
    if not data then return '' end
    -- Unknown is explained on hover, never displayed as a removable debuff.
    if data.kind=='found' then
        local marks={Poison='|cff55ff88[Poison]|r ',Disease='|cffffcc55[Disease]|r ',Curse='|cffcc88ff[Curse]|r '}
        return marks[data.dispel] or ''
    end
    return ''
end

function Dispel:Tooltip(row,db)
    local data=row.dispelData
    if not GameTooltip then return end
    if row.nativePoisonReady then
        GameTooltip:AddLine('Green-bordered icon: removable poison (game display).',0.35,1,0.5,true)
    elseif row.nativePoisonError then
        GameTooltip:AddLine('Native poison display unavailable; text scan only.',0.7,0.7,0.7,true)
    end
    if not data then return end
    if data.kind=='unknown' then GameTooltip:AddLine(row.nativePoisonReady and 'Text debuff scan unavailable; native icon updates separately.' or 'Debuffs unknown (restricted or unavailable)',0.7,0.7,0.7,true)
    elseif data.kind=='clear' then GameTooltip:AddLine('No matching removable debuff found in last scan.',0.7,0.7,0.7,true)
    elseif data.kind=='found' then
        local actions={}
        if db.healLeftID==data.spell.id then actions[#actions+1]='Left click' end
        if db.healRightID==data.spell.id then actions[#actions+1]='Shift-right click' end
        local action=#actions>0 and table.concat(actions,' / ') or 'Assign a click in /mja heals'
        GameTooltip:AddLine(data.dispel..': '..data.spell.name..' - '..action,0.8,1,0.5,true)
    end
end
