# Director de tomas del rodaje en vivo (generacion 2, prueba RT-04; doc 134).
#
# Cada toma es una sesion de la demo (/demo) etiquetada con su escena. Este script:
#   1. espera a que el chequeo previo de la demo este en verde (motor fresco, broker, camara);
#   2. mide el desfase entre el reloj del host y el de los contenedores;
#   3. lanza la sesion con la escena (POST /api/demo/start);
#   4. cuando llega el primer cuadro, dice el guion de la escena por los parlantes (tono + voz)
#      y anota la hora REAL de cada indicacion;
#   5. al terminar el guion cierra la sesion (lo mismo que F F en /demo) y deja marcas.json
#      junto a la sesion, en defensa\sesiones\<sesion>\.
# La pantalla /demo (en el proyector o en otra ventana) muestra todo en vivo y, al final, el
# Resultado de la toma. Despues: .\evidencia.ps1 correr RT-04 importa las sesiones.
#
# Uso (-Chaleco es obligatorio en cada toma: julio = los chalecos reflectantes del rodaje de julio,
# los de RT-04/RT-05/RT-06; amarillo = el amarillo no reflectivo, prueba RT-07; doc 134 13.14):
#   .\rodaje.ps1 -Lista                                  # las escenas y su guion
#   .\rodaje.ps1 -Escena P1 -Chaleco julio               # una toma de P1 (RT-04)
#   .\rodaje.ps1 -Escena DEMO -Chaleco julio             # un ensayo de la demo (cuenta para G3)
#   .\rodaje.ps1 -Escena P2 -Chaleco amarillo            # una toma de RT-07 (chaleco amarillo)
#   .\rodaje.ps1 -Escena P2 -Chaleco amarillo -Fuente rtsp_dvr_sub   # RT-08 (amarillo + camara IP)
#   .\rodaje.ps1 -Escena P2 -Chaleco julio -SinVoz       # sin parlantes: el guion sale solo por pantalla
#
# Exploracion (prueba RT-05): la misma escena con otro motor u otra cadencia de camara, de la
# lista cerrada de experiments\demo_defensa\exploracion.yaml. Activa la instancia si no es la
# activa, deja el motor fresco y marca la sesion como exploracion (RT-04 no la cuenta):
#   .\rodaje.ps1 -Escena DEMO -Chaleco julio -Motor mp-yoloe-26s -Camara 960x540@15
# Al terminar la exploracion, volver al campeon: ..\demo\demo.ps1 up
#
# Camara IP (prueba RT-06, enmienda 2026-11-01): las escenas del subset del guion (P1, P2, P5) con
# la camara IP por RTSP en vez de la OAK-D. Una camara a la vez, directo a la Ethernet. -Fuente es
# el id del preset de cameras/, uno por stream: el secundario (/Streaming/Channels/2) y el
# principal (/Streaming/Channels/1). Antes de cada toma se comprueba que la camara entregue video:
#   .\rodaje.ps1 -Escena P1 -Chaleco julio -Fuente rtsp_dvr_sub     # secundario
#   .\rodaje.ps1 -Escena P1 -Chaleco julio -Fuente rtsp_dvr_1       # principal
#   ..\evidencia.ps1 correr RT-06
#
# No se graba ni se anota nada: son tomas en vivo. La marca de cada accion es el instante del
# tono; el tiempo de reaccion del actor queda DENTRO de la medicion (declarado).
param(
    [string]$Escena,
    [string]$Motor,
    [string]$Camara,
    [string]$Fuente,
    # CR-02 depende del chaleco: cada toma lo declara y el driver la cuenta solo en la prueba que fija ese.
    [ValidateSet('julio', 'amarillo')]
    [string]$Chaleco,
    [switch]$Lista,
    [switch]$SinVoz,
    [switch]$SinConfirmar,
    # 127.0.0.1 y no localhost: en Windows PowerShell 5.1 `localhost` puede resolver primero a IPv6
    # y colgarse hasta el timeout aunque la consola este sana.
    [string]$Consola = 'http://127.0.0.1:8090'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).ProviderPath
$archivoEscenas = Join-Path $repo 'experiments\evidencia\RT-04\escenas.json'
$sesionesDir = Join-Path $repo 'defensa\sesiones'
$escenas = (Get-Content -LiteralPath $archivoEscenas -Raw -Encoding UTF8 | ConvertFrom-Json).escenas

if ($Lista -or -not $Escena) {
    foreach ($e in $escenas) {
        $esp = ($e.espera.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ', '
        Write-Host ("{0,-5} {1}  [{2}]  tomas sugeridas: {3}" -f $e.id, $e.titulo, $esp, $e.tomas_sugeridas)
        foreach ($p in $e.guion) { Write-Host ("        {0,3} s  {1}" -f $p.s, $p.texto) }
        Write-Host ("        {0,3} s  fin de la toma" -f $e.fin_s)
    }
    Write-Host ''
    Write-Host 'Exploracion (RT-05): -Motor <instancia> -Camara <camara>; la lista esta en experiments\demo_defensa\exploracion.yaml'
    exit 0
}
$esc = $escenas | Where-Object { $_.id -eq $Escena } | Select-Object -First 1
if (-not $esc) { throw "No existe la escena '$Escena'. Ver: .\rodaje.ps1 -Lista" }
if (-not $Chaleco) {
    throw 'Falta -Chaleco: julio (los reflectantes del rodaje de julio: RT-04, RT-05, RT-06) o amarillo (el amarillo no reflectivo: RT-07).'
}

function Ahora-Ms { [double][DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() }
function Pedir([string]$metodo, [string]$ruta, $cuerpo, [int]$Espera = 30) {
    $parametros = @{ Method = $metodo; Uri = "$Consola$ruta"; TimeoutSec = $Espera }
    if ($null -ne $cuerpo) {
        $parametros.Body = [Text.Encoding]::UTF8.GetBytes(($cuerpo | ConvertTo-Json -Compress))
        $parametros.ContentType = 'application/json'
    }
    try { return Invoke-RestMethod @parametros }
    catch {
        $detalle = $_.ErrorDetails.Message
        if (-not $detalle) { $detalle = $_.Exception.Message }
        throw "$metodo $ruta -> $detalle"
    }
}

$voz = $null
if (-not $SinVoz) {
    try {
        Add-Type -AssemblyName System.Speech
        $voz = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $es = $voz.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'es*' } | Select-Object -First 1
        if ($es) { $voz.SelectVoice($es.VoiceInfo.Name) }
        else { Write-Host 'Aviso: no hay una voz en espanol instalada; habla la voz por defecto.' }
    } catch {
        Write-Host 'Aviso: sin sintesis de voz en esta PowerShell (usar Windows PowerShell 5.1). Sigue sin voz.'
        $voz = $null
    }
}

Write-Host ''
Write-Host "=== Escena $($esc.id): $($esc.titulo) ===" -ForegroundColor Cyan
Write-Host "Preparacion: $($esc.preparacion)"
Write-Host "Chaleco: $Chaleco" -ForegroundColor Cyan
foreach ($p in $esc.guion) { Write-Host ("  {0,3} s  {1}" -f $p.s, $p.texto) }
Write-Host ("  {0,3} s  fin" -f $esc.fin_s)

# 0a. Camara IP (RT-06): que exista, que sea la de la prueba y que entregue video ANTES de lanzar.
if ($Fuente) {
    if ($Motor -or $Camara) { throw 'La exploracion (RT-05, -Motor/-Camara) es con la OAK-D: no se combina con -Fuente.' }
    $camaras = @(Pedir 'GET' '/api/demo/camaras' $null) | ForEach-Object { $_ }
    $cam = $camaras | Where-Object { $_.id -eq $Fuente } | Select-Object -First 1
    if (-not $cam) { throw "No existe la camara '$Fuente' en cameras/. Hay: $(($camaras | ForEach-Object { $_.id }) -join ', ')" }
    Write-Host "Camara: $($cam.nombre) ($($cam.destino), $($cam.plugin))" -ForegroundColor Cyan
    if ($cam.plugin -eq 'rtsp') {
        $chk = Pedir 'POST' "/api/demo/camaras/$Fuente/comprobar" $null 60
        if ($chk.estado -ne 'ok') {
            Write-Host "La camara no se ve: $($chk.causa)" -ForegroundColor Red
            foreach ($a in $chk.ayuda) { Write-Host "  - $a" }
            throw 'Arreglar la camara (o comprobarla en /demo) y volver a lanzar la toma.'
        }
        $video = ($chk.pasos | Where-Object { $_.id -eq 'video' } | Select-Object -First 1).detalle
        Write-Host "  se ve: $video" -ForegroundColor Green
    }
}

# 0. Exploracion (RT-05): el motor pedido activo y fresco.
$exploracion = $null
$consulta = ''
if ($Motor -or $Camara) {
    if (-not $Motor) { $Motor = 'mp-gdino-tiny-560' }
    if (-not $Camara) { $Camara = '960x540@5' }
    $exploracion = @{ motor = $Motor; camara = $Camara }
    $consulta = '?motor=' + [uri]::EscapeDataString($Motor) + '&camara=' + [uri]::EscapeDataString($Camara)
    Write-Host "MODO EXPLORACION (RT-05): $Motor con la camara a $Camara. No es la demo congelada." -ForegroundColor Magenta
    $activa = (Pedir 'GET' '/api/platform/instances' $null) | Where-Object { $_.is_target } | Select-Object -First 1
    if (-not $activa -or $activa.name -ne $Motor) {
        Write-Host "Activando $Motor (puede tardar unos minutos)..."
        Pedir 'POST' "/api/platform/instances/$Motor/activate" $null 900 | Out-Null
    }
    $pf = Pedir 'GET' "/api/demo/preflight$consulta" $null
    if ($pf.motor.estado -in @('desconocido', 'usado', 'error')) {
        Write-Host 'Dejando el motor fresco (F-101.5)...'
        Pedir 'POST' '/api/demo/motor/reiniciar' $null | Out-Null
    }
}

# 1. Chequeo previo de la demo en verde (el motor se reinicia solo despues de cada toma).
$limite = (Get-Date).AddSeconds(180)
$ultimo = ''
while ($true) {
    $pf = Pedir 'GET' "/api/demo/preflight$consulta" $null
    if ($pf.listo) { break }
    $rojos = ($pf.items | Where-Object { $_.estado -eq 'error' } | ForEach-Object { "$($_.nombre): $($_.detalle)" }) -join ' | '
    if ($rojos -ne $ultimo) { Write-Host "Esperando el chequeo previo: $rojos" -ForegroundColor Yellow; $ultimo = $rojos }
    if ((Get-Date) -gt $limite) { throw 'El chequeo previo de la demo no quedo en verde en 3 minutos.' }
    Start-Sleep -Seconds 2
}
if (-not $SinConfirmar) {
    Read-Host 'Escena armada (vestuario puesto, actores fuera de cuadro, cuadro limpio)? Enter para lanzar'
}

# 2. Desfase reloj de los contenedores - reloj del host (mediana de 5 idas y vueltas).
$desfases = @()
for ($i = 0; $i -lt 5; $i++) {
    $t1 = Ahora-Ms
    $h = Pedir 'GET' '/api/demo/hora' $null
    $t2 = Ahora-Ms
    $desfases += ([double]$h.ms - ($t1 + $t2) / 2)
}
$desfase = ($desfases | Sort-Object)[2]

# 3. Lanzar la sesion etiquetada.
$cuerpo = @{ escena = $esc.id }
if ($exploracion) { $cuerpo.exploracion = $exploracion }
if ($Fuente) { $cuerpo.camara = $Fuente }
$inicio = Pedir 'POST' '/api/demo/start' $cuerpo
$sid = $inicio.session_id
Write-Host "Sesion $sid lanzada. Nadie entra a cuadro hasta el primer aviso." -ForegroundColor Green
$cerrada = $false
try {
    # 4. Primer cuadro procesado = arranca el reloj del guion.
    $limite = (Get-Date).AddSeconds(90)
    while ($true) {
        $st = Pedir 'GET' '/api/demo/state' $null
        if ($st.fase -eq 'live' -and $st.en_vivo_desde_ms) { break }
        if ($st.fase -eq 'failed') { throw "La sesion fallo antes de arrancar: $($st.error)" }
        if ((Get-Date) -gt $limite) { throw 'No llego el primer cuadro en 90 s: revisar la camara (y cerrar con F F en /demo).' }
        Start-Sleep -Milliseconds 200
    }
    $inicioHost = [double]$st.en_vivo_desde_ms - $desfase
    Write-Host 'Primer cuadro procesado. Arranca el guion.' -ForegroundColor Green

    $acciones = @()
    foreach ($paso in $esc.guion) {
        $objetivo = $inicioHost + 1000 * [double]$paso.s
        while ((Ahora-Ms) -lt ($objetivo - 3)) { Start-Sleep -Milliseconds 2 }
        [console]::Beep(1000, 150)
        $real = Ahora-Ms
        $acciones += [pscustomobject]@{
            accion = $paso.accion; condicion = $paso.condicion; texto = $paso.texto
            programado_ms = $objetivo; pared_ms = $real
        }
        Write-Host ("{0,6:N1} s  >>> {1}" -f (($real - $inicioHost) / 1000), $paso.texto) -ForegroundColor Yellow
        if ($voz) { $voz.Speak($paso.texto) }
    }
    $fin = $inicioHost + 1000 * [double]$esc.fin_s
    while ((Ahora-Ms) -lt $fin) { Start-Sleep -Milliseconds 20 }
    if ($voz) { $voz.Speak('Fin de la toma') }

    # 5. Cerrar (como F F) y esperar el Resultado.
    Pedir 'POST' '/api/demo/finish' $null | Out-Null
    $cerrada = $true
    Write-Host 'Cerrando la sesion y armando el Resultado...'
    $limite = (Get-Date).AddSeconds(240)
    do {
        Start-Sleep -Seconds 2
        $st = Pedir 'GET' '/api/demo/state' $null
    } while ($st.session_id -eq $sid -and $st.fase -notin @('done', 'failed') -and (Get-Date) -lt $limite)

    $salida = [pscustomobject]@{
        session_id = $sid
        escena = $esc.id
        chaleco = $Chaleco
        exploracion = $exploracion
        desfase_contenedor_menos_host_ms = $desfase
        desfases_ms = $desfases
        primer_cuadro_contenedor_ms = [double]$st.en_vivo_desde_ms
        acciones = $acciones
        nota = 'pared_ms: hora del host al sonar el tono, antes de la voz. Incluye la reaccion del actor.'
    }
    $destino = Join-Path $sesionesDir $sid
    if (-not (Test-Path -LiteralPath $destino)) { New-Item -ItemType Directory -Path $destino | Out-Null }
    [IO.File]::WriteAllText((Join-Path $destino 'marcas.json'), ($salida | ConvertTo-Json -Depth 5),
        (New-Object Text.UTF8Encoding($false)))

    Write-Host ''
    Write-Host "Toma $sid ($($esc.id)) terminada en fase $($st.fase)." -ForegroundColor Cyan
    foreach ($c in $st.condiciones) {
        $esperado = $esc.espera.($c.condicion)
        Write-Host ("  {0}: alertas {1}  (el guion espera: {2})" -f $c.condicion, $c.alertas, $esperado)
    }
    if ($exploracion) {
        Write-Host 'Toma de exploracion. Para importar: .\evidencia.ps1 correr RT-05 (al final, volver al campeon: ..\demo\demo.ps1 up)'
    } elseif ($Fuente -and $cam.plugin -eq 'rtsp' -and $Chaleco -eq 'amarillo') {
        Write-Host 'Toma con la camara IP y el chaleco amarillo. Para importar: .\evidencia.ps1 correr RT-08'
    } elseif ($Fuente -and $cam.plugin -eq 'rtsp') {
        Write-Host 'Toma con la camara IP. Para importar: .\evidencia.ps1 correr RT-06 (RT-04 no la cuenta)'
    } elseif ($Chaleco -eq 'amarillo') {
        Write-Host 'Toma con el chaleco amarillo. Para importar: .\evidencia.ps1 correr RT-07 (RT-04 no la cuenta)'
    } else {
        Write-Host 'El Resultado de la toma esta en /demo. Para importar el rodaje: .\evidencia.ps1 correr RT-04'
    }
} finally {
    if (-not $cerrada) {
        try { Pedir 'POST' '/api/demo/finish' $null | Out-Null; Write-Host 'Sesion cerrada (interrumpida).' }
        catch { Write-Host 'No se pudo cerrar la sesion: cerrarla con F F en /demo.' }
    }
}
