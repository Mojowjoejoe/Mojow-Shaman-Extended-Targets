-- Test boundary for WoW-only APIs. Does not emulate secure execution or taint.
COMBAT = false
ROSTER = {player={'Me','Realm'}, party1={'Lead','Realm'}, party2={'Friend','Realm'}}
LEADER = 'party1'
BINDINGS = {}
SENT = {}
MESSAGES = {}
local Frame = {}
Frame.__index = Frame
local function guard(self)
    if self.protected and COMBAT and not NATIVE_SECURE then error('protected mutation in combat') end
end
function Frame:SetAttribute(k,v)
 guard(self); self.attrs[k]=v
 if self.isHeader and self.shown and k=='nameList' then UpdateNativeHeader(self) end
 if k=='unit' and self.attrs._onattributechanged then
  local f=assert(loadstring('return function(self,name,value) '..self.attrs._onattributechanged..' end'))()
  f(self,k,v)
 end
end
function Frame:GetFrameRef(k) return self.refs and self.refs[k] end
function SecureHandlerSetFrameRef(frame,k,value) frame.refs=frame.refs or {}; frame.refs[k]=value end
function Frame:GetAttribute(k) return self.attrs[k] end
function Frame:SetScript(k,v) self.scripts[k]=v end
function Frame:HookScript(k,v) self.scripts[k]=v end
function Frame:RegisterEvent(e) self.events[e]=true end
function Frame:RegisterForClicks(...) self.clicks={...} end
function Frame:RegisterForDrag(...) end
function Frame:SetSize(w,h) guard(self); self.width=w; self.height=h end
function Frame:GetWidth() return self.width or 140 end
function Frame:GetHeight() return self.height or 140 end
function Frame:SetValueStep(v) self.step=v end
function Frame:SetObeyStepOnDrag(v) end
function Frame:SetAlpha(v) self.alpha=v end
function Frame:GetScript(k) return self.scripts[k] end
function Frame:SetHighlightTexture(...) end
function Frame:SetWidth(...) guard(self) end
function Frame:SetHeight(...) guard(self) end
function Frame:SetPoint(...) guard(self); self.point={...} end
function Frame:ClearAllPoints() guard(self) end
function Frame:GetPoint() return 'CENTER',UIParent,'CENTER',0,160 end
function Frame:GetCenter() return 500,500 end
function Frame:GetEffectiveScale() return 1 end
function Frame:SetScale(s) guard(self); self.scale=s end
function Frame:Show() guard(self); self.shown=true; if self.isHeader then UpdateNativeHeader(self) end end
function Frame:Hide() guard(self); self.shown=false end
function Frame:IsShown() return self.shown end
function Frame:SetText(t) self.text=t end
function Frame:GetText() return self.text or '' end
function Frame:SetTextColor(...) self.textColor={...} end
function Frame:SetFont(path,size,flags) self.font={path,size,flags}; return true end
function Frame:SetJustifyH(...) end
function Frame:SetWordWrap(...) end
function Frame:SetBackdrop(...) end
function Frame:SetBackdropColor(...) self.fill={...} end
function Frame:SetBackdropBorderColor(...) self.border={...} end
function Frame:SetMovable(...) end
function Frame:SetClampedToScreen(...) end
function Frame:EnableMouse(...) end
function Frame:EnableMouseWheel(...) end
function Frame:SetFrameStrata(...) end
function Frame:SetNormalFontObject(...) end
function Frame:SetHighlightFontObject(...) end
function Frame:SetAutoFocus(...) end
function Frame:SetMaxLetters(...) end
function Frame:ClearFocus() end
function Frame:EnableKeyboard(...) end
function Frame:SetPropagateKeyboardInput(...) end
function Frame:SetChecked(v) self.checked=v end
function Frame:GetChecked() return self.checked end
function Frame:StartMoving() guard(self); self.moving=true end
function Frame:StopMovingOrSizing() guard(self); self.moving=false end
function Frame:Enable() end
function Frame:Disable() end
function Frame:CreateTexture() return self:CreateFontString() end
function Frame:SetTexture(...) end
function Frame:SetTexCoord(...) self.texCoord={...} end
function Frame:SetColorTexture(...) self.fill={...} end
function Frame:SetAllPoints(...) end
function Frame:CreateFontString() return setmetatable({scripts={},attrs={},events={}},Frame) end
function CreateFrame(kind,name,parent,template)
 local f=setmetatable({attrs={},scripts={},events={},shown=true,protected=template and template:find('SecureAction')~=nil},Frame)
 if f.protected and parent then parent.protected=true end
 if template and template:find('SecureGroupHeaderTemplate') then f.isHeader=true; f.shown=false; f.protected=true end
 if name then _G[name]=f end
 return f
end
UIParent=CreateFrame('Frame')
function InCombatLockdown() return COMBAT end
function issecretvalue(v) return type(v)=='table' and v.secret==true end
function GetNormalizedRealmName() return 'Realm' end
function UnitFullName(unit) local v=ROSTER[unit]; if v then return v[1],v[2] end end
function UnitName(unit) if unit:find('target$') then return 'Enemy' end local n,r=UnitFullName(unit); if r=='Realm' then r=nil end return n,r end
function UnitExists(unit) return ROSTER[unit]~=nil end
function UnitIsGroupLeader(unit) return unit==LEADER end
function IsInRaid() return false end
function IsInGroup(category) if category == 2 then return false end return ROSTER.party1~=nil end
function GetNumSubgroupMembers() return 2 end
function GetNumGroupMembers() return 3 end
function UnitIsConnected(unit) return true end
function GetBindingAction(k) return BINDINGS[k] or '' end
function SetBindingClick(k,n,b) assert(not COMBAT); BINDINGS[k]='CLICK '..n..':'..b; return true end
function SaveBindings(which) SAVED_BINDINGS=which end
function GetCurrentBindingSet() return 2 end
function GetBindingKey(action) for k,v in pairs(BINDINGS) do if v==action then return k end end end
function IsShiftKeyDown() return false end
function IsControlKeyDown() return false end
function IsAltKeyDown() return false end
function GetBuildInfo() return '1.60.1','69977','Sep 25 2026',16001 end
function GetTime() return 100 end
function print(message) table.insert(MESSAGES,message) end
Enum={SendAddonMessageResult={Success=0},RegisterAddonMessagePrefixResult={Success=0}}
LE_PARTY_CATEGORY_INSTANCE=2
C_ChatInfo={
 RegisterAddonMessagePrefix=function(prefix) return 0 end,
 SendAddonMessage=function(prefix,message,channel) table.insert(SENT,{prefix,message,channel}); return 0 end
}
SlashCmdList={}
UISpecialFrames={}

Minimap=CreateFrame('Frame')
function GetCursorPosition() return CURSOR_X or 570,CURSOR_Y or 500 end
function UpdateNativeHeader(header)
 local nativeBefore=NATIVE_SECURE; NATIVE_SECURE=true
 local child=header.attrs.child1
 if not child then child=CreateFrame('Frame',nil,header,'SecureHandlerAttributeTemplate'); header.attrs.child1=child end
 local unit=nil
 for candidate,info in pairs(ROSTER) do
  local raw=info[1]
  if info[2] and info[2]~='Realm' then raw=raw..'-'..info[2] end
  if raw==header.attrs.nameList and IsInGroup() then unit=candidate end
 end
 child:SetAttribute('unit',unit)
 NATIVE_SECURE=nativeBefore
end
function NativeDispatch(button)
 local unit=button:GetAttribute('unit')
 if not UnitExists(unit) or button:GetAttribute('type')~='assist' then return false end
 ASSISTED_UNIT=unit
 return true
end

function Frame:CreateMaskTexture() return self:CreateTexture() end
function Frame:AddMaskTexture(...) end
function Frame:SetBlendMode(mode) self.blendMode=mode end
function Frame:SetVertexColor(...) self.vertexColor={...} end
function SetPortraitTexture(texture, unit) texture.unit = unit end

function UnitIsPlayer(unit) return PLAYER_UNITS and PLAYER_UNITS[unit] or false end
function UnitClass(unit) return "Mage", "MAGE" end
RAID_CLASS_COLORS={MAGE={r=0.25,g=0.78,b=0.92}}

function UnitIsVisible(unit) return not DISTANT end
function UnitCanAttack(a,b) return not FRIENDLY end
function UnitGUID(unit) return GUIDS and GUIDS[unit] end
function UnitIsUnit(a,b) return GUIDS and GUIDS[a] ~= nil and GUIDS[a] == GUIDS[b] or false end

function SetBinding(key, action) assert(not COMBAT); BINDINGS[key]=action; return true end

function Frame:SetStatusBarTexture(...) end
function Frame:SetStatusBarColor(...) self.color={...} end
function Frame:SetMinMaxValues(a,b) self.minimum=a; self.maximum=b end
function Frame:SetValue(value) self.value=value end
function UnitCastingInfo(unit) if CAST then return unpack(CAST) end end
function UnitChannelInfo(unit) if CHANNEL then return unpack(CHANNEL) end end

function Frame:SetFormattedText(format,value) self.format=format; self.formattedValue=value end

function Frame:SetTimerDuration(duration, interpolation, direction) self.duration=duration; self.direction=direction end
