# Plataforma E-OVRT desde PowerShell (PC de la demo, Docker Desktop): levanta lo que falte y
# verifica que todo este listo para ejecutar cualquier cosa. Gemelo de plataforma.sh (mismo
# orden y mismas guardas). Archivo en ASCII a proposito: Windows PowerShell 5.1 lee los .ps1
# sin BOM como ANSI y un acento o una raya rompen las comillas.
#
#   .\infra\platform\plataforma.ps1 [up]          asegura la plataforma (default)
#   .\infra\platform\plataforma.ps1 estado        solo mira y informa; no cambia nada
#   .\infra\platform\plataforma.ps1 construir [servicio...] [-ConMedia] [-Recrear]
#   .\infra\platform\plataforma.ps1 bajar         detiene todo SIN borrar contenedores
#
# Opciones de `up`:  -Modelo <instancia>  (default mp-gdino-tiny-560, el campeon)
#                    -SinModelo           no activa ninguna instancia de modelo
#                    -SinMotorFresco      no reinicia el motor para dejarlo "fresco"
#                    -Forzar              sigue aunque haya una sesion en curso o poco disco
#
# Reglas: NUNCA `docker compose up -d` a secas (el .env trae COMPOSE_PROFILES=models y arrancaria
# los 9 modelos juntos); aca siempre se nombran los servicios. Nunca recrea un contenedor que ya
# existe (doc 133, sec. 5.5): arranca el existente. Ningun build del media-plane sin >= 35 GB
# libres en C:. La memoria de la VM de WSL solo se mide desde WSL (plataforma.sh).
param(
    [Parameter(Position = 0)][string]$Comando = 'up',
    [string]$Modelo = 'mp-gdino-tiny-560',
    [switch]$SinModelo,
    [switch]$SinMotorFresco,
    [switch]$Forzar,
    [switch]$ConMedia,
    [switch]$Recrear,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Servicios
)
$ErrorActionPreference = 'Stop'

# 127.0.0.1 y no localhost: en Windows PowerShell 5.1 `localhost` puede resolver primero a IPv6 y
# colgarse hasta el timeout aunque la consola este sana (verificado en la PC de desarrollo).
$Consola = if ($env:EOVRT_CONSOLE_URL) { $env:EOVRT_CONSOLE_URL } else { 'http://127.0.0.1:8090' }
$Proyecto = 'eovrt'
$Nucleo = @('mosquitto', 'control-plane', 'distribution', 'console')
$DiscoCriticoGb = 4
$DiscoMinGb = 8
$DiscoBuildGb = 8
$DiscoBuildMediaGb = 35
$script:Fallas = 0
$script:Avisos = 0

function Ok([string]$m) { Write-Host "  [ok] $m" -ForegroundColor Green }
function Av([string]$m) { Write-Host "  [!]  $m" -ForegroundColor Yellow; $script:Avisos++ }
function Fa([string]$m) { Write-Host "  [X]  $m" -ForegroundColor Red; $script:Fallas++ }
function Paso([string]$m) { Write-Host ''; Write-Host "== $m" }

function Compose { & (Join-Path $PSScriptRoot 'compose.ps1') @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $args fallo" } }
function Contenedor([string]$servicio) { "$Proyecto-$servicio-1" }
function ImagenDe([string]$servicio) {
    if ($servicio -eq 'mosquitto') { return 'eclipse-mosquitto:2' }
    if ($servicio -like 'mp-*') { return 'eovrt/media-plane:latest' }
    return "eovrt/${servicio}:latest"
}
function ExisteImagen([string]$imagen) { docker image inspect $imagen 2>$null | Out-Null; return ($LASTEXITCODE -eq 0) }
function EstadoContenedor([string]$servicio) {
    $estado = docker inspect -f '{{.State.Status}}' (Contenedor $servicio) 2>$null
    if ($LASTEXITCODE -ne 0) { return 'ausente' }
    return $estado.Trim()
}
function SaludContenedor([string]$servicio) {
    $salud = docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-healthcheck{{end}}' (Contenedor $servicio) 2>$null
    if ($LASTEXITCODE -ne 0) { return 'ausente' }
    return $salud.Trim()
}
function Api([string]$metodo, [string]$ruta, [int]$timeout = 30) {
    $params = @{ Method = $metodo; Uri = "$Consola$ruta"; TimeoutSec = $timeout }
    if ($metodo -eq 'POST') { $params.Body = ''; $params.ContentType = 'application/json' }
    return Invoke-RestMethod @params
}
# Windows PowerShell 5.1 entrega un arreglo JSON de nivel superior como UN solo objeto (un Object[]
# adentro de otro): `.ready` daba un arreglo de 9 valores y `-and` lo tomaba por verdadero.
function Aplanar($x) { foreach ($e in @($x)) { if ($e -is [System.Array]) { Aplanar $e } else { $e } } }
function DiscoLibreGb { [math]::Floor((Get-PSDrive -Name C).Free / 1GB) }
function EsperarSaludable([string]$servicio, [int]$segundos = 120) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        if ((SaludContenedor $servicio) -in @('healthy', 'sin-healthcheck')) { return $true }
        Start-Sleep 2
    }
    return $false
}

function VerificarDocker {
    Paso 'Docker'
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker no responde. Abri Docker Desktop. Si ningun puerto responde: Inicio -> Reiniciar Windows.'
    }
    Ok "Docker $((docker version --format '{{.Server.Version}}' 2>$null)) responde"
}

function VerificarRecursos {
    Paso 'Recursos'
    $d = DiscoLibreGb
    if ($d -lt $DiscoCriticoGb) { Fa "C: con $d GB libres (< $DiscoCriticoGb): no se crea ni se carga nada hasta liberar espacio" }
    elseif ($d -lt $DiscoMinGb) { Av "C: con $d GB libres (< $DiscoMinGb): justo; los discos virtuales de Docker/WSL crecen sobre C:" }
    else { Ok "C: con $d GB libres" }
}

function LevantarNucleo {
    Paso 'Nucleo (mosquitto, control-plane, distribution, console)'
    $ausentes = @(); $arrancados = @()
    foreach ($s in $Nucleo) {
        switch (EstadoContenedor $s) {
            'running' { Ok "${s}: corriendo" }
            'ausente' {
                if (ExisteImagen (ImagenDe $s)) { $ausentes += $s }
                else { Fa "${s}: no existe el contenedor ni la imagen $(ImagenDe $s) -> plataforma.ps1 construir $s" }
            }
            default { Write-Host "  . ${s}: arrancando el contenedor existente"; docker start (Contenedor $s) | Out-Null; $arrancados += $s }
        }
    }
    if ($ausentes.Count -gt 0) {
        Av "faltan contenedores ($($ausentes -join ', ')): se CREAN con compose, nombrandolos. Hacelo en la preparacion, no el dia de la demo."
        try { Compose up -d --no-build @ausentes | Out-Null; $arrancados += $ausentes } catch { Fa "compose no pudo crear: $($ausentes -join ', ')" }
    }
    foreach ($s in $Nucleo) {
        if ((EstadoContenedor $s) -eq 'ausente') { continue }
        if (EsperarSaludable $s 120) { if ($arrancados -contains $s) { Ok "${s}: healthy" } }
        else { Fa "${s}: no quedo healthy en 120 s (docker logs $(Contenedor $s))" }
    }
}

function EsperarConsola {
    Paso "Consola ($Consola)"
    $limite = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $limite) {
        try { Invoke-RestMethod -Uri "$Consola/api/health" -TimeoutSec 3 | Out-Null; Ok 'la consola responde'; return $true } catch { Start-Sleep 2 }
    }
    Fa 'la consola no respondio en 120 s. Si NINGUN puerto responde: Inicio -> Reiniciar Windows.'
    return $false
}

function AsegurarModelo {
    Paso "Instancia de modelo: $Modelo"
    try { $lista = @(Aplanar (Api 'GET' '/api/platform/instances' 20)) } catch { Fa 'no pude leer /api/platform/instances'; return }
    $fila = $lista | Where-Object { $_.name -eq $Modelo } | Select-Object -First 1
    if (-not $fila) { Fa "$Modelo no esta en el fleet: $(($lista | ForEach-Object { $_.name }) -join ', ')"; return }
    if ($fila.ready -and $fila.is_target -and (EstadoContenedor $Modelo) -eq 'running') { Ok "$Modelo ya es el target y esta listo"; return }
    if ((EstadoContenedor $Modelo) -eq 'ausente') {
        if (-not (ExisteImagen (ImagenDe $Modelo))) {
            Fa "falta la imagen $(ImagenDe $Modelo) -> plataforma.ps1 construir media-plane -ConMedia (necesita >= $DiscoBuildMediaGb GB libres)"
            return
        }
        Av "$Modelo no existe: se CREA (sin arrancar) con compose. Hacelo en la preparacion, no el dia de la demo."
        try { Compose --profile models create $Modelo | Out-Null } catch { Fa "compose no pudo crear $Modelo"; return }
    }
    if ((DiscoLibreGb) -lt $DiscoCriticoGb -and -not $Forzar) { Fa "C: con poco espacio: no cargo el modelo (-Forzar para seguir igual)"; return }
    Write-Host "  . activando $Modelo (la consola apaga cualquier otro modelo y espera readyz; hasta ~5 min)..."
    try { $r = Api 'POST' "/api/platform/instances/$Modelo/activate" 340; Ok "activa: $($r.model_ref)" }
    catch { Fa "no se pudo activar ${Modelo}: $($_.Exception.Message)" }
}

function ReiniciarMotor {
    Write-Host '  . reiniciando el motor (~20-30 s) para dejarlo fresco...'
    try { Api 'POST' '/api/demo/motor/reiniciar' | Out-Null } catch { Fa 'la consola no acepto reiniciar el motor'; return }
    $limite = (Get-Date).AddSeconds(330)
    while ((Get-Date) -lt $limite) {
        Start-Sleep 2
        $motor = (Api 'GET' '/api/demo/state' 10).motor
        if ($motor.estado -eq 'fresco') { Ok 'motor fresco'; return }
        if ($motor.estado -eq 'error') { Fa 'el reinicio del motor fallo'; return }
    }
    Fa 'el motor no quedo fresco en 330 s'
}

function AsegurarMotorFresco {
    Paso 'Motor fresco (lo pide la demo: una corrida con la OAK-D por vida del proceso, F-101.5)'
    $estado = Api 'GET' '/api/demo/state' 10
    if ($estado.motor.estado -eq 'fresco') { Ok 'el motor ya esta fresco'; return }
    $sesion = ((Api 'GET' '/api/demo/preflight' 20).items | Where-Object { $_.id -eq 'sesion' }).estado
    if (-not $Forzar -and ($sesion -ne 'ok' -or $estado.fase -in @('preparing', 'live', 'finishing', 'rendering'))) {
        Av "hay una sesion o un experimento en curso (fase=$($estado.fase)): no reinicio el motor (-Forzar para hacerlo igual)"
        return
    }
    ReiniciarMotor
}

function VerificarPlataforma {
    Paso 'Chequeo de la plataforma (/api/preflight)'
    try { $pf = Api 'GET' '/api/preflight' 30 } catch { Fa 'no pude leer /api/preflight'; return }
    if ($pf.ready) { Ok "lista: motor $($pf.media.model.ref), control y distribucion respondiendo" }
    else { Fa "no lista: $($pf.blockers -join '; ')" }
}

function VerificarDemo {
    Paso 'Chequeo de la demo (/api/demo/preflight)'
    try { $pf = Api 'GET' '/api/demo/preflight' 30 } catch { Fa 'no pude leer /api/demo/preflight'; return }
    foreach ($i in $pf.items) {
        $extra = if ($i.accion -and $i.estado -ne 'ok') { " -> $($i.accion)" } else { '' }
        $linea = "$($i.nombre): $($i.detalle)$extra"
        switch ($i.estado) { 'ok' { Ok $linea } 'aviso' { Write-Host "  [!]  $linea" -ForegroundColor Yellow } default { Write-Host "  [X]  $linea" -ForegroundColor Red } }
    }
    if ($pf.listo) { Ok 'la demo puede iniciarse (la tecla I funciona)' } else { Fa 'la demo todavia no puede iniciarse' }
    $host_ = $pf.items | Where-Object { $_.id -eq 'host' }
    if ($host_ -and $host_.estado -ne 'ok') { Av 'el chequeo del host es el de la PC con la OAK-D: infra\demo\demo.ps1 check (no bloquea la tecla I)' }
}

function Resumen {
    Paso 'Resumen'
    foreach ($s in ($Nucleo + $Modelo)) {
        Write-Host ('  {0,-28} {1} ({2})' -f (Contenedor $s), (EstadoContenedor $s), (SaludContenedor $s))
    }
    Write-Host ''
    if ($script:Fallas -eq 0) {
        Write-Host "  PLATAFORMA LISTA ($($script:Avisos) aviso(s))  -  consola: $Consola/#/demo   (P = proyeccion)" -ForegroundColor Green
        return 0
    }
    Write-Host "  NO ESTA LISTA: $($script:Fallas) falla(s), $($script:Avisos) aviso(s). Revisa los [X] de arriba." -ForegroundColor Red
    Write-Host '  Para dejarla lista:  .\infra\platform\plataforma.ps1 up'
    return 1
}

function CmdUp {
    VerificarDocker; VerificarRecursos; LevantarNucleo
    if (-not (EsperarConsola)) { return (Resumen) }
    if (-not $SinModelo) { AsegurarModelo }
    if (-not $SinModelo -and -not $SinMotorFresco) { AsegurarMotorFresco }
    if (-not $SinModelo -and (EstadoContenedor $Modelo) -eq 'running') {
        if (-not (EsperarSaludable $Modelo 120)) { Av "$Modelo no quedo healthy en 120 s" }
    }
    VerificarPlataforma; VerificarDemo
    return (Resumen)
}

function CmdEstado {
    VerificarDocker; VerificarRecursos
    Paso 'Contenedores'
    foreach ($s in $Nucleo) {
        switch (EstadoContenedor $s) {
            'running' { if ((SaludContenedor $s) -in @('healthy', 'sin-healthcheck')) { Ok "${s}: corriendo ($(SaludContenedor $s))" } else { Av "${s}: corriendo pero $(SaludContenedor $s)" } }
            'ausente' { Fa "${s}: no existe" }
            default { Fa "${s}: $(EstadoContenedor $s)" }
        }
    }
    try { Invoke-RestMethod -Uri "$Consola/api/health" -TimeoutSec 5 | Out-Null } catch { Fa "la consola no responde en $Consola"; return (Resumen) }
    Paso 'Modelos'
    foreach ($i in (Aplanar (Api 'GET' '/api/platform/instances' 20))) {
        if ($i.state -eq 'running' -or $i.is_target) { Write-Host ("  {0} {1}: {2}{3}" -f $(if ($i.is_target) { '*' } else { '.' }), $i.name, $i.state, $(if ($i.ready) { ' listo' } else { '' })) }
    }
    VerificarPlataforma; VerificarDemo
    return (Resumen)
}

function CmdConstruir {
    if (-not $Servicios -or $Servicios.Count -eq 0) { $Servicios = @('console', 'control-plane', 'distribution') }
    VerificarDocker
    $minimo = $DiscoBuildGb
    foreach ($s in $Servicios) {
        if ($s -eq 'media-plane' -or $s -like 'mp-*') {
            $minimo = $DiscoBuildMediaGb
            if (-not $ConMedia) { throw "el media-plane pesa 13 GB y duplica capas: agrega -ConMedia (necesita >= $DiscoBuildMediaGb GB libres en C:)" }
        }
    }
    $d = DiscoLibreGb
    if ($d -lt $minimo) { throw "C: con $d GB libres; este build necesita >= $minimo GB. Libera espacio (o compacta los vhdx) antes." }
    Write-Host "  C: libres antes: $d GB - construyendo: $($Servicios -join ' ')"
    Compose build @Servicios
    Write-Host "  C: libres despues: $(DiscoLibreGb) GB"
    if ($Recrear) {
        Write-Host "  recreando SOLO: $($Servicios -join ' ') (si despues ningun puerto responde: Inicio -> Reiniciar Windows)"
        Compose up -d --no-build @Servicios
    } else {
        Write-Host "  imagen lista. Para que la use el contenedor:  plataforma.ps1 construir $($Servicios -join ' ') -Recrear"
    }
}

function CmdBajar {
    VerificarDocker
    if (-not $Forzar) {
        try {
            Invoke-RestMethod -Uri "$Consola/api/health" -TimeoutSec 3 | Out-Null
            $sesion = ((Api 'GET' '/api/demo/preflight' 20).items | Where-Object { $_.id -eq 'sesion' }).estado
            if ($sesion -and $sesion -ne 'ok') { throw 'hay una sesion o un experimento en curso: terminalo antes (o -Forzar)' }
        } catch [System.Net.WebException] { }
    }
    Paso 'Deteniendo (sin borrar contenedores)'
    foreach ($c in (docker ps --format '{{.Names}}' | Where-Object { $_ -like "$Proyecto-mp-*" })) { docker stop $c | Out-Null; Ok "$c detenido" }
    foreach ($s in @('console', 'distribution', 'control-plane', 'mosquitto')) {
        if ((EstadoContenedor $s) -eq 'running') { docker stop (Contenedor $s) | Out-Null; Ok "$s detenido" }
    }
    Write-Host '  Para volver:  .\infra\platform\plataforma.ps1 up'
}

switch ($Comando) {
    'up' { exit ([int]@(CmdUp)[-1]) }
    'estado' { exit ([int]@(CmdEstado)[-1]) }
    'construir' { CmdConstruir }
    'bajar' { CmdBajar }
    default { Get-Content $PSCommandPath | Select-Object -First 21 | ForEach-Object { $_ -replace '^# ?', '' } }
}
