#!/usr/bin/env bash
set -euo pipefail

# Los nodos de cómputo de Mendieta no tienen salida confiable a registros OCI. Esta
# preparación se ejecuta una sola vez desde el login, que sí tiene conectividad. No
# solicita GPU ni ejecuta entrenamiento; el smoke posterior se envía por Slurm.
ROOT="${EOVRT_T1_ROOT:?set EOVRT_T1_ROOT to the remote T1 working directory}"
BUNDLE="${ROOT}/bundle"
IMAGE_DIR="${ROOT}/images"
IMAGE="${IMAGE_DIR}/eovrt-t1-yoloe.sif"
TEMP_IMAGE="${IMAGE_DIR}/.eovrt-t1-yoloe-login-build.sif"

test -d "${BUNDLE}/containers"
test ! -e "${IMAGE}"
test ! -e "${TEMP_IMAGE}"
mkdir -p "${IMAGE_DIR}" "${ROOT}/apptainer-cache"
export APPTAINER_CACHEDIR="${ROOT}/apptainer-cache"

cd "${BUNDLE}"
sha256sum --quiet -c bundle.sha256
cd containers
nice -n 10 apptainer build "${TEMP_IMAGE}" t1-yoloe.def
apptainer inspect "${TEMP_IMAGE}"
mv "${TEMP_IMAGE}" "${IMAGE}"
(
    cd "${IMAGE_DIR}"
    sha256sum eovrt-t1-yoloe.sif >eovrt-t1-yoloe.sif.sha256
    sha256sum -c eovrt-t1-yoloe.sif.sha256
)
echo "LOGIN_IMAGE_BUILD_OK image=${IMAGE}"
