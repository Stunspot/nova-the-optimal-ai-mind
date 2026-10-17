Option Explicit
Dim fso, sh, root, dest, launcher, pathParts, part, link, target, icon
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
If WScript.Arguments.Count > 0 Then
  dest = WScript.Arguments(0)
Else
  dest = sh.SpecialFolders("Desktop")
End If
If Not fso.FolderExists(dest) Then WScript.Quit 2
target = fso.BuildPath(root, "workspace\launch.py")
icon = fso.BuildPath(root, "workspace\assets\dennis.ico")
If Not fso.FileExists(target) Or Not fso.FileExists(icon) Then WScript.Quit 3
launcher = ""
Dim windir, localApp
windir = sh.ExpandEnvironmentStrings("%WINDIR%")
If fso.FileExists(fso.BuildPath(windir, "pyw.exe")) Then launcher = fso.BuildPath(windir, "pyw.exe")
If launcher = "" Then
  localApp = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%")
  If fso.FileExists(localApp & "\Programs\Python\Launcher\pyw.exe") Then launcher = localApp & "\Programs\Python\Launcher\pyw.exe"
End If
If launcher = "" Then
  pathParts = Split(sh.ExpandEnvironmentStrings("%PATH%"), ";")
  For Each part In pathParts
    part = Replace(part, Chr(34), "")
    If part <> "" And fso.FileExists(fso.BuildPath(part, "pyw.exe")) Then
      launcher = fso.BuildPath(part, "pyw.exe")
      Exit For
    End If
  Next
End If
If launcher = "" Then WScript.Quit 4
Set link = sh.CreateShortcut(fso.BuildPath(dest, "Project Bridge.lnk"))
link.TargetPath = launcher
link.Arguments = "-3 " & Chr(34) & target & Chr(34)
link.WorkingDirectory = root
link.IconLocation = icon & ",0"
link.Description = "Open Project Bridge - see what your projects need next."
link.Save
' No dialog: double-clicking this helper quietly creates the desktop shortcut.