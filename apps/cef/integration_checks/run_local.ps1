[CmdletBinding()]
param(
    [ValidateSet('offline','audit')][string]$Mode = 'offline',
    [string[]]$Only,
    [string]$Report
)
$ErrorActionPreference = 'Stop'
$CefArguments = @('--mode', $Mode)
if ($Mode -eq 'offline') {
    if ($Only) { $CefArguments += @('--only') + $Only }
} else {
    if ($Only) { throw 'La auditoria no acepta casos offline.' }
    Write-Host 'Usar exclusivamente un servicio PostgreSQL ya configurado para un rol de solo lectura.'
    Write-Host 'No ingresar claves ni datos personales. Este modo queda pendiente de revision por ChatGPT.'
    $CefService = Read-Host 'Nombre del servicio PostgreSQL RO'
    $CefDb = Read-Host 'Nombre esperado de la BD'
    $CefHost = Read-Host 'IP literal esperada del servidor'
    $CefPortText = Read-Host 'Puerto esperado'
    $CefCycleText = Read-Host 'PK del ciclo confirmado localmente'
    $CefPort = 0; $CefCycle = 0
    if (-not [int]::TryParse($CefPortText,[ref]$CefPort) -or $CefPort -lt 1 -or $CefPort -gt 65535) {
        throw 'Puerto invalido.'
    }
    if (-not [int]::TryParse($CefCycleText,[ref]$CefCycle) -or $CefCycle -lt 1) {
        throw 'Ciclo invalido.'
    }
    if (-not $CefService -or -not $CefDb -or -not $CefHost) {
        throw 'Faltan metadatos explicitos del servicio RO.'
    }
    $CefArguments += @('--service',$CefService,'--expect-db',$CefDb,
        '--expect-host',$CefHost,'--expect-port',"$CefPort",'--cycle',"$CefCycle")
}
if ([string]::IsNullOrWhiteSpace($Report)) {
    $Report = Join-Path -Path (Get-Location).Path -ChildPath (
        'cef-{0}-{1}-{2}.json' -f $Mode,(Get-Date -Format 'yyyyMMdd-HHmmss'),
        ([guid]::NewGuid().ToString('N').Substring(0,8)))
}
$CefArguments += @('--report',$Report)
& python -B (Join-Path -Path $PSScriptRoot -ChildPath 'run.py') @CefArguments
exit $LASTEXITCODE
