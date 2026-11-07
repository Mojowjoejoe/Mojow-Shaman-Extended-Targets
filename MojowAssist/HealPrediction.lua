-- Native calculator owns clamping/secret arithmetic; this only displays it.
local _,NS=...
local Prediction={}; NS.HealPrediction=Prediction
local function secret(v) return issecretvalue and issecretvalue(v) or false end
local function read(fn,...)
    if type(fn)~='function' then return end
    local ok,v=pcall(fn,...); if ok and not secret(v) then return v end
end
function Prediction:Create(row)
    if row.incomingHeal or InCombatLockdown() then return end
    if type(CreateUnitHealPredictionCalculator)~='function' or type(UnitGetDetailedHealPrediction)~='function'
        or not Enum or not Enum.UnitIncomingHealClampMode then return end
    local ok,calculator=pcall(function()
        local c=CreateUnitHealPredictionCalculator()
        c:SetIncomingHealClampMode(Enum.UnitIncomingHealClampMode.MissingHealth)
        c:SetIncomingHealOverflowPercent(1)
        return c
    end)
    if not ok then return end
    local bar=CreateFrame('StatusBar',nil,row.health)
    bar:Hide(); bar:EnableMouse(false)
    bar:SetStatusBarTexture('Interface\\Buttons\\WHITE8X8')
    bar:SetStatusBarColor(0.2,1,0.5,0.45)
    row.incomingHeal={bar=bar,calculator=calculator}
end
function Prediction:Clear(row)
    local entry=row.incomingHeal
    if entry then entry.bar:Hide(); entry.bar:SetMinMaxValues(0,1); entry.bar:SetValue(0) end
    row.incomingHealAmount=nil
end
function Prediction:Update(row,unit)
    self:Clear(row)
    local entry=row.incomingHeal
    if not entry or read(UnitExists,unit)~=true or read(UnitCanAssist,'player',unit)~=true
        or read(UnitIsDeadOrGhost,unit)~=false then return end
    local ok=pcall(function()
        local calculator,bar=entry.calculator,entry.bar
        UnitGetDetailedHealPrediction(unit,'player',calculator)
        local _,mine=calculator:GetIncomingHeals()
        if not secret(mine) then
            if type(mine)~='number' or mine~=mine or mine<=0 or mine==math.huge then return end
            row.incomingHealAmount=mine
        end
        bar:ClearAllPoints()
        bar:SetSize(row.health:GetWidth(),row.health:GetHeight())
        bar:SetPoint('TOPLEFT',row.health:GetStatusBarTexture(),'TOPRIGHT',0,0)
        bar:SetMinMaxValues(0,calculator:GetMaximumHealth())
        bar:SetValue(mine)
        bar:Show()
        if row.incomingHealAmount then row.value:SetFormattedText('+%.0f',row.incomingHealAmount) end
    end)
    if not ok then self:Clear(row) end
end
