Set shell = CreateObject("Shell.Application")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.ShellExecute "C:\Users\A\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe", """" & scriptDir & "\main.py""", "", "runas", 0
