local _,NS=...
local Shield={}
Shield.__index=Shield
NS.ShieldHelper=Shield

local function secret(value)
    return issecretvalue and issecretvalue(value) or false
end

local function info(id)
    if C_Spell and C_Spell.GetSpellInfo then return C_Spell.GetSpellInfo(id) end
    if GetSpellInfo then
        local name,_,icon=GetSpellInfo(id)
        if name then return {name=name,iconID=icon} end
    end
end

-- Resolve learned entries from their displayed spellbook names, even when the
-- spell database has no metadata for a historical base ID or current rank.
function Shield:FromBook(names)
    local found,ids=nil,{}
    local bank=Enum.SpellBookSpellBank.Player
    for lineIndex=1,C_SpellBook.GetNumSpellBookSkillLines() do
        local line=C_SpellBook.GetSpellBookSkillLineInfo(lineIndex)
        if line and (not line.offSpecID or line.offSpecID==0) then
            for index=line.itemIndexOffset+1,line.itemIndexOffset+line.numSpellBookItems do
                local item=C_SpellBook.GetSpellBookItemInfo(index,bank)
                if item and item.itemType==Enum.SpellBookItemType.Spell and not item.isPassive then
                    local id=item.spellID or item.actionID
                    if secret(id) or type(id)~='number' then error('Learned spell ID unavailable') end
                    local ok,spell=pcall(info,id)
                    spell=ok and spell or nil
                    local name
                    if C_SpellBook.GetSpellBookItemName then name=C_SpellBook.GetSpellBookItemName(index,bank) end
                    if name==nil and spell then name=spell.name end
                    if secret(name) or type(name)~='string' then error('Learned spell name unavailable') end
                    if names[name] then
                        local icon=spell and spell.iconID
                        if not icon and C_SpellBook.GetSpellBookItemTexture then
                            local iconOK,value=pcall(C_SpellBook.GetSpellBookItemTexture,index,bank)
                            if iconOK and not secret(value) then icon=value end
                        end
                        found={name=name,iconID=icon,spellID=id}
                        ids[id]=true
                    end
                end
            end
        end
    end
    return found,ids
end

-- The saved value identifies the shield choice, not a required runtime spell ID.
function Shield:Discover(choice)
    local first,names,candidates=nil,{},{}
    for _,id in ipairs(choice==52127 and {52127,24398} or {324}) do
        local ok,spell=pcall(info,id)
        if ok and spell and not secret(spell.name) and type(spell.name)=='string' then
            first=first or spell
            names[spell.name]=true
            candidates[#candidates+1]={id=id,spell=spell}
        end
    end
    if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
        -- Exact English labels are used only for English clients when metadata
        -- is missing; the actual learned entry supplies the cast name and ID.
        local localeOK,locale=pcall(function() return GetLocale and GetLocale() end)
        if localeOK and (locale=='enUS' or locale=='enGB') then
            names[choice==52127 and 'Water Shield' or 'Lightning Shield']=true
        end
        if not next(names) then return nil,nil,nil,'No readable shield names' end
        local ok,spell,ids=pcall(self.FromBook,self,names)
        if not ok then return first,nil,nil,tostring(spell) end
        return spell or first,spell~=nil,ids,spell and ('Spellbook ID '..spell.spellID) or 'No learned matching spellbook entry'
    end
    local uncertain=false
    for _,candidate in ipairs(candidates) do
        local ok,known=pcall(function() return IsSpellKnown and IsSpellKnown(candidate.id) end)
        if ok and not secret(known) and known==true then
            return candidate.spell,true,{[candidate.id]=true},'Known spell ID '..candidate.id
        elseif not ok or secret(known) or known==nil then uncertain=true end
    end
    if first and not uncertain then return first,false,nil,'Known-ID fallback reports unlearned' end
    return first,nil,nil,'Spellbook unavailable; known-ID fallback did not find shield'
end

function Shield:Configure()
    if not self.button or InCombatLockdown() then return end
    self.spellID=self.addon.db.shieldSpellID==52127 and 52127 or 324
    local spell,known,ids=self:Discover(self.spellID)
    self.name=spell and spell.name or nil
    self.shieldSpellIDs=ids or {[self.spellID]=true}
    self.known=known==true and self.name~=nil
    self.discoveryFailed=known==nil or not self.name
    self.button:SetAttribute('type1',self.known and 'spell' or nil)
    self.button:SetAttribute('spell',self.name)
    self.button:SetAttribute('unit','player')
    self.title:SetText(self.name or 'Shield')
    if spell then self.icon:SetTexture(spell.iconID) end
    if NS.NativeShieldDisplay and (self.known or self.nativeDisplay) then
        local filters=self.shieldSpellIDs
        if self.nativeDisplay then
            local configured,err=pcall(self.nativeDisplay.SetAuraSlotCandidateFilters,self.nativeDisplay,'lightningShield',{includeSpellIDs=filters})
            self.nativeError=not configured and tostring(err) or nil
            if not configured then self.nativeDisplay:Hide(); self.nativeDisplay=nil end
        else
            self.nativeDisplay,self.nativeError=NS.NativeShieldDisplay:Create(self.button,filters,self.name)
        end
    end
    if self.nativeDisplay and self.nativeDisplay.shieldTitle then self.nativeDisplay.shieldTitle:SetText(self.name or 'Shield') end
    local otherSpell=self:Discover(self.spellID==52127 and 324 or 52127)
    self.otherName=otherSpell and otherSpell.name or nil
    self:Update()
end

function Shield:Cycle()
    local function report(message)
        if self.addon.Say then self.addon:Say(message) end
    end
    if not self.button then return false end
    if InCombatLockdown() then report('Switch shields outside combat.'); return false end
    local id=self.spellID==52127 and 324 or 52127
    local spell,known=self:Discover(id)
    local name=spell and spell.name or (id==52127 and 'Water Shield' or 'Lightning Shield')
    if known~=true then
        report(known==false and name..' is not learned.' or name..' lookup unavailable. Try /mja shield debug.')
        return false
    end
    self.addon.db.shieldSpellID=id
    self:Configure()
    report((self.name or name)..' selected. Left-click to cast.')
    return true
end

function Shield:RememberAura(name,aura)
    local id=aura.auraInstanceID
    if not secret(id) and type(id)=='number' then
        self.auraInstances=self.auraInstances or {}
        self.auraInstances[name]=id
    end
    return aura,true
end

function Shield:Aura(name)
    if not name or not C_UnitAuras then return nil,false end
    local api=C_UnitAuras.GetAuraDataBySpellName
    local ok,aura=false,nil
    if api then ok,aura=pcall(api,'player',name,'HELPFUL') end
    local nameReadable=ok and not secret(aura)
    if nameReadable and aura then return self:RememberAura(name,aura) end

    -- Re-query an ID observed from a readable matching aura. Never retain an
    -- old presence flag or guess charges after the client stops exposing it.
    local id=self.auraInstances and self.auraInstances[name]
    if id and C_UnitAuras.GetAuraDataByAuraInstanceID then
        local found,current=pcall(C_UnitAuras.GetAuraDataByAuraInstanceID,'player',id)
        if found and not secret(current) and current then return current,true end
    end

    local scan=C_UnitAuras.GetAuraDataByIndex
    if scan then
        local restricted=false
        for index=1,255 do
            local found,current=pcall(scan,'player',index,'HELPFUL')
            if not found or secret(current) then return nil,false end
            if not current then
                if not restricted and self.auraInstances then self.auraInstances[name]=nil end
                return nil,not restricted
            end
            local currentName=current.name
            if secret(currentName) or type(currentName)~='string' then restricted=true
            elseif currentName==name then return self:RememberAura(name,current) end
        end
        return nil,false
    end
    -- A missing named result in combat is not proof of buff absence.
    return nil,nameReadable and not InCombatLockdown()
end

function Shield:Debug()
    local say=function(message) self.addon:Say(message) end
    local describe=function(ok,value)
        if not ok then return 'error' end
        if secret(value) then return 'restricted' end
        return value and 'present' or 'empty'
    end
    say('Shield: combat='..tostring(InCombatLockdown())..', learned='..tostring(not not self.known))
    for _,id in ipairs({324,52127}) do
        local spell,known,_,detail=self:Discover(id)
        say('Shield option '..(spell and spell.name or tostring(id))..': '..(known==true and 'learned' or known==false and 'not learned' or 'lookup unavailable')..' | '..(detail or 'No details'))
    end
    say('Native shield display: '..(self.nativeDisplay and 'configured' or 'unavailable')..(self.nativeError and ' | '..self.nativeError or ''))
    local api=C_UnitAuras or {}
    if self.name and api.GetAuraDataBySpellName then
        say('Shield name lookup: '..describe(pcall(api.GetAuraDataBySpellName,'player',self.name,'HELPFUL')))
    else say('Shield name lookup: unavailable API/name') end
    local id=self.name and self.auraInstances and self.auraInstances[self.name]
    if id and api.GetAuraDataByAuraInstanceID then
        say('Shield cached instance: '..describe(pcall(api.GetAuraDataByAuraInstanceID,'player',id)))
    else say('Shield cached instance: none') end
    if not api.GetAuraDataByIndex then say('Shield buff scan: unavailable API'); return end
    local total,names,ids=0,0,0
    local outcome='limit'
    for index=1,255 do
        local ok,aura=pcall(api.GetAuraDataByIndex,'player',index,'HELPFUL')
        if not ok or secret(aura) then outcome=describe(ok,aura); break end
        if not aura then outcome='end'; break end
        total=total+1
        if not secret(aura.name) and type(aura.name)=='string' then names=names+1 end
        if not secret(aura.spellId) and type(aura.spellId)=='number' then ids=ids+1 end
    end
    say('Shield buff scan: '..total..' entries, '..names..' readable names, '..ids..' readable spell IDs; '..outcome)
end

function Shield:Update()
    if not self.button then return end
    if not self.known then
        self.status:SetText(self.discoveryFailed and 'Spell lookup unavailable' or 'Learn '..(self.name or 'selected shield'))
        self.status:SetTextColor(0.7,0.7,0.7)
        return
    end
    if InCombatLockdown() then
        self.status:SetText(self.nativeDisplay and 'Live shield icon shown above' or 'Shield status hidden in combat')
        self.status:SetTextColor(0.7,0.85,1)
        return
    end
    local aura,readable=self:Aura(self.name)
    if not readable then
        self.status:SetText('Shield status unavailable')
        self.status:SetTextColor(0.7,0.7,0.7)
    elseif aura then
        local detail='Active'
        local charges=aura.applications
        if not secret(charges) and type(charges)=='number' and charges>0 then detail=detail..' | '..charges..' charges' end
        local expires=aura.expirationTime
        if not secret(expires) and type(expires)=='number' and expires>0 then
            local remaining=math.max(0,expires-GetTime())
            detail=detail..string.format(' | %d:%02d',math.floor(remaining/60),math.floor(remaining%60))
        end
        self.status:SetText(detail)
        self.status:SetTextColor(0.35,1,0.45)
    else
        local other,otherKnown=self:Aura(self.otherName)
        if otherKnown and other then
            self.status:SetText(self.otherName..' active')
            self.status:SetTextColor(0.35,0.8,1)
        else
            self.status:SetText('MISSING - click to cast')
            self.status:SetTextColor(1,0.55,0.15)
        end
    end
end

function Shield:Create(addon)
    local self=setmetatable({addon=addon},Shield)
    local ok,_,class=pcall(UnitClass,'player')
    if not ok or secret(class) or class~='SHAMAN' then return self end
    local button=CreateFrame('Button','MojowLightningShieldButton',UIParent,'SecureActionButtonTemplate,BackdropTemplate')
    self.button=button
    button:SetSize(240,48)
    button:SetPoint('CENTER',UIParent,'CENTER',addon.db.shieldX,addon.db.shieldY)
    button:SetClampedToScreen(true)
    button:SetMovable(true)
    button:RegisterForClicks('AnyDown','AnyUp')
    button:RegisterForDrag('RightButton')
    button:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
    NS.Appearance:Background(button,0.025,0.035,0.05,0.94)
    button:SetBackdropBorderColor(0.25,0.55,0.7,1)
    button:SetHighlightTexture('Interface\\Buttons\\ButtonHilight-Square','ADD')
    self.icon=button:CreateTexture(nil,'ARTWORK')
    self.icon:SetSize(36,36)
    self.icon:SetPoint('LEFT',button,'LEFT',6,0)
    self.title=button:CreateFontString(nil,'OVERLAY','GameFontNormalSmall')
    self.title:SetPoint('TOPLEFT',button,'TOPLEFT',48,-8)
    self.title:SetWidth(160); self.title:SetWordWrap(false)
    self.title:SetText('Lightning Shield')
    self.status=button:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    self.status:SetPoint('TOPLEFT',button,'TOPLEFT',48,-26)
    button:SetScript('OnEnter',function()
        if GameTooltip then
            GameTooltip:SetOwner(button,'ANCHOR_RIGHT')
            GameTooltip:AddLine(self.name or 'Shield')
            GameTooltip:AddLine('Left-click: cast on yourself',1,1,1)
            GameTooltip:AddLine('Right-click: switch learned shields outside combat',1,1,1,true)
            GameTooltip:AddLine('Right-drag: move outside combat',1,1,1)
            GameTooltip:Show()
        end
    end)
    button:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    button:SetScript('OnMouseDown',function() self.dragged=false end)
    button:SetScript('OnMouseUp',function(_,mouseButton)
        if mouseButton=='RightButton' and not self.dragged then self:Cycle() end
    end)
    button:SetScript('OnDragStart',function()
        self.dragged=true
        if not InCombatLockdown() then button:StartMoving(); self.moving=true end
    end)
    button:SetScript('OnDragStop',function()
        if not InCombatLockdown() and self.moving then
            button:StopMovingOrSizing(); self.moving=false
            local x,y=button:GetCenter()
            local cx,cy=UIParent:GetCenter()
            addon.db.shieldX,addon.db.shieldY=x-cx,y-cy
        end
    end)
    -- A separate ordinary button keeps selection independent of secure cast clicks.
    self.switch=CreateFrame('Button',nil,button,'UIPanelButtonTemplate')
    self.switch:SetSize(20,20)
    self.switch:SetPoint('TOPRIGHT',button,'TOPRIGHT',-4,-4)
    self.switch:SetText('>')
    self.switch:SetScript('OnClick',function() self:Cycle() end)
    self.switch:SetScript('OnEnter',function()
        if GameTooltip then
            GameTooltip:SetOwner(self.switch,'ANCHOR_RIGHT')
            GameTooltip:AddLine('Switch shield')
            GameTooltip:AddLine('Choose the other learned shield outside combat.',1,1,1,true)
            GameTooltip:AddLine('Then left-click the shield icon to cast.',0.7,0.7,0.7,true)
            GameTooltip:Show()
        end
    end)
    self.switch:SetScript('OnLeave',function() if GameTooltip then GameTooltip:Hide() end end)
    self.events=CreateFrame('Frame')
    for _,event in ipairs({'UNIT_AURA','SPELLS_CHANGED','PLAYER_REGEN_ENABLED','PLAYER_REGEN_DISABLED'}) do self.events:RegisterEvent(event) end
    self.events:SetScript('OnEvent',function(_,event,unit)
        if event=='PLAYER_REGEN_DISABLED' then
            if self.moving then
                local stopped=pcall(button.StopMovingOrSizing,button)
                if stopped then self.moving=false end
            end
        elseif event=='UNIT_AURA' then
            if unit=='player' then self:Update() end
        else
            if event=='PLAYER_REGEN_ENABLED' and self.moving then button:GetScript('OnDragStop')() end
            self:Configure()
        end
    end)
    local elapsed=0
    self.events:SetScript('OnUpdate',function(_,delta)
        elapsed=elapsed+delta
        if elapsed>=0.5 then elapsed=0; self:Update() end
    end)
    self:Configure()
    return self
end
