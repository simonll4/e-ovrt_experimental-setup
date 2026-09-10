#!/usr/bin/env python3
"""Imprime A.4 sin modificar manifiestos, excepciones ni artefactos.

Ejecutar con webconsole/backend/.venv/bin/python webconsole/tools/classify_evidence.py.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import yaml
from eovrt_webconsole.evidence import EvidenceRegistry, clasificar_ejecuciones
from eovrt_webconsole.routers.experiments import _iter_umbrella_manifests


def verdict(evidence: dict) -> str:
    return 'Evidencia' if evidence['is_evidence'] else 'Archivado'


def report(root: Path) -> str:
    registry = EvidenceRegistry(root / 'results/evidence-runs')
    executions = clasificar_ejecuciones(root / 'runs', registry)
    groups: dict[str, list[dict]] = defaultdict(list)
    for execution in executions:
        groups[execution['slug']].append(execution)
    umbrellas = list(_iter_umbrella_manifests(root / 'experiments'))
    slugs = {manifest.slug for _, manifest in umbrellas}
    lines = [
        '# Tramo 6 — clasificación A.4 regenerada', '',
        ('Decisión del usuario del 2026-09-10: conservar sólo los paraguas con '
         'evidencia abrible; resultado esperado `talert_integrated_video`, 4 '
         'ejecuciones, 3 de evidencia. Las dos listas de `consola.yaml` siguen vacías.'), '',
        ('El clasificador descubre recursivamente cada `manifest.effective.yaml` '
         'y busca identidades en todo su subárbol JSON/JSONL/YAML. '
         '`_ejecuciones_por_slug` permanece intacto; sus conteos no se sustituyen.'), '',
        f'Registro disponible: **{registry.available}**. Resultados: **{len(registry.resultados())}**.',
        '', '## Los 11 paraguas del listado', '',
        '| Slug | Ejecuciones recursivas | Con evidencia | Veredicto | Motivo / resultado |',
        '| --- | ---: | ---: | --- | --- |',
    ]
    for _, manifest in umbrellas:
        group = groups[manifest.slug]
        evidence = registry.manifiesto(manifest.slug, [e['evidence'] for e in group])
        results = ', '.join(evidence['result_ids'])
        lines.append(f'| `{manifest.slug}` | {len(group)} | '
                     f'{sum(e["evidence"]["is_evidence"] for e in group)} | '
                     f'{verdict(evidence)} | {evidence["reason"]}'
                     + (f'; `{results}`' if results else '') + ' |')
    lines += ['', '## Contraste con archivos persistidos y el registro', '',
              ('Los cuatro directorios siguientes contienen manifiesto y reporte. '
               'Se contrastan los ids persistidos, no el nombre de la campaña. '
               'Admisión no figura en los CSV; las tres repeticiones sí.'), '',
              '| Ejecución | Manifiesto y artefactos dentro de runs/ | Corridas | Veredicto / resultados |',
              '| --- | --- | --- | --- |']
    for e in groups['talert_integrated_video']:
        directory = e['directory'].relative_to(root)
        lines.append(f'| `{e["experiment_id"]}` | `{directory}`: '
                     '`manifest.effective.yaml`, `media/summary.json`, '
                     '`control/summary.json`, `report/report.json` | '
                     + '<br>'.join(f'`{r}`' for r in e['run_ids']) + ' | '
                     + verdict(e['evidence']) + ': '
                     + ', '.join(e['evidence']['result_ids']) + ' |')
    lines += ['', '## Grupos huérfanos: slugs ausentes del catálogo de paraguas', '',
              ('No cuelgan de ninguno de los 11 manifiestos listados. Se incluyen '
               'en el inventario y en el contador de ejecuciones archivadas; '
               'no se agregan recetas a la pantalla ni se infiere un slug por similitud.'), '',
              '| Slug huérfano | Ejecuciones | Con evidencia | Archivadas | Motivo |',
              '| --- | ---: | ---: | ---: | --- |']
    for slug in sorted(set(groups) - slugs):
        group = groups[slug]
        n = sum(e['evidence']['is_evidence'] for e in group)
        lines.append(f'| `{slug}` | {len(group)} | {n} | {len(group)-n} | '
                     'Slug fuera del catálogo; ' +
                     ('ninguna corrida figura en los CSV.' if n == 0 else 'ver detalle de ids abajo.')
                     + ' |')
    n_evidence = sum(e['evidence']['is_evidence'] for e in executions)
    lines += ['', (f'Total descubierto: **{len(executions)}**; evidencia: **{n_evidence}**; '
              f'archivadas: **{len(executions)-n_evidence}**.'), '',
              ('Los conteos son la foto del disco al ejecutar el script. Las suites '
               'anteriores generan smokes del orquestador en runs/; por eso el número '
               'de huérfanas puede crecer sin cambiar los 4/3 de talert ni los 5/0 de diag.'), '',
              '## Los 19 individuales: documentados aparte, fuera del filtro', '',
              '| Manifiesto individual | Alcance |', '| --- | --- |']
    individual = sorted([
        *[p for p in (root / 'experiments').glob('*.yaml')
          if (yaml.safe_load(p.read_text()) or {}).get('schema_version') != 'experiment.manifest.v1'],
        *(root / 'experiments/bench_v2').glob('*.yaml'),
    ])
    for path in individual:
        lines.append(f'| `{path.relative_to(root)}` | No listado; no se clasifica ni filtra. |')
    lines += ['', '## Cada ejecución: pertenencia, ruta, ids y motivo', '',
              '| Slug | Pertenece al catálogo | Directorio | Corridas | Veredicto y motivo |',
              '| --- | --- | --- | --- | --- |']
    for e in executions:
        evidence = e['evidence']
        lines.append(f'| `{e["slug"]}` | {"Sí" if e["slug"] in slugs else "No: huérfana"} | '
                     f'`{e["directory"].relative_to(root)}` | '
                     + ('<br>'.join(f'`{r}`' for r in e['run_ids']) or 'Sin ids persistidos')
                     + f' | {verdict(evidence)}: {evidence["reason"]} |')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(report(args.repo_root), end='')
