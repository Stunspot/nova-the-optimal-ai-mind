"""Create an explicitly requested product entry without replacing an existing entry."""
from pathlib import Path
import argparse,json,os,plistlib,shlex,shutil,subprocess,sys,tempfile,uuid
import stat

def unlinked(value):
    path=Path(os.path.abspath(value))
    for current in (path,*path.parents):
        try:info=current.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
            raise ValueError('Linked entry/runtime path is unsupported: '+str(current))
    return path

ROOT=Path(__file__).absolute().parent

def ps(value):return "'"+str(value).replace("'","''")+"'"

def create_entry(directory,platform,headless=False):
    directory=unlinked(directory)
    if not directory.is_dir():raise ValueError('Choose an existing entry directory with --directory')
    unlinked(ROOT)
    if platform=='windows':
        if os.name!='nt':raise ValueError('Windows entry creation requires Windows')
        target=unlinked(directory/'Beryl IT Studio.lnk')
        if target.exists():raise FileExistsError('Existing Beryl IT Studio.lnk retained; choose another directory')
        icon=unlinked(ROOT/'assets/beryl.ico');launcher=unlinked(ROOT/'Open.cmd')
        if not icon.is_file() or not launcher.is_file():raise ValueError('Keep the complete installed runtime together')
        temp=directory/('.beryl-'+uuid.uuid4().hex+'.lnk')
        command=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/cmd.exe')
        tail=' --no-browser --port 0' if headless else ''
        arguments='/d /c ""'+str(launcher)+'"'+tail+'"'
        script="$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut("+ps(temp)+");$s.TargetPath="+ps(command)+";$s.Arguments="+ps(arguments)+";$s.WorkingDirectory="+ps(ROOT)+";$s.IconLocation="+ps(str(icon)+',0')+";$s.Description='Beryl IT Studio';$s.WindowStyle=7;$s.Save()"
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:raise RuntimeError(result.stderr.strip() or 'Windows shortcut creation failed')
            with target.open('xb') as stream:stream.write(temp.read_bytes())
        finally:
            if temp.exists():temp.unlink()
        return {'state':'created','platform':'windows','entry':str(target),'icon':str(icon),'launcher':str(launcher),'arguments':arguments,'starts_automatically':False}
    if platform!='mac':raise ValueError('Use windows or mac')
    target=unlinked(directory/'Beryl IT Studio.app')
    if target.exists():raise FileExistsError('Existing Beryl IT Studio.app retained; choose another directory')
    icon=unlinked(ROOT/'assets/beryl.icns')
    if not icon.is_file():raise ValueError('Keep the complete installed runtime together')
    relative=os.path.relpath(ROOT,directory).replace(os.sep,'/')
    stage=Path(tempfile.mkdtemp(prefix='.beryl-',dir=directory))
    try:
        contents=stage/'Contents';(contents/'MacOS').mkdir(parents=True);(contents/'Resources').mkdir()
        info={'CFBundleName':'Beryl IT Studio','CFBundleDisplayName':'Beryl IT Studio','CFBundleIdentifier':'com.collaborative-dynamics.beryl','CFBundlePackageType':'APPL','CFBundleExecutable':'Beryl IT Studio','CFBundleIconFile':'beryl.icns','CFBundleShortVersionString':'0.5.0','CFBundleVersion':'0.5.0'}
        (contents/'Info.plist').write_bytes(plistlib.dumps(info));shutil.copyfile(icon,contents/'Resources/beryl.icns')
        flags=' --no-browser --port 0' if headless else ''
        script='#!/bin/sh\nset -eu\nENTRY_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)\nWORKSPACE="$ENTRY_DIR"/'+shlex.quote(relative)+'\ncd "$WORKSPACE"\nexec /usr/bin/env python3 -B -X utf8 host.py'+flags+'\n'
        executable=contents/'MacOS/Beryl IT Studio';executable.write_bytes(script.encode());executable.chmod(0o755)
        # mkdir is exclusive: a destination appearing during construction is retained.
        target.mkdir();shutil.copytree(stage,target,dirs_exist_ok=True)
    finally:
        if not stage.resolve().is_relative_to(directory.resolve()):raise ValueError("Entry staging escaped its selected directory")
        shutil.rmtree(stage)
    return {'state':'created','platform':'mac','entry':str(target),'icon':str(target/'Contents/Resources/beryl.icns'),'runtime_relative_to_entry_directory':relative,'starts_automatically':False,'boundary':'Native macOS launch is verified only on a Mac.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True,help='Existing destination you choose; an existing product entry is preserved.');p.add_argument('--platform',choices=['windows','mac'],default='windows' if os.name=='nt' else 'mac');p.add_argument('--headless',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
    try:print(json.dumps(create_entry(a.directory,a.platform,a.headless)));return 0
    except (OSError,ValueError,RuntimeError) as error:print(json.dumps({'state':'refused','error':str(error)}));return 2
if __name__=='__main__':raise SystemExit(main())
