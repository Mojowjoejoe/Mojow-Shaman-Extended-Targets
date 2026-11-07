local _,NS=...
local Totems={}
Totems.__index=Totems
NS.TotemModel=Totems
Totems.elements={{slot=2,name='Earth'},{slot=1,name='Fire'},{slot=3,name='Water'},{slot=4,name='Air'}}
-- Reused from the beta MojowShaman catalog. Unknown/unlearned spells are omitted.
Totems.catalog={
    {8071,2},{2484,2},{5730,2},{8075,2},{8143,2},
    {3599,1},{1535,1},{8190,1},{8227,1},{8181,1},
    {5394,3},{5675,3},{8166,3},{8170,3},{8184,3},{16190,3},
    {8177,4},{8512,4},{8835,4},{6495,4},{15107,4},{10595,4},{25908,4},
}

function Totems:Secret(value)
    return issecretvalue and issecretvalue(value) or false
end

function Totems:Info(id)
    if C_Spell and C_Spell.GetSpellInfo then return C_Spell.GetSpellInfo(id) end
    if GetSpellInfo then
        local name,_,icon=GetSpellInfo(id)
        if name then return {name=name,iconID=icon} end
    end
end

function Totems:Create(db)
    return setmetatable({db=db,spells={},groups={{},{},{},{}},error=nil},self)
end

function Totems:Refresh()
    if InCombatLockdown() then return false,'Wait until combat ends.' end
    local found={}
    local ok,err=pcall(function()
        local names,baseIDs={},{}
        for _,entry in ipairs(self.catalog) do
            local spell=self:Info(entry[1])
            local previous=self.spells[entry[1]]
            local name=spell and spell.name or previous and previous.name
            if self:Secret(name) then error('Totem names unavailable') end
            if type(name)=='string' and name~='' then names[name]=entry end
            baseIDs[entry[1]]=entry
        end
        local learnedCount=0
        local function add(id,bookName,rankText,bookIndex,bank)
            if self:Secret(id) or type(id)~='number' then error('Learned spell ID unavailable') end
            local spell=self:Info(id)
            local name=bookName or spell and spell.name
            if self:Secret(name) or type(name)~='string' or name=='' then error('Learned spell name unavailable') end
            learnedCount=learnedCount+1
            local entry=baseIDs[id] or names[name]
            if not entry then return end
            if self:Secret(rankText) then error('Learned spell rank unavailable') end
            local rank=type(rankText)=='string' and tonumber(rankText:match('%d+')) or nil
            local previous=found[entry[1]]
            if previous and previous.rank and (not rank or previous.rank>rank) then return end
            local old=self.spells[entry[1]]
            local icon=spell and spell.iconID or old and old.icon
            if not icon and bank and C_SpellBook.GetSpellBookItemTexture then icon=C_SpellBook.GetSpellBookItemTexture(bookIndex,bank) end
            if self:Secret(icon) then icon=nil end
            found[entry[1]]={baseID=entry[1],spellID=id,rank=rank,slot=entry[2],name=name,icon=icon}
        end
        if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
            local bank=Enum.SpellBookSpellBank.Player
            for tab=1,C_SpellBook.GetNumSpellBookSkillLines() do
                local line=C_SpellBook.GetSpellBookSkillLineInfo(tab)
                if not line then error('Spellbook skill line unavailable') end
                if line and (not line.offSpecID or line.offSpecID==0) then
                    for index=line.itemIndexOffset+1,line.itemIndexOffset+line.numSpellBookItems do
                        local item=C_SpellBook.GetSpellBookItemInfo(index,bank)
                        if not item then error('Spellbook entry unavailable') end
                        if self:Secret(item.itemType) or type(item.itemType)~='number' then error('Spellbook entry type unavailable') end
                        if item and item.itemType==Enum.SpellBookItemType.Spell and not item.isPassive then
                            local name,rank
                            if C_SpellBook.GetSpellBookItemName then name,rank=C_SpellBook.GetSpellBookItemName(index,bank) end
                            add(item.spellID or item.actionID,name,rank,index,bank)
                        end
                    end
                end
            end
        elseif GetNumSpellTabs and GetSpellTabInfo and GetSpellBookItemInfo then
            for tab=1,GetNumSpellTabs() do
                local _,_,offset,count=GetSpellTabInfo(tab)
                for index=offset+1,offset+count do
                    local kind,id=GetSpellBookItemInfo(index,'spell')
                    if not kind then error('Spellbook entry unavailable') end
                    if kind=='SPELL' then
                        local name,rank
                        if GetSpellBookItemName then name,rank=GetSpellBookItemName(index,'spell') end
                        add(id,name,rank,index)
                    end
                end
            end
        else error('Spellbook API unavailable') end
        -- A complete empty book is authoritative. A nonempty book with no
        -- usable catalog names cannot establish that every totem is unlearned.
        if learnedCount>0 and not next(names) and not next(found) then error('Totem catalog names unavailable') end
    end)
    if not ok then self.error=tostring(err); return false,self.error end
    self.spells=found; self.groups={{},{},{},{}}; self.error=nil
    for _,entry in ipairs(self.catalog) do
        local spell=found[entry[1]]
        if spell then table.insert(self.groups[spell.slot],spell) end
    end
    return true
end

function Totems:Ordered(slot)
    local result={}
    local favorite=self.db.totemFavorites[slot]
    if favorite and self.spells[favorite] and self.spells[favorite].slot==slot then result[1]=self.spells[favorite] end
    for _,spell in ipairs(self.groups[slot]) do if spell.baseID~=favorite then result[#result+1]=spell end end
    return result
end

function Totems:SetFavorite(baseID)
    if InCombatLockdown() then return false,'Favorites change outside combat.' end
    local spell=self.spells[baseID]
    if not spell then return false,'That totem is not learned.' end
    self.db.totemFavorites[spell.slot]=baseID
    return true
end

function Totems:SavePreset(index)
    if InCombatLockdown() then return false,'Presets change outside combat.' end
    if index~=1 and index~=2 and index~=3 then return false,'Choose preset 1, 2, or 3.' end
    local copy={}
    for slot,id in pairs(self.db.totemFavorites) do copy[slot]=id end
    self.db.totemPresets[index]=copy
    return true,'Saved favorites to preset '..index..'.'
end

function Totems:LoadPreset(index)
    if InCombatLockdown() then return false,'Presets change outside combat.' end
    local preset=self.db.totemPresets[index]
    if type(preset)~='table' then return false,'That preset has not been saved.' end
    local copy={}
    for slot,id in pairs(preset) do
        if not self.spells[id] or self.spells[id].slot~=slot then return false,'Preset contains an unavailable totem; favorites unchanged.' end
        copy[slot]=id
    end
    self.db.totemFavorites=copy
    return true,'Loaded preset '..index..' favorites. Click each totem to summon.'
end

-- No current Forever totem API reports the player's distance from a totem or
-- whether its aura covers the player. Do not substitute target spell range.
function Totems:ActiveState(selected,have,name,start,duration,spellID)
    if not self:Secret(have) and have==false then return 'missing' end
    -- Empty details can accompany a present/unreadable totem on Forever.
    if not self:Secret(name) and name=='' then return 'unknown' end
    if not self:Secret(start) and not self:Secret(duration) and type(start)=='number' and type(duration)=='number'
        and start==start and duration==duration and start<math.huge and duration<math.huge
        and duration>0 and start+duration<=GetTime() then return 'missing' end
    if not selected then return 'unknown' end
    if not self:Secret(spellID) and type(spellID)=='number' and (spellID==selected.spellID or spellID==selected.baseID) then return 'active' end
    if not self:Secret(name) and type(name)=='string' then
        return name==selected.name and 'active' or 'other'
    end
    return 'unknown'
end

function Totems:Next(slot)
    local list=self.groups[slot] or {}
    if #list<2 then return nil end
    local selected=self:Ordered(slot)[1]
    for index,spell in ipairs(list) do
        if spell.baseID==selected.baseID then return list[index % #list+1] end
    end
end

function Totems:Sequence()
    local names={}
    for _,element in ipairs(self.elements) do
        local spell=self:Ordered(element.slot)[1]
        if spell then
            -- Localized spell names are command data; reject macro delimiters.
            if spell.name:find('[%c,;/]') then return nil,0 end
            names[#names+1]=spell.name
        end
    end
    if #names==0 then return nil,0 end
    local macro='/castsequence reset=6 '..table.concat(names,', ')
    if #macro>255 then return nil,#names end
    return macro,#names
end
