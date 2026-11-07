-- Configure Blizzard's display outside combat. Never inspect its live aura,
-- visibility, text, cooldown, or charge values from addon code.
local _,NS=...
local Native={}
NS.NativeShieldDisplay=Native

function Native:Create(anchor,spellIDs,spellName)
    if InCombatLockdown() then return nil,'Setup waits until combat ends' end
    if not CustomAuraContainerSlotDefaultOptions then
        return nil,'Native aura container is unavailable on this client'
    end
    local container
    local ok,result=pcall(function()
        container=CreateFrame('AuraContainer',nil,UIParent,'CustomAuraContainerTemplate')
        assert(type(container.AddAuraSlot)=='function' and type(container.SetUnit)=='function','Native aura methods unavailable')
        container:SetSize(240,44)
        container:SetPoint('TOPLEFT',anchor,'TOPLEFT',0,48)
        container:EnableMouse(false)
        local initialized,initializationError=false,nil
        container:AddAuraSlot('lightningShield','HELPFUL',{
            candidateFilters={includeSpellIDs=spellIDs},
            initializeFrame=function(frame)
                initialized,initializationError=pcall(function()
                frame:SetSize(240,44)
                frame:SetPoint('TOPLEFT',container,'TOPLEFT',0,0)
                frame:EnableMouse(false)
                local background=frame:CreateTexture(nil,'BACKGROUND')
                background:SetAllPoints()
                NS.Appearance:Background(background,0.025,0.035,0.05,0.94,true)
                local icon=frame:CreateTexture(nil,'ARTWORK')
                icon:SetSize(34,34)
                icon:SetPoint('LEFT',frame,'LEFT',6,0)
                local cooldown=CreateFrame('Cooldown',nil,frame,'CooldownFrameTemplate')
                cooldown:SetAllPoints(icon)
                local title=frame:CreateFontString(nil,'OVERLAY','GameFontNormalSmall')
                title:SetPoint('TOPLEFT',frame,'TOPLEFT',48,-6)
                title:SetText(spellName or 'Lightning Shield')
                container.shieldTitle=title
                title:SetTextColor(0.35,1,0.45)
                local duration=frame:CreateFontString(nil,'OVERLAY','GameFontHighlightSmall')
                duration:SetPoint('TOPLEFT',frame,'TOPLEFT',48,-25)
                local charges=frame:CreateFontString(nil,'OVERLAY','GameFontNormalSmall')
                charges:SetPoint('TOPRIGHT',frame,'TOPRIGHT',-8,-5)
                charges:SetText('Charges')
                local count=frame:CreateFontString(nil,'OVERLAY','GameFontNormalLarge')
                count:SetPoint('TOP',charges,'BOTTOM',0,-1)
                count:SetTextColor(1,0.85,0.25)
                frame:SetIcon(icon)
                frame:SetDurationCooldown(cooldown)
                frame:SetDurationText(duration,{})
                frame:SetApplicationCount(count,{})
                end)
            end,
        })
        assert(initialized,initializationError or 'Native aura slot did not initialize')
        container:SetUnit('player')
        return container
    end)
    if not ok then
        if container then pcall(container.Hide,container) end
        return nil,tostring(result)
    end
    return result
end
