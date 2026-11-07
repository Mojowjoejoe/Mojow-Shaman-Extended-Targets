"""Optional check using a separately obtained Blizzard SecureGroupHeaders.lua.
Usage: python3 tests/native_header_smoke.py /path/to/SecureGroupHeaders.lua
No Blizzard source is bundled. This is still a stubbed API, not a game test.
"""
from pathlib import Path
import sys
from lupa.lua51 import LuaRuntime

class NativeHeaderSmoke:
    def run(self, source):
        root=Path(__file__).resolve().parents[1]
        addon=root/'MojowAssist' if (root/'MojowAssist').is_dir() else root
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute((root/'tests/wow_stub.lua').read_text())
        lua.execute('''
            table.wipe=function(t) for k in pairs(t) do t[k]=nil end return t end
            string.trim=function(s) return s:match('^%s*(.-)%s*$') end
            strsplit=function(delimiter,s)
                local out={}; for token in s:gmatch('[^'..delimiter..']+') do out[#out+1]=token end
                return unpack(out)
            end
            GetFrameHandle=function(f) return f end
            GetManagedEnvironment=function() return {} end
            CallRestrictedClosure=function(frame,signature,environment,handle,code,...)
                return assert(loadstring('return function('..signature..') '..code..' end'))()(...)
            end
            local frame=getmetatable(UIParent).__index
            frame.GetName=function(self) return self.name end
            frame.IsVisible=function(self) return self.shown end
            UnitClass=function() return 'Warrior','WARRIOR' end
            GetPartyAssignment=function() return false end
            UnitGroupRolesAssigned=function() return 'DAMAGER' end
        ''')
        lua.execute(Path(source).read_text())
        lua.execute('''
            UpdateNativeHeader=function(header)
                local before=NATIVE_SECURE; NATIVE_SECURE=true
                SecureGroupHeader_Update(header)
                NATIVE_SECURE=before
            end
        ''')
        ns=lua.table()
        for name in ['Appearance.lua', 'Model.lua','Panel.lua','AssistAction.lua','MinimapButton.lua','Runtime.lua']:
            lua.execute((addon/name).read_text(),'MojowAssist',ns)
        app=ns.Addon; app.Initialize(app)
        assert app.action.child is not None, 'native empty header did not create child1'
        app.SelectMaster(app,'Lead-Realm')
        assert app.panel.assist.attrs.unit=='party1', 'native short-name selection failed'
        lua.execute("COMBAT=true; ROSTER.party1={'Other','Realm'}; ROSTER.party2={'Lead','Realm'}")
        lua.globals().UpdateNativeHeader(app.action.header)
        assert app.panel.assist.attrs.unit=='party2', 'native combat reorder did not follow identity'
        lua.execute('ROSTER.party2=nil')
        lua.globals().UpdateNativeHeader(app.action.header)
        assert app.panel.assist.attrs.unit=='none', 'native departure did not clear unit'
        assert app.panel.assist.attrs.type is None
        print('Native header source smoke passed: empty child, select, combat reorder, departure')

if __name__=='__main__': NativeHeaderSmoke().run(sys.argv[1])
