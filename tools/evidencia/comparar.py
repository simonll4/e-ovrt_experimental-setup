"""Veredicto propuesto contra la generación 1 (doc 134 §1).

Tres veredictos posibles, que siempre confirma una persona (`python -m tools.evidencia
veredicto <ID> <veredicto> --motivo ...`):

- `identico`: mismos números, campo a campo, que la referencia de la generación 1.
- `equivalente_con_diferencia`: mismo insumo, otra máquina o pila; la diferencia se explica.
  El driver solo lo propone si el pre-registro declaró de antemano la causa esperada
  (`diferencia_esperada`); si no, propone `a_revisar`.
- `otra_combinacion`: cambió el insumo o la configuración (`gen1.relacion:
  otra_combinacion` en el pre-registro); se muestra al lado, nunca en reemplazo.

La referencia contra la que se compara es la que declara el pre-registro en
`gen1.referencia` (para el banco temporal, la generación 1 RE-EVALUADA con el GT corregido:
comparar contra lo publicado en el v0.1 mezclaría el cambio de referencia con el de máquina).
"""
from __future__ import annotations

from .catalogo import Prueba

DECIMALES = 6


def _igual(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is b
        return round(float(a), DECIMALES) == round(float(b), DECIMALES)
    return a == b


def diferencias(actual: dict, referencia: dict) -> dict:
    return {
        clave: {"gen2": actual.get(clave), "gen1": esperado}
        for clave, esperado in referencia.items()
        if not _igual(actual.get(clave), esperado)
    }


def proponer(actual: dict, prueba: Prueba, valores_ref: dict | None = None) -> dict:
    """`valores_ref` reemplaza a `gen1.referencia.valores` cuando la referencia se lee de un
    archivo versionado (p.ej. el `metrics.json` publicado del Nivel A) en vez de transcribirse."""
    gen1 = prueba.gen1
    ref = gen1.get("referencia") or {}
    valores = valores_ref if valores_ref is not None else (ref.get("valores") or {})
    base = {"confirmado": None, "referencia": ref.get("fuente") or ref.get("archivo")}
    if gen1.get("relacion") == "otra_combinacion":
        return {
            **base,
            "propuesto": "otra_combinacion",
            "motivo": gen1.get("motivo") or "el pre-registro declara otra combinación",
            "diferencias": diferencias(actual, valores) if valores else {},
        }
    if not valores:
        return {**base, "propuesto": "sin_referencia",
                "motivo": "el pre-registro no declara valores de la generación 1 para comparar",
                "diferencias": {}}
    difs = diferencias(actual, valores)
    if not difs:
        return {**base, "propuesto": "identico",
                "motivo": f"los {len(valores)} campos coinciden con la generación 1",
                "diferencias": {}}
    esperada = prueba.datos.get("diferencia_esperada")
    return {
        **base,
        "propuesto": "equivalente_con_diferencia" if esperada else "a_revisar",
        "motivo": esperada
        or "difiere de la generación 1 y el pre-registro no declara una causa: lo revisa una persona",
        "diferencias": difs,
    }
