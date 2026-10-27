# demo_defensa — plantillas de la demo en vivo

No son manifiestos para lanzar desde **Experimentos**: las resuelve la pantalla `/demo` de la
consola al apretar Iniciar (`webconsole/backend/src/eovrt_webconsole/demo/config.py`), que arma
el manifiesto en código (control → distribución → medios, live) y guarda las configs resueltas en
`defensa/sesiones/<sesión>/config/`.

| Archivo | Qué es |
|---|---|
| `media.template.yaml` | OAK-D 169.254.31.137, 960×540 a 5 fps, prompt set congelado por referencia, previews |
| `control.template.yaml` | pattern set oficial `cr01_cr02_v2`, escena, bus de alertas habilitado |
| `distribution.template.yaml` | MQTT QoS 1, enfriamiento de 30 s por `[condition_id, source_id]` |
| `congelado.yaml` | huellas del tag `informe-2026` que el chequeo previo compara |
| `../demo_defensa_ensayo/media.template.yaml` | la variante con la cámara de ensayo (RTSP) |

Marcadores (`EOVRT_*`) que resuelve la consola según el despliegue: `EOVRT_WORKSPACE`,
`EOVRT_MEDIA_BUS_ENDPOINT`, `EOVRT_ALERT_BUS_ENDPOINT`, `EOVRT_MQTT_HOST`, `EOVRT_MQTT_PORT`,
`EOVRT_ENSAYO_RTSP_URL`. Operación: `infra/demo/README.md`.
