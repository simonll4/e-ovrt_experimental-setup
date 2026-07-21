"""Redacción de credenciales RTSP: única fuente de verdad, compartida entre módulos.

Cualquier texto que pueda contener una URL de cámara (`rtsp://user:pass@host/...`) y
termine en un artefacto persistente (manifiesto guardado, sidecar `.rec.json`, log)
debe pasar por acá antes de salir. Un solo regex evita que dos copias diverjan con el
tiempo (p. ej. una que cubra `rtsps://` y otra que no).
"""
from __future__ import annotations

import re

# Redacta el userinfo (user[:pass]) entre el esquema y el primer '/'. Case-insensitive
# (RTSP:// es válido por RFC 3986), cubre rtsps:// (TLS) y toma el ÚLTIMO '@' antes del
# path para no dejar credenciales si el password trae un '@' sin escapar.
_RTSP_USERINFO = re.compile(r"(rtsps?://)[^/]+@", re.IGNORECASE)


def redact_rtsp_credentials(text: str) -> str:
    """Reemplaza `user:pass@` por `***:***@` en cualquier URL rtsp(s):// dentro de `text`.

    No asume que `text` sea *solo* una URL: funciona igual sobre stderr de ffmpeg u
    otro texto libre que pueda contener una URL embebida.
    """
    return _RTSP_USERINFO.sub(r"\1***:***@", text)
