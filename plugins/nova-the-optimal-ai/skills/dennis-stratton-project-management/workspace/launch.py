"""Launch or reuse one verified local Project Bridge instance."""
from __future__ import annotations
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request,webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def _module_path(value):
    value=str(Path(value).resolve())
    if sys.platform=="win32" and not value.startswith("\\\\?\\"):
        value=("\\\\?\\UNC\\"+value[2:]) if value.startswith("\\\\") else ("\\\\?\\"+value)
    return value
sys.path.insert(0,_module_path(ROOT))
from bridge_runtime import PRODUCT,BUILD,resolve_user_store,safe_data_home
from storage_io import lock

def default_home():
    base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
    return (base/"Collaborative Dynamics"/"Project Bridge").expanduser()

def choose_store(explicit,data_home):
    if explicit is not None:return resolve_user_store(explicit)
    if os.environ.get("DENNIS_PROJECT_HOME","").strip():return resolve_user_store(None)
    saved=data_home/"selected-store.json"
    try:
        value=json.loads(saved.read_text(encoding="utf-8"))
        if isinstance(value,dict) and isinstance(value.get("path"),str):
            return resolve_user_store(Path(value["path"]))[0],"saved-folder-selection"
    except (OSError,ValueError,TypeError):pass
    return resolve_user_store(None)

def main():
    p=argparse.ArgumentParser();p.add_argument("--store",type=Path);p.add_argument("--data-home",type=Path);p.add_argument("--no-browser",action="store_true");p.add_argument("--port",type=int,default=0);a=p.parse_args()
    home=safe_data_home(a.data_home or default_home(),ROOT.parent.parent)
    try:home.mkdir(parents=True,exist_ok=True)
    except OSError:raise SystemExit("Project Bridge cannot use its separate reading-preferences folder: "+str(home))
    store,source=choose_store(a.store,home)
    with lock(home/".launch.lock"):
        result=None;instance=home/"instance.json"
        if instance.exists():
            try:
                old=json.loads(instance.read_text(encoding="utf-8"))
                if not old.get("url","").startswith("http://127.0.0.1:"):raise ValueError("Invalid local address")
                health=json.load(urllib.request.urlopen(old["url"]+"health",timeout=1))
                expected={k:old[k] for k in ("product","build","home","store","nonce","protocol")}
                if health==expected:
                    if old["product"]!=PRODUCT or old["home"]!=str(home) or old["store"]!=str(store) or old["build"]!=BUILD:
                        raise SystemExit("A different Project Bridge build or project-record estate is using this reading folder. Exit it before reopening this shortcut.")
                    result=old
            except (OSError,ValueError,KeyError):pass
        if result is None:
            fd,name=tempfile.mkstemp(prefix="bridge-ready-",suffix=".json");os.close(fd);ready=Path(name);ready.unlink()
            with open(home/"reader.log","ab") as log:
                flags=0x08000000|0x00000008 if os.name=="nt" else 0
                proc=subprocess.Popen([sys.executable,"-B",str(ROOT/"bridge_server.py"),"--store",str(store),"--store-source",source,"--data-home",str(home),"--ready-file",str(ready),"--port",str(a.port)],cwd=tempfile.gettempdir(),stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,start_new_session=os.name!="nt")
            try:
                for _ in range(100):
                    if ready.exists():result=json.loads(ready.read_text(encoding="utf-8"));break
                    if proc.poll() is not None:raise SystemExit("Project Bridge could not start. Your native project records are untouched. See "+str(home/"reader.log"))
                    time.sleep(.1)
                if result is None:
                    if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
                    raise SystemExit("Project Bridge took too long to start. Reopen the shortcut. Details: "+str(home/"reader.log"))
                health=json.load(urllib.request.urlopen(result["url"]+"health",timeout=2))
                if health!={k:result[k] for k in ("product","build","home","store","nonce","protocol")}:
                    raise SystemExit("Project Bridge could not confirm its local identity. Reopen the shortcut.")
            except BaseException:
                if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
                raise
            finally:ready.unlink(missing_ok=True)
    if not a.no_browser:webbrowser.open(result["url"]+"#"+result["token"])
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
