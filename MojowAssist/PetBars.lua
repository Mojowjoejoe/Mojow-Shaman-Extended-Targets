-- Owner-side companions. Only stable roster pets receive secure heal bindings.
local _,NS=...
local Pets={}
NS.PetBars=Pets
local WIDTH,HEIGHT=146,36

function Pets:StablePet(owner)
    if type(owner)~='string' then return end
    if owner=='player' then return 'pet' end
    if owner:match('^party[1-4]$') then return 'partypet'..owner:sub(6) end
    local index=tonumber(owner:match('^raid(%d+)$'))
    if index and index>=1 and index<=40 and owner=='raid'..index then return 'raidpet'..index end
end

function Pets:Owned(panel,owner,pet)
    local r=panel.roster
    if r:Read(UnitIsOtherPlayersPet,pet)~=true then return false end
    if r:Read(UnitIsOwnerOrControllerOfUnit,owner,pet)==true then return true end
    local ownerGUID=r:Read(UnitGUID,owner)
    local petOwner=r:Read(UnitOwnerGUID,pet)
    return type(ownerGUID)=='string' and ownerGUID~='' and type(petOwner)=='string' and ownerGUID==petOwner
end

function Pets:Find(panel,owner)
    if not owner then return end
    local r=panel.roster
    if r:Read(UnitCanAttack,'player',owner)==true then return end
    local pet=self:StablePet(owner)
    if pet then return pet,true end
    if r:Read(UnitIsPlayer,owner)~=true then return end
    -- Resolve nameplate aliases to player/party/raid owners, never target/focus.
    local resolved=NS.NearbyHealing and NS.NearbyHealing:Resolve(owner)
    pet=self:StablePet(resolved)
    if pet then return pet,true end
    for _,unit in ipairs(panel.roster.order) do
        if r:Read(UnitExists,unit)==true and self:Owned(panel,owner,unit) then return unit,false end
    end
end

local function label(parent,x,y,width)
    local value=parent:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    value:SetPoint('TOPLEFT',parent,'TOPLEFT',x,y)
    value:SetWidth(width); value:SetJustifyH('LEFT'); value:SetWordWrap(false)
    value:SetFont(STANDARD_TEXT_FONT or 'Fonts\\FRIZQT__.TTF',11,'OUTLINE')
    return value
end

function Pets:Create(panel,row)
    if InCombatLockdown() then return end
    local bar=CreateFrame(panel.clickHealing and 'Button' or 'Frame',nil,row,
        panel.clickHealing and 'SecureActionButtonTemplate,BackdropTemplate' or 'BackdropTemplate')
    bar:SetSize(WIDTH,HEIGHT)
    bar:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    bar:SetBackdropBorderColor(0.2,0.5,0.6,1)
    NS.Appearance:Background(bar,0.025,0.035,0.05,0.94)
    bar.health=CreateFrame('StatusBar',nil,bar)
    bar.health:SetPoint('TOPLEFT',bar,'TOPLEFT',2,-2); bar.health:SetSize(WIDTH-4,18)
    bar.health:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    bar.health:SetStatusBarColor(0.12,0.4,0.65,0.85)
    bar.name=label(bar.health,2,-2,WIDTH-50)
    bar.value=label(bar.health,WIDTH-48,-2,42)
    bar.status=label(bar,4,-22,WIDTH-8)
    bar.status:SetTextColor(0.65,0.85,0.95)
    if panel.clickHealing then bar:RegisterForClicks('AnyDown','AnyUp') end
    bar:SetScript('OnEnter',function()
        if not GameTooltip then return end
        GameTooltip:SetOwner(bar,'ANCHOR_RIGHT')
        GameTooltip:AddLine(bar.tooltipName or 'Pet',0.65,0.85,1)
        GameTooltip:AddLine(bar.status:GetText(),1,1,1)
        if bar.healable then
            GameTooltip:AddLine('Left-click: '..(bar.left or 'Disabled'),1,1,1)
            GameTooltip:AddLine('Right-click: '..(bar.right or 'Disabled'),1,1,1)
            GameTooltip:AddLine('Uses this owner\'s exact pet. Range and line of sight still apply.',0.8,0.8,0.8,true)
        else
            GameTooltip:AddLine('Display only: no stable party/raid pet target is available.',0.8,0.8,0.8,true)
        end
        GameTooltip:Show()
    end)
    bar:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    bar:Hide(); row.petBar=bar
    return bar
end

function Pets:Position(panel,row,bar)
    local left=false
    if type(panel.frame.GetRight)=='function' and type(UIParent.GetRight)=='function' then
        local edge,screen=panel.frame:GetRight(),UIParent:GetRight()
        if edge and screen then
            left=(edge+WIDTH+8)*panel.frame:GetEffectiveScale()>screen*UIParent:GetEffectiveScale()
        end
    end
    bar:ClearAllPoints()
    bar:SetPoint(left and 'TOPRIGHT' or 'TOPLEFT',row,left and 'TOPLEFT' or 'TOPRIGHT',left and -8 or 8,0)
end

function Pets:Bind(panel,row,owner)
    if InCombatLockdown() then return false end
    local pet,stable=self:Find(panel,owner)
    local bar=row.petBar
    if not bar and not pet then return false end
    bar=bar or self:Create(panel,row)
    if not bar then return false end
    self:Position(panel,row,bar)
    local healable=not not (stable and panel.clickHealing)
    local left,right=panel.healLeft,panel.healRight
    local changed=bar.petUnit~=pet or bar.ownerUnit~=owner or bar.healable~=healable or bar.left~=left or bar.right~=right
    if changed then
        if bar.watching and type(UnregisterUnitWatch)=='function' then UnregisterUnitWatch(bar) end
        bar.watching=false
        bar.petUnit,bar.ownerUnit,bar.stable,bar.healable=pet,owner,stable,healable
        bar.left,bar.right=left,right
        if panel.clickHealing then
            bar:SetAttribute('unit',healable and pet or 'none')
            for index,entry in ipairs({{'petLeft',left},{'petRight',right}}) do
                local action,spell=entry[1],entry[2]
                -- Learned spell names are obtained by NearbyHealing. A conditional
                -- exact-pet cast cannot fall back to the current target or player.
                local macro=healable and type(spell)=='string' and spell~='' and not spell:find('[\r\n]')
                    and ('/cast [@'..pet..',exists,help,nodead] '..spell) or nil
                bar:SetAttribute('type'..index,nil)
                bar:SetAttribute('helpbutton'..index,macro and action or nil)
                bar:SetAttribute('type-'..action,macro and 'macro' or nil)
                bar:SetAttribute('macrotext-'..action,macro)
            end
            if healable and type(RegisterUnitWatch)=='function' then
                RegisterUnitWatch(bar); bar.watching=true
            end
        end
    end
    if not bar.watching then
        if pet and panel.roster:Read(UnitExists,pet)==true then bar:Show() else bar:Hide() end
    end
    return pet~=nil
end

function Pets:Update(panel,row)
    local bar=row.petBar
    if not bar then return end
    local r,unit=panel.roster,bar.petUnit
    local valid=unit and r:Read(UnitExists,unit)==true
    if valid and not bar.stable then valid=self:Owned(panel,bar.ownerUnit,unit) end
    if not valid then
        bar.name:SetText('Pet unavailable'); bar.value:SetText('')
        bar.status:SetText('Pet unavailable'); bar.tooltipName=nil
        bar.health:SetMinMaxValues(0,1); bar.health:SetValue(0); bar.health:SetAlpha(1)
        return
    end
    local name=r:Read(UnitName,unit)
    bar.tooltipName=type(name)=='string' and name or 'Pet'
    bar.name:SetText(bar.tooltipName)
    panel:Health(bar,unit)
    local dead=r:Read(UnitIsDeadOrGhost,unit)==true
    local status='Pet - display only'
    local alpha=1
    if dead then status='Pet - dead'
    elseif bar.healable then
        local spell=bar.left or bar.right
        if spell then
            local range=NS.NearbyHealing:Range(spell,unit)
            alpha=NS.NearbyHealing:RangeFade(spell,unit,false,range)
            status=range=='out' and 'Pet - out of range' or 'Pet - click to heal'
        else status='Pet - heals disabled' end
    end
    bar.health:SetAlpha(alpha); bar.status:SetText(status)
end
