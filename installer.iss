#define MyVer "1.0.1"
[Setup]
AppId={{F7397060-9B24-49F6-AB06-1358C47FDB97}
AppName=NOT TUBE
AppVersion={#MyVer}
AppVerName=NOT TUBE {#MyVer}
AppPublisher=EX Inc./HYPERION DIGITAL
AppPublisherURL=https://github.com/Teobokki/not-tube
AppCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoVersion={#MyVer}.0
VersionInfoCompany=EX Inc.
VersionInfoCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoProductName=NOT TUBE
VersionInfoDescription=NOT TUBE Setup
DefaultDirName={localappdata}\Programs\NOT TUBE
DefaultGroupName=NOT TUBE
UsePreviousAppDir=no
UsePreviousGroup=no
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=NOT-TUBE-Setup-{#MyVer}
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\NOT TUBE.exe
UninstallDisplayName=NOT TUBE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\NOT TUBE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NOT TUBE"; Filename: "{app}\NOT TUBE.exe"; IconFilename: "{app}\NOT TUBE.exe"
Name: "{group}\Uninstall NOT TUBE"; Filename: "{uninstallexe}"
Name: "{userdesktop}\NOT TUBE"; Filename: "{app}\NOT TUBE.exe"; IconFilename: "{app}\NOT TUBE.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NOT TUBE.exe"; Description: "Launch NOT TUBE"; Flags: nowait postinstall skipifsilent
