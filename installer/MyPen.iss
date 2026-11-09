[Setup]
AppId={{C9A88079-31E8-4D58-A24A-8364D9C9021F}
AppName=My Pen
AppVersion=10.0
AppVerName=My Pen V10.0
AppPublisher=Engr Ibrahim Khalil
DefaultDirName={localappdata}\Programs\My Pen
DefaultGroupName=My Pen
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer-output
OutputBaseFilename=MyPen-Setup-10.0-x64
SetupIconFile=..\images\app\my_pen.ico
UninstallDisplayIcon={app}\My Pen.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\My Pen\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\My Pen"; Filename: "{app}\My Pen.exe"
Name: "{autodesktop}\My Pen"; Filename: "{app}\My Pen.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\My Pen.exe"; Description: "Launch My Pen"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  RunValue: String;
begin
  if CurUninstallStep = usUninstall then
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'My Pen', RunValue) then
      if Pos('"' + ExpandConstant('{app}\My Pen.exe') + '"', RunValue) = 1 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'My Pen');
end;
