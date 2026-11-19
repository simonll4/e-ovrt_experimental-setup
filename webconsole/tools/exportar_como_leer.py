"""Exporta la documentación larga de la consola al repositorio público (`e-ovrt-vdp`).

La consola muestra la evidencia y el sistema funcionando; cómo se trabajó, qué aporta cada cosa, las equivalencias con
el código, los símbolos con más de un sentido y el vocabulario completo son documentación y viven en el repositorio
público (revisión del 2026-11-19). La fuente es una sola, `results/evidence-vista/documentacion.yaml`: la consola lee
de ahí el vocabulario (los términos marcados de sus pantallas) y este script escribe de ahí la página pública.

    python3 webconsole/tools/exportar_como_leer.py [--salida ../e-ovrt-vdp/evidencia/consola/como-leer.md]

Después, en `e-ovrt-vdp`: `python3 herramientas/verificar.py` (cero violaciones). Solo biblioteca estándar y PyYAML.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
FUENTE = REPO / "results" / "evidence-vista" / "documentacion.yaml"
SALIDA = REPO.parent / "e-ovrt-vdp" / "evidencia" / "consola" / "como-leer.md"
RESULTADOS = "https://github.com/simonll4/e-ovrt_experimental-setup/tree/main/results/"


def _limpio(texto: object) -> str:
    return " ".join(str(texto or "").split())


def _celda(texto: object) -> str:
    return _limpio(texto).replace("|", "\\|")


def exportar(doc: dict) -> str:
    l: list[str] = [
        "# Cómo leer la consola",
        "",
        "<!-- Generado por e-ovrt_experimental-setup/webconsole/tools/exportar_como_leer.py desde",
        "     results/evidence-vista/documentacion.yaml. No editar a mano: se edita el YAML y se vuelve a exportar. -->",
        "",
        "La consola de `e-ovrt_experimental-setup/webconsole` muestra la evidencia del informe y la plataforma "
        "funcionando. Lo que sigue es la documentación que la acompaña: cómo se trabajó, qué aporta cada cosa, cómo "
        "aparece cada término en el código, los símbolos que significan más de una cosa y el vocabulario completo. "
        "Dentro de la consola, cada término marcado muestra su definición al pasar el mouse.",
        "",
        "## Cómo se trabajó",
        "",
    ]
    for paso in doc.get("metodo") or []:
        l += [f"### {paso.get('n')}. {_limpio(paso.get('titulo'))}", "",
              f"- **Qué se hizo.** {_limpio(paso.get('hizo'))}",
              f"- **Por qué.** {_limpio(paso.get('porque'))}",
              f"- **Qué quedó.** {_limpio(paso.get('quedo'))}", ""]
    l += ["## Qué aporta cada cosa", "",
          "Corrida, experimento, campaña, evidencia y resultado se usan casi como sinónimos y no lo son.", "",
          "| Qué es | Identificador | De qué habla | Qué suma |", "|---|---|---|---|"]
    for a in doc.get("aportes") or []:
        ident = f"`{_celda(a.get('identificador'))}`" if a.get("identificador") else "sin identificador propio"
        l.append(f"| {_celda(a.get('termino'))} | {ident} | {_celda(a.get('que_es'))} | {_celda(a.get('que_suma'))} |")
    l += ["", "## Equivalencias", "",
          "Cada término del informe y de la consola, su código y cómo aparece en la implementación.", "",
          "| En el informe y la consola | Código | En la implementación |", "|---|---|---|"]
    for e in doc.get("equivalencias") or []:
        codigo = f"`{_celda(e.get('codigo'))}`" if e.get("codigo") else "—"
        l.append(f"| {_celda(e.get('termino'))} | {codigo} | {_celda(e.get('implementacion'))} |")
    l += ["", "## Símbolos que significan más de una cosa", ""]
    for c in doc.get("colisiones") or []:
        l += [f"### `{_limpio(c.get('simbolo'))}`", "", _limpio(c.get("en_la_consola")), ""]
        l += [f"- **{_limpio(s.get('de'))}.** {_limpio(s.get('es'))}" for s in c.get("sentidos") or []]
        l.append("")
    l += ["## Vocabulario", ""]
    for familia in doc.get("vocabulario") or []:
        l += [f"### {_limpio(familia.get('titulo'))}", ""]
        if familia.get("nota"):
            l += [_limpio(familia.get("nota")), ""]
        for t in familia.get("terminos") or []:
            nombre = f"`{_limpio(t.get('termino'))}`" if t.get("mono") else f"**{_limpio(t.get('termino'))}**"
            linea = f"- {nombre}: {_limpio(t.get('definicion'))}"
            rids = [r for r in t.get("result_ids") or [] if isinstance(r, str)]
            if rids:
                linea += " Resultados: " + ", ".join(f"[`{r}`]({RESULTADOS}{r})" for r in rids) + "."
            if isinstance(t.get("fuente"), str) and t["fuente"].startswith("https://github.com/"):
                linea += f" [Fuente]({t['fuente']})."
            l.append(linea)
        l.append("")
    return "\n".join(l).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()
    doc = yaml.safe_load(FUENTE.read_text(encoding="utf-8")) or {}
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(exportar(doc), encoding="utf-8")
    print(f"escrito {args.salida}")


if __name__ == "__main__":
    main()
