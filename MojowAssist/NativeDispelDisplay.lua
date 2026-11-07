-- Optional Group-row poison display. Blizzard owns live aura evaluation and
-- visibility; addon code configures only fixed unit tokens outside combat.
local _,NS=...
local Native={}
NS.NativeDispelDisplay=Native

function Native:Create(row)
    if InCombatLockdown() then return nil,'Setup waits until combat ends' end
    if not CustomAuraContainerSlotDefaultOptions then return nil,'Native aura display unavailable' end
    local container
    local ok,result=pcall(function()
        container=CreateFrame('AuraContainer',nil,row,'CustomAuraContainerTemplate')
        assert(type(container.AddAuraSlot)=='function' and type(container.SetUnit)=='function'
            and type(container.SetAuraSlotEnabled)=='function','Native aura methods unavailable')
        container:SetSize(16,16)
        container:SetPoint('TOPRIGHT',row.health,'TOPRIGHT',-58,-1)
        container:EnableMouse(false)
        local initialized,initializationError=false,nil
        container:AddAuraSlot('poison','HARMFUL|RAID',{
            candidateFilters={includeDispelTypes={Poison=true}},
            initializeFrame=function(frame)
                initialized,initializationError=pcall(function()
                    frame:SetSize(16,16)
                    frame:SetPoint('TOPLEFT',container,'TOPLEFT',0,0)
                    frame:EnableMouse(false)
                    local border=frame:CreateTexture(nil,'BACKGROUND')
                    border:SetAllPoints(); border:SetColorTexture(0.2,1,0.35,1)
                    local icon=frame:CreateTexture(nil,'ARTWORK')
                    icon:SetSize(12,12); icon:SetPoint('CENTER',frame,'CENTER',0,0)
                    frame:SetIcon(icon)
                end)
            end,
        })
        assert(initialized,initializationError or 'Native poison slot did not initialize')
        container:SetAuraSlotEnabled('poison',false)
        return container
    end)
    if not ok then
        if container then pcall(container.Hide,container) end
        return nil,tostring(result)
    end
    return result
end

function Native:Bind(row,unit,enabled)
    if InCombatLockdown() then return false end
    local token=enabled and row.groupWindow and NS.NearbyHealing and NS.NearbyHealing:GroupUnit(unit)
    if not enabled or not token then
        if row.nativePoison and row.nativePoisonEnabled then
            local ok=pcall(row.nativePoison.SetAuraSlotEnabled,row.nativePoison,'poison',false)
            if not ok then pcall(row.nativePoison.Hide,row.nativePoison); row.nativePoison=nil end
        end
        row.nativePoisonEnabled=false; row.nativePoisonReady=false
        row.nativePoisonAttempt=nil; row.nativePoisonError=nil
        return false
    end
    if row.nativePoisonReady and row.nativePoisonUnit==token then return true end
    if row.nativePoisonError and row.nativePoisonAttempt==token then return false end
    row.nativePoisonAttempt=token; row.nativePoisonReady=false
    if not row.nativePoison then
        row.nativePoison,row.nativePoisonError=self:Create(row)
        if not row.nativePoison then return false end
    end
    local ok,err=pcall(function()
        row.nativePoison:SetAuraSlotEnabled('poison',false)
        row.nativePoisonEnabled=false
        row.nativePoison:SetUnit(token)
        row.nativePoison:SetAuraSlotEnabled('poison',true)
    end)
    if not ok then
        local disabled=pcall(row.nativePoison.SetAuraSlotEnabled,row.nativePoison,'poison',false)
        if not disabled then pcall(row.nativePoison.Hide,row.nativePoison); row.nativePoison=nil end
        row.nativePoisonEnabled=false
        row.nativePoisonError=tostring(err)
        return false
    end
    row.nativePoisonUnit=token; row.nativePoisonEnabled=true
    row.nativePoisonReady=true; row.nativePoisonError=nil
    return true
end
