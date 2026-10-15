"""Pruebas del lanzador (lanzador/arranque.py). No instalan paquetes ni abren ventanas."""
import importlib.util
import os
import subprocess
import sys
import sysconfig
import threading
from types import SimpleNamespace
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / 'lanzador' / 'arranque.py'


@pytest.fixture(scope='module')
def arranque():
    spec = importlib.util.spec_from_file_location('arranque_micrograno', RUTA)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    yield modulo
    sys.modules.pop(spec.name, None)


def _restricciones():
    fijadas = {}
    for linea in (RAIZ / 'constraints.txt').read_text(encoding='utf-8').splitlines():
        linea = linea.split('#', 1)[0].strip()
        if '==' in linea:
            nombre, version = linea.split('==', 1)
            fijadas[nombre.strip().lower().replace('_', '-')] = version.strip()
    return fijadas


def test_requisitos_siguen_pyproject_y_constraints(arranque):
    pedidos = arranque.requisitos(RAIZ)
    fijadas = _restricciones()
    assert {'numpy', 'scipy', 'scikit-image', 'pandas', 'Pillow', 'matplotlib', 'tifffile', 'PySide6'} <= set(pedidos)
    assert pedidos['micrograno'] == '1.0.0'
    for nombre, version in pedidos.items():
        if nombre != 'micrograno':
            assert version == fijadas[nombre.lower()], nombre


def test_lista_del_lanzador_py(arranque):
    texto = ('Installed Pythons found by py Launcher for Windows\n'
             ' -V:3.13 *        C:\\Python313\\python.exe\n'
             ' -V:3.13t         C:\\Python313\\python3.13t.exe\n'
             ' -V:3.12-32       C:\\Python312-32\\python.exe\n'
             ' -3.11-64         C:\\Python311\\python.exe\n'
             ' -V:3.10          C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe\n')
    assert arranque.leer_lista_py(texto) == [
        ((3, 13), 'C:\\Python313\\python.exe'),
        ((3, 11), 'C:\\Python311\\python.exe'),
        ((3, 10), 'C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe')]


def test_preferencia_de_interpretes(arranque):
    I = arranque.Interprete
    candidatos = [I(['a'], (3, 14, 0), ruta='a'), I(['b'], (3, 11, 9), ruta='b'),
                  I(['c'], (3, 13, 3), ruta='C:\\WindowsApps\\c'), I(['d'], (3, 13, 1), ruta='d'),
                  I(['e'], (3, 10, 11), ruta='e'), I(['f'], (3, 13, 5), sin_gil=True, ruta='f'),
                  I(['g'], (3, 12, 0), bits=32, ruta='g'), I(['h'], (3, 12, 9), ruta='h')]
    ordenados = arranque.ordenar_interpretes(candidatos)
    assert [i.ruta for i in ordenados] == ['d', 'C:\\WindowsApps\\c']


@pytest.mark.parametrize('version,bits,sin_gil,compatible', [
    ((3, 10, 11), 64, False, False),
    ((3, 11, 9), 64, False, False),
    ((3, 12, 9), 64, False, False),
    ((3, 13, 0), 64, False, True),
    ((3, 13, 5), 32, False, False),
    ((3, 13, 5), 64, True, False),
    ((3, 14, 0), 64, False, False),
    ((3, 15, 0), 64, False, False),
])
def test_compatibilidad_del_entorno_fijado(arranque, version, bits, sin_gil, compatible):
    interprete = arranque.Interprete(['python'], version, bits=bits, sin_gil=sin_gil)
    assert interprete.compatible is compatible


@pytest.mark.parametrize('version', [(3, 11, 9), (3, 14, 0)])
def test_no_elige_python_fuera_del_entorno_fijado(arranque, monkeypatch, version):
    monkeypatch.setattr(arranque, 'candidatos', lambda: [['python']])
    monkeypatch.setattr(arranque, 'sondear', lambda comando: arranque.Interprete(comando, version, ruta='python'))
    with pytest.raises(arranque.ErrorArranque, match='Python 3.13') as error:
        arranque.elegir_interprete()
    assert error.value.accion == 'instalar_python'


def test_sonda_rechaza_compilacion_sin_gil_aunque_este_activado(arranque, monkeypatch, capsys):
    obtener_configuracion = sysconfig.get_config_var
    monkeypatch.setattr(sysconfig, 'get_config_var',
                        lambda nombre: 1 if nombre == 'Py_GIL_DISABLED' else obtener_configuracion(nombre))
    monkeypatch.setattr(sys, '_is_gil_enabled', lambda: True, raising=False)
    exec(arranque._SONDA, {})
    assert capsys.readouterr().out.split(maxsplit=6)[4] == '1'


@pytest.mark.parametrize('version', [(3, 11, 9), (3, 14, 0)])
def test_no_recrea_un_entorno_incompatible_en_uso(arranque, monkeypatch, tmp_path, version):
    entorno = tmp_path / '.venv'
    python = entorno / 'python'
    entorno.mkdir()
    python.touch()
    errores, recreados = [], []
    ui = SimpleNamespace(estado=lambda *args: None, progreso=lambda *args: None, fin_error=errores.append)
    monkeypatch.setattr(arranque, 'ubicaciones', lambda raiz: (entorno, tmp_path / 'estado'))
    monkeypatch.setattr(arranque, 'python_entorno', lambda carpeta: python)
    monkeypatch.setattr(arranque, 'sondear', lambda comando: arranque.Interprete(comando, version))
    monkeypatch.setattr(arranque, 'corriendo_desde', lambda carpeta: True)
    monkeypatch.setattr(arranque, 'crear_entorno', lambda *args: recreados.append(args))
    assert arranque.preparar(arranque.Opciones(reparar=True), ui, threading.Event()) == 1
    assert not recreados
    assert len(errores) == 1 and 'en uso' in errores[0].mensaje
    assert python.exists()


def test_sondea_el_interprete_actual(arranque):
    actual = arranque.sondear([sys.executable])
    assert actual is not None
    assert actual.version == tuple(sys.version_info[:3])
    assert actual.compatible == (arranque.MINIMA <= sys.version_info[:2] < arranque.LIMITE
                                 and sys.maxsize > 2 ** 32
                                 and not sysconfig.get_config_var('Py_GIL_DISABLED')
                                 and getattr(sys, '_is_gil_enabled', lambda: True)())


def test_evaluar_diagnostico(arranque, tmp_path):
    origen = str(RAIZ / 'src' / 'micrograno' / '__init__.py')
    completo = {'faltan': [], 'distintos': [], 'modulos': {'micrograno': origen, 'numpy': 'x'}}
    assert arranque.evaluar_diagnostico(completo, RAIZ).listo
    incompleto = {'faltan': ['PySide6'], 'distintos': [['numpy', '2.0.0', '2.3.5']],
                  'modulos': {'micrograno': str(tmp_path / 'otro' / '__init__.py'), 'scipy': None}}
    d = arranque.evaluar_diagnostico(incompleto, RAIZ)
    assert not d.listo
    assert len(d.problemas) == 4


def test_diagnostico_del_entorno_de_pruebas(arranque):
    d = arranque.diagnosticar(Path(sys.executable), RAIZ)
    assert d.datos['python'] == list(sys.version_info[:3])
    assert not d.datos['faltan']
    assert arranque.dentro_de(Path(d.datos['modulos']['micrograno']), RAIZ / 'src')


def test_mensajes_de_error_de_pip(arranque):
    red = arranque.error_de_pip('ERROR: ... NewConnectionError(... getaddrinfo failed)')
    assert 'conexión' in red.mensaje
    assert arranque.error_de_pip('ERROR: No matching distribution found for pandas').accion == 'reparar'
    assert 'certificados' in arranque.error_de_pip('SSLError CERTIFICATE_VERIFY_FAILED').mensaje
    assert arranque.error_de_pip('algo distinto').accion == 'reparar'


def test_lector_de_progreso_de_pip(arranque):
    class Ui:
        def __init__(self):
            self.estados, self.progresos = [], []

        def estado(self, texto, detalle=''):
            self.estados.append((texto, detalle))

        def progreso(self, valor):
            self.progresos.append(valor)

    ui = Ui()
    lector = arranque.LectorPip(ui)
    assert lector.leer('Collecting numpy<3,>=2.0 (from micrograno==1.0.0)')
    assert lector.leer('Downloading numpy-2.3.5-cp313-cp313-win_amd64.whl (12.8 MB)')
    assert not lector.leer('Progress 50 of 200')
    assert lector.leer('Installing collected packages: numpy, scipy, micrograno')
    assert ui.estados[1] == ('Descargando librerías…', 'numpy 2.3.5 · 12.8 MB')
    assert ui.estados[-1][0] == 'Instalando 3 paquetes…'
    assert ui.progresos == [0.0, 0.25, None]
    assert arranque.nombre_paquete('https://x/y/pyside6_addons-6.10.2-cp39-abi3-win_amd64.whl') == 'pyside6_addons 6.10.2'


def test_comprobar_no_modifica_el_repositorio(tmp_path):
    entorno_existia = (RAIZ / '.venv').exists()
    variables = dict(os.environ, MICROGRANO_SIN_PAUSA='1', PYTHONIOENCODING='utf-8')
    r = subprocess.run([sys.executable, str(RUTA), '--comprobar', '--consola'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180, env=variables, stdin=subprocess.DEVNULL)
    assert r.returncode in (0, 1), r.stdout + r.stderr
    assert 'Comprobando el entorno' in r.stdout
    assert (RAIZ / '.venv').exists() == entorno_existia


def test_la_interfaz_avisa_cuando_su_ventana_es_visible(tmp_path, monkeypatch):
    from micrograno_lab import app
    senal = tmp_path / 'listo.txt'
    monkeypatch.setenv('MICROGRANO_SENAL_LISTO', str(senal))
    app._senalar_ventana_visible()
    assert senal.read_text(encoding='utf-8') == str(os.getpid())
    assert 'MICROGRANO_SENAL_LISTO' not in os.environ
