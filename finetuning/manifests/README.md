# Manifiestos

Metadatos livianos y versionables de datos, pesos, contenedores, entornos, runs y promociones.
Cada recurso pesado debe quedar identificado por origen, licencia, tamaño y SHA-256; los
manifiestos no contienen secretos ni rutas personales.

El manifiesto de `finetuning_v1` debe registrar, como mínimo: dataset y split fuente, ruta
canónica, SHA-256, id de linaje, grupo perceptual, split final, clases/conteos, licencia y motivo
de inclusión o exclusión. También debe registrar la huella de `bench_v3` usada por el guard y
demostrar disjunción por hash, linaje y grupo perceptual.

Las filas del split registran además URL, versión fuente y licencia SPDX para que el payload
pueda reconstruir su atribución sin depender de rutas locales.

`t1_yoloe26s_bench_v3_protocol.json` congela el protocolo pre-resultado del baseline y la
comparación tuned sobre una vista sólo lectura de BENCH v3. No es una autorización: la clase
objetivo y los márgenes numéricos de promoción permanecen nulos hasta decisión explícita.

`t1_source_inventory.json` y `t1_source_snapshot.json` describen el snapshot determinístico de
T-FT-023. El tar pesado vive bajo `cache/`; `t1_source_provenance_attestation.json` es la
atestación posterior que enlaza sus hashes, el bundle activo y la copia read-only verificada en
Mendieta. El snapshot conserva deliberadamente el estado previo al cierre y no se reescribe.

PPE aporta una sola imagen por linaje visual refinado. La representante se elige por mayor
cantidad de anotaciones canónicas y, ante empate, por split fuente `train`→`val`→`test` y ruta.
El inventario conserva todas las variantes y hashes para auditar la elección.
