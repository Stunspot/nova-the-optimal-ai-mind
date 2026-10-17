param([string]$ShortcutDirectory,[string]$DataHome,[string]$IconDirectory)
$ErrorActionPreference='Stop'
$offerWorkspace=Split-Path -Parent $MyInvocation.MyCommand.Path
$offerPythonCommand=Get-Command py -ErrorAction SilentlyContinue
if($offerPythonCommand){$offerPythonPath=(& $offerPythonCommand.Source -3 -c "import sys;print(sys.executable)").Trim()}
else{$offerPythonCommand=Get-Command python -ErrorAction SilentlyContinue;if(!$offerPythonCommand){throw 'Install Python 3.10 or newer, then run this installer again.'};$offerPythonPath=(& $offerPythonCommand.Source -c "import sys;print(sys.executable)").Trim()}
$offerInstallArgs=@('-B',(Join-Path $offerWorkspace 'install_shortcut.py'))
if($ShortcutDirectory){$offerInstallArgs+=@('--shortcut-directory',$ShortcutDirectory)}
if($DataHome){$offerInstallArgs+=@('--data-home',$DataHome)}
if($IconDirectory){$offerInstallArgs+=@('--icon-directory',$IconDirectory)}
& $offerPythonPath @offerInstallArgs
if($LASTEXITCODE -ne 0){throw 'Shortcut installation did not complete. Follow the message above; an existing shortcut is preserved.'}