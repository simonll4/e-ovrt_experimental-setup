# Captura de pantalla para la evidencia de la generacion 2 (jornada en vivo, doc 136 del repo docs).
#
# Guarda un PNG de la pantalla y devuelve su ruta. Por defecto va a defensa\capturas\<fecha>\,
# que esta FUERA de git: una captura puede mostrar caras o datos del equipo. Solo una captura
# revisada y sin caras se copia despues a results\gen2\<ID>\capturas\ (publico).
#
# Uso (Windows PowerShell 5.1, en la Victus):
#   .\captura.ps1 -Nombre rt04_P1_alerta
#   .\captura.ps1 -Nombre plat01_compose_ps -Pantalla 1      # segunda pantalla
# Desde WSL:
#   powershell.exe -NoProfile -File infra/platform/captura.ps1 -Nombre rt04_P1_alerta
param(
    [Parameter(Mandatory = $true)][string]$Nombre,
    [string]$Destino,
    [int]$Pantalla = 0
)
$ErrorActionPreference = 'Stop'
if ($Nombre -notmatch '^[A-Za-z0-9_-]{1,60}$') { throw "Nombre invalido: letras, numeros, '-' y '_' (hasta 60)." }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not $Destino) { $Destino = Join-Path $repo ('defensa\capturas\' + (Get-Date -Format 'yyyy-MM-dd')) }
if (-not (Test-Path -LiteralPath $Destino)) { New-Item -ItemType Directory -Path $Destino | Out-Null }

# Sin esto, con la escala de Windows en 125/150 % se captura solo una parte de la pantalla.
Add-Type @'
using System.Runtime.InteropServices;
public static class EovrtCapturaDpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
'@
[void][EovrtCapturaDpi]::SetProcessDPIAware()
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$pantallas = [System.Windows.Forms.Screen]::AllScreens
if ($Pantalla -ge $pantallas.Count) { throw "No hay pantalla $Pantalla (hay $($pantallas.Count))." }
$area = $pantallas[$Pantalla].Bounds
$imagen = New-Object System.Drawing.Bitmap $area.Width, $area.Height
$lienzo = [System.Drawing.Graphics]::FromImage($imagen)
try {
    $lienzo.CopyFromScreen($area.Location, [System.Drawing.Point]::Empty, $area.Size)
    $archivo = Join-Path $Destino ((Get-Date -Format 'HHmmss') + '_' + $Nombre + '.png')
    $imagen.Save($archivo, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $lienzo.Dispose()
    $imagen.Dispose()
}
Write-Output $archivo
