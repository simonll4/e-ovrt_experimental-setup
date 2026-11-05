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
#
# Segunda jornada de F7 (enmienda 2026-11-04, doc 134 13.18):
#   -Remera es obligatoria en cada toma: la prenda bajo el chaleco decide CR-02 (F-RT1, doc 140).
#     Texto corto y estable, el mismo para la misma prenda: 'negra lisa', 'gris clara lisa', 'A negra / B blanca'.
#   -Proposito dice para que es la toma (por defecto 'toma': cuenta en la prueba de su escena):
#     'prendas' = la prueba de prendas (RT-09; RT-04..RT-08 no la cuentan);
#     'ensayo'  = un ensayo del guion de la demo (G3, despues del informe; no entra a ninguna prueba).
#   -Modo corre un modo de prompts de experiments\demo_defensa\modos.yaml (p. ej. 'reflective');
#     la sesion queda marcada y RT-04..RT-08 no la cuentan. No se combina con -Motor/-Camara.
#   .\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'negra lisa' -Proposito prendas
#   .\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'negra lisa' -Proposito prendas -Modo reflective
#   .\rodaje.ps1 -Escena P2 -Chaleco julio -Remera 'negra lisa' -Proposito prendas -Motor mp-gdino-base-560 -Camara 960x540@5
#   .\rodaje.ps1 -Escena P1 -Chaleco julio -Remera 'gris clara lisa'                    # RT-04
#
# Calibracion de encuadre (enmienda 2026-11-05, doc 134 13.19; propuesta completa: doc 143). Antes de la
# PRIMERA toma de una jornada y antes de la demo, con la camara ya ubicada por el operador: una persona en
# regla (casco y chaleco) se para en la marca cercana, camina a la lejana y vuelve. Es una sesion de /demo
# con escena CAL; el guion y los criterios (geometricos, fijados antes) estan en
# experiments\demo_defensa\calibracion.json. Despues, .\evidencia.ps1 calibrar la mide y deja la
# calibracion VIGENTE de esa camara; sin una vigente que haya pasado (o aceptada con motivo), este script
# no lanza ninguna toma con esa camara. Si se mueve la camara, se calibra de nuevo.
#   .\rodaje.ps1 -Calibrar -Altura 1.9 -Cerca 3 -Lejos 6          # OAK-D (altura de la lente en m, cinta metrica)
#   .\rodaje.ps1 -Calibrar -Altura 2.1 -Fuente rtsp_dvr_sub       # la camara IP (una calibracion por camara fisica)
#   .\evidencia.ps1 calibrar                                       # el veredicto y la vigente
param(
    [string]$Escena,
    [string]$Motor,
    [string]$Camara,
    [string]$Fuente,
    # CR-02 depende del chaleco: cada toma lo declara y el driver la cuenta solo en la prueba que fija ese.
    [ValidateSet('julio', 'amarillo')]
    [string]$Chaleco,
    # Y de la prenda de abajo (F-RT1): se declara en cada toma (doc 134 13.18).
    [string]$Remera,
    # 'calibracion' lo pone el script con -Calibrar (ValidateSet se aplica tambien al asignar adentro).
    [ValidateSet('toma', 'prendas', 'ensayo', 'calibracion')]
    [string]$Proposito = 'toma',
    [string]$Modo,
    # Calibracion de encuadre (doc 134 13.19): la escena CAL con lo declarado por el operador.
    [switch]$Calibrar,
    [double]$Altura,     # altura de la lente, en metros (obligatoria con -Calibrar)
    [double]$Cerca,      # distancia de la camara a la marca cercana, en metros (recomendado)
    [double]$Lejos,      # distancia de la camara a la marca lejana, en metros (recomendado)
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
$archivoCalibracion = Join-Path $repo 'experiments\demo_defensa\calibracion.json'
$archivoVigente = Join-Path $repo 'results\gen2\_calibraciones\vigente.json'
$sesionesDir = Join-Path $repo 'defensa\sesiones'
$escenas = (Get-Content -LiteralPath $archivoEscenas -Raw -Encoding UTF8 | ConvertFrom-Json).escenas
$calibracion = Get-Content -LiteralPath $archivoCalibracion -Raw -Encoding UTF8 | ConvertFrom-Json

if ($Lista -or (-not $Escena -and -not $Calibrar)) {
    foreach ($e in $escenas) {
        $esp = ($e.espera.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ', '
        Write-Host ("{0,-5} {1}  [{2}]  tomas sugeridas: {3}" -f $e.id, $e.titulo, $esp, $e.tomas_sugeridas)
        foreach ($p in $e.guion) { Write-Host ("        {0,3} s  {1}" -f $p.s, $p.texto) }
        Write-Host ("        {0,3} s  fin de la toma" -f $e.fin_s)
    }
    Write-Host ''
    Write-Host ("{0,-5} {1}  (-Calibrar -Altura <m> [-Cerca <m> -Lejos <m>]; despues .\evidencia.ps1 calibrar)" -f $calibracion.escena, $calibracion.titulo)
    foreach ($p in $calibracion.guion) { Write-Host ("        {0,3} s  {1}" -f $p.s, $p.texto) }
    Write-Host ("        {0,3} s  fin" -f $calibracion.fin_s)
    Write-Host ''
    Write-Host 'Exploracion (RT-05): -Motor <instancia> -Camara <camara>; la lista esta en experiments\demo_defensa\exploracion.yaml'
    exit 0
}
if ($Calibrar) {
    if ($Escena -or $Motor -or $Camara -or $Modo) {
        throw 'La calibracion es con la configuracion de la demo (el campeon) y su propia escena (CAL): no se combina con -Escena, -Motor, -Camara ni -Modo.'
    }
    if (-not $Altura) {
        throw 'Falta -Altura: la altura de la lente en metros, medida con cinta (ej.: -Calibrar -Altura 1.9 -Cerca 3 -Lejos 6).'
    }
    $esc = [pscustomobject]@{
        id = $calibracion.escena; titulo = $calibracion.titulo; preparacion = $calibracion.preparacion
        guion = $calibracion.guion; fin_s = $calibracion.fin_s; espera = [pscustomobject]@{}
    }
    $Proposito = 'calibracion'
} else {
    if ($Proposito -eq 'calibracion') { throw 'Para calibrar el encuadre usar -Calibrar -Altura <m> (no -Proposito calibracion).' }
    $esc = $escenas | Where-Object { $_.id -eq $Escena } | Select-Object -First 1
    if (-not $esc) { throw "No existe la escena '$Escena'. Ver: .\rodaje.ps1 -Lista" }
    if (-not $Chaleco) {
        throw 'Falta -Chaleco: julio (los reflectantes del rodaje de julio: RT-04, RT-05, RT-06) o amarillo (el amarillo no reflectivo: RT-07).'
    }
    if (-not $Remera -or -not $Remera.Trim()) {
        throw "Falta -Remera: la prenda bajo el chaleco decide CR-02 (F-RT1). Ej.: -Remera 'gris clara lisa' (doc 134 13.18)."
    }
    $Remera = $Remera.Trim()
    if ($Modo -and ($Motor -or $Camara)) {
        throw '-Modo (otro prompt set) no se combina con -Motor/-Camara (la exploracion de RT-05 es con el set congelado).'
    }
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
if ($Calibrar) {
    Write-Host ("Camara: altura de la lente {0} m; marca cercana a {1} m; marca lejana a {2} m" -f $Altura, $(if ($Cerca) { $Cerca } else { '?' }), $(if ($Lejos) { $Lejos } else { '?' })) -ForegroundColor Cyan
} else {
    Write-Host "Chaleco: $Chaleco   Remera: $Remera" -ForegroundColor Cyan
}
if ($Proposito -ne 'toma') {
    Write-Host "Proposito: $Proposito (RT-04..RT-08 no cuentan esta toma)" -ForegroundColor Magenta
}
if ($Modo) { Write-Host "Modo de prompts: $Modo (experiments\demo_defensa\modos.yaml)" -ForegroundColor Magenta }
foreach ($p in $esc.guion) { Write-Host ("  {0,3} s  {1}" -f $p.s, $p.texto) }
Write-Host ("  {0,3} s  fin" -f $esc.fin_s)

# 0a. Camara IP (RT-06): que exista, que sea la de la prueba y que entregue video ANTES de lanzar.
$cam = $null
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

# 0d. Encuadre calibrado (doc 134 13.19): toda toma lleva la calibracion vigente de su camara, y sin una que
# haya pasado (o aceptada con motivo y firma: .\evidencia.ps1 calibrar --aceptar) no se lanza.
$vigente = $null
if (-not $Calibrar) {
    $plugin = if ($cam) { $cam.plugin } else { 'oak_d' }
    if (Test-Path -LiteralPath $archivoVigente) {
        $vigente = (Get-Content -LiteralPath $archivoVigente -Raw -Encoding UTF8 | ConvertFrom-Json).por_camara.$plugin
    }
    if (-not $vigente) {
        throw "No hay calibracion de encuadre para la camara '$plugin'. Ubicar la camara y calibrar: .\rodaje.ps1 -Calibrar -Altura <m> [-Cerca <m> -Lejos <m>] y despues .\evidencia.ps1 calibrar (doc 134 13.19)."
    }
    # PowerShell 7 convierte las fechas ISO de ConvertFrom-Json en [datetime]; 5.1 las deja como texto.
    $fechaCal = if ($vigente.fecha -is [datetime]) { $vigente.fecha.ToUniversalTime() } else { [DateTimeOffset]::Parse([string]$vigente.fecha).UtcDateTime }
    $edadH = ((Get-Date).ToUniversalTime() - $fechaCal).TotalHours
    $maxH = [double]$calibracion.umbrales.vigencia_max_h
    if ($edadH -gt $maxH) {
        throw "La calibracion vigente de '$plugin' ($($vigente.session_id)) tiene $([math]::Round($edadH, 1)) h (maximo $maxH): repetirla (.\rodaje.ps1 -Calibrar ...)."
    }
    if (-not $vigente.ok -and -not $vigente.aceptada) {
        throw "La calibracion vigente de '$plugin' ($($vigente.session_id)) NO paso ($($vigente.fallan -join ', ')): mover la camara y repetirla, o aceptarla con motivo (.\evidencia.ps1 calibrar --aceptar --motivo '...' --quien '...')."
    }
    if ($vigente.ok) {
        Write-Host ("Encuadre calibrado: {0} (hace {1} min, altura {2} m)" -f $vigente.session_id, [math]::Round($edadH * 60), $vigente.altura_m) -ForegroundColor Green
    } else {
        Write-Host ("Encuadre: la calibracion vigente ({0}) NO paso ({1}) y fue aceptada con motivo: {2}" -f $vigente.session_id, ($vigente.fallan -join ', '), $vigente.motivo) -ForegroundColor Yellow
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

# 0b. Modo de prompts: el chequeo previo verifica lo que se va a mandar (huella) con ese modo.
if ($Modo) {
    $consulta = '?modo=' + [uri]::EscapeDataString($Modo)
}

# 0c. Una sesion que quedo abierta (p. ej. un lanzamiento cortado) no se espera: se avisa ya.
# (Jornada del 2026-11-01: una sesion huerfana quedo 16 min en vivo; doc 140, defecto 6.)
$st0 = Pedir 'GET' '/api/demo/state' $null
if ($st0.fase -in @('preparing', 'live')) {
    throw "Hay una sesion abierta ($($st0.session_id), $($st0.fase)): cerrarla con F F en /demo antes de lanzar otra toma."
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
    if ($Calibrar) {
        Read-Host 'Camara ubicada y fija, las dos marcas en el piso, una persona en regla fuera de cuadro, cuadro limpio? Enter para lanzar'
    } else {
        Read-Host 'Escena armada (vestuario puesto, actores fuera de cuadro, cuadro limpio)? Enter para lanzar'
    }
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
if ($Modo) { $cuerpo.modo = $Modo }
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
        chaleco = $(if ($Calibrar) { $null } else { $Chaleco })
        remera = $(if ($Calibrar) { $null } else { $Remera })
        proposito = $Proposito
        modo = $(if ($Modo) { $Modo } else { $null })
        exploracion = $exploracion
        # La calibracion de encuadre bajo la que corre la toma (doc 134 13.19); en la calibracion misma, lo declarado.
        calibracion = $(if ($vigente) { [pscustomobject]@{ session_id = $vigente.session_id; ok = $vigente.ok; aceptada = $vigente.aceptada; fecha = $vigente.fecha; altura_m = $vigente.altura_m } } else { $null })
        fisica = $(if ($Calibrar) { [pscustomobject]@{ altura_m = $Altura; distancia_cerca_m = $(if ($Cerca) { $Cerca } else { $null }); distancia_lejos_m = $(if ($Lejos) { $Lejos } else { $null }) } } else { $null })
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
    if ($Calibrar) {
        Write-Host 'Calibracion de encuadre hecha. Ahora el veredicto: .\evidencia.ps1 calibrar   (mover la camara y repetir si no pasa)' -ForegroundColor Green
    } else {
        foreach ($c in $st.condiciones) {
            $esperado = $esc.espera.($c.condicion)
            Write-Host ("  {0}: alertas {1}  (el guion espera: {2})" -f $c.condicion, $c.alertas, $esperado)
        }
    }
    if ($Calibrar) {
        # ya avisado arriba
    } elseif ($Proposito -eq 'prendas') {
        Write-Host 'Toma de la prueba de prendas. Para importar: .\evidencia.ps1 correr RT-09 (RT-04..RT-08 no la cuentan)'
    } elseif ($Proposito -eq 'ensayo') {
        Write-Host 'Ensayo de la demo: no entra a ninguna prueba (RT-04..RT-09 no lo cuentan).'
    } elseif ($Modo) {
        Write-Host "Toma con el modo $Modo`: RT-04..RT-08 no la cuentan (no es el set congelado)."
    } elseif ($exploracion) {
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
