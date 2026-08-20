# Archivo histórico — infra

## `console-docker-compose.yml`

Archivado el 2026-08-19. Era el deploy standalone de la consola web del 2026-07-05
(era de servicio único: la consola sola, sin los demás módulos), superado por
`infra/platform/`, que compone la plataforma completa.

**Ojo:** `infra/console/Dockerfile` **sigue vivo** — el compose de la plataforma
(`infra/platform/`) lo construye. Lo archivado es sólo el compose standalone.
