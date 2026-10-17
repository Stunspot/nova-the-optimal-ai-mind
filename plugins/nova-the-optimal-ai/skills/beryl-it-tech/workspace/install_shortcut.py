"""Create a verified Windows shortcut using Python and native Shell COM; no extra modules."""
import argparse,ctypes,hashlib,os,sys,uuid
from pathlib import Path
from ctypes import wintypes as W
ROOT=Path(__file__).resolve().parent

class GUID(ctypes.Structure):
    _fields_=[("Data1",W.DWORD),("Data2",W.WORD),("Data3",W.WORD),("Data4",ctypes.c_ubyte*8)]
    def __init__(self,text):
        super().__init__();ctypes.memmove(ctypes.byref(self),uuid.UUID(text).bytes_le,16)

def call(obj,index,types,*args):
    table=ctypes.cast(obj,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    fn=ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,*types)(table[index])
    result=fn(obj,*args)
    if result<0:raise OSError("Windows could not complete the shortcut operation (0x%08x)."%(result&0xffffffff))
    return result

def desktop():
    value=ctypes.create_unicode_buffer(32768)
    result=ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,value)
    if result:raise OSError("Windows could not find your Desktop. Choose --shortcut-directory.")
    return Path(value.value)

def install(destination=None,data_home=None,icons=None):
    if os.name!="nt":raise ValueError("This installer is for Windows. Use Open.command or Open.sh on this computer.")
    destination=Path(destination).resolve() if destination else desktop()
    icons=Path(icons).resolve() if icons else Path(os.environ["LOCALAPPDATA"])/"Collaborative Dynamics/Companion Icons"
    target=destination/"Beryl Repair Companion.lnk"
    if target.exists():raise ValueError("A Beryl Repair Companion shortcut already exists here. Preserve it or choose another shortcut folder.")
    if len(str(target))>240 or len(str(icons))>185:raise ValueError("Choose a shorter shortcut or icon folder so Windows can retain every part of the shortcut.")
    python=Path(sys.executable).with_name("pythonw.exe")
    if not python.is_file():raise ValueError("This Python installation has no pythonw.exe. Repair Python or use Open.cmd.")
    if data_home:
        data_home=Path(data_home).resolve()
        def identity(p):
            value=str(Path(p).resolve())
            prefix=chr(92)*2+"?"+chr(92)
            if value.startswith(prefix+"UNC"+chr(92)):value=chr(92)*2+value[8:]
            elif value.startswith(prefix):value=value[4:]
            return Path(value)
        if identity(data_home).is_relative_to(identity(ROOT.parent)):
            raise ValueError("Choose a saved-material folder outside the installed application.")
        if not data_home.is_dir():raise ValueError("Your chosen saved-material folder is unavailable. Reconnect it before creating the shortcut.")
    icon_source=ROOT/"assets/beryl.ico";raw=icon_source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    icon=icons/("beryl-repair-companion-"+digest[:16]+".ico")
    destination.mkdir(parents=True,exist_ok=True);icons.mkdir(parents=True,exist_ok=True)
    if not icon.exists() or hashlib.sha256(icon.read_bytes()).hexdigest()!=digest:
        temp_icon=icons/(uuid.uuid4().hex+".tmp")
        try:temp_icon.write_bytes(raw);os.replace(temp_icon,icon)
        finally:temp_icon.unlink(missing_ok=True)
    args='-B "'+str(ROOT/"launch_gui.py")+'"'
    if data_home:args+=' --data-home "'+str(data_home)+'"'
    ole=ctypes.OleDLL("ole32");ole.CoInitialize(None)
    link=ctypes.c_void_p();persist=ctypes.c_void_p()
    temporary=destination/(uuid.uuid4().hex+".lnk")
    try:
        clsid=GUID("00021401-0000-0000-C000-000000000046");iid=GUID("000214F9-0000-0000-C000-000000000046")
        ole.CoCreateInstance(ctypes.byref(clsid),None,1,ctypes.byref(iid),ctypes.byref(link))
        call(link,20,[W.LPCWSTR],str(python))
        call(link,11,[W.LPCWSTR],args)
        call(link,9,[W.LPCWSTR],str(icons))
        call(link,17,[W.LPCWSTR,ctypes.c_int],str(icon),0)
        call(link,7,[W.LPCWSTR],"Observe this Windows PC, compare bounded samples, and follow a prepared investigation.")
        piid=GUID("0000010b-0000-0000-C000-000000000046")
        call(link,0,[ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)],ctypes.byref(piid),ctypes.byref(persist))
        call(persist,6,[W.LPCWSTR,W.BOOL],str(temporary),True)
        call(persist,5,[W.LPCWSTR,W.DWORD],str(temporary),0)
        def read(index):
            buf=ctypes.create_unicode_buffer(32768);call(link,index,[W.LPWSTR,ctypes.c_int],buf,len(buf));return buf.value
        path=ctypes.create_unicode_buffer(32768);call(link,3,[W.LPWSTR,ctypes.c_int,ctypes.c_void_p,W.DWORD],path,len(path),None,0)
        ibuf=ctypes.create_unicode_buffer(32768);idx=ctypes.c_int();call(link,16,[W.LPWSTR,ctypes.c_int,ctypes.POINTER(ctypes.c_int)],ibuf,len(ibuf),ctypes.byref(idx))
        if path.value!=str(python) or read(10)!=args or read(8)!=str(icons) or ibuf.value!=str(icon) or idx.value!=0:
            raise ValueError("Windows did not retain the full shortcut. Choose shorter installation, shortcut and icon folders.")
        os.rename(temporary,target)
    finally:
        if persist.value:call(persist,2,[])
        if link.value:call(link,2,[])
        ole.CoUninitialize();temporary.unlink(missing_ok=True)
    return target

def main():
    if sys.version_info<(3,10):
        print("Install Python 3.10 or newer, then run this installer again.",file=sys.stderr);return 1
    p=argparse.ArgumentParser(description="Install the Beryl Repair Companion Windows shortcut.")
    p.add_argument("--shortcut-directory",type=Path);p.add_argument("--data-home",type=Path);p.add_argument("--icon-directory",type=Path);a=p.parse_args()
    try:print(install(a.shortcut_directory,a.data_home,a.icon_directory))
    except (OSError,ValueError) as e:print("Shortcut could not be created: "+str(e),file=sys.stderr);return 1
    return 0
if __name__=="__main__":raise SystemExit(main())
