local _,NS=...
local Healing={}
NS.NearbyHealing=Healing

local function info(id)
    if C_Spell and C_Spell.GetSpellInfo then return C_Spell.GetSpellInfo(id) end
    if GetSpellInfo then local name=GetSpellInfo(id); if name then return {name=name} end end
end

function Healing:Enabled()
    local ok,_,class=pcall(UnitClass,'player')
    return ok and not (issecretvalue and issecretvalue(class)) and class=='SHAMAN'
end

function Healing:Learned(id)
    if id==0 then return end
    local spell=info(id)
    if not spell or type(spell.name)~='string' then return end
    if C_SpellBook and C_SpellBook.GetNumSpellBookSkillLines then
        for i=1,C_SpellBook.GetNumSpellBookSkillLines() do
            local line=C_SpellBook.GetSpellBookSkillLineInfo(i)
            if line and (not line.offSpecID or line.offSpecID==0) then
                for index=line.itemIndexOffset+1,line.itemIndexOffset+line.numSpellBookItems do
                    local item=C_SpellBook.GetSpellBookItemInfo(index,Enum.SpellBookSpellBank.Player)
                    if item and item.itemType==Enum.SpellBookItemType.Spell and not item.isPassive then
                        local learned=info(item.spellID)
                        if learned and learned.name==spell.name then return spell.name end
                    end
                end
            end
        end
    elseif IsSpellKnown and IsSpellKnown(id) then return spell.name end
end

function Healing:Spells(db)
    local leftOK,left=pcall(self.Learned,self,db and db.healLeftID or 331)
    local rightOK,right=pcall(self.Learned,self,db and db.healRightID or 8004)
    return leftOK and left or nil,rightOK and right or nil
end

function Healing:DamageSpells(db)
    local leftOK,left=pcall(self.Learned,self,db and db.enemyLeftID or 403)
    local rightOK,right=pcall(self.Learned,self,db and db.enemyRightID or 8042)
    return leftOK and left or nil,rightOK and right or nil
end

function Healing:Choose(panel,side,id,enemy)
    if InCombatLockdown() or (side~='left' and side~='right') then return false end
    if NS.Model:HealingChoice(id,-1,enemy)~=id then return false end
    local ok,name=pcall(self.Learned,self,id)
    if id~=0 and (not ok or not name) then return false end
    panel.addon.db[self:ChoiceKey(side,enemy)]=id
    panel.healsDirty=true; panel:Refresh()
    for _,key in ipairs({'enemies','groupMembers'}) do
        local other=panel.addon[key]
        if other and other~=panel then other.healsDirty=true; other:Refresh() end
    end
    return true
end

function Healing:ChoiceKey(side,enemy)
    if enemy then return side=='left' and 'enemyLeftID' or 'enemyRightID' end
    return side=='left' and 'healLeftID' or 'healRightID'
end

function Healing:BindingLabel(db,side,learned,enemy)
    local id=db[self:ChoiceKey(side,enemy)]
    if id==0 then return 'Disabled' end
    if learned then return learned end
    local infoOK,spell=pcall(info,id)
    return (infoOK and spell and spell.name or 'Selected spell')..' (unavailable)'
end

function Healing:Choices(enemy)
    local choices={{id=0,name='Disabled'}}
    for _,id in ipairs(enemy and NS.Model.EnemySpellIDs or NS.Model.HealingSpellIDs) do
        local ok,name=pcall(self.Learned,self,id)
        if ok and name then choices[#choices+1]={id=id,name=name} end
    end
    return choices
end

-- Nameplates are observation tokens, not spell targets. Use a matching supported token.
function Healing:Resolve(unit)
    local tokens={'player'}
    for i=1,4 do tokens[#tokens+1]='party'..i end
    for i=1,40 do tokens[#tokens+1]='raid'..i end
    tokens[#tokens+1]='target'; tokens[#tokens+1]='focus'
    for _,token in ipairs(tokens) do
        local ok,same=pcall(UnitIsUnit,unit,token)
        if ok and not (issecretvalue and issecretvalue(same)) and same==true then return token end
    end
end

local function readable(fn,...)
    if type(fn)~='function' then return end
    local ok,value=pcall(fn,...)
    if ok and not (issecretvalue and issecretvalue(value)) then return value end
end

local function safeText(value)
    return type(value)=='string' and #value>0 and #value<=160
        and not value:find('[%c%[%];/\\|]') and not value:find('^%s') and not value:find('%s$')
end

function Healing:TargetName(unit)
    if readable(UnitIsPlayer,unit)~=true or readable(UnitCanAttack,'player',unit)~=false then return end
    local ok,name,realm=pcall(UnitName,unit)
    if not ok or (issecretvalue and (issecretvalue(name) or issecretvalue(realm))) or not safeText(name) then return end
    if realm and realm~='' then
        if not safeText(realm) then return end
        name=name..'-'..realm
    end
    return name
end

function Healing:Macro(name,spell)
    if not safeText(name) or not safeText(spell) then return end
    -- Forever live testing: /target shortname works; /targetexact does not.
    local shortName=name:match('^([^-]+)')
    if not safeText(shortName) then return end
    return '/cleartarget\n/target '..shortName..'\n/cast [@target,exists,help,nodead] '..spell
end

-- Exact unit tokens only. Clear the previous target before selection so a failed
-- target operation cannot leave the cast aimed at a different, old target.
function Healing:EnemyMacro(unit,spell)
    if type(unit)~='string' or (unit~='focus' and unit~='focustarget' and not unit:match('^nameplate%d+$')) then return end
    if not safeText(spell) then return end
    local macro='/cleartarget\n/target [@'..unit..',exists,harm,nodead]\n/cast [@target,exists,harm,nodead] '..spell
    if #macro<=255 then return macro end
end

function Healing:GroupUnit(unit)
    if type(unit)~='string' then return end
    if unit=='player' or unit:match('^party[1-4]$') then return unit end
    local raid=tonumber(unit:match('^raid(%d+)$'))
    if raid and raid>=1 and raid<=40 and unit=='raid'..raid then return unit end
end

function Healing:FocusTargetMacro(spell)
    local macro='/cleartarget\n/target [@focustarget,exists]'
    if safeText(spell) then macro=macro..'\n/cast [@target,exists,harm,nodead] '..spell end
    return macro
end

function Healing:GroupMacro(unit,spell)
    if not self:GroupUnit(unit) or not safeText(spell) then return end
    -- Both commands use the same roster token: healing never falls back to an old target.
    local macro='/target [@'..unit..',exists]\n/cast [@'..unit..',exists,help,nodead] '..spell
    if #macro<=255 then return macro end
end

function Healing:Bind(row,unit,left,right,damageLeft,damageRight,fixedEnemy)
    if InCombatLockdown() then return end
    fixedEnemy=fixedEnemy and (unit=='target' or unit=='focustarget')
    row.focusTargetRow=not not (fixedEnemy and unit=='focustarget')
    local groupUnit=row.groupWindow and self:GroupUnit(unit)
    row.enemyRow=not groupUnit and (fixedEnemy or (unit and readable(UnitCanAttack,'player',unit)==true)) or false
    local resolved=groupUnit or (unit and self:Resolve(unit))
    if row.enemyRow then
        -- Attack only an exact supported alias. Never target duplicate NPC names.
        resolved=(fixedEnemy or unit=='target' or unit=='focus') and unit or nil
        if not resolved then
            for _,token in ipairs({'target','focus'}) do
                if readable(UnitIsUnit,unit,token)==true then resolved=token; break end
            end
        end
        left,right=nil,nil
    end
    local enemyMacro=row.focusTargetRow and self:FocusTargetMacro(damageLeft)
        or (row.enemyRow and self:EnemyMacro(resolved or unit,damageLeft))
    row.enemySelectCast=enemyMacro and true or false
    row.targetOnlyUnit=not enemyMacro and row.enemyRow and not resolved and type(unit)=='string' and unit:match('^nameplate%d+$') and unit or nil
    row.attackUnit=row.enemyRow and resolved or nil
    row.damageLeft,row.damageRight=damageLeft,damageRight
    row.hasEnemyAction=not not (enemyMacro or (row.attackUnit and (damageLeft or damageRight)))
    row.macroName=not row.enemyRow and not resolved and unit and self:TargetName(unit) or nil
    row.healUnit=not row.enemyRow and resolved or nil
    row.groupSelectUnit=row.groupWindow and row.healUnit and self:GroupUnit(row.healUnit) or nil
    local groupMacro=row.groupSelectUnit and self:GroupMacro(row.groupSelectUnit,left)
    row.boundUnit=resolved or unit
    local leftMacro=enemyMacro or groupMacro or (row.macroName and self:Macro(row.macroName,left))
    local rightMacro=row.macroName and self:Macro(row.macroName,right)
    row.hasHealingAction=not row.enemyRow and not not (leftMacro or rightMacro or (resolved and (left or right)))
    row:SetAttribute('type1',leftMacro and 'macro' or ((row.targetOnlyUnit or row.groupSelectUnit) and 'target' or nil))
    row:SetAttribute('macrotext1',leftMacro)
    local menuUnit=not row.enemyRow and resolved and unit and readable(UnitIsPlayer,unit)==true and readable(UnitCanAttack,'player',unit)==false and unit or nil
    row.menuUnit=menuUnit and resolved or nil
    row:SetAttribute('type2',rightMacro and 'macro' or nil)
    row:SetAttribute('unit2',menuUnit and (resolved or unit) or nil)
    row:SetAttribute('macrotext2',rightMacro)
    row:SetAttribute('shift-type2',menuUnit and 'togglemenu' or ((row.macroName or row.healUnit) and '' or nil))
    row:SetAttribute('shift-macrotext2',nil)
    if not resolved then left,right=nil,nil end
    local actionUnit=resolved or (enemyMacro and unit) or row.targetOnlyUnit
    if not actionUnit and not row.macroName then actionUnit='none' end
    row:SetAttribute('unit',actionUnit)
    -- Only the native helpful-unit remap can invoke a heal. No default action.
    row:SetAttribute('helpbutton1',row.healUnit and 'healLeft' or nil)
    row:SetAttribute('helpbutton2',row.healUnit and 'healRight' or nil)
    row:SetAttribute('type-healLeft',row.groupSelectUnit and (groupMacro and 'macro' or 'target') or (left and 'spell' or nil))
    row:SetAttribute('macrotext-healLeft',groupMacro)
    row:SetAttribute('spell-healLeft',left)
    row:SetAttribute('type-healRight',right and 'spell' or nil)
    row:SetAttribute('shift-type-healRight',menuUnit and 'togglemenu' or (row.healUnit and '' or nil))
    row:SetAttribute('spell-healRight',right)
    -- Native harm remaps prevent damaging a friendly unit if an alias changes.
    row:SetAttribute('harmbutton1',row.attackUnit and 'damageLeft' or nil)
    row:SetAttribute('harmbutton2',row.attackUnit and 'damageRight' or nil)
    row:SetAttribute('type-damageLeft',row.attackUnit and (row.focusTargetRow or damageLeft) and (enemyMacro and 'macro' or 'spell') or nil)
    row:SetAttribute('macrotext-damageLeft',row.attackUnit and enemyMacro or nil)
    row:SetAttribute('spell-damageLeft',row.attackUnit and damageLeft or nil)
    row:SetAttribute('type-damageRight',row.attackUnit and damageRight and 'spell' or nil)
    row:SetAttribute('spell-damageRight',row.attackUnit and damageRight or nil)
end

function Healing:Range(spell,unit)
    if not spell then return 'unavailable' end
    if type(unit)~='string' or unit=='' or unit=='none' then return 'unknown' end
    local api=C_Spell and C_Spell.IsSpellInRange or IsSpellInRange
    if type(api)~='function' then return 'unknown' end
    local ok,value=pcall(api,spell,unit)
    if not ok or (issecretvalue and issecretvalue(value)) then return 'unknown' end
    if value==true or value==1 then return 'in' end
    if value==false or value==0 then return 'out' end
    return 'unknown'
end

-- Keep restricted range values inside native UI evaluation. They are never
-- inspected for targeting, spell selection or textual status.
function Healing:RangeFade(spell,unit,group,state)
    if state=='in' then return 1,state,'spell' end
    if state=='out' then return 0.35,state,'spell' end
    local evaluate=C_CurveUtil and C_CurveUtil.EvaluateColorValueFromBoolean
    local api=C_Spell and C_Spell.IsSpellInRange or IsSpellInRange
    if spell and type(api)=='function' and type(evaluate)=='function' then
        local ok,value=pcall(api,spell,unit)
        if ok and issecretvalue and issecretvalue(value) then
            local applied,alpha=pcall(evaluate,value,1,0.35)
            if applied then return alpha,'unknown','native spell' end
        end
    end
    if group and type(UnitInRange)=='function' then
        local ok,value,checked=pcall(UnitInRange,unit)
        if ok then
            local hidden=(issecretvalue and (issecretvalue(value) or issecretvalue(checked)))
            if hidden and type(evaluate)=='function' then
                local applied,alpha=pcall(function()
                    local distanceAlpha=evaluate(value,1,0.35)
                    return evaluate(checked,distanceAlpha,1)
                end)
                if applied then return alpha,'unknown','native group' end
            elseif not hidden and checked==true then
                if value==true then return 1,'in','group' end
                if value==false then return 0.35,'out','group' end
            end
        end
    end
    return 1,state,'unavailable'
end

function Healing:RangeMarker(left,right)
    if left=='unavailable' then left=right end
    if right=='unavailable' then right=left end
    if left=='unavailable' then return '' end
    if left=='unknown' or right=='unknown' then return '|cffaaaaaa[?]|r ' end
    if left~=right then return '|cffffcc55[MIX]|r ' end
    return left=='in' and '|cff55ff88[IN]|r ' or '|cffff7777[FAR]|r '
end

function Healing:RangeTooltip(row,left,right)
    local labels={['in']='In range',out='Out of range',unknown='Range unknown',unavailable='No active spell'}
    local leftRange,rightRange='unknown','unknown'
    local sameName=not row.macroName or self:TargetName(row.boundUnit)==row.macroName
    if sameName then
        leftRange=self:Range(left,row.boundUnit); rightRange=self:Range(right,row.boundUnit)
    end
    GameTooltip:AddLine('Left: '..labels[leftRange]..' | Right: '..labels[rightRange],1,1,1)
    if not row.enemyRow then GameTooltip:AddLine('Faded row: outside the selected heal range, or group range when spell range is unavailable.',0.7,0.7,0.7,true) end
    GameTooltip:AddLine('Range only; movement, line of sight and mana can still prevent casting.',0.7,0.7,0.7,true)
end

local function readable(value)
    return not (issecretvalue and issecretvalue(value))
end

local function finite(value)
    return readable(value) and type(value)=='number' and value==value and value>-math.huge and value<math.huge
end

function Healing:TrackHealClick(panel,row,button,down)
    if not down or row.enemyRow or not row.hasHealingAction then return end
    if button~='LeftButton' and not (button=='RightButton' and type(IsShiftKeyDown)=='function' and IsShiftKeyDown()) then return end
    local spell
    if button=='LeftButton' then spell=panel.healLeft else spell=panel.healRight end
    if not spell then panel.lastHealClick=nil; return end
    row.lastHealError=nil
    local name=self:TargetName(row.boundUnit)
    if not name then panel.lastHealClick=nil; return end
    panel.lastHealClick={row=row,unit=row.boundUnit,name=name,time=GetTime()}
end

function Healing:CaptureHealError(panel,message)
    local click=panel.lastHealClick
    if not click or GetTime()-click.time>1.5 or not readable(message) or type(message)~='string' then return end
    local row=click.row
    if row.boundUnit~=click.unit or self:TargetName(row.boundUnit)~=click.name then return end
    row.lastHealError={unit=click.unit,name=click.name,text=message:sub(1,250),expires=GetTime()+5}
    panel.lastHealClick=nil
end

function Healing:Cooldown(spell)
    local ok,start,duration,enabled,rate,active
    if C_Spell and type(C_Spell.GetSpellCooldown)=='function' then
        ok,start,duration,enabled,rate,active=pcall(function()
            local data=C_Spell.GetSpellCooldown(spell)
            if not readable(data) or type(data)~='table' then return end
            return data.startTime,data.duration,data.isEnabled,data.modRate,data.isActive
        end)
    elseif type(GetSpellCooldown)=='function' then
        ok,start,duration,enabled,rate=pcall(GetSpellCooldown,spell)
    end
    if not ok or not readable(enabled) then return 'unknown','Cooldown unavailable' end
    if enabled==false or enabled==0 then return 'blocked','Spell not ready' end
    if enabled~=true and enabled~=1 then return 'unknown','Cooldown unavailable' end
    if readable(active) and active==false then return 'ready','No cooldown' end
    if not finite(start) or not finite(duration) or start<0 or duration<0 then
        if readable(active) and active==true then return 'blocked','Cooldown active (timer unavailable)' end
        return 'unknown','Cooldown unavailable'
    end
    if start==0 or duration==0 then return 'ready','No cooldown' end
    if not readable(rate) or (rate~=nil and rate~=1) then return 'blocked','Cooldown active (timer unavailable)' end
    local remaining=math.max(0,start+duration-GetTime())
    if remaining>0 then return 'blocked',string.format('Cooldown: %.1fs',remaining) end
    return 'ready','No cooldown'
end

function Healing:ReadinessTooltip(row,spell,click)
    if not spell then return end
    local reasons={}
    local unit=row.boundUnit
    local valid=unit and (not row.macroName or self:TargetName(unit)==row.macroName)
    local existsOK,exists=pcall(UnitExists,unit)
    if not valid or not existsOK or not readable(exists) or exists~=true or row.displayUnavailable then
        GameTooltip:AddLine(click..': target unavailable',1,0.6,0.4,true); return
    end
    if row.groupStatus then
        GameTooltip:AddLine(click..': cannot heal this unit right now',1,0.6,0.4,true); return
    end
    local range=self:Range(spell,unit)
    reasons[#reasons+1]=range=='in' and 'In range' or range=='out' and 'Out of range' or 'Range unavailable'
    local api=C_Spell and C_Spell.IsSpellUsable or IsUsableSpell
    local ok,usable,shortage=false,nil,nil
    if type(api)=='function' then ok,usable,shortage=pcall(api,spell) end
    if not ok or not readable(usable) then usable=nil end
    if not ok or not readable(shortage) then shortage=nil end
    if shortage==true or shortage==1 then reasons[#reasons+1]='Not enough mana'
    elseif shortage==false or shortage==0 then reasons[#reasons+1]='Mana available'
    else reasons[#reasons+1]='Mana check unavailable' end
    if usable==false or usable==0 then
        if shortage~=true and shortage~=1 then reasons[#reasons+1]='Spell currently unusable' end
    elseif usable~=true and usable~=1 then reasons[#reasons+1]='Usability unavailable' end
    local cooldown,cooldownText=self:Cooldown(spell)
    reasons[#reasons+1]=cooldownText
    local ready=range=='in' and (usable==true or usable==1) and (shortage==false or shortage==0) and cooldown=='ready'
    GameTooltip:AddLine(click..': '..(ready and 'Ready by current checks | ' or '')..table.concat(reasons,' | '),ready and 0.5 or 1,ready and 1 or 0.8,0.6,true)
end

function Healing:TooltipDetails(row,friendly,db)
    if row.questTexture then
        GameTooltip:AddLine(row.questKind=='kill' and 'Questie: unfinished kill objective'
            or 'Questie: active quest-item or object objective',1,0.85,0.3,true)
    end
    local failure=row.lastHealError
    if failure and GetTime()<failure.expires and row.boundUnit==failure.unit and self:TargetName(row.boundUnit)==failure.name then
        GameTooltip:AddLine('Game message after last heal click: '..failure.text,1,0.6,0.4,true)
    end
    local seen={['Select and cast']=true,['Target only']=true}
    local function status(value,r,g,b)
        if value and not seen[value] then
            GameTooltip:AddLine(value,r or 1,g or 1,b or 1,true); seen[value]=true
        end
    end
    status(row.identityStatus,0.3,1,0.8)
    status(row.statusPrimary)
    status(row.statusDetail,0.8,0.8,0.8)
    status(row.aggroStatus,1,0.6,0.3)
    local cast=row.castInfo
    if cast then
        if cast.restricted then status('Cast info unavailable',0.7,0.7,0.7)
        else
            if not (issecretvalue and issecretvalue(cast.name)) and type(cast.name)=='string' then
                status((cast.channel and 'Channeling: ' or 'Casting: ')..cast.name)
            end
            status(cast.interruptible==true and 'Interruptible' or cast.interruptible==false and 'Cannot interrupt' or 'Interrupt info unavailable',1,0.8,0.4)
        end
    end
    if row.rangeSource=='group' or row.rangeSource=='native group' then
        status('Fade uses group range; exact spell range is unavailable.',0.7,0.7,0.7)
    elseif row.rangeSource=='native spell' then
        status('The game controls range fading; exact range text is unavailable.',0.7,0.7,0.7)
    end
    if row.groupStatus then
        local status=row.groupStatus=='DOWN' and 'Dead or ghost' or row.groupStatus
        GameTooltip:AddLine(status..' - cannot currently receive a heal.',1,0.75,0.4,true)
    end
    if NS.DispelHelper and db and (friendly or row.macroName) then NS.DispelHelper:Tooltip(row,db) end
end

function Healing:Tooltip(row,left,right,friendly,db)
    local leftLabel=db and self:BindingLabel(db,'left',left) or left or 'Unavailable'
    local rightLabel=db and self:BindingLabel(db,'right',right) or right or 'Unavailable'
    if not GameTooltip then return end
    GameTooltip:SetOwner(row,'ANCHOR_RIGHT')
    if row.tooltipName then GameTooltip:AddLine(row.tooltipName,1,0.82,0.2) end
    local function finish() self:TooltipDetails(row,friendly,db); GameTooltip:Show() end
    if row.displayUnavailable then
        GameTooltip:AddLine('Inactive slot; list refreshes after combat.',0.7,0.7,0.7,true)
        GameTooltip:Show(); return
    end
    if row.enemyRow then
        if row.focusTargetRow then
            GameTooltip:AddLine("Left-click: select your focus's current target",1,1,1,true)
            if row.damageLeft then
                GameTooltip:AddLine('On a living hostile target, also cast '..self:BindingLabel(db,'left',row.damageLeft,true),1,1,1,true)
            end
            GameTooltip:AddLine(row.damageRight and ('Right-click: '..self:BindingLabel(db,'right',row.damageRight,true)..' on hostile targets only') or 'Right-click: disabled',1,1,1,true)
            GameTooltip:AddLine('Friendly targets are selected without casting a damage spell. Clears the old target before selecting.',0.7,0.9,1,true)
            finish(); return
        end
        if row.enemySelectCast then
            GameTooltip:AddLine('Left: select and cast '..self:BindingLabel(db,'left',row.damageLeft,true),1,1,1,true)
            GameTooltip:AddLine(row.attackUnit and ('Right: '..self:BindingLabel(db,'right',row.damageRight,true)) or 'Right: no supported spell target',1,1,1,true)
            self:ReadinessTooltip(row,row.damageLeft,'Left')
            if row.attackUnit then self:ReadinessTooltip(row,row.damageRight,'Right') end
            GameTooltip:AddLine('Clears old target; failed selection prevents casting.',1,0.85,0.4,true)
            if not row.attackUnit then GameTooltip:AddLine('Nameplate selection: live test pending.',0.7,0.9,1,true) end
            GameTooltip:AddLine('Movement, line of sight and cooldowns are checked by the game.',0.7,0.7,0.7,true)
            finish(); return
        end
        if row.targetOnlyUnit then
            GameTooltip:AddLine('Left-click: target this unit (client support unconfirmed)',1,0.85,0.4,true)
            GameTooltip:AddLine('Right-click: no action',0.7,0.7,0.7,true)
            GameTooltip:AddLine('Selection only. Spell bindings refresh outside combat.',0.7,0.9,1,true)
            finish(); return
        end
        if row.attackUnit then
            GameTooltip:AddLine('Left: '..self:BindingLabel(db,'left',row.damageLeft,true),1,1,1)
            GameTooltip:AddLine('Right: '..self:BindingLabel(db,'right',row.damageRight,true),1,1,1)
        end
        if row.attackUnit then
            self:ReadinessTooltip(row,row.damageLeft,'Left')
            self:ReadinessTooltip(row,row.damageRight,'Right')
            GameTooltip:AddLine('Movement and line of sight are checked by the game.',0.7,0.7,0.7,true)
            GameTooltip:AddLine('This row follows your '..(row.attackUnit=='focustarget' and "focus's target" or row.attackUnit)..'. Harmful targets only.',0.45,0.95,0.85,true)
        else
            GameTooltip:AddLine('No supported click target. Bindings refresh outside combat.',1,1,1,true)
        end
        finish(); return
    end
    if row.macroName then
        GameTooltip:AddLine('Left: '..leftLabel,1,1,1)
        GameTooltip:AddLine('Right: '..rightLabel,1,1,1)
        GameTooltip:AddLine(row.menuUnit and 'Shift-right-click: player menu' or 'Player menu: target/focus this player outside combat first.',1,1,1,true)
        self:ReadinessTooltip(row,left,'Left')
        self:ReadinessTooltip(row,right,'Right')
        GameTooltip:AddLine('Movement and line of sight are checked by the game.',0.7,0.7,0.7,true)
        GameTooltip:AddLine('Targets by short name; similar names can match.',0.45,0.95,0.85,true)
        finish(); return
    end
    if not row.healUnit then
        GameTooltip:AddLine('Display only: no supported healing target')
        GameTooltip:AddLine('Target or focus this player outside combat, or invite them to your party.',1,1,1,true)
        finish(); return
    end
    if not friendly then
        GameTooltip:AddLine(row.groupSelectUnit and 'Left: select this member; cannot currently heal them.' or 'Display only: this row is not a friendly player',1,1,1,true)
        finish(); return
    end
    GameTooltip:AddLine(row.groupSelectUnit and (left and ('Left: select and heal with '..leftLabel) or 'Left: select this member (heal disabled or unavailable)') or ('Left: '..leftLabel),1,1,1,true)
    GameTooltip:AddLine('Right: '..rightLabel,1,1,1)
        GameTooltip:AddLine(row.menuUnit and 'Shift-right-click: player menu' or 'Player menu: target/focus this player outside combat first.',1,1,1,true)
    self:ReadinessTooltip(row,left,'Left')
    self:ReadinessTooltip(row,right,'Right')
    GameTooltip:AddLine('Movement and line of sight are checked by the game.',0.7,0.7,0.7,true)
    GameTooltip:AddLine('Combat locks row positions; new units wait until combat ends.',0.45,0.95,0.85,true)
    finish()
end

-- Read-only diagnostic. Never change a secure action from a click handler.
function Healing:Trace(addon,row,button)
    local function read(fn,...)
        if type(fn)~='function' then return 'missing API' end
        local ok,value=pcall(fn,...)
        if not ok then return 'error' end
        if issecretvalue and issecretvalue(value) then return 'restricted' end
        return tostring(value)
    end
    local unit=row.boundUnit or 'none'
    local remap=(row.macroName or (row.enemySelectCast and not row.attackUnit) or row.targetOnlyUnit) and button or (row.enemyRow and (button=='RightButton' and 'damageRight' or 'damageLeft') or (button=='RightButton' and 'healRight' or 'healLeft'))
    local suffix=button=='RightButton' and '2' or '1'
    addon:Say('Heal click: '..button..', mode='..(row.macroName and 'name macro' or 'direct')..', combat='..tostring(InCombatLockdown()))
    addon:Say('Heal resolved: type='..read(SecureButton_GetModifiedAttribute,row,'type',remap)..', unit='..read(SecureButton_GetModifiedUnit,row,remap))
    if row.macroName then
        addon:Say('Heal macro: '..read(function()
            local value=row:GetAttribute('macrotext'..suffix)
            if issecretvalue and issecretvalue(value) then return value end
            return type(value)=='string' and value:gsub('\n',' | ') or value
        end))
        addon:Say('Macro API='..type(C_Macro and C_Macro.RunMacroText)..', target now='..read(UnitName,'target'))
    else
        addon:Say('Heal action: type='..read(row.GetAttribute,row,'type-'..remap)..', spell='..read(row.GetAttribute,row,'spell-'..remap))
    end
end

function Healing:TraceEvent(addon,event,...)
    local parts={event}
    for i=1,select('#',...) do
        local value=select(i,...)
        parts[#parts+1]=(issecretvalue and issecretvalue(value)) and 'restricted' or tostring(value)
    end
    addon:Say('Heal client event: '..table.concat(parts,' | '))
end
