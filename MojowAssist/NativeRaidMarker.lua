-- Restricted marker values go straight to the native texture sink, never to
-- Lua arithmetic, table indexing, string construction, or action selection.
local _,NS=...
local Marker={}
NS.NativeRaidMarker=Marker
local sheet='Interface\\TargetingFrame\\UI-RaidTargetingIcons'

function Marker:Refresh(texture,unit)
    texture:Hide()
    if type(GetRaidTargetIndex)~='function' then return end
    local ok,index=pcall(GetRaidTargetIndex,unit)
    if not ok then return end
    local secret=issecretvalue and issecretvalue(index)
    if not secret and (type(index)~='number' or index<1 or index>8 or index~=math.floor(index)) then return end
    texture:SetTexture(sheet)
    if type(texture.SetSpriteSheetCell)=='function' then
        if pcall(texture.SetSpriteSheetCell,texture,index,4,4) then
            texture:Show()
            return
        end
    end
    -- Older clients may lack the native secret-capable sink. Never send an
    -- opaque value through a legacy helper or construct an asset name from it.
    if secret then return end
    if type(SetRaidTargetIconTexture)=='function' and pcall(SetRaidTargetIconTexture,texture,index) then
        texture:Show()
        return
    end
    texture:SetTexture('Interface\\TargetingFrame\\UI-RaidTargetingIcon_'..index)
    texture:SetTexCoord(0,1,0,1)
    texture:Show()
end
