# Demo en vivo de la defensa - operacion desde PowerShell en la PC de la demo (HP Victus,
# Docker Desktop sobre WSL en modo espejo). Spec: docs/superpowers/specs/2026-10-23-demo-defensa-design.md
# Manual del dia: infra/demo/README.md. (Archivo en ASCII a proposito: Windows PowerShell 5.1
# lee los .ps1 sin BOM como ANSI y un acento o una raya rompen las comillas.)
#
#   .\infra\demo\demo.ps1 up                  stack + motor de la demo (sin recrear nada)
#   .\infra\demo\demo.ps1 check               chequeo del host -> defensa/sesiones/preflight_host.json
#   .\infra\demo\demo.ps1 smoke               la cadena completa con la camara de ensayo (G1)
#   .\infra\demo\demo.ps1 camara-ensayo on    prende / apaga la camara de ensayo (mediamtx + clip)
#   .\infra\demo\demo.ps1 restart-motor       reinicia el motor y lo deja "fresco" (F-101.5)
#   .\infra\demo\demo.ps1 respaldo <sesion>   marca una sesion como respaldo nivel 1 (tecla R)
#   .\infra\demo\demo.ps1 reset               control + distribucion + motor, para salir de una corrida colgada
#   .\infra\demo\demo.ps1 down                detiene el stack SIN borrar contenedores
#
# Reglas del doc 133 que este script respeta: nunca `docker compose up -d` que recree
# contenedores (tira el adaptador de red de WSL: solo lo arregla reiniciar Windows); un
# reinicio del motor entre corridas con la OAK-D.
param(
    [Parameter(Position = 0)][string]$Comando = 'help',
    [Parameter(Position = 1)][string]$Arg = ''
)
$ErrorActionPreference = 'Stop'

$Consola = if ($env:EOVRT_CONSOLE_URL) { $env:EOVRT_CONSOLE_URL } else { 'http://localhost:8090' }
$Motor = 'mp-gdino-tiny-560'
$Proyecto = 'eovrt'
$Platform = Join-Path $PSScriptRoot '..\platform'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Sesiones = Join-Path $Repo 'defensa\sesiones'
$Nucleo = @('mosquitto', 'control-plane', 'distribution', 'console')

function Compose { & (Join-Path $Platform 'compose.ps1') @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $args fallo" } }
function Contenedor([string]$servicio) { "$Proyecto-$servicio-1" }
function EstadoContenedor([string]$servicio) {
    $estado = docker inspect -f '{{.State.Status}}' (Contenedor $servicio) 2>$null
    if ($LASTEXITCODE -ne 0) { return 'ausente' }
    return $estado.Trim()
}
function Api([string]$metodo, [string]$ruta, $cuerpo = $null, [int]$timeout = 30) {
    $params = @{ Method = $metodo; Uri = "$Consola$ruta"; TimeoutSec = $timeout }
    if ($null -ne $cuerpo) { $params.Body = ($cuerpo | ConvertTo-Json -Depth 5); $params.ContentType = 'application/json' }
    return Invoke-RestMethod @params
}
function EsperarConsola([int]$segundos = 120) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        try { Invoke-RestMethod -Uri "$Consola/api/health" -TimeoutSec 3 | Out-Null; return } catch { Start-Sleep 2 }
    }
    throw "la consola no respondio en $segundos s ($Consola). Si NINGUN puerto responde: Inicio -> Reiniciar Windows (doc 133, sec. 5.5)."
}

function Up {
    New-Item -ItemType Directory -Force -Path $Sesiones | Out-Null
    $ausentes = @()
    foreach ($s in $Nucleo) {
        switch (EstadoContenedor $s) {
            'running' { Write-Host "  ${s}: corriendo" }
            'ausente' { $ausentes += $s }
            default { Write-Host "  ${s}: arrancando el contenedor existente"; docker start (Contenedor $s) | Out-Null }
        }
    }
    if ($ausentes.Count -gt 0) {
        Write-Warning "Faltan contenedores ($($ausentes -join ', ')): se CREAN con compose. Hacelo en la preparacion, nunca el dia de la demo: si despues ningun puerto responde, Inicio -> Reiniciar Windows."
        Compose up -d --no-build @ausentes
    }
    EsperarConsola
    Write-Host "Activando $Motor (espera readyz, hasta 5 min la primera vez)..."
    Api 'POST' "/api/platform/instances/$Motor/activate" $null 330 | Out-Null
    RestartMotor
    Write-Host 'Listo: abrir http://localhost:8090/demo (F11), y correr demo.ps1 check.'
}

function RestartMotor {
    Write-Host 'Reiniciando el motor (~20-30 s) para dejarlo fresco...'
    Api 'POST' '/api/demo/motor/reiniciar' | Out-Null
    $limite = (Get-Date).AddSeconds(330)
    while ((Get-Date) -lt $limite) {
        Start-Sleep 2
        $motor = (Api 'GET' '/api/demo/state').motor
        if ($motor.estado -eq 'fresco') { Write-Host "Motor fresco ($($motor.instancia))."; return }
        if ($motor.estado -eq 'error') { throw "el reinicio del motor fallo: $($motor.detalle)" }
    }
    throw 'el motor no quedo fresco a tiempo'
}

function Check {
    New-Item -ItemType Directory -Force -Path $Sesiones | Out-Null
    $chequeos = [ordered]@{}
    # Disco: el techo real es C: (el ext4.vhdx de WSL crece sobre el). Minimo 8 GB.
    $libreGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
    $chequeos.disco_c = @{ ok = ($libreGB -ge 8); detalle = "$libreGB GB libres en C: (minimo 8)" }
    # Cargador: a bateria la inferencia casi se duplica (doc 133, sec. 5.2).
    $bateria = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
    if ($bateria) { $chequeos.cargador = @{ ok = ($bateria.BatteryStatus -eq 2); detalle = "BatteryStatus=$($bateria.BatteryStatus) (2 = enchufada)" } }
    # Red: la Ethernet de la camara en 169.254.x.x y la camara respondiendo.
    $eth = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object IPAddress -like '169.254.*'
    $chequeos.ethernet_link_local = @{ ok = [bool]$eth; detalle = $(if ($eth) { "$($eth[0].InterfaceAlias) $($eth[0].IPAddress)" } else { 'ninguna interfaz en 169.254.x.x (cable directo a la camara, IP automatica)' }) }
    $ping = Test-Connection -ComputerName 169.254.31.137 -Count 1 -Quiet -ErrorAction SilentlyContinue
    $chequeos.camara_ping = @{ ok = [bool]$ping; detalle = '169.254.31.137 (el ping es un primer filtro; la prueba que vale es una corrida)' }
    # Wi-Fi de la sede en 172.20.x.x choca con la subred de Docker (doc 133, sec. 5.6).
    $choque = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object IPAddress -like '172.20.*'
    $chequeos.subred_docker = @{ ok = -not $choque; detalle = $(if ($choque) { "una interfaz del host esta en 172.20.x.x ($($choque[0].InterfaceAlias))" } else { 'sin choque con 172.20.0.0/16' }) }
    $zt = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.InterfaceDescription -like '*ZeroTier*' -and $_.Status -eq 'Up' }
    $chequeos.zerotier_caido = @{ ok = -not $zt; detalle = $(if ($zt) { 'ZeroTier arriba: bajarlo' } else { 'ok' }) }
    $gpu = (& nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>$null) -join '; '
    $chequeos.gpu = @{ ok = [bool]$gpu; detalle = $(if ($gpu) { $gpu } else { 'nvidia-smi no respondio' }) }
    $faltan = @($Nucleo + $Motor | Where-Object { (EstadoContenedor $_) -ne 'running' })
    $chequeos.contenedores = @{ ok = ($faltan.Count -eq 0); detalle = $(if ($faltan.Count) { "sin correr: $($faltan -join ', ')" } else { 'nucleo y motor corriendo' }) }
    $sistema = Get-CimInstance Win32_ComputerSystem
    $datos = [ordered]@{
        generado_en = (Get-Date).ToUniversalTime().ToString('o')
        origen = 'demo.ps1 check (Windows)'
        equipo = "$($sistema.Manufacturer) $($sistema.Model)"
        ram_gb = [math]::Round($sistema.TotalPhysicalMemory / 1GB, 1)
        gpu = $gpu
        docker = ((docker version --format '{{.Server.Platform.Name}} {{.Server.Version}}') 2>$null)
        chequeos = $chequeos
    }
    $destino = Join-Path $Sesiones 'preflight_host.json'
    # UTF-8 sin BOM (lo lee Python): Set-Content -Encoding utf8 de PS 5.1 agrega BOM.
    [System.IO.File]::WriteAllText($destino, ($datos | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding $false))
    foreach ($k in $chequeos.Keys) {
        $c = $chequeos[$k]
        $marca = if ($c.ok) { 'OK' } else { 'XX' }
        Write-Host "$marca  $k - $($c.detalle)"
    }
    Write-Host "-> $destino"
}

function CamaraEnsayo([string]$accion) {
    if ($accion -eq 'on') {
        Compose -f docker-compose.yml -f docker-compose.demo.yml up -d --no-build mediamtx ensayo-camara
        Write-Host 'Camara de ensayo arriba: rtsp://mediamtx:8554/ensayo (desde el host: rtsp://127.0.0.1:8554/ensayo).'
    } elseif ($accion -eq 'off') {
        Compose -f docker-compose.yml -f docker-compose.demo.yml stop ensayo-camara mediamtx
    } else { throw 'uso: demo.ps1 camara-ensayo on|off' }
}

function Smoke {
    CamaraEnsayo 'on'
    Start-Sleep 5
    $pf = Api 'GET' '/api/demo/preflight'
    if (-not $pf.listo) {
        $pf.items | Where-Object estado -eq 'error' | ForEach-Object { Write-Host "XX $($_.nombre): $($_.detalle) - $($_.accion)" }
        throw 'chequeo previo en rojo'
    }
    $inicio = Api 'POST' '/api/demo/start' @{ variante = 'ensayo' } 60
    Write-Host "Sesion $($inicio.session_id): esperando el primer cuadro..."
    $limite = (Get-Date).AddSeconds(90)
    do { Start-Sleep 1; $st = Api 'GET' '/api/demo/state' } while ($st.fase -eq 'preparing' -and (Get-Date) -lt $limite)
    if ($st.fase -ne 'live') { throw "no llego a Listo (fase $($st.fase)): $($st.error)" }
    Write-Host 'En vivo: esperando un CR-01 confirmado y su mensaje en el broker (hasta 90 s)...'
    $limite = (Get-Date).AddSeconds(90)
    do {
        Start-Sleep 1
        $st = Api 'GET' '/api/demo/state'
        $cr01 = $st.condiciones | Where-Object condicion -eq 'CR-01'
    } while (-not ($cr01.alertas -ge 1 -and $cr01.broker -eq 'recibido') -and (Get-Date) -lt $limite)
    $alerta = ($cr01.alertas -ge 1)
    $broker = ($cr01.broker -eq 'recibido')
    Api 'POST' '/api/demo/finish' | Out-Null
    $limite = (Get-Date).AddSeconds(180)
    do { Start-Sleep 2; $st = Api 'GET' '/api/demo/state' } while ($st.fase -notin @('done', 'failed') -and (Get-Date) -lt $limite)
    $detalle = Api 'GET' "/api/demo/sessions/$($inicio.session_id)"
    CamaraEnsayo 'off'
    $video = [bool]$detalle.resumen.video
    Write-Host ''
    Write-Host "CR-01 confirmado: $alerta | mensaje en el broker: $broker | sesion: $($st.fase) | video: $video"
    Write-Host "Resultado: $Consola/demo/resultado/$($inicio.session_id)"
    if (-not ($alerta -and $broker -and $st.fase -eq 'done' -and $video)) { throw 'SMOKE G1 EN ROJO' }
    Write-Host 'SMOKE G1 EN VERDE'
}

function Reset {
    Write-Host 'Reiniciando control-plane y distribucion (sin recrear)...'
    docker restart (Contenedor 'control-plane') (Contenedor 'distribution') | Out-Null
    EsperarConsola
    RestartMotor
}

switch ($Comando) {
    'up' { Up }
    'check' { Check }
    'smoke' { Smoke }
    'camara-ensayo' { CamaraEnsayo $Arg }
    'restart-motor' { RestartMotor }
    'respaldo' {
        if (-not $Arg) { throw 'uso: demo.ps1 respaldo <session_id>' }
        Api 'POST' "/api/demo/sessions/$Arg/respaldo" | Out-Null
        Write-Host "Respaldo nivel 1 (tecla R): $Arg"
    }
    'reset' { Reset }
    'down' { Compose stop; Write-Host 'Stack detenido (los contenedores quedan: el proximo up no los recrea).' }
    { $_ -in @('native-up', 'native-down') } {
        Write-Host 'La Victus no tiene entorno nativo (doc 133, sec. 6): el respaldo nativo de la spec (D-3) no aplica aca.'
        Write-Host 'Respaldo en esta PC: nivel 1 (tecla R), nivel 2 (grabacion del ensayo) y el plan B de camara (camara-ensayo).'
    }
    default { Get-Content $PSCommandPath | Select-Object -First 16 | ForEach-Object { $_ -replace '^# ?', '' } }
}
