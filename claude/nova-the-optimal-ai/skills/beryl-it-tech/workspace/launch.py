"""Launch a verified instance; user material stays outside replaceable application files."""
import argparse,json,os,subprocess,sys,tempfile,time,urllib.request,webbrowser
from pathlib import Path

# Windows importlib needs extended paths for neighboring modules in deep extractions.
import sys
from pathlib import Path
def _module_path(value):
    value = str(Path(value).resolve())
    if sys.platform == "win32" and not value.startswith("\\\\?\\"):
        value = ("\\\\?\\UNC\\" + value[2:]) if value.startswith("\\\\") else ("\\\\?\\" + value)
    return value
sys.path.insert(0, _module_path(Path(__file__).parent))

from bench_store import ROOT,PRODUCT,BUILD,checked_home
from storage_io import lock
def location_selector():
    base=Path(os.environ.get("CD_WORKSPACE_CONFIG",os.environ.get("LOCALAPPDATA",str(Path.home()/".config"))))
    return base/"Collaborative Dynamics"/"location-beryl-it-benchcraft.txt"
def default_home():
    if os.environ.get("BERYL_WORK_HOME"):return Path(os.environ["BERYL_WORK_HOME"]).expanduser()
    selector=location_selector()
    if selector.exists():return Path(selector.read_text(encoding="utf8").strip()).expanduser()
    return Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))/"Collaborative Dynamics"/"beryl-it-benchcraft"
def main():
    p=argparse.ArgumentParser();p.add_argument("--data-home",type=Path);p.add_argument("--no-browser",action="store_true");p.add_argument("--port",type=int,default=0);a=p.parse_args()
    home=checked_home(a.data_home or default_home())
    if (a.data_home or os.environ.get("BERYL_WORK_HOME") or location_selector().exists()) and not home.is_dir():raise SystemExit("Your Beryl Repair Companion saved-material folder is unavailable: "+str(home)+". Reconnect it before launching.")
    try:home.mkdir(parents=True,exist_ok=True)
    except OSError:raise SystemExit("Beryl Repair Companion cannot use "+str(home)+". Choose an accessible saved-material folder with --data-home.")
    with lock(home/".launch.lock"):
        result=None;instance=home/"instance.json"
        if instance.exists():
            try:
                old=json.loads(instance.read_text("utf-8"))
                if not old.get("url","").startswith("http://127.0.0.1:"):raise ValueError("Invalid local address")
                health=json.load(urllib.request.urlopen(old["url"]+"health",timeout=1))
                if health=={k:old[k] for k in ("product","build","home","nonce","protocol")}:
                    if old["product"]!=PRODUCT or old["home"]!=str(home) or old["build"]!=BUILD:raise SystemExit("Another Beryl Repair Companion version is using this folder. Choose Exit in that app, then reopen this shortcut.")
                    result=old
            except (OSError,ValueError,KeyError):pass
        if result is None:
            from bench_store import initialize
            initialize(home)
            fd,name=tempfile.mkstemp(prefix="beryl-ready-",suffix=".json");os.close(fd);ready=Path(name);ready.unlink()
            with open(home/"reader.log","ab") as log:
                proc=subprocess.Popen([sys.executable,"-B",str(ROOT/"bench_server.py"),"--data-home",str(home),"--ready-file",str(ready),"--port",str(a.port)],cwd=tempfile.gettempdir(),stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=0x08000000|0x00000008 if os.name=="nt" else 0,start_new_session=os.name!="nt")
            try:
                for _ in range(100):
                    if ready.exists():result=json.loads(ready.read_text("utf-8"));break
                    if proc.poll() is not None:raise SystemExit("Beryl Repair Companion could not start. Your saved material is untouched. See "+str(home/"reader.log"))
                    time.sleep(.1)
                if result is None:
                    if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
                    raise SystemExit("Beryl Repair Companion took too long to start. Reopen the shortcut. Details: "+str(home/"reader.log"))
                health=json.load(urllib.request.urlopen(result["url"]+"health",timeout=2))
                if health!={k:result[k] for k in ("product","build","home","nonce","protocol")}:raise SystemExit("Beryl Repair Companion could not confirm the local app identity. Reopen the shortcut.")
            except BaseException:
                if proc.poll() is None:
                    proc.terminate();proc.wait(timeout=5)
                raise
            finally:ready.unlink(missing_ok=True)
    if not a.no_browser:webbrowser.open(result["url"]+"#"+result["token"])
    print(json.dumps(result))
if __name__=="__main__":main()
