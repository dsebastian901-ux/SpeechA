param(
    [Parameter(Mandatory=$true)][string]$ReleaseVersion,
    [Parameter(Mandatory=$true)][string]$DistributionDir,
    [Parameter(Mandatory=$true)][string]$IsccPath
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'La compilacion final y prueba del instalador requieren Windows.' }
$readiness = Get-Content (Join-Path $PSScriptRoot 'release-readiness.json') -Raw | ConvertFrom-Json
$requirements = @('authentication_integrated','offline_usb_accounts_integrated','operator_permissions_enforced',
'administrator_reviews_guarded','user_data_outside_program_directory','full_model_and_runtime_bundled',
'windows_offline_two_computers_verified','regression_for_installed_candidate_passed')
$missing = @($requirements | Where-Object { $readiness.$_ -ne $true })
if ($missing.Count -gt 0) { throw ('Entrega bloqueada; faltan verificaciones: ' + ($missing -join ', ')) }
$executable = Join-Path $DistributionDir 'MRS-Speech-Analytics.exe'
if (!(Test-Path $executable -PathType Leaf)) { throw 'Falta el ejecutable compilado.' }
$model = Join-Path $DistributionDir '_internal\app\resources\models\small'
foreach ($name in @('model.bin','config.json','tokenizer.json')) {
    $file = Join-Path $model $name
    if (!(Test-Path $file -PathType Leaf)) { throw ('Falta archivo del modelo offline: ' + $name) }
    if ((Get-Item $file).Length -eq 0) { throw ('Archivo del modelo vacio: ' + $name) }
}
if (!(Test-Path $IsccPath -PathType Leaf)) { throw 'Falta Inno Setup 6 (ISCC.exe) en el equipo de compilacion.' }
& $IsccPath "/DReleaseVersion=$ReleaseVersion" "/DDistributionDir=$DistributionDir" (Join-Path $PSScriptRoot 'MRS.iss')
if ($LASTEXITCODE -ne 0) { throw 'No se completo la compilacion del instalador.' }
