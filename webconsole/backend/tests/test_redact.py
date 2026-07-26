"""`redact.py` es la única fuente de verdad del repo sobre qué cuenta como
credencial de cámara. `has_rtsp_credentials` se apoya en el mismo regex que la
redacción para que la detección y el borrado no puedan divergir."""
from __future__ import annotations

import pytest

from eovrt_webconsole.redact import has_rtsp_credentials, redact_rtsp_credentials


@pytest.mark.parametrize("url", [
    "rtsp://usuario:clave@169.254.31.140:554/s",
    "rtsp://usuario@169.254.31.140:554/s",
    "RTSP://u:p@h/s",
    "rtsps://u:p@h/s",
    "rtsp://u:p@ss@h/s",  # '@' sin escapar en el password
])
def test_detecta_credenciales(url):
    assert has_rtsp_credentials(url) is True


@pytest.mark.parametrize("url", [
    "169.254.31.137",
    "rtsp://169.254.31.140:554/s",
    "rtsp://1.2.3.4:554/stream",
    "",
])
def test_sin_credenciales(url):
    assert has_rtsp_credentials(url) is False


def test_coherente_con_la_redaccion():
    """La detección es exactamente 'la redacción cambiaría algo'."""
    for url in ["rtsp://u:p@h/s", "rtsp://h/s", "169.254.31.137"]:
        assert has_rtsp_credentials(url) == (redact_rtsp_credentials(url) != url)
