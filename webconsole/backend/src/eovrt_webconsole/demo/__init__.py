"""Demo en vivo de la defensa (spec docs/superpowers/specs/2026-10-23-demo-defensa-design.md).

Todo lo nuevo de la demo vive acá y es de OBSERVACIÓN: no toca lo medido (modelo, prompt
set, pattern set, umbrales, enfriamiento). Módulos:

- `config`: plantillas versionadas de experiments/demo_defensa → configs resueltas por
  sesión, y el chequeo de lo congelado contra el tag `informe-2026`.
- `testigo`: suscriptor MQTT independiente del distribuidor (la prueba de que el mensaje
  pasó por el broker) y la ida y vuelta del chequeo previo.
- `estado`: deriva, de los episodios del control-plane, lo que muestra cada tarjeta.
- `render`: después de la corrida, el video anotado, los cuadros clave y la línea de tiempo.
- `cifras`: las cifras de la generación 2 que muestra la pantalla de Resultado.
- `sesion`: `DemoManager`, una sesión a la vez (idle → preparing → live → finishing →
  rendering → done | failed).
"""
