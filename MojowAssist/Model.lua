-- Mojow Assist | 0.2.1-test | By Mojow
local _, NS = ...
local Model = {}
NS.Model = Model
Model.HealingSpellIDs={331,8004,1064,61295,974,526,2870,51886}
Model.EnemySpellIDs={403,8042,8050,8056,421,370}
function Model:HealingChoice(id,default,enemy)
    if id==0 then return 0 end
    for _,known in ipairs(enemy and self.EnemySpellIDs or self.HealingSpellIDs) do if id==known then return id end end
    return default
end

function Model:ValidateName(name)
    if type(name) ~= 'string' or #name < 3 or #name > 160 then return false end
    -- Character names and realm names have different punctuation rules.
    local character, realm = name:match('^([^-]+)%-(.+)$')
    if not character or character:find('[%s%c%p]') then return false end
    if realm:find("^[-']") or realm:find("[-']$") or realm:find('--', 1, true) then return false end
    local letters = realm:gsub("[-']", '')
    return letters ~= '' and not letters:find('[%s%c%p]')
end

local function number(value, default, low, high)
    if type(value) ~= 'number' or value ~= value or value == math.huge or value == -math.huge then return default end
    return math.max(low, math.min(high, value))
end

local function totemSelection(value)
    local result={}
    if type(value)=='table' then
        for slot=1,4 do
            local id=value[slot]
            if type(id)=='number' and id>0 and id<10000000 and id==math.floor(id) then result[slot]=id end
        end
    end
    return result
end

function Model:Normalize(saved)
    if type(saved) ~= 'table' then saved = {} end
    local presets={}
    if type(saved.totemPresets)=='table' then
        for index=1,3 do
            if type(saved.totemPresets[index])=='table' then presets[index]=totemSelection(saved.totemPresets[index]) end
        end
    end
    local restore={}
    if type(saved.nameplateRestore)=='table' then
        for key,entry in pairs(saved.nameplateRestore) do
            if type(key)=='string' and key:match('^nameplate%a+$') and type(entry)=='table'
                and type(entry.before)=='string' and tonumber(entry.before)
                and type(entry.applied)=='string' and tonumber(entry.applied) then
                restore[key]={before=entry.before,applied=entry.applied}
            end
        end
    end
    return {
        nameplateRestore=restore,
        nameplateBadges=saved.nameplateBadges==true,
        schema = 1,
        markerBarVisible = saved.markerBarVisible~=false,
        markerBarX = number(saved.markerBarX,0,-4000,4000),
        markerBarY = number(saved.markerBarY,-240,-4000,4000),
        autoFindMinerals = type(saved.autoFindMinerals)~='boolean' or saved.autoFindMinerals,
        windowTransparency = number(saved.windowTransparency, 0, 0, 100),
        enemyLeftID = self:HealingChoice(saved.enemyLeftID,403,true),
        enemyRightID = self:HealingChoice(saved.enemyRightID,8042,true),
        healLeftID = self:HealingChoice(saved.healLeftID,331),
        healRightID = self:HealingChoice(saved.healRightID,8004),
        mode = (saved.mode == 'auto' or saved.mode == 'focus' or saved.mode == 'group') and saved.mode or (self:ValidateName(saved.master) and 'group' or 'auto'),
        minimapAngle = number(saved.minimapAngle, 225, -3600, 3600) % 360,
        master = self:ValidateName(saved.master) and saved.master or nil,
        scale = number(saved.scale, 0.7, 0.7, 1.6),
        x = number(saved.x, 0, -4000, 4000),
        y = number(saved.y, 160, -4000, 4000),
        locked = type(saved.locked) ~= 'boolean' or saved.locked,
        visible = type(saved.visible) ~= 'boolean' or saved.visible,
        followLeader = type(saved.followLeader) ~= 'boolean' or saved.followLeader,
        enemyVisible = type(saved.enemyVisible) ~= 'boolean' or saved.enemyVisible,
        enemyShowGroup = type(saved.enemyShowGroup) ~= 'boolean' or saved.enemyShowGroup,
        enemyShowNPCs = type(saved.enemyShowNPCs) ~= 'boolean' or saved.enemyShowNPCs,
        enemyShowEnemyPlayers = type(saved.enemyShowEnemyPlayers) ~= 'boolean' or saved.enemyShowEnemyPlayers,
        enemyShowFriendlyPlayers = type(saved.enemyShowFriendlyPlayers) ~= 'boolean' or saved.enemyShowFriendlyPlayers,
        enemyX = number(saved.enemyX, 300, -4000, 4000),
        enemyY = number(saved.enemyY, 100, -4000, 4000),
        enemyScale = number(saved.enemyScale, 1, 0.7, 1.6),
        groupX = number(saved.groupX, math.max(-4000,number(saved.enemyX,300,-4000,4000)-250), -4000, 4000),
        groupY = number(saved.groupY, number(saved.enemyY,100,-4000,4000), -4000, 4000),
        groupNativePoison = saved.groupNativePoison == true,
        groupScale = number(saved.groupScale, number(saved.enemyScale,1,0.7,1.6), 0.7, 1.6),
        shieldSpellID = saved.shieldSpellID==52127 and 52127 or 324,
        shieldX = number(saved.shieldX, 0, -4000, 4000),
        shieldY = number(saved.shieldY, -200, -4000, 4000),
        totemVisible = type(saved.totemVisible) ~= 'boolean' or saved.totemVisible,
        totemExpanded = saved.totemExpanded == true,
        totemTopLeft = saved.totemTopLeft == true,
        totemX = number(saved.totemX, -250, -4000, 4000),
        totemY = number(saved.totemY, 0, -4000, 4000),
        totemFavorites = totemSelection(saved.totemFavorites),
        totemPresets = presets,
    }
end

function Model:Encode(master)
    if self:ValidateName(master) then return '1|SET|' .. master end
end

function Model:Decode(message, sender, leader, roster)
    if type(message) ~= 'string' or #message > 200 or not leader or sender ~= leader then return nil end
    local master = message:match('^1|SET|([^|]+)$')
    if self:ValidateName(master) and roster[master] and roster[sender] then return master end
end
