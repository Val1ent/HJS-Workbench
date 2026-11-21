; HJS-Workbench Windows graphical installer (Inno Setup 6).
;
; Packages the PyInstaller GUI onedir output (dist/HJSWorkbench-GUI)
; into a single Setup executable. The installer asks for its own
; language first (the Inno Setup language dialog appears before any
; other page); the installed application keeps its separate in-app
; language setting chosen on its first run.
;
; Usability additions:
;   - The install-scope question ("for all users or only for the
;     current user") is reworded per installer language into a plain,
;     beginner-friendly question with a short explanation per choice.
;     The recommended all-users default is kept; the underlying install
;     behavior is unchanged.
;   - The finished page shows a centered brand block (the application
;     icon over "HJS", "Workbench", and the version) instead of the
;     default box-and-disc picture, with the "Run HJS-Workbench" check
;     box repositioned below the block.
;   - The uninstaller uses the standard Windows confirmation and
;     completion dialogs in the active installer language; no custom
;     uninstall forms are shown.
;
; Build prerequisites:
;   - Inno Setup 6 installed (https://jrsoftware.org/isinfo.php)
;   - dist/HJSWorkbench-GUI produced by:  pyinstaller packaging/gui.spec --noconfirm
;
; Build from the repository root with:
;   python packaging/build_installer.py
; which reads the version from gui/version.py and passes it to the
; compiler as /DMyAppVersion=<version>.
;
; The Setup executable lands in
; dist/HJS-Workbench-Setup-<version>-windows-x86_64.exe.

#define MyAppName "HJS-Workbench"
#ifndef MyAppVersion
  ; Fallback only. The normal build passes the real version via
  ; ISCC /DMyAppVersion=<version>, sourced from gui/version.py.
  ; Direct "ISCC installer.iss" without the switch uses this value.
  #define MyAppVersion "0.6.4"
#endif
; The version is supplied by the build script from gui/version.py, so this
; fallback does not need to be synchronized by hand for a release.
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
OutputBaseFilename=HJS-Workbench-Setup-{#MyAppVersion}-windows-x86_64
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

; The install-scope dialog is kept (it is a standard Windows security
; mechanism), but its title, lead-in text, and option labels are
; reworded per language into a plain question about where to install.
[Messages]
english.PrivilegesRequiredOverrideTitle=Where should HJS-Workbench be installed?
english.PrivilegesRequiredOverrideInstruction=Choose who can use this application
english.PrivilegesRequiredOverrideText1=Choose whether everyone on this computer can use HJS-Workbench or only your own account.
english.PrivilegesRequiredOverrideText2=Choose whether everyone on this computer can use HJS-Workbench or only your own account.
english.PrivilegesRequiredOverrideAllUsers=Everyone on this computer (installs under Program Files, needs administrator approval)
english.PrivilegesRequiredOverrideAllUsersRecommended=Everyone on this computer (installs under Program Files, needs administrator approval) (recommended)
english.PrivilegesRequiredOverrideCurrentUser=Only my account (installs in my user profile, no administrator approval needed)
english.PrivilegesRequiredOverrideCurrentUserRecommended=Only my account (installs in my user profile, no administrator approval needed) (recommended)

french.PrivilegesRequiredOverrideTitle=Où installer HJS-Workbench ?
french.PrivilegesRequiredOverrideInstruction=Choisissez qui peut utiliser cette application
french.PrivilegesRequiredOverrideText1=Choisissez si toutes les personnes de cet ordinateur peuvent utiliser HJS-Workbench ou seulement votre propre compte.
french.PrivilegesRequiredOverrideText2=Choisissez si toutes les personnes de cet ordinateur peuvent utiliser HJS-Workbench ou seulement votre propre compte.
french.PrivilegesRequiredOverrideAllUsers=Toutes les personnes de cet ordinateur (installation dans Program Files, approbation de l'administrateur requise)
french.PrivilegesRequiredOverrideAllUsersRecommended=Toutes les personnes de cet ordinateur (installation dans Program Files, approbation de l'administrateur requise) (recommandé)
french.PrivilegesRequiredOverrideCurrentUser=Mon compte uniquement (installation dans mon profil utilisateur, aucune approbation requise)
french.PrivilegesRequiredOverrideCurrentUserRecommended=Mon compte uniquement (installation dans mon profil utilisateur, aucune approbation requise) (recommandé)

german.PrivilegesRequiredOverrideTitle=Wo soll HJS-Workbench installiert werden?
german.PrivilegesRequiredOverrideInstruction=Wählen Sie, wer diese Anwendung verwenden darf
german.PrivilegesRequiredOverrideText1=Wählen Sie, ob alle Personen auf diesem Computer HJS-Workbench verwenden können oder nur Ihr eigenes Konto.
german.PrivilegesRequiredOverrideText2=Wählen Sie, ob alle Personen auf diesem Computer HJS-Workbench verwenden können oder nur Ihr eigenes Konto.
german.PrivilegesRequiredOverrideAllUsers=Alle Personen auf diesem Computer (Installation unter Programme, Administratorfreigabe erforderlich)
german.PrivilegesRequiredOverrideAllUsersRecommended=Alle Personen auf diesem Computer (Installation unter Programme, Administratorfreigabe erforderlich) (empfohlen)
german.PrivilegesRequiredOverrideCurrentUser=Nur mein Konto (Installation in meinem Benutzerprofil, keine Administratorfreigabe erforderlich)
german.PrivilegesRequiredOverrideCurrentUserRecommended=Nur mein Konto (Installation in meinem Benutzerprofil, keine Administratorfreigabe erforderlich) (empfohlen)

chinesesimplified.PrivilegesRequiredOverrideTitle=将 HJS-Workbench 安装到哪里？
chinesesimplified.PrivilegesRequiredOverrideInstruction=选择可以使用此应用程序的人员
chinesesimplified.PrivilegesRequiredOverrideText1=选择这台电脑上的所有用户都可以使用 HJS-Workbench，还是只有您自己的账户可以使用。
chinesesimplified.PrivilegesRequiredOverrideText2=选择这台电脑上的所有用户都可以使用 HJS-Workbench，还是只有您自己的账户可以使用。
chinesesimplified.PrivilegesRequiredOverrideAllUsers=这台电脑上的所有用户（安装到 Program Files，需要管理员批准）
chinesesimplified.PrivilegesRequiredOverrideAllUsersRecommended=这台电脑上的所有用户（安装到 Program Files，需要管理员批准）（推荐）
chinesesimplified.PrivilegesRequiredOverrideCurrentUser=仅我的账户（安装到我的用户文件夹，无需管理员批准）
chinesesimplified.PrivilegesRequiredOverrideCurrentUserRecommended=仅我的账户（安装到我的用户文件夹，无需管理员批准）（推荐）

chinesetraditional.PrivilegesRequiredOverrideTitle=要將 HJS-Workbench 安裝到哪裡？
chinesetraditional.PrivilegesRequiredOverrideInstruction=選擇可以使用此應用程式的人員
chinesetraditional.PrivilegesRequiredOverrideText1=選擇這台電腦上的所有使用者都可以使用 HJS-Workbench，還是只有您自己的帳戶可以使用。
chinesetraditional.PrivilegesRequiredOverrideText2=選擇這台電腦上的所有使用者都可以使用 HJS-Workbench，還是只有您自己的帳戶可以使用。
chinesetraditional.PrivilegesRequiredOverrideAllUsers=這台電腦上的所有使用者（安裝到 Program Files，需要系統管理員核准）
chinesetraditional.PrivilegesRequiredOverrideAllUsersRecommended=這台電腦上的所有使用者（安裝到 Program Files，需要系統管理員核准）（建議）
chinesetraditional.PrivilegesRequiredOverrideCurrentUser=僅我的帳戶（安裝到我的使用者資料夾，不需要系統管理員核准）
chinesetraditional.PrivilegesRequiredOverrideCurrentUserRecommended=僅我的帳戶（安裝到我的使用者資料夾，不需要系統管理員核准）（建議）

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The complete GUI onedir: executable, bundled assets, examples, and
; locales. Locales and examples land at the bundle root, which is what
; core.paths.resource_path expects in the frozen application.
Source: "..\dist\{#MyAppOnedir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The application icon: extracted to {tmp} for the branded finished
; page and installed in the application directory.
Source: "..\assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\app.ico"; DestDir: "{tmp}"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  FinishedIconImage: TBitmapImage;
  FinishedBrandLabel: TLabel;
  FinishedNameLabel: TLabel;
  FinishedVersionLabel: TLabel;

{ -------------------------------------------------------------------- }
{ Finished page brand block: the application icon over "HJS",          }
{ "Workbench", and the version, horizontally centered and stacked      }
{ vertically; the positions are computed from the page size so the     }
{ block stays centered when the window is resized.                     }
{ -------------------------------------------------------------------- }

procedure LayoutFinishedBrandBlock;
var
  PageWidth: Integer;
  CenterX: Integer;
  Y: Integer;
begin
  if FinishedIconImage = nil then
    Exit;
  PageWidth := WizardForm.FinishedPage.ClientWidth;
  CenterX := PageWidth div 2;

  FinishedIconImage.Width := 96;
  FinishedIconImage.Height := 96;
  FinishedIconImage.Left := CenterX - (FinishedIconImage.Width div 2);
  FinishedIconImage.Top := ScaleY(24);

  Y := FinishedIconImage.Top + FinishedIconImage.Height + ScaleY(12);

  FinishedBrandLabel.Font.Size := 22;
  FinishedBrandLabel.Font.Style := [fsBold];
  FinishedBrandLabel.AutoSize := True;
  FinishedBrandLabel.Left := CenterX - (FinishedBrandLabel.Width div 2);
  FinishedBrandLabel.Top := Y;
  Y := Y + FinishedBrandLabel.Height;

  FinishedNameLabel.Font.Size := 13;
  FinishedNameLabel.AutoSize := True;
  FinishedNameLabel.Left := CenterX - (FinishedNameLabel.Width div 2);
  FinishedNameLabel.Top := Y;
  Y := Y + FinishedNameLabel.Height + ScaleY(2);

  FinishedVersionLabel.Font.Size := 10;
  FinishedVersionLabel.Font.Color := clGrayText;
  FinishedVersionLabel.AutoSize := True;
  FinishedVersionLabel.Left := CenterX - (FinishedVersionLabel.Width div 2);
  FinishedVersionLabel.Top := Y;
  Y := Y + FinishedVersionLabel.Height + ScaleY(20);

  { Keep the "Run HJS-Workbench" check box functional, below the block. }
  WizardForm.RunList.Top := Y;
  WizardForm.RunList.Left := ScaleX(20);
  WizardForm.RunList.Width := PageWidth - ScaleX(40);
end;

procedure WizardFormResize(Sender: TObject);
begin
  LayoutFinishedBrandBlock;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    LayoutFinishedBrandBlock;
end;

procedure InitializeWizard;
begin
  { Hide the default finished-page picture, heading, and body; the
    welcome page keeps its own picture. }
  WizardForm.WizardBitmapImage2.Visible := False;
  WizardForm.FinishedHeadingLabel.Visible := False;
  WizardForm.FinishedLabel.Visible := False;

  ExtractTemporaryFile('app.ico');

  FinishedIconImage := TBitmapImage.Create(WizardForm.FinishedPage);
  FinishedIconImage.Parent := WizardForm.FinishedPage;
  FinishedIconImage.Width := 96;
  FinishedIconImage.Height := 96;
  if not InitializeBitmapImageFromIcon(FinishedIconImage,
      ExpandConstant('{tmp}\app.ico'), clNone, []) then
    Log('Could not load the application icon for the finished page.');
  FinishedIconImage.Width := 96;
  FinishedIconImage.Height := 96;

  FinishedBrandLabel := TLabel.Create(WizardForm.FinishedPage);
  FinishedBrandLabel.Parent := WizardForm.FinishedPage;
  FinishedBrandLabel.Caption := 'HJS';

  FinishedNameLabel := TLabel.Create(WizardForm.FinishedPage);
  FinishedNameLabel.Parent := WizardForm.FinishedPage;
  FinishedNameLabel.Caption := 'Workbench';

  FinishedVersionLabel := TLabel.Create(WizardForm.FinishedPage);
  FinishedVersionLabel.Parent := WizardForm.FinishedPage;
  FinishedVersionLabel.Caption := '{#MyAppVersion}';

  WizardForm.OnResize := @WizardFormResize;
  LayoutFinishedBrandBlock;
end;
