; HJS-Workbench Windows graphical installer (Inno Setup 6).
;
; Packages the PyInstaller GUI onedir output (dist/HJSWorkbench-GUI)
; into a single Setup executable. The installer asks for its own
; language first (the Inno Setup language dialog appears before any
; other page); the installed application keeps its separate in-app
; language setting chosen on its first run.
;
; Build prerequisites:
;   - Inno Setup 6 installed (https://jrsoftware.org/isinfo.php)
;   - dist/HJSWorkbench-GUI produced by:  pyinstaller packaging/gui.spec --noconfirm
;
; Build from the repository root with:
;   ISCC.exe packaging\installer.iss
;
; The Setup executable lands in dist/HJS-Workbench-Setup-0.6.2.exe.

#define MyAppName "HJS-Workbench"
#define MyAppVersion "0.6.2"
; Keep MyAppVersion in sync with the released application version.
#define MyAppPublisher "HJS"
#define MyAppExeName "HJSWorkbench-GUI.exe"
#define MyAppOnedir "HJSWorkbench-GUI"

[Setup]
AppId={{7B2E4A1C-9D3F-4E6B-8A5C-1F2D3E4B5A6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=HJS-Workbench-Setup-{#MyAppVersion}
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
; The default install location is under Program Files and needs no
; forced custom directory; the user can still change it on the
; directory page.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The complete GUI onedir: executable, bundled assets, examples, and
; locales. Locales and examples land at the bundle root, which is what
; core.paths.resource_path expects in the frozen application.
Source: "..\dist\{#MyAppOnedir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
