"""La documentación de la consola: se lee del disco y no afirma lo que no tiene.

Los tres chequeos anti-envejecimiento viven acá, con la misma forma que los de
`test_evidence_clases.py`:

  1. Todo término citado —desde el código de la consola o desde otro bloque del
     propio YAML— tiene que estar DEFINIDO. Un término sin definición rompe el
     build antes de llegar a la pantalla.
  2. Todo `result_id` que aparezca en la documentación tiene que existir en el
     registro de evidencia.
  3. Toda MEDICIÓN escrita en prosa tiene que coincidir con algún número de
     algún `metrics.json`. Es el mismo test anti-fraude que ya rige para
     `titulos.yaml` y `recorrido.yaml`.
"""
import csv
import glob
import json
import re
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.documentacion import Documentacion

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / 'results/evidence-vista'
DOC = VISTA / 'documentacion.yaml'
FRONTEND = REPO / 'webconsole/frontend/src'


def _doc() -> dict:
    # Se llama en tiempo de colección (`parametrize` evalúa su argumento al
    # importar el módulo). Si el archivo no está, se tolera acá y devuelve
    # vacío: explotar en la colección tumbaría el módulo entero, incluidos los
    # tests que declaran justamente ese estado. `test_sin_archivo_...` sigue
    # fallando ruidosamente si el archivo desapareció del repositorio.
    if not DOC.is_file():
        return {}
    return yaml.safe_load(DOC.read_text(encoding='utf-8')) or {}


def _definidos() -> set[str]:
    return {t['id'] for familia in (_doc().get('vocabulario') or [])
            for t in (familia.get('terminos') or []) if t.get('id')}


def _resultados_del_registro() -> set[str]:
    ids = set()
    for path in glob.glob(str(REPO / 'results/evidence-runs/collections/*.csv')):
        with open(path, newline='', encoding='utf-8') as src:
            ids.update(row['result_id'] for row in csv.DictReader(src))
    return ids


# --------------------------------------------------------------------------
# 1. Nada mudo: todo término citado está definido.
# --------------------------------------------------------------------------

def test_el_archivo_de_documentacion_existe_y_define_vocabulario():
    assert DOC.is_file(), f'falta {DOC}'
    assert _definidos(), 'documentacion.yaml no define ningún término'


def test_los_ids_de_termino_no_se_repiten():
    ids = [t['id'] for familia in (_doc().get('vocabulario') or [])
           for t in (familia.get('terminos') or []) if t.get('id')]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert not repetidos, f'ids de término definidos dos veces: {repetidos}'


def test_todo_termino_tiene_definicion_no_vacia():
    sin_texto = [t.get('id') for familia in (_doc().get('vocabulario') or [])
                 for t in (familia.get('terminos') or [])
                 if not (t.get('definicion') or '').strip() or not (t.get('termino') or '').strip()]
    assert not sin_texto, f'términos sin nombre o sin definición: {sin_texto}'


def _terminos_declarados_en_el_codigo() -> list[str]:
    """Los ids que `src/terminos.ts` declara que la consola marca.

    Se leen del archivo, no se reimplementan acá: si alguien agrega un término
    a la lista del frontend y se olvida de definirlo, este test lo caza. Es el
    patrón anti-envejecimiento de `clasificacion.yaml`, del otro lado del
    contrato.
    """
    fuente = (FRONTEND / 'terminos.ts').read_text(encoding='utf-8')
    # Sólo los arrays `TERMINOS_*`, y dentro de ellos las cadenas entre
    # comillas simples. `TERMINO_DE_CLASE` es un mapa y se lee aparte.
    ids: list[str] = []
    for bloque in re.findall(r'export const TERMINOS_\w+[^=]*=\s*\[(.*?)\]', fuente, re.DOTALL):
        ids.extend(re.findall(r"'([^']+)'", bloque))
    mapa = re.search(r'export const TERMINO_DE_CLASE[^=]*=\s*\{(.*?)\n\}', fuente, re.DOTALL)
    if mapa:
        ids.extend(re.findall(r":\s*'([^']+)'", mapa.group(1)))
    return ids


def test_terminos_marcados_en_el_codigo_estan_definidos():
    """Un término usado en el código y sin definición en el YAML FALLA.

    Preferimos romper el build antes que mostrar un término marcado que al
    abrirlo no dice nada: es exactamente el defecto que este proyecto arrastra
    —una ausencia de dato convertida en una afirmación— y que la pantalla ya
    evita en runtime cayendo a texto plano. Acá se evita antes, en el repo.
    """
    declarados = _terminos_declarados_en_el_codigo()
    assert declarados, 'no se leyó ningún término de src/terminos.ts: revisar el parser'
    faltan = sorted(set(declarados) - _definidos())
    assert not faltan, f'términos usados en el código y sin definición en documentacion.yaml: {faltan}'


def test_los_terminos_citados_por_el_metodo_estan_definidos():
    definidos = _definidos()
    faltan = sorted({t for paso in (_doc().get('metodo') or [])
                     for t in (paso.get('terminos') or [])} - definidos)
    assert not faltan, f'el método cita términos sin definir: {faltan}'


def test_cada_paso_del_metodo_dice_que_hizo_por_que_y_que_quedo():
    """El POR QUÉ es lo que hace que los nombres se entiendan en vez de
    memorizarse. Un paso sin él es una lista de tareas, no un método."""
    pasos = _doc().get('metodo') or []
    assert pasos, 'documentacion.yaml no declara ningún paso de método'
    for paso in pasos:
        for campo in ('titulo', 'hizo', 'porque', 'quedo'):
            assert (paso.get(campo) or '').strip(), f"paso {paso.get('n')}: falta `{campo}`"


def test_la_tabla_de_aportes_cubre_los_cinco_terminos_que_se_confunden():
    ids = [fila.get('id') for fila in (_doc().get('aportes') or [])]
    assert ids == ['corrida', 'experimento', 'campana', 'evidencia', 'resultado']
    for fila in _doc().get('aportes') or []:
        for campo in ('termino', 'que_es', 'que_suma'):
            assert (fila.get(campo) or '').strip(), f"aporte {fila.get('id')}: falta `{campo}`"


def test_las_colisiones_de_simbolo_estan_declaradas():
    """Las tres canónicas del glosario más `T1`/`T2`, que es la peor de todas y
    no estaba declarada en ninguna parte: sus dos sentidos viven a un click en
    `results/` (campañas del banco de clips contra brazos del ajuste fino) y sus
    veredictos son OPUESTOS — T1 es la línea de base que todo supera en una
    serie, y un NO-GO en la otra.

    La lista se afirma por CONTENIDO, no por longitud: agregar una quinta
    colisión no debe romper este test, y la pantalla saca su título y su conteo
    de la misma lista. Lo que sí se exige es que ninguna entrada afirme una
    colisión con un solo sentido, y que todas digan qué significan ACÁ — sin eso
    la sección informa que hay un problema y no lo resuelve.
    """
    colisiones = _doc().get('colisiones') or []
    simbolos = [c['simbolo'] for c in colisiones]
    for esperado in ('R1', 'D1', 'A1', 'T1 / T2'):
        assert esperado in simbolos, f'colisión sin declarar: {esperado}'
    for c in colisiones:
        assert len(c.get('sentidos') or []) >= 2, f"{c['simbolo']}: una colisión de un solo sentido"
        assert (c.get('en_la_consola') or '').strip(), f"{c['simbolo']}: falta qué significa acá"
        for s in c['sentidos']:
            assert (s.get('de') or '').strip() and (s.get('es') or '').strip(), (
                f"{c['simbolo']}: un sentido sin nombre o sin explicación")


# --------------------------------------------------------------------------
# 2. Toda campaña o result_id citado existe de verdad.
# --------------------------------------------------------------------------

def _result_ids_citados() -> list[tuple[str, str]]:
    citados = []
    for familia in _doc().get('vocabulario') or []:
        for t in familia.get('terminos') or []:
            for rid in t.get('result_ids') or []:
                citados.append((f"vocabulario:{t.get('id')}", rid))
    return citados


def test_hay_al_menos_un_result_id_citado():
    """Guardia de «cero casos»: sin ninguna cita, el test de abajo pasaría en
    silencio, que es justo el modo de falla que existe para evitar."""
    assert _result_ids_citados(), 'ningún término cita un result_id'


@pytest.mark.parametrize('cita', _result_ids_citados(), ids=lambda c: f'{c[0]}:{c[1]}')
def test_todo_result_id_citado_existe_en_el_registro(cita):
    donde, rid = cita
    assert rid in _resultados_del_registro(), (
        f'{donde} cita un result_id que no está en el registro de evidencia: {rid}')


def test_las_campanas_declaran_su_result_id():
    """Una campaña es una combinación concreta con artefacto. Si el término la
    nombra y no la puede señalar, está afirmando algo que no puede sostener."""
    campanas = next((f for f in (_doc().get('vocabulario') or [])
                     if f.get('id') == 'campanas'), None)
    assert campanas, 'no hay familia `campanas`'
    sin_rid = [t['id'] for t in campanas['terminos'] if not (t.get('result_ids') or [])]
    assert not sin_rid, f'campañas sin result_id: {sin_rid}'


# --------------------------------------------------------------------------
# 3. Anti-fraude de cifras: la misma regla que `test_evidence_clases.py`.
# --------------------------------------------------------------------------

MEDICION = re.compile(r'\b\d+,\d{3}\b')

# Los campos de PROSA de este archivo. Un valor de configuración (560, 0,30) o
# una afirmación editorial (24 %) queda fuera de alcance a propósito: no derivan
# de recomputar una campaña, así que no envejecen con ella.
CAMPOS_PROSA = ('titulo', 'bajada', 'hizo', 'porque', 'quedo', 'que_es', 'que_suma',
                'definicion', 'nota', 'en_la_consola', 'es', 'de', 'termino')


def _mediciones_en_prosa() -> list[tuple[str, str]]:
    encontradas: list[tuple[str, str]] = []

    def mirar(donde: str, obj):
        if isinstance(obj, dict):
            for clave, valor in obj.items():
                if isinstance(valor, str) and clave in CAMPOS_PROSA:
                    for m in MEDICION.findall(valor):
                        encontradas.append((f'{donde}.{clave}', m))
                else:
                    mirar(f'{donde}.{clave}', valor)
        elif isinstance(obj, list):
            for i, valor in enumerate(obj):
                mirar(f'{donde}[{i}]', valor)

    mirar('documentacion.yaml', _doc())
    return encontradas


def _valores_de_metrics_json() -> set[float]:
    """Todo número, a cualquier profundidad, de cada metrics.json del registro.
    La búsqueda es CRUZADA entre los 17 archivos, no por result_id."""
    valores: set[float] = set()

    def recorrer(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                recorrer(v)
        elif isinstance(obj, list):
            for v in obj:
                recorrer(v)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            valores.add(round(float(obj), 3))

    for path in glob.glob(str(REPO / 'results/*/*/metrics.json')):
        recorrer(json.loads(Path(path).read_text(encoding='utf-8')))
    return valores


def test_hay_al_menos_una_medicion_en_prosa_para_verificar():
    assert _mediciones_en_prosa(), (
        'no se encontró ninguna medición en la prosa de documentacion.yaml: '
        'revisar el regex o el contenido')


def test_toda_medicion_en_prosa_tiene_respaldo_en_algun_metrics_json():
    """El proyecto ya se comió una vez que «el número estrella del TFG no tenía
    respaldo en el repo». Una cifra escrita acá y recomputada mañana envejecería
    en silencio, frente al tribunal, en la pantalla que explica el trabajo.

    Ojo con lo que ESTO implica: el mAP50 del campeón NO puede escribirse en
    este archivo, porque `bench_imagenes` no tiene `metrics.json` en este
    repositorio (sus cifras se verifican contra el doc 64). Esa cifra vive en
    `/evidencia/paso?n=1`, declarada como citada y con su fuente al lado — que
    es el camino correcto, no una omisión.
    """
    valores = _valores_de_metrics_json()
    sin_respaldo = [(donde, texto) for donde, texto in _mediciones_en_prosa()
                    if round(float(texto.replace(',', '.')), 3) not in valores]
    assert not sin_respaldo, f'mediciones sin respaldo en metrics.json: {sin_respaldo}'


# --------------------------------------------------------------------------
# El módulo: estados de disponibilidad y conteos.
# --------------------------------------------------------------------------

def test_el_archivo_real_carga_y_declara_disponible():
    doc = Documentacion(REPO)
    assert doc.available is True
    payload = doc.payload()
    assert payload['message'] is None
    assert len(payload['metodo']) == 5
    assert len(payload['aportes']) == 5
    assert payload['terminos'], 'el índice plano de términos vino vacío'
    # El índice plano es lo único que la pantalla consulta para decidir si algo
    # se marca: tiene que cubrir todo lo que las familias listan.
    de_familias = {t['id'] for f in payload['vocabulario'] for t in f['terminos']}
    assert de_familias == set(payload['terminos'])


def test_sin_archivo_se_declara_no_disponible_con_su_remedio(tmp_path):
    doc = Documentacion(tmp_path)
    assert doc.available is False
    payload = doc.payload()
    assert payload['available'] is False
    assert 'restauralo' in payload['message']
    assert payload['metodo'] == [] and payload['terminos'] == {}


def test_archivo_presente_pero_vacio_tambien_se_declara(tmp_path):
    """R-31 otra vez: el chequeo mira CONTENIDO, no existencia. Un YAML válido
    con `vocabulario:` renombrado carga sin excepción y dejaría la pantalla
    afirmando una documentación que no tiene. Y el remedio es OTRO: no es
    «restauralo», es «revisá las claves»."""
    vista = tmp_path / 'results/evidence-vista'
    vista.mkdir(parents=True)
    (vista / 'documentacion.yaml').write_text(
        yaml.safe_dump({'metodo': [], 'vocabulariox': []}, allow_unicode=True), encoding='utf-8')
    doc = Documentacion(tmp_path)
    assert doc.available is False
    assert 'renombrad' in doc.payload()['message'] or 'vací' in doc.payload()['message']


def test_un_termino_citado_que_no_existe_no_llega_a_la_pantalla(tmp_path):
    """La red de abajo de la regla: aunque el test de repositorio se saltee, el
    lector nunca ve un chip que no explica nada."""
    vista = tmp_path / 'results/evidence-vista'
    vista.mkdir(parents=True)
    (vista / 'documentacion.yaml').write_text(yaml.safe_dump({
        'metodo': [{'n': 1, 'titulo': 't', 'hizo': 'h', 'porque': 'p', 'quedo': 'q',
                    'terminos': ['existe', 'fantasma']}],
        'vocabulario': [{'id': 'f', 'titulo': 'F', 'terminos': [
            {'id': 'existe', 'termino': 'existe', 'definicion': 'd'}]}],
    }, allow_unicode=True), encoding='utf-8')
    payload = Documentacion(tmp_path).payload()
    assert payload['metodo'][0]['terminos'] == ['existe']


def test_los_conteos_salen_del_registro_y_nunca_del_yaml(tmp_path):
    """Un total escrito a mano envejece en cuanto el inventario crece. Sin
    registro no se muestra número, en vez de mostrar uno viejo."""
    sin_registro = Documentacion(REPO)
    por_id = {f['id']: f for f in sin_registro.payload()['aportes']}
    assert por_id['resultado']['conteo'] is None, 'sin archivo no hay conteo'
    assert por_id['campana']['conteo'] is None, 'campaña no declara conteo_de'

    from eovrt_webconsole.evidence import EvidenceRegistry
    from eovrt_webconsole.evidence_archive import EvidenceArchive
    registry = EvidenceRegistry(REPO / 'results/evidence-runs')
    archive = EvidenceArchive(REPO, registry)
    con_registro = {f['id']: f for f in Documentacion(REPO, archive).payload()['aportes']}
    assert con_registro['resultado']['conteo'] == len(archive.by_result)
    assert con_registro['corrida']['conteo'] == len(archive.by_run)


def test_la_ruta_contesta_sin_ningun_servicio_arriba(client):
    """La propiedad declarada de la pantalla: funciona con los tres planos
    apagados. El `client` de la suite apunta a un repositorio sintético, así que
    acá además se ejerce el camino «no disponible»: 200 con el estado declarado,
    nunca un 500."""
    response = client.get('/api/documentacion')
    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo['available'] is False
    assert cuerpo['message']
    assert cuerpo['terminos'] == {}
