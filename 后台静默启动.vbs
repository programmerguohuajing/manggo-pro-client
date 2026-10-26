Set ws = CreateObject("Wscript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = scriptDir
ws.Run """C:\Users\A\AppData\Local\Python\bin\pythonw.exe"" """ & scriptDir & "\main.py""", 0, False
