# Contenedores

Aquí se versionan definiciones Apptainer y lockfiles. Las imágenes construidas viven en
`containers/images/` y están ignoradas por Git. Cada imagen usada debe tener manifiesto con
hash, base, dependencias y comando de construcción.

En Mendieta la construcción se hace desde el login mediante
`scripts/build_t1_image_login.sh`; el nodo de cómputo del primer intento no pudo alcanzar Docker
Hub. La SIF resultante queda en el filesystem compartido, se verifica por SHA-256 y los jobs GPU
la consumen sin red.
