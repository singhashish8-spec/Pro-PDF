; Inno Setup script for PDF Pro (Blueprint v2, Section 10 Phase 10).
; Built by .github/workflows/windows-build.yml on a windows-latest runner,
; against the PyInstaller output in dist\PDF Pro\.
; Unsigned installer — fine for the internal phase (Section 3); code signing
; becomes relevant only at external release.

#define MyAppName "PDF Pro"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "PDF Pro"
#define MyAppExeName "PDF Pro.exe"

[Setup]
AppId={{B6E1B4B0-6C7D-4B9D-9C6A-9E7B6B9F2C10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=PDFPro-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Source paths are relative to this .iss file's own directory (packaging\),
; not the working directory ISCC is invoked from — PyInstaller's output
; lives at the repo root's dist\, one level up.
Source: "..\dist\PDF Pro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
