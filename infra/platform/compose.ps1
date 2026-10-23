# Docker Desktop: ejecutar Compose con las mismas rutas Linux que usa la consola.
$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$envFile = Join-Path $PSScriptRoot '.env'
$workspaceEntry = Get-Content -LiteralPath $envFile |
    Where-Object { $_ -match '^EOVRT_WORKSPACE=' } |
    Select-Object -First 1
if (-not $workspaceEntry) {
    throw 'Defini EOVRT_WORKSPACE en infra/platform/.env con la ruta Linux de Docker Desktop.'
}
$containerWorkspace = $workspaceEntry.Substring('EOVRT_WORKSPACE='.Length).Trim()
& docker run --rm `
    --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock `
    --mount "type=bind,source=$workspace,target=$containerWorkspace" `
    --workdir "$containerWorkspace/e-ovrt_experimental-setup/infra/platform" `
    docker:cli compose @args
exit $LASTEXITCODE
