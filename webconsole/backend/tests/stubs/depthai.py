"""Stub mínimo de DepthAI para testear record_oakd.py sin hardware ni SDK real."""

import base64

# Flujo H.264 Annex-B mínimo pero DECODABLE (SPS+PPS+IDR, 5 frames a 64x64/10fps,
# generado una vez con `ffmpeg -f lavfi -i testsrc=... -c:v libx264 -f h264`).
# Necesario para que la Tarea 8 (muxeo real con ffmpeg -c copy) pueda verificarse
# de punta a punta: bytes arbitrarios no arrancan como Annex-B válido y todo mux
# real falla con "no frame!". Se entrega entero en el primer paquete de la cola;
# los paquetes siguientes no agregan bytes, así el archivo final es exactamente
# este stream válido sin importar cuántas iteraciones haga el bucle de captura.
_STUB_H264_B64 = (
    "AAAAAWdNQArsohNgIgAAAwACAAADACgeJEssAAAAAWjr48sgAAABBgX//5zcRem95tlIt5Ys2CDZI+7veDI2NCAtIGNvcmUg"
    "MTY1IC0gSC4yNjQvTVBFRy00IEFWQyBjb2RlYyAtIENvcHlsZWZ0IDIwMDMtMjAyNSAtIGh0dHA6Ly93d3cudmlkZW9sYW4u"
    "b3JnL3gyNjQuaHRtbCAtIG9wdGlvbnM6IGNhYmFjPTEgcmVmPTMgZGVibG9jaz0xOjA6MCBhbmFseXNlPTB4MToweDExMSBt"
    "ZT1oZXggc3VibWU9NyBwc3k9MSBwc3lfcmQ9MS4wMDowLjAwIG1peGVkX3JlZj0xIG1lX3JhbmdlPTE2IGNocm9tYV9tZT0x"
    "IHRyZWxsaXM9MSA4eDhkY3Q9MCBjcW09MCBkZWFkem9uZT0yMSwxMSBmYXN0X3Bza2lwPTEgY2hyb21hX3FwX29mZnNldD0t"
    "MiB0aHJlYWRzPTIgbG9va2FoZWFkX3RocmVhZHM9MSBzbGljZWRfdGhyZWFkcz0wIG5yPTAgZGVjaW1hdGU9MSBpbnRlcmxh"
    "Y2VkPTAgYmx1cmF5X2NvbXBhdD0wIGNvbnN0cmFpbmVkX2ludHJhPTAgYmZyYW1lcz0zIGJfcHlyYW1pZD0yIGJfYWRhcHQ9"
    "MSBiX2JpYXM9MCBkaXJlY3Q9MSB3ZWlnaHRiPTEgb3Blbl9nb3A9MCB3ZWlnaHRwPTIga2V5aW50PTI1MCBrZXlpbnRfbWlu"
    "PTEwIHNjZW5lY3V0PTQwIGludHJhX3JlZnJlc2g9MCByY19sb29rYWhlYWQ9NDAgcmM9Y3JmIG1idHJlZT0xIGNyZj0yMy4w"
    "IHFjb21wPTAuNjAgcXBtaW49MCBxcG1heD02OSBxcHN0ZXA9NCBpcF9yYXRpbz0xLjQwIGFxPTE6MS4wMACAAAABZYiEAEe8"
    "ieKen/4RsA1mwZOLF4DDatcqQMQS0zqB6c0YxtwxZYkzo8zHlFSqq1zePYhRxjFNxXm80v8zCFXGFwHxmw2I9wiaeN4iDBu6"
    "k+PY0uqjiH6CjPDrWQ4uSMCQRHa/2wX59ojv0QsWFw2Ikif6NtZSNhZ53kM5YqqK1kqnQkEE91WTlWag0oLj/UP2JcFwMPQq"
    "x4zZufgjC9QqFfBHBEtvfZ6LYcn5q8k61d6dgs4pCu91uKIVz+nG5ype7j6vFXOllO5Ry8HtQJ9ZGyH2EX8ygi+IeM78RDJF"
    "++zTKeUN1t9rnikgcEJ1guWsIrefUvtfvDidl+lMsUzDCeZV6HDBwCUS48m1YcvUnfOwgD1cFEWnWCdgbVJay7mBcKsGFNFa"
    "+heH15Ei+lk6A/Jww0VIm7U25psFRGz39dn2PvVqSR4nhEhHs6PB9mO35AXu61A1qN8/HQpxY0rojpWvzzwBp5bKTLOpKa/y"
    "mTvY4SzVN94QGQKGZXLDxvq+7vr5PePbzfuhhXS3pPWw8Gq/Kyc9HXS50JpovKhWNwc+BZIBSXDItlr2sEnQggwYhM8R2hLa"
    "MUmi9Y68cURmlmPG9xmfupqzOpZZUgUj9yRpF7+192XjFl2aDDe8udTj3RucEdKXNiLw/iXteqJTJfqTK/Y+X/ZWPsNdYi7T"
    "2dUmfWebOL/Apwd2J2YcgtToK6bgD64LQ3BES3ItjmCwjZzKsueQSJKcS1zWxbUuOPOEKKDMTuMaAECQLf5MZg5fkGS0OU+g"
    "E/9rXfyv1dB+NqepRRoyj9uYgECLGk07TVqrqpEPeg4ICHZBjpsed3/iURTAcJ2xQc26t/SnqtsP71Y6W2ePSQRvrSXrQ6cV"
    "RxgeqmsFX/kr9N5KcMngxH6GZt33jYS1U26ew9vI/bWNlm5T3vjW5VveHCyzAh1H8Kl0frS8RqA5BnOWGXbcSEpgtmJ/cO5l"
    "uS0qN5/zaj6+Uvp5xoM2PZbkWZ23L2BOOuCnu7PKFV1Gd2XQYQAAAAFBmiRsQl8XXCjTFZb3WXRDCJRGdI5MWPgHB038CRd9"
    "AS1yrTyt23jNysbUkCGIPgf0Av74DnAIaJ22yb0Hbb+AAAAAAUGeQniO/2eIf3FomEFDR4vGYUQohrWOhkgtAAAAAQGeYXRC"
    "X2DAAAAAAQGeY2pCX2DB"
)
_STUB_H264 = base64.b64decode(_STUB_H264_B64)


class _Node:
    def __init__(self):
        self.out = self
        self.bitstream = self
        self.video = self
        self.input = self

    def link(self, other):
        return None

    def __getattr__(self, name):
        # Todos los setters del SDK (setFps, setResolution, setBitrate, ...) son no-op.
        return lambda *args, **kwargs: None


class _Queue:
    def __init__(self):
        self._emitted = 0

    def get(self):
        # El stream Annex-B válido completo va en el primer paquete; después no
        # se agrega nada más, para no corromper el archivo con relleno.
        self._emitted += 1
        payload = _STUB_H264 if self._emitted == 1 else b""
        return _Packet(payload)

    def tryGet(self):
        return self.get()


class _Packet:
    def __init__(self, payload):
        self._payload = payload

    def getData(self):
        return self._payload


class Device:
    def __init__(self, pipeline, device_info=None, *args, **kwargs):
        self.pipeline = pipeline

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def getOutputQueue(self, name, maxSize=30, blocking=True):
        return _Queue()

    def close(self):
        return None


class DeviceInfo:
    def __init__(self, ip):
        self.ip = ip


class Pipeline:
    def create(self, node_cls):
        return _Node()


class _NodeNamespace:
    ColorCamera = object
    VideoEncoder = object
    XLinkOut = object


node = _NodeNamespace()


class CameraBoardSocket:
    CAM_A = "CAM_A"


class _SensorResolution:
    THE_720_P = "720p"
    THE_1080_P = "1080p"
    THE_4_K = "4k"


class ColorCameraProperties:
    SensorResolution = _SensorResolution


class _Profile:
    H264_MAIN = "h264_main"


class VideoEncoderProperties:
    Profile = _Profile
