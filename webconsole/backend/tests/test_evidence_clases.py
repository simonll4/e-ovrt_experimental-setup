"""La taxonomía se define sobre los roles del registro, no sobre las corridas."""
import csv
import glob
import json
import re
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.evidence import (
    CLASES,
    EvidenceRegistry,
    cabeceras_de_disponibilidad,
    clase_mas_fuerte,
)
from eovrt_webconsole.evidence_metrics import campo_de

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / 'results/evidence-vista'


def roles_del_registro() -> set[str]:
    roles = set()
    for path in glob.glob(str(REPO / 'results/evidence-runs/collections/*.csv')):
        with open(path, newline='', encoding='utf-8') as src:
            roles.update(row['role'] for row in csv.DictReader(src))
    return roles


def test_todo_rol_tiene_exactamente_una_clase():
    """Un rol nuevo sin clasificar FALLA. Es el chequeo anti-envejecimiento."""
    data = yaml.safe_load((VISTA / 'clasificacion.yaml').read_text(encoding='utf-8'))
    declarados = [rol for clase in data['roles'].values() for rol in clase]
    assert len(declarados) == len(set(declarados)), 'un rol declarado en dos clases'
    faltan = roles_del_registro() - set(declarados)
    assert not faltan, f'roles sin clase en clasificacion.yaml: {sorted(faltan)}'


def test_las_clases_declaradas_son_las_del_vocabulario():
    data = yaml.safe_load((VISTA / 'clasificacion.yaml').read_text(encoding='utf-8'))
    assert set(data['roles']) <= set(CLASES)
    assert set(data.get('excepciones', {})) <= set(CLASES)


def test_clase_de_run_toma_la_mas_fuerte(tmp_path):
    """Una corrida con dos roles se clasifica por el más fuerte, no por el primero."""
    registry = _registro(tmp_path, [
        ('resultado_role', 'campaign_media', 'm1'),
        ('instrumento_role', 'bloques_ab', 'm1'),
    ])
    assert registry.clase_de('m1') == 'resultado'


def test_run_fuera_del_registro_es_sin_clasificar(tmp_path):
    registry = _registro(tmp_path, [('x', 'campaign_media', 'm1')])
    assert registry.clase_de('desconocida') == 'sin_clasificar'


def test_clase_mas_fuerte_sin_clases_es_el_default_no_una_heuristica():
    assert clase_mas_fuerte([]) == 'sin_clasificar'
    assert clase_mas_fuerte(['ensayo', 'resultado']) == 'resultado'
    assert clase_mas_fuerte(['sin_clasificar', 'ensayo']) == 'ensayo'


def test_clasificacion_ausente_se_declara_aunque_el_registro_cargue(tmp_path):
    """C-3, la mitad peor: `clasificacion.yaml` es MUTABLE y lo edita una
    persona. Si falta, el registro carga bien (`available` sigue en True) y
    TODO cae a `sin_clasificar` en silencio. Los dos estados viajan sueltos
    porque son dos fallas distintas."""
    registry = _registro(tmp_path, [('x', 'campaign_media', 'm1')])
    assert cabeceras_de_disponibilidad(registry) == {
        'X-Evidence-Available': 'true', 'X-Clasificacion-Available': 'true',
        'X-Clasificacion-Roles': '0/1'}

    (tmp_path / 'evidence-vista' / 'clasificacion.yaml').unlink()
    sin_config = EvidenceRegistry(tmp_path / 'evidence-runs', tmp_path / 'evidence-vista')
    assert sin_config.available is True, 'el archivo congelado sigue estando'
    assert sin_config.clase_de('m1') == 'sin_clasificar'
    assert cabeceras_de_disponibilidad(sin_config) == {
        'X-Evidence-Available': 'true', 'X-Clasificacion-Available': 'false',
        'X-Clasificacion-Roles': '1/1'}


def test_clasificacion_presente_pero_vacia_se_declara_no_disponible(tmp_path):
    """R-31: el chequeo mira CONTENIDO, no existencia.

    `clasificacion.yaml` existe justamente porque lo edita una persona. Si le
    renombran o le vacían `roles:`, el YAML carga, no salta ninguna excepción y
    TODAS las corridas caen a `sin_clasificar` — la pantalla afirmaba entonces
    "Fuera del registro N" sin una sola advertencia. Era el último camino que
    afirmaba una clasificación sin declarar que no la tenía.
    """
    vacia = _registro(tmp_path / 'a', [('x', 'campaign_media', 'm1')],
                      clasificacion={'roles': {}})
    assert vacia.available is True, 'el archivo congelado no tiene nada que ver'
    assert vacia.clase_de('m1') == 'sin_clasificar'
    assert cabeceras_de_disponibilidad(vacia)['X-Clasificacion-Available'] == 'false'

    # `roles:` renombrado a mano: la clave que el cargador lee desaparece y el
    # resto del archivo sigue siendo YAML válido.
    renombrada = _registro(tmp_path / 'b', [('x', 'campaign_media', 'm1')],
                           clasificacion={'rolez': {'resultado': ['campaign_media']}})
    assert cabeceras_de_disponibilidad(renombrada)['X-Clasificacion-Available'] == 'false'


def test_clasificacion_que_no_alcanza_a_ningun_rol_del_registro_se_declara(tmp_path):
    """Declarar roles que ya nadie usa clasifica tan poco como no declarar nada.

    Es el modo de falla por RENOMBRE: el archivo trae roles válidos, pero el
    registro cambió los suyos. `roles_sin_clasificar()` —el detector que ya
    existía sin cablear— los devuelve todos.
    """
    ajena = _registro(tmp_path / 'a', [('x', 'campaign_media', 'm1')],
                      clasificacion={'roles': {'resultado': ['rol_que_ya_no_existe']}})
    assert ajena.roles_sin_clasificar() == ['campaign_media']
    assert cabeceras_de_disponibilidad(ajena)['X-Clasificacion-Available'] == 'false'

    # Alcanzar a UNO alcanza: la clasificación existe y es parcial, que es otra
    # cosa que no tenerla. El rol nuevo sin clase lo caza el test de arriba de
    # este archivo, que es donde corresponde.
    parcial = _registro(tmp_path / 'b', [('x', 'campaign_media', 'm1'), ('y', 'rol_nuevo', 'm2')],
                        clasificacion={'roles': {'resultado': ['campaign_media']}})
    assert parcial.roles_sin_clasificar() == ['rol_nuevo']
    assert cabeceras_de_disponibilidad(parcial)['X-Clasificacion-Available'] == 'true'


def test_la_cabecera_lleva_el_conteo_de_roles_sin_clasificar(tmp_path):
    """Un booleano no distingue «no hay clasificación» de «hay una y es parcial».

    Con 1 de 2 roles declarados `clasificacion_disponible` dice `true` —y es
    cierto— pero las corridas del rol restante se muestran «Fuera del registro»
    sin que nada diga que es por falta de declaración. El conteo viaja para que
    la pantalla pueda decirlo en vez de callar.
    """
    completa = _registro(tmp_path / 'a', [('x', 'campaign_media', 'm1')])
    assert cabeceras_de_disponibilidad(completa)['X-Clasificacion-Roles'] == '0/1'

    parcial = _registro(tmp_path / 'b',
                        [('x', 'campaign_media', 'm1'), ('y', 'rol_nuevo', 'm2')])
    assert parcial.clasificacion_disponible is True, 'hay clasificación, y es parcial'
    assert cabeceras_de_disponibilidad(parcial)['X-Clasificacion-Roles'] == '1/2'

    ninguna = _registro(tmp_path / 'c', [('x', 'campaign_media', 'm1')],
                        clasificacion={'roles': {}})
    assert cabeceras_de_disponibilidad(ninguna)['X-Clasificacion-Roles'] == '1/1'

    # Registro vacío: cero sobre cero, nunca una fracción inventada.
    vacio = _registro(tmp_path / 'd', [])
    assert cabeceras_de_disponibilidad(vacio)['X-Clasificacion-Roles'] == '0/0'


def test_registro_presente_pero_sin_filas_no_esta_disponible(tmp_path):
    """La otra mitad de R-31: los cuatro CSV con encabezado y cero filas.

    Cargan sin error, dejan cada corrida fuera del registro y `available`
    decía `true`. La disponibilidad tiene que mirar las filas, no los archivos.
    """
    vacio = _registro(tmp_path, [])
    assert vacio.available is False
    assert cabeceras_de_disponibilidad(vacio) == {
        'X-Evidence-Available': 'false', 'X-Clasificacion-Available': 'true',
        'X-Clasificacion-Roles': '0/0'}


def _registro(tmp_path: Path, filas, clasificacion: dict | None = None) -> EvidenceRegistry:
    from eovrt_webconsole.evidence import CSV_FILES
    archive = tmp_path / 'evidence-runs'
    (archive / 'collections').mkdir(parents=True)
    campos = ['collection', 'result_id', 'role', 'plane', 'run_id', 'status',
              'source_ref', 'artifact_path']
    for nombre in CSV_FILES:
        with (archive / 'collections' / nombre).open('w', newline='') as dst:
            writer = csv.writer(dst)
            writer.writerow(campos)
            if nombre == 'shared.csv':
                for result_id, rol, run_id in filas:
                    writer.writerow(['shared', result_id, rol, 'media-plane', run_id,
                                     'copied', 'x.json', 'artifacts/x'])
    config = tmp_path / 'evidence-vista'
    config.mkdir()
    # Por defecto, el archivo REAL del repo: los tests de clase se apoyan en sus
    # roles de verdad. `clasificacion` sólo lo reemplaza para ejercitar los
    # modos de falla de contenido (R-31).
    (config / 'clasificacion.yaml').write_text(
        yaml.safe_dump(clasificacion, allow_unicode=True) if clasificacion is not None
        else (VISTA / 'clasificacion.yaml').read_text(encoding='utf-8'), encoding='utf-8')
    return EvidenceRegistry(archive, config)


def _recorrido() -> dict:
    # Se llama en tiempo de colección (parametrize evalúa el argumento al importar
    # el módulo). Si `recorrido.yaml` no existe, tolerar y devolver vacío: que
    # explote acá tumbaría la colección del módulo entero, incluidos los tests de
    # arriba que no tienen nada que ver. `test_recorrido_particiona_los_resultados`
    # sigue fallando ruidosamente en ese caso, porque compara contra los 35
    # result_id reales del registro.
    path = VISTA / 'recorrido.yaml'
    if not path.is_file():
        return {'pasos': []}
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _resultados_del_registro() -> set[str]:
    ids = set()
    for path in glob.glob(str(REPO / 'results/evidence-runs/collections/*.csv')):
        with open(path, newline='', encoding='utf-8') as src:
            ids.update(row['result_id'] for row in csv.DictReader(src))
    return ids


def test_recorrido_particiona_los_resultados():
    """Total y disyunta: ninguno invisible, ninguno contado dos veces."""
    data = _recorrido()
    asignados = [r for paso in data['pasos'] for r in paso['resultados']]
    asignados += data['respaldo_instrumental']['resultados']
    assert len(asignados) == len(set(asignados)), 'un result_id en dos pasos'
    assert set(asignados) == _resultados_del_registro()


def test_titulos_cubren_los_resultados():
    data = yaml.safe_load((VISTA / 'titulos.yaml').read_text(encoding='utf-8'))
    filas = {row['result_id']: row for row in data['resultados']}
    assert set(filas) == _resultados_del_registro()
    sin_titulo = [k for k, v in filas.items() if not v.get('titulo')]
    assert not sin_titulo, f'resultados sin titulo redactado: {sin_titulo}'
    sin_reclamo = [k for k, v in filas.items() if not v.get('reclamo')]
    assert not sin_reclamo, f'resultados sin reclamo: {sin_reclamo}'


@pytest.mark.parametrize('paso', _recorrido()['pasos'], ids=lambda p: str(p['n']))
def test_cada_paso_declara_su_cifra_de_una_sola_forma(paso):
    """Leída o citada, nunca las dos ni ninguna."""
    citada = 'cifra' in paso
    leida = 'leer' in paso
    assert citada != leida, f"paso {paso['n']}: cifra y leer son excluyentes"
    if citada:
        assert paso.get('fuente'), f"paso {paso['n']}: una cifra citada necesita fuente"


@pytest.mark.parametrize('paso', [p for p in _recorrido()['pasos'] if 'cifra' in p],
                         ids=lambda p: str(p['n']))
def test_cifra_citada_aparece_literal_en_su_fuente(paso):
    """El chequeo (b) de 96-verificar-indices.py, aplicado a la consola.

    Sin esto la consola es un lugar donde puede aparecer, frente al tribunal, un
    número que ningún verificador chequea.
    """
    fuente = REPO / paso['fuente']
    assert fuente.is_file(), f"fuente inexistente: {paso['fuente']}"
    assert paso['cifra'] in fuente.read_text(encoding='utf-8'), (
        f"la cifra {paso['cifra']!r} del paso {paso['n']} no aparece en {paso['fuente']}")


def _lecturas_del_recorrido() -> list[dict]:
    data = _recorrido()
    return [item for paso in data.get('pasos', []) for item in (paso.get('leer') or [])]


def test_hay_al_menos_una_lectura_para_verificar():
    """Guardia de "cero casos", simétrica a la de `_mediciones_en_prosa()`.

    Si `recorrido.yaml` se quedara sin ningún `leer:`, `parametrize` generaría 0
    tests para `test_toda_lectura_del_recorrido_resuelve_a_un_numero_real` y la
    suite pasaría en silencio -- exactamente el modo de falla que ese test
    existe para evitar.
    """
    assert _lecturas_del_recorrido(), 'no hay ninguna entrada leer: en recorrido.yaml'


@pytest.mark.parametrize('lectura', _lecturas_del_recorrido(),
                          ids=lambda item: f"{item['result_id']}:{item['campo']}")
def test_toda_lectura_del_recorrido_resuelve_a_un_numero_real(lectura):
    """Red anti-guión: un `result_id` o `campo` mal escrito en `leer:` hoy se
    renderiza como "—" y nadie se entera. `campo_de` sólo mira `positives` y la
    raíz del JSON (ver docstring de `evidence_metrics.py`): si un `leer:` futuro
    apuntara a un campo anidado más profundo, esto fallaría en vez de degradar
    en silencio -- y ESO es el comportamiento correcto, no un bug de `campo_de`.
    """
    valor = campo_de(REPO / f"results/{lectura['result_id']}/metrics.json", lectura['campo'])
    assert isinstance(valor, float), (
        f"{lectura['result_id']}.{lectura['campo']} no resolvió a un número "
        f"(campo_de devolvió {valor!r}); revisar el result_id/campo en recorrido.yaml")


MEDICION = re.compile(r'\b\d+,\d{3}\b')


def _mediciones_en_prosa() -> list[tuple[str, str]]:
    """Toda cifra con coma decimal y EXACTAMENTE 3 decimales en los campos de
    prosa (`reclamo` de titulos.yaml; `claim`/`cifra_label`/`cifra_nota` de
    recorrido.yaml). Un valor de configuración (560, 0,30) o una afirmación
    editorial (24 %) queda fuera de alcance a propósito: no derivan de
    recomputar una campaña, así que no envejecen con ella.
    """
    encontradas = []
    titulos = yaml.safe_load((VISTA / 'titulos.yaml').read_text(encoding='utf-8'))
    for row in titulos['resultados']:
        for m in MEDICION.findall(row.get('reclamo') or ''):
            encontradas.append((f"titulos.yaml:{row['result_id']}.reclamo", m))
    data = _recorrido()
    for paso in data.get('pasos', []):
        for campo in ('claim', 'cifra_label', 'cifra_nota'):
            for m in MEDICION.findall(paso.get(campo) or ''):
                encontradas.append((f"recorrido.yaml:paso {paso['n']}.{campo}", m))
    respaldo = data.get('respaldo_instrumental') or {}
    for campo in ('titulo', 'claim'):
        for m in MEDICION.findall(respaldo.get(campo) or ''):
            encontradas.append((f"recorrido.yaml:respaldo_instrumental.{campo}", m))
    return encontradas


def _valores_de_metrics_json() -> set[float]:
    """Todo número, a cualquier profundidad, de cada metrics.json del registro
    -- la búsqueda es cruzada entre los 17 metrics.json, no por result_id."""
    valores: set[float] = set()

    def _recorrer(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                _recorrer(v)
        elif isinstance(obj, list):
            for v in obj:
                _recorrer(v)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            valores.add(round(float(obj), 3))

    for path in glob.glob(str(REPO / 'results/*/*/metrics.json')):
        _recorrer(json.loads(Path(path).read_text(encoding='utf-8')))
    return valores


def test_toda_medicion_en_prosa_tiene_respaldo_en_algun_metrics_json():
    """Si mañana se recomputa una campaña, un `reclamo` o una `cifra_nota`
    pueden envejecer en silencio -- el proyecto ya se comió una vez que "el
    número estrella del TFG no tenía respaldo en el repo". Cada medición en
    prosa tiene que coincidir con ALGÚN número de ALGÚN metrics.json del
    registro (redondeado a 3 decimales); no tiene que ser el metrics.json del
    resultado de esa fila -- p. ej. el reclamo de g1 cita 0,789, el F1 de t1.
    """
    encontradas = _mediciones_en_prosa()
    assert encontradas, 'no se encontró ninguna medición en prosa: revisar el regex o el contenido'
    valores = _valores_de_metrics_json()
    sin_respaldo = [(donde, texto) for donde, texto in encontradas
                     if round(float(texto.replace(',', '.')), 3) not in valores]
    assert not sin_respaldo, f'mediciones en prosa sin respaldo en metrics.json: {sin_respaldo}'
