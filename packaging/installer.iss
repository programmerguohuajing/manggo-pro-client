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
