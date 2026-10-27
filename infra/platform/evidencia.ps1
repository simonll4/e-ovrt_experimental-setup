# Driver de evidencia de la generacion 2 (doc 134) desde PowerShell: lo corre DENTRO del
# contenedor de la consola (paridad de rutas, red del compose, docker CLI).
#
#   .\evidencia.ps1 lista
#   .\evidencia.ps1 verificar F1 F3
#   .\evidencia.ps1 correr INT-01 INT-02 INT-03 PLAT-01 GT-01
#   .\evidencia.ps1 -Fondo correr F3       # sigue aunque se cierre la terminal
#   .\evidencia.ps1 estado
#   .\evidencia.ps1 vivo RT-03 --toma lat_a --config 960x540@5   (el rodaje en vivo, RT-04: .\rodaje.ps1)
#   .\evidencia.ps1 veredicto ALR-01 identico --motivo "..." --quien "Nombre"
#
# Con -Fondo la salida va a e-ovrt_experimental-setup\results\gen2\_registro\<hora>.log.
# El driver se retoma donde quedo: si se corta, se vuelve a lanzar el mismo comando.
param(
    [switch]$Fondo,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Resto
)
$ErrorActionPreference = 'Stop'
$contenedor = if ($env:EOVRT_CONSOLE_CONTAINER) { $env:EOVRT_CONSOLE_CONTAINER } else { 'eovrt-console-1' }

if (-not $Resto -or $Resto.Count -eq 0) {
    Get-Content -LiteralPath $PSCommandPath -TotalCount 13 | Select-Object -Skip 1
    exit 2
}
$corriendo = & docker ps --format '{{.Names}}'
if (-not ($corriendo -contains $contenedor)) {
    Write-Error "el contenedor $contenedor no esta corriendo: levantar la plataforma (infra/platform/README.md)"
    exit 2
}

if ($Fondo) {
    $hora = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    $script = 'cd "$EOVRT_CONSOLE_REPO_ROOT" && mkdir -p results/gen2/_registro && exec python -m tools.evidencia "$@" > "results/gen2/_registro/$0.log" 2>&1'
    & docker exec -d -e PYTHONDONTWRITEBYTECODE=1 $contenedor sh -c $script $hora @Resto
    Write-Host "corriendo en segundo plano."
    Write-Host "  log:      e-ovrt_experimental-setup\results\gen2\_registro\$hora.log"
    Write-Host "  progreso: .\evidencia.ps1 estado"
    exit $LASTEXITCODE
}
$script = 'cd "$EOVRT_CONSOLE_REPO_ROOT" && exec python -m tools.evidencia "$@"'
& docker exec -i -e PYTHONDONTWRITEBYTECODE=1 $contenedor sh -c $script sh @Resto
exit $LASTEXITCODE
