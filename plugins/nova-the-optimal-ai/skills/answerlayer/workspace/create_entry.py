"""Create an explicitly requested product entry without replacing an existing entry."""
from pathlib import Path
import argparse,json,os,plistlib,shlex,shutil,subprocess,sys,tempfile,uuid
from launch_runtime import unlinked
ROOT=Path(__file__).absolute().parent

def ps(value):return "'"+str(value).replace("'","''")+"'"

def create_entry(directory,platform,headless=False):
    directory=unlinked(directory)
    if not directory.is_dir():raise ValueError('Choose an existing entry directory with --directory')
    unlinked(ROOT)
    if platform=='windows':
        if os.name!='nt':raise ValueError('Windows entry creation requires Windows')
        target=unlinked(directory/'AnswerLayer.lnk')
        if target.exists():raise FileExistsError('Existing AnswerLayer.lnk retained; choose another directory')
        icon=unlinked(ROOT/'assets/answerlayer.ico');launcher=unlinked(ROOT/'Open.cmd')
        if not icon.is_file() or not launcher.is_file():raise ValueError('Keep the complete installed runtime together')
        temp=directory/('.answerlayer-'+uuid.uuid4().hex+'.lnk')
        command=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/cmd.exe')
        tail=' --no-browser --port 0' if headless else ''
        arguments='/d /c ""'+str(launcher)+'"'+tail+'"'
        script="$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut("+ps(temp)+");$s.TargetPath="+ps(command)+";$s.Arguments="+ps(arguments)+";$s.WorkingDirectory="+ps(ROOT)+";$s.IconLocation="+ps(str(icon)+',0')+";$s.Description='AnswerLayer Answer Change Desk';$s.WindowStyle=7;$s.Save()"
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:raise RuntimeError(result.stderr.strip() or 'Windows shortcut creation failed')
            with target.open('xb') as stream:stream.write(temp.read_bytes())
        finally:
            if temp.exists():temp.unlink()
        return {'state':'created','platform':'windows','entry':str(target),'icon':str(icon),'launcher':str(launcher),'arguments':arguments,'starts_automatically':False}
    if platform!='mac':raise ValueError('Use windows or mac')
    target=unlinked(directory/'AnswerLayer.app')
    if target.exists():raise FileExistsError('Existing AnswerLayer.app retained; choose another directory')
    icon=unlinked(ROOT/'assets/answerlayer.icns')
    if not icon.is_file():raise ValueError('Keep the complete installed runtime together')
    relative=os.path.relpath(ROOT,directory).replace(os.sep,'/')
    stage=Path(tempfile.mkdtemp(prefix='.answerlayer-',dir=directory))
    try:
        contents=stage/'Contents';(contents/'MacOS').mkdir(parents=True);(contents/'Resources').mkdir()
        info={'CFBundleName':'AnswerLayer','CFBundleDisplayName':'AnswerLayer','CFBundleIdentifier':'com.collaborative-dynamics.answerlayer','CFBundlePackageType':'APPL','CFBundleExecutable':'AnswerLayer','CFBundleIconFile':'answerlayer.icns','CFBundleShortVersionString':'0.3.1','CFBundleVersion':'0.3.1'}
        (contents/'Info.plist').write_bytes(plistlib.dumps(info));shutil.copyfile(icon,contents/'Resources/answerlayer.icns')
        flags=' --no-browser --port 0' if headless else ''
        script='#!/bin/sh\nset -eu\nENTRY_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)\nWORKSPACE="$ENTRY_DIR"/'+shlex.quote(relative)+'\ncd "$WORKSPACE"\nexec /usr/bin/env python3 -B -X utf8 host.py'+flags+'\n'
        executable=contents/'MacOS/AnswerLayer';executable.write_bytes(script.encode());executable.chmod(0o755)
        # mkdir is exclusive: a destination appearing during construction is retained.
        target.mkdir();shutil.copytree(stage,target,dirs_exist_ok=True)
    finally:
        if not stage.resolve().is_relative_to(directory.resolve()):raise ValueError("Entry staging escaped its selected directory")
        shutil.rmtree(stage)
    return {'state':'created','platform':'mac','entry':str(target),'icon':str(target/'Contents/Resources/answerlayer.icns'),'runtime_relative_to_entry_directory':relative,'starts_automatically':False,'boundary':'Native macOS launch is verified only on a Mac.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True,help='Existing destination you choose; an existing product entry is preserved.');p.add_argument('--platform',choices=['windows','mac'],default='windows' if os.name=='nt' else 'mac');p.add_argument('--headless',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
    try:print(json.dumps(create_entry(a.directory,a.platform,a.headless)));return 0
    except (OSError,ValueError,RuntimeError) as error:print(json.dumps({'state':'refused','error':str(error)}));return 2
if __name__=='__main__':raise SystemExit(main())
