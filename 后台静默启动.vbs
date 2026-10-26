Set ws = CreateObject("Wscript.Shell")
ws.Run """C:\Users\A\AppData\Local\Python\bin\pythonw.exe"" """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\main.py""", 0, False
