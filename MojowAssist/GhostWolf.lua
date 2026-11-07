local _,NS=...
local Wolf={}
Wolf.__index=Wolf
NS.GhostWolf=Wolf

local function readable(value)
    assert(not (issecretvalue and issecretvalue(value)),'Spellbook value unavailable')
    return value
end

local function count(value)
    value=readable(value)
    assert(type(value)=='number' and value>=0 and value<=10000 and value==math.floor(value),'Spellbook count unavailable')
    return value
end

-- A complete readable negative is different from an incomplete spellbook.
function Wolf:Learned(name)
    if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
        local bank=Enum.SpellBookSpellBank.Player
        for index=1,count(C_SpellBook.GetNumSpellBookSkillLines()) do
            local line=readable(C_SpellBook.GetSpellBookSkillLineInfo(index))
            assert(type(line)=='table','Spellbook line unavailable')
            local offSpec=readable(line.offSpecID)
            assert(offSpec==nil or type(offSpec)=='number','Spellbook specialization unavailable')
            if not offSpec or offSpec==0 then
                local offset,size=count(line.itemIndexOffset),count(line.numSpellBookItems)
                for slot=offset+1,offset+size do
                    local item=readable(C_SpellBook.GetSpellBookItemInfo(slot,bank))
                    assert(type(item)=='table' and readable(item.itemType)~=nil,'Spellbook entry unavailable')
                    if item.itemType==Enum.SpellBookItemType.Spell and not readable(item.isPassive) then
                        local id=readable(item.spellID) or readable(item.actionID)
                        assert(type(id)=='number' and id>0,'Spellbook spell ID unavailable')
                        if id==2645 then return true end
                        local bookName
                        if C_SpellBook.GetSpellBookItemName then bookName=C_SpellBook.GetSpellBookItemName(slot,bank) end
                        if bookName==nil and C_Spell and C_Spell.GetSpellInfo then
                            local info=readable(C_Spell.GetSpellInfo(id))
                            bookName=info and info.name
                        end
                        bookName=readable(bookName)
                        assert(type(bookName)=='string' and bookName~='','Spellbook name unavailable')
                        if bookName==name then return true end
                    end
                end
            end
        end
        return false
    end
    assert(type(IsSpellKnown)=='function','Learned spell API unavailable')
    local known=readable(IsSpellKnown(2645))
    assert(type(known)=='boolean','Learned spell result unavailable')
    return known
end

function Wolf:Configure()
    if not self.button or InCombatLockdown() then return end
    if self.anchor.SetClampRectInsets then
        local left,right,top,bottom=0,0,0,0
        if self.anchor.GetClampRectInsets then left,right,top,bottom=self.anchor:GetClampRectInsets() end
        -- Positive right/top offsets extend the clamped footprint beyond the shield.
        if self.addon.shield and self.addon.shield.nativeDisplay then top=math.max(top,48) end
        self.anchor:SetClampRectInsets(left,math.max(right,180),top,bottom)
    end
    local infoOK,spell=pcall(function()
        if C_Spell and C_Spell.GetSpellInfo then return C_Spell.GetSpellInfo(2645) end
        if GetSpellInfo then local name,_,icon=GetSpellInfo(2645); return {name=name,iconID=icon} end
    end)
    local readable=infoOK and not (issecretvalue and issecretvalue(spell)) and type(spell)=='table'
        and not (issecretvalue and issecretvalue(spell.name)) and type(spell.name)=='string' and spell.name~=''
    local ok,known=false,nil
    if readable then ok,known=pcall(self.Learned,self,spell.name) end
    self.discoveryFailed=not readable or not ok
    self.known=not self.discoveryFailed and known==true
    self.button:SetAttribute('type1',self.known and 'spell' or nil)
    self.button:SetAttribute('spell',self.known and spell.name or nil)
    self.button:SetAttribute('unit','player')
    if readable then self.icon:SetTexture(spell.iconID) end
    self:Update()
end

function Wolf:Update()
    if not self.button then return end
    if not self.known then
        self.status:SetText(self.discoveryFailed and 'Lookup unavailable' or 'Not learned')
        self.button:SetBackdropBorderColor(0.3,0.3,0.3,1)
        return
    end
    local ok,form=pcall(function() assert(type(GetShapeshiftFormID)=='function'); return GetShapeshiftFormID() end)
    if not ok or (issecretvalue and issecretvalue(form)) or (form~=nil and type(form)~='number') then
        self.status:SetText('Status unavailable')
        self.button:SetBackdropBorderColor(0.25,0.55,0.7,1)
    elseif form==16 then
        self.status:SetText('Active - click to exit')
        self.button:SetBackdropBorderColor(0.35,1,0.45,1)
    else
        self.status:SetText('Click to transform')
        self.button:SetBackdropBorderColor(0.25,0.55,0.7,1)
    end
end

function Wolf:Create(addon,anchor)
    local self=setmetatable({addon=addon,anchor=anchor},Wolf)
    if not anchor then return self end
    local button=CreateFrame('Button','MojowGhostWolfButton',anchor,'SecureActionButtonTemplate,BackdropTemplate')
    self.button=button
    button:SetSize(174,48)
    button:SetPoint('LEFT',anchor,'RIGHT',6,0)
    button:RegisterForClicks('AnyDown','AnyUp')
    button:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    NS.Appearance:Background(button,0.025,0.035,0.05,0.94)
    button:SetHighlightTexture('Interface\\Buttons\\ButtonHilight-Square','ADD')
    self.icon=button:CreateTexture(nil,'ARTWORK')
    self.icon:SetSize(36,36); self.icon:SetPoint('LEFT',button,'LEFT',6,0)
    local title=button:CreateFontString(nil,'OVERLAY','GameFontNormalSmall')
    title:SetPoint('TOPLEFT',button,'TOPLEFT',48,-8); title:SetText('Ghost Wolf')
    self.status=button:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    self.status:SetPoint('TOPLEFT',button,'TOPLEFT',48,-26)
    self.status:SetWidth(120); self.status:SetWordWrap(false)
    button:SetScript('OnEnter',function()
        if not GameTooltip then return end
        GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
        if GameTooltip.SetSpellByID then GameTooltip:SetSpellByID(2645) else GameTooltip:AddLine('Ghost Wolf') end
        GameTooltip:AddLine('Left-click: toggle Ghost Wolf',1,1,1)
        GameTooltip:AddLine('Moves with your shield button.',0.7,0.7,0.7)
        GameTooltip:Show()
    end)
    button:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    self.events=CreateFrame('Frame')
    for _,event in ipairs({'SPELLS_CHANGED','PLAYER_REGEN_ENABLED','UPDATE_SHAPESHIFT_FORM','UPDATE_SHAPESHIFT_FORMS'}) do self.events:RegisterEvent(event) end
    self.events:SetScript('OnEvent',function(_,event)
        if event=='SPELLS_CHANGED' or event=='PLAYER_REGEN_ENABLED' then self:Configure() else self:Update() end
    end)
    self:Configure()
    return self
end
