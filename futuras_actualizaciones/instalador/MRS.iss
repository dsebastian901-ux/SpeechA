; Receta para Inno Setup 6 / Windows. No es un instalador ya compilado.
; Build-Release.ps1 debe aprobar las verificaciones antes de ejecutar ISCC.
#ifndef ReleaseVersion
  #error Debe definir ReleaseVersion desde la compilacion validada.
#endif
#ifndef DistributionDir
  #error Debe definir DistributionDir con la aplicacion compilada y validada.
#endif
#define ProductName "MRS Speech Analytics"
[Setup]
AppId={{41617303-D6F0-47C6-A2B8-719A81C55499}
AppName={#ProductName}
AppVersion={#ReleaseVersion}
DefaultDirName={localappdata}\Programs\MRS Speech Analytics
DefaultGroupName=MRS Speech Analytics
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=assets\MRS.ico
UninstallDisplayIcon={app}\MRS-Speech-Analytics.exe
OutputBaseFilename=MRS-Speech-Analytics-Setup-{#ReleaseVersion}
OutputDir=output
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
[Files]
Source: "{#DistributionDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.bat,*.cmd,*.ps1,*.py,*.pyw,tests\*,tools\*,data\*,logs\*,reports\*,*checkpoint*.json"
[Icons]
Name: "{userdesktop}\MRS Speech Analytics"; Filename: "{app}\MRS-Speech-Analytics.exe"; WorkingDir: "{app}"
Name: "{group}\MRS Speech Analytics"; Filename: "{app}\MRS-Speech-Analytics.exe"; WorkingDir: "{app}"
[Run]
Filename: "{app}\MRS-Speech-Analytics.exe"; Description: "Abrir MRS Speech Analytics"; Flags: nowait postinstall skipifsilent
; No borrar cuentas, proyectos ni resultados en LocalAppData\MRS Speech Analytics.
; El ejecutable debe almacenar esos datos fuera de la carpeta de instalacion.
