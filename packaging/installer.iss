; Manggo Pro Client Windows 安装器（Inno Setup 6）。
; 由 .github/workflows/build-packages.yml 的 Windows job 调用：
;   iscc packaging/installer.iss /DAppVersion=<VERSION> /DSourceDir=dist\ManggoProClient
; 注意：不要给这个安装器加 UPX 或 strip——spec 里 Windows 的 strip/UPX
; 已经关掉，原因见 spec 注释（UPX 后的 python312.dll 在真机上
; LoadLibrary 失败，2026-10-27 实测）。
;
; AppId 一旦发布不要改，否则卸载信息会认成两个程序。

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "dist\ManggoProClient"
#endif

[Setup]
AppId={{024FFBE5-30E3-402B-AF98-EE87142AB7A8}
AppName=Manggo Pro Client
AppVersion={#AppVersion}
AppPublisher=Manggo Pro Client
DefaultDirName={autopf}\ManggoProClient
DefaultGroupName=Manggo Pro Client
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=ManggoProClient-Setup
SolidCompression=yes
Compression=lzma2
CloseApplications=yes
RestartApplications=no
DisableWelcomePage=no

; 安装前互斥检查：程序是托盘常驻的，关窗口不等于退出；旧进程
; 还活着时 _internal 里的 DLL 正被它占着，复制到一半就会报
; DeleteFile failed: code 5（2026-10-27 v1.0.2 实测）。AppMutex 让
; 安装器在动手之前就拦下来、明说“请先退出”，而不是中途报哑巴错。
; 互斥名必须跟 main.py 里 CreateMutex 的名字一字不差。
AppMutex=ManggoProClient_SingleInstance_Mutex

; 语言：只留英文。Inno Setup 官方发行版不带简体中文语言文件
; （ChineseSimplified.isl 属于官方仓库的 Unofficial 翻译），
; runner 自带的 Inno Setup 6.7.1 里没有它，写上会直接编译失败
; （2026-10-27 run 40472157707 实测）。向导英文不影响程序本身；
; 如需中文向导，再把官方翻译文件钉版本随仓库带上。
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Manggo Pro Client"; Filename: "{app}\ManggoProClient.exe"
Name: "{autodesktop}\Manggo Pro Client"; Filename: "{app}\ManggoProClient.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ManggoProClient.exe"; Description: "{cm:LaunchProgram,Manggo Pro Client}"; Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
; 卸载时删掉开机自启任务，避免卸载后登录时还尝试启动已不存在的程序。
; 任务不存在时 schtasks 会报错退出，但不影响卸载继续。
Filename: "{sys}\schtasks.exe"; Parameters: "/DELETE /TN ""ManggoProClient"" /F"; Flags: runhidden

; 卸载侧同样拦：Inno 卸载器本身不会关应用，进程活着时卸载删不掉
; 被占用的 DLL，卸载完残留文件 + 残留进程，下次安装必撞 code 5。
; 拦在卸载之前，让用户先从托盘退出，比卸完再报错强。
[Code]
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if CheckForMutexes('ManggoProClient_SingleInstance_Mutex') then
  begin
    MsgBox('Manggo Pro Client 仍在运行（托盘图标还在）。请先右键托盘图标 → 退出应用，再卸载，否则被占用的文件删不掉，下次安装还会报错。', mbError, MB_OK);
    Result := False;
  end;
end;
