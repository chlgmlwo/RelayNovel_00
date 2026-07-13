Option Explicit
' Launcher: starts the local web app (the .py in this folder) with NO console window.
' Double-click this file to start the program. It opens in your web browser.

Dim fso, sh, folder, pyfile, f, exe, rc

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

folder = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = folder

' Find the .py file in this folder (avoids hardcoding a non-ASCII filename here)
pyfile = ""
For Each f In fso.GetFolder(folder).Files
    If LCase(fso.GetExtensionName(f.Name)) = "py" Then pyfile = f.Name
Next
If pyfile = "" Then
    MsgBox "No .py file was found in this folder.", vbCritical, "Launcher"
    WScript.Quit
End If

' Detect Python (run hidden, wait for exit code). Try py first, then python.
exe = ""
On Error Resume Next
rc = sh.Run("py --version", 0, True)
If Err.Number = 0 And rc = 0 Then exe = "py"
Err.Clear
If exe = "" Then
    rc = sh.Run("python --version", 0, True)
    If Err.Number = 0 And rc = 0 Then exe = "python"
End If
On Error GoTo 0

If exe = "" Then
    MsgBox "Python was not found." & vbCrLf & vbCrLf & _
           "Install it from https://www.python.org/downloads/" & vbCrLf & _
           "and check ""Add Python to PATH"" during setup, then try again.", _
           vbCritical, "Launcher"
    WScript.Quit
End If

' Start with the console window hidden (window style 0); it opens the browser.
sh.Run exe & " """ & pyfile & """", 0, False
