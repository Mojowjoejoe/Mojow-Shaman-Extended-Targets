local _,NS=...
local Settings={}
NS.HealingSettings=Settings

local function label(frame,x,y,width,value)
    local out=frame:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
    out:SetPoint('TOPLEFT',frame,'TOPLEFT',x,y); out:SetWidth(width)
    out:SetJustifyH('LEFT'); out:SetText(value)
    return out
end

function Settings:Refresh(panel,enemy)
    local view=panel[enemy and 'enemySettings' or 'healingSettings']
    local choices=NS.NearbyHealing:Choices(enemy)
    for _,button in ipairs(view.buttons) do button:Hide() end
    local index=0
    for column,side in ipairs({'left','right'}) do
        local selected=panel.addon.db[NS.NearbyHealing:ChoiceKey(side,enemy)]
        local spell
        if enemy then
            if side=='left' then spell=panel.damageLeft else spell=panel.damageRight end
        elseif side=='left' then spell=panel.healLeft else spell=panel.healRight end
        view.current[column]:SetText(NS.NearbyHealing:BindingLabel(panel.addon.db,side,spell,enemy))
        for row,choice in ipairs(choices) do
            index=index+1
            local button=view.buttons[index]
            if not button then
                button=CreateFrame('Button',nil,view.frame,'UIPanelButtonTemplate')
                button:SetSize(170,24); view.buttons[index]=button
                button:SetScript('OnClick',function()
                    if NS.NearbyHealing:Choose(panel,button.side,button.spellID,enemy) then self:Refresh(panel,enemy)
                    else panel.addon:Say('Choose a learned spell outside combat.') end
                end)
            end
            button.side,button.spellID=side,choice.id
            button:ClearAllPoints()
            button:SetPoint('TOPLEFT',view.frame,'TOPLEFT',12+(column-1)*182,-83-(row-1)*28)
            button:SetText((selected==choice.id and '* ' or '')..choice.name)
            button:Show()
        end
    end
    view.frame:SetHeight(122+#choices*28)
end

function Settings:Open(panel,enemy)
    local key=enemy and 'enemySettings' or 'healingSettings'
    local frameName=enemy and 'MojowEnemyClickSettings' or 'MojowHealingSettings'
    if not panel or not panel.clickHealing then
        if panel then panel.addon:Say('Click settings require a Shaman.') end
        return false
    end
    if InCombatLockdown() then panel.addon:Say('Change click spells outside combat.'); return false end
    panel.healsDirty=true; panel:Refresh()
    if not panel[key] then
        local frame=CreateFrame('Frame',frameName,UIParent,'BackdropTemplate')
        local view={frame=frame,buttons={},current={}}
        panel[key]=view
        frame:SetSize(376,200); frame:SetPoint('CENTER',UIParent,'CENTER',0,0)
        frame:SetFrameStrata('DIALOG'); frame:SetClampedToScreen(true); frame:EnableMouse(true)
        frame:SetBackdrop({bgFile='Interface\\Buttons\\WHITE8X8',edgeFile='Interface\\Buttons\\WHITE8X8',edgeSize=1})
        NS.Appearance:Background(frame,0.025,0.035,0.05,0.98); frame:SetBackdropBorderColor(0.45,0.95,0.85,1)
        label(frame,12,-12,320,enemy and 'MOJOW | ENEMY CLICKS' or 'MOJOW | HEALING CLICKS')
        label(frame,12,-39,170,'Left click'); label(frame,194,-39,170,'Right click')
        view.current[1]=label(frame,12,-57,170,''); view.current[2]=label(frame,194,-57,170,'')
        local hint=label(frame,12,-100,352,'* Selected | Only learned spells are listed.\nChanges save immediately outside combat.')
        hint:ClearAllPoints(); hint:SetPoint('BOTTOMLEFT',frame,'BOTTOMLEFT',12,12)
        local close=CreateFrame('Button',nil,frame,'UIPanelButtonTemplate')
        close:SetSize(24,22); close:SetPoint('TOPRIGHT',frame,'TOPRIGHT',-6,-6); close:SetText('X')
        close:SetScript('OnClick',function() frame:Hide() end)
        table.insert(UISpecialFrames,frameName)
    end
    self:Refresh(panel,enemy); panel[key].frame:Show()
    return true
end
