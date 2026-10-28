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
;
; 2026-10-28 v1.0.13 覆盖更新：AppMutex 现在只是兜底。下面的
; InitializeSetup 会先自己把旧版关掉（温和关 → 3 秒后互斥还在就
; 强制结束），关掉了 AppMutex 就不会弹；实在关不掉它才会出现，
; 让用户手动去托盘退出。CloseApplications=yes 也还开着，是第二道兜底。
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
; 1.0.9 回归：打包版 manifest 改成 requireAdministrator 后，安装完成时
; 勾选启动会报 CreateProcess failed code 740（740 = 需要提升，说明
; [Run] 的启动上下文并非已提权）。改用 shellexec 走 ShellExecute：
; 遇到 requireAdministrator 清单时它会像双击桌面图标一样弹 UAC，
; 点“是”即正常启动，而不是 CreateProcess 那样直接失败。
Filename: "{app}\ManggoProClient.exe"; Description: "{cm:LaunchProgram,Manggo Pro Client}"; Flags: nowait postinstall skipifsilent unchecked shellexec; Check: ShowLaunchOption
; 覆盖更新自动重启：更新前正在运行的旧版被 InitializeSetup 关掉后，
; 装完用这一条把它拉起来（shellexec，走 UAC 弹一次），不用用户再去
; 勾启动框；上面那个勾选框只在没跑过旧版时出现，两条路互斥，不会弹两次 UAC。
Filename: "{app}\ManggoProClient.exe"; Flags: nowait postinstall skipifsilent shellexec; Check: AutoRestartNeeded

[UninstallRun]
; 卸载时删掉开机自启任务，避免卸载后登录时还尝试启动已不存在的程序。
; 任务不存在时 schtasks 会报错退出，但不影响卸载继续。
Filename: "{sys}\schtasks.exe"; Parameters: "/DELETE /TN ""ManggoProClient"" /F"; Flags: runhidden

; 卸载侧同样拦：Inno 卸载器本身不会关应用，进程活着时卸载删不掉
; 被占用的 DLL，卸载完残留文件 + 残留进程，下次安装必撞 code 5。
; 拦在卸载之前，让用户先从托盘退出，比卸完再报错强。
[Code]
var
  AppWasRunning: Boolean;

function AutoRestartNeeded(): Boolean;
begin
  Result := AppWasRunning;
end;

function ShowLaunchOption(): Boolean;
begin
  Result := not AppWasRunning;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Taskkill: String;
begin
  Result := True;
  AppWasRunning := False;
  { 覆盖更新：安装器自己先把正在运行的旧版关掉，免得用户看到
    AppMutex 对话框还得手动去托盘退出。taskkill 不带 /F 是发
    WM_CLOSE（温和关），给 3 秒让它自己收尾写盘；3 秒后互斥还在
    说明它没走（托盘常驻关窗口不等于退出），再 /F 强制结束。
    实在关不掉时后面的 AppMutex 对话框仍会兜底明说。
    注意：AppMutex 检查发生在 InitializeSetup 返回之后，所以
    在这里关是来得及的。 }
  Taskkill := ExpandConstant('{sys}\taskkill.exe');
  if Exec(Taskkill, '/IM ManggoProClient.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      AppWasRunning := True;
      Sleep(3000);
      if CheckForMutexes('ManggoProClient_SingleInstance_Mutex') then
      begin
        Exec(Taskkill, '/F /IM ManggoProClient.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Sleep(2000);
      end;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if CheckForMutexes('ManggoProClient_SingleInstance_Mutex') then
  begin
    MsgBox('Manggo Pro Client 仍在运行（托盘图标还在）。请先右键托盘图标 → 退出应用，再卸载，否则被占用的文件删不掉，下次安装还会报错。', mbError, MB_OK);
    Result := False;
  end;
end;
