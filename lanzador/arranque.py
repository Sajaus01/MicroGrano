#!/usr/bin/env python3
"""Arranque de MicroGrano Lab: prepara el entorno de Python y abre la interfaz.

1. Busca Python 3.13 de 64 bits con GIL, compatible con las versiones fijadas.
2. Crea el entorno virtual `.venv` del repositorio si no existe o está dañado.
3. Comprueba las librerías contra `pyproject.toml` y `constraints.txt` e instala
   solo cuando falta algo o no coincide la versión fijada.
4. Abre MicroGrano Lab y espera a que su ventana aparezca.

Solo usa la biblioteca estándar, de modo que funciona antes de instalar nada.

Uso:
    python lanzador/arranque.py                  comprobar, instalar si hace falta y abrir
    python lanzador/arranque.py --consola        mostrar el progreso en la consola
    python lanzador/arranque.py --solo-instalar  preparar el entorno sin abrir la interfaz
    python lanzador/arranque.py --comprobar      informar del estado sin cambiar nada
    python lanzador/arranque.py --reparar        recrear el entorno desde cero
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

VERSION_LANZADOR = '1.0'
PREFERIDAS = ((3, 13),)
MINIMA, LIMITE = (3, 13), (3, 14)
RAIZ = Path(__file__).resolve().parent.parent
RECURSOS = Path(__file__).resolve().parent / 'recursos'
ES_WINDOWS = os.name == 'nt'
ES_MAC = sys.platform == 'darwin'
SIN_VENTANA = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if ES_WINDOWS else 0
URL_PYTHON = 'https://www.python.org/downloads/'
ESPACIO_MINIMO = 1_500_000_000
ESPERA_VENTANA = 150
MODULOS = ('micrograno', 'micrograno_lab', 'numpy', 'scipy', 'skimage', 'pandas', 'PIL',
           'matplotlib', 'tifffile', 'PySide6')


class Cancelado(Exception):
    """El usuario canceló la preparación."""


class ErrorArranque(Exception):
    """Fallo explicable al usuario, con una sugerencia y, si procede, una acción."""

    def __init__(self, mensaje: str, sugerencia: str = '', accion: str | None = None, detalle: str = ''):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.sugerencia = sugerencia
        self.accion = accion
        self.detalle = detalle


# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

def entorno_limpio() -> dict:
    """Variables de entorno para los subprocesos, sin rutas de Python ajenas."""
    entorno = dict(os.environ)
    for clave in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', '__PYVENV_LAUNCHER__'):
        entorno.pop(clave, None)
    entorno['PYTHONIOENCODING'] = 'utf-8'
    return entorno


def ejecutar(comando, timeout: float = 60, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run([str(x) for x in comando], capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout, cwd=cwd, env=entorno_limpio(),
                          stdin=subprocess.DEVNULL, creationflags=SIN_VENTANA)


def ultima_linea(texto: str) -> str:
    lineas = [x for x in (texto or '').strip().splitlines() if x.strip()]
    return lineas[-1] if lineas else ''


def dentro_de(ruta: Path, base: Path) -> bool:
    try:
        a = os.path.normcase(str(Path(ruta).resolve()))
        b = os.path.normcase(str(Path(base).resolve()))
        return os.path.commonpath([a, b]) == b
    except (OSError, ValueError):
        return False


def abrir_en_sistema(destino) -> None:
    """Abre un archivo, una carpeta o una dirección web con la aplicación del sistema."""
    destino = str(destino)
    try:
        if destino.startswith('http'):
            webbrowser.open(destino)
        elif ES_WINDOWS:
            os.startfile(destino)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(['open' if ES_MAC else 'xdg-open', destino])
    except Exception:
        pass


class Registro:
    """Registro de texto para diagnosticar instalaciones; se recorta si crece mucho."""

    def __init__(self, ruta: Path):
        self.ruta = ruta
        self._archivo = None
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            if ruta.exists() and ruta.stat().st_size > 2_000_000:
                ruta.write_bytes(ruta.read_bytes()[-1_000_000:])
            self._archivo = open(ruta, 'a', encoding='utf-8', errors='replace')
        except OSError:
            self._archivo = None
        self.escribir(f'==== {datetime.now():%Y-%m-%d %H:%M:%S} · lanzador {VERSION_LANZADOR} · '
                      f'Python {platform.python_version()} · {platform.platform()} ====')

    def escribir(self, texto: str) -> None:
        if self._archivo is not None:
            try:
                self._archivo.write(texto.rstrip('\n') + '\n')
                self._archivo.flush()
            except (OSError, ValueError):
                pass

    def cerrar(self) -> None:
        if self._archivo is not None:
            try:
                self._archivo.close()
            except OSError:
                pass
            self._archivo = None


# ---------------------------------------------------------------------------
# Requisitos del proyecto
# ---------------------------------------------------------------------------

def normalizar_nombre(nombre: str) -> str:
    return re.sub(r'[-_.]+', '-', nombre).lower()


def leer_restricciones(ruta: Path) -> dict[str, str]:
    """Versiones exactas `paquete==versión` de constraints.txt, por nombre normalizado."""
    fijadas = {}
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.split('#', 1)[0].strip()
        m = re.match(r'^([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s;]+)', linea)
        if m:
            fijadas[normalizar_nombre(m.group(1))] = m.group(2)
    return fijadas


def leer_dependencias(ruta: Path) -> list[str]:
    """Nombres de las dependencias de ejecución y del extra `gui` de pyproject.toml."""
    texto = ruta.read_text(encoding='utf-8')
    nombres = []
    for patron in (r'^dependencies\s*=\s*\[(.*?)\]', r'^gui\s*=\s*\[(.*?)\]'):
        m = re.search(patron, texto, re.S | re.M)
        if not m:
            continue
        for doble, simple in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1)):
            requisito = (doble or simple).strip()
            nombre = re.split(r'[\s<>=!~;\[(]', requisito, maxsplit=1)[0]
            if nombre and nombre not in nombres:
                nombres.append(nombre)
    return nombres


def leer_version_proyecto(ruta: Path) -> str | None:
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', ruta.read_text(encoding='utf-8'), re.M)
    return m.group(1) if m else None


def requisitos(raiz: Path = RAIZ) -> dict[str, str | None]:
    """Paquetes necesarios y la versión exacta esperada (None si no está fijada)."""
    pyproject = raiz / 'pyproject.toml'
    restricciones = raiz / 'constraints.txt'
    fijadas = leer_restricciones(restricciones) if restricciones.is_file() else {}
    pedidos = {nombre: fijadas.get(normalizar_nombre(nombre)) for nombre in leer_dependencias(pyproject)}
    pedidos['micrograno'] = leer_version_proyecto(pyproject)
    return pedidos


def firma(raiz: Path = RAIZ) -> str:
    h = hashlib.sha256(VERSION_LANZADOR.encode())
    for nombre in ('pyproject.toml', 'constraints.txt'):
        ruta = raiz / nombre
        if ruta.is_file():
            h.update(ruta.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Intérpretes de Python
# ---------------------------------------------------------------------------

_SONDA = ('import sys,sysconfig,struct,importlib.util as u;'
          'g=getattr(sys,"_is_gil_enabled",None);'
          'print(sys.version_info[0],sys.version_info[1],sys.version_info[2],struct.calcsize("P")*8,'
          'int(bool(sysconfig.get_config_var("Py_GIL_DISABLED")) or (g is not None and not g())),'
          'int(u.find_spec("venv") is not None and u.find_spec("ensurepip") is not None),'
          'sys.executable)')


@dataclass
class Interprete:
    comando: list
    version: tuple
    bits: int = 64
    sin_gil: bool = False
    con_venv: bool = True
    ruta: str = ''

    @property
    def compatible(self) -> bool:
        return MINIMA <= tuple(self.version[:2]) < LIMITE and self.bits == 64 and not self.sin_gil

    @property
    def texto(self) -> str:
        return '.'.join(str(x) for x in self.version)


def sondear(comando, timeout: float = 30) -> Interprete | None:
    """Ejecuta el intérprete para conocer su versión; None si no funciona."""
    comando = [str(x) for x in comando]
    if ES_WINDOWS and comando[0].lower().endswith('pythonw.exe'):
        consola = Path(comando[0]).with_name('python.exe')
        if consola.is_file():
            comando = [str(consola)] + comando[1:]
    try:
        r = ejecutar(comando + ['-c', _SONDA], timeout=timeout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if r.returncode != 0:
        return None
    partes = ultima_linea(r.stdout).split(maxsplit=6)
    if len(partes) < 7:
        return None
    try:
        mayor, menor, micro, bits, sin_gil, con_venv = (int(x) for x in partes[:6])
    except ValueError:
        return None
    return Interprete(comando, (mayor, menor, micro), bits, bool(sin_gil), bool(con_venv), partes[6])


def leer_lista_py(texto: str) -> list[tuple[tuple[int, int], str]]:
    """Interpreta la salida de `py -0p` (formatos nuevo y antiguo del lanzador)."""
    encontrados = []
    for linea in texto.splitlines():
        m = re.match(r'\s*-(?:V:)?(\d+)\.(\d+)(\S*)\s+(?:\*\s+)?(\S.*?)\s*$', linea)
        if not m or m.group(3) not in ('', '-64'):
            continue  # Se descartan 32 bits, ARM y las variantes sin GIL («t»).
        encontrados.append(((int(m.group(1)), int(m.group(2))), m.group(4)))
    return encontrados


def orden_version(version) -> int:
    version = tuple(version[:2])
    return PREFERIDAS.index(version) if version in PREFERIDAS else len(PREFERIDAS)


def buscar_lanzador_py() -> str | None:
    ruta = shutil.which('py')
    if ruta:
        return ruta
    for candidata in (Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Python' / 'Launcher' / 'py.exe',
                      Path(os.environ.get('WINDIR', r'C:\Windows')) / 'py.exe'):
        if candidata.is_file():
            return str(candidata)
    return None


def candidatos() -> list[list[str]]:
    """Comandos que podrían iniciar un Python adecuado, del más al menos probable."""
    lista: list[list[str]] = []

    def agregar(*comando):
        c = [str(x) for x in comando]
        if c not in lista:
            lista.append(c)

    agregar(sys.executable)
    if ES_WINDOWS:
        py = buscar_lanzador_py()
        if py:
            try:
                r = ejecutar([py, '-0p'], timeout=30)
                if r.returncode == 0:
                    for _, ruta in sorted(leer_lista_py(r.stdout), key=lambda x: orden_version(x[0])):
                        agregar(ruta)
            except (OSError, subprocess.SubprocessError):
                pass
        local = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
        programas = [Path(os.environ[v]) for v in ('ProgramFiles', 'ProgramW6432') if os.environ.get(v)]
        for mayor, menor in PREFERIDAS:
            for base in [local / 'Programs' / 'Python'] + programas:
                ruta = base / f'Python{mayor}{menor}' / 'python.exe'
                if ruta.is_file():
                    agregar(ruta)
        for nombre in ('python', 'python3'):
            ruta = shutil.which(nombre)
            # El alias de Microsoft Store abriría la tienda si Python no está instalado.
            if ruta and 'windowsapps' not in ruta.lower():
                agregar(ruta)
    else:
        for mayor, menor in PREFERIDAS:
            ruta = shutil.which(f'python{mayor}.{menor}')
            if ruta:
                agregar(ruta)
            if ES_MAC:
                v = f'{mayor}.{menor}'
                for base in (f'/Library/Frameworks/Python.framework/Versions/{v}/bin/python{v}',
                             f'/opt/homebrew/bin/python{v}', f'/usr/local/bin/python{v}'):
                    if Path(base).is_file():
                        agregar(base)
        for nombre in ('python3', 'python'):
            ruta = shutil.which(nombre)
            if ruta:
                agregar(ruta)
    return lista


def ordenar_interpretes(interpretes: list[Interprete]) -> list[Interprete]:
    compatibles = [i for i in interpretes if i.compatible]
    return sorted(compatibles, key=lambda i: (orden_version(i.version), 'windowsapps' in i.ruta.lower()))


def elegir_interprete(registro: Registro | None = None, excluir: Path | None = None) -> Interprete:
    """Mejor Python disponible; `excluir` descarta los intérpretes de ese entorno."""
    encontrados, rutas = [], set()
    for interprete in (sondear(c) for c in candidatos()):
        if interprete is None or os.path.normcase(interprete.ruta) in rutas:
            continue
        if excluir is not None and dentro_de(Path(interprete.ruta), excluir):
            continue
        rutas.add(os.path.normcase(interprete.ruta))
        encontrados.append(interprete)
    if registro is not None:
        for i in encontrados:
            registro.escribir(f'Python encontrado: {i.texto} ({i.bits} bits) en {i.ruta}')
    ordenados = ordenar_interpretes(encontrados)
    if ordenados:
        elegido = ordenados[0]
        if not elegido.con_venv:
            v = f'{elegido.version[0]}.{elegido.version[1]}'
            raise ErrorArranque(f'Python {elegido.texto} no incluye el módulo «venv».',
                                f'Instale el paquete del sistema, por ejemplo: sudo apt install python{v}-venv')
        return elegido
    vistos = ', '.join(sorted({f'{i.texto} ({i.bits} bits{", sin GIL" if i.sin_gil else ""})' for i in encontrados}))
    raise ErrorArranque('No se encontró Python 3.13 de 64 bits con GIL.',
                        (f'Versiones encontradas: {vistos}. ' if vistos else '')
                        + 'Instale Python 3.13 y vuelva a abrir MicroGrano Lab.', 'instalar_python')


# ---------------------------------------------------------------------------
# Entorno virtual
# ---------------------------------------------------------------------------

def carpeta_usuario() -> Path:
    if ES_WINDOWS:
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'MicroGrano'
    if ES_MAC:
        return Path.home() / 'Library' / 'Application Support' / 'MicroGrano'
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'micrograno'


def es_escribible(carpeta: Path) -> bool:
    prueba = carpeta / f'.prueba-escritura-{os.getpid()}'
    try:
        prueba.write_text('ok', encoding='utf-8')
        prueba.unlink()
        return True
    except OSError:
        return False


def ubicaciones(raiz: Path = RAIZ) -> tuple[Path, Path]:
    """(entorno, carpeta de estado). Si el repositorio es de solo lectura, se usa el perfil."""
    if (raiz / '.venv').exists() or es_escribible(raiz):
        return raiz / '.venv', raiz / '.micrograno'
    base = carpeta_usuario() / ('repo-' + hashlib.sha256(str(raiz).encode('utf-8')).hexdigest()[:12])
    return base / 'venv', base


def python_entorno(entorno: Path, con_ventana: bool = False) -> Path:
    if ES_WINDOWS:
        nombre = 'pythonw.exe' if con_ventana else 'python.exe'
        ruta = entorno / 'Scripts' / nombre
        return ruta if ruta.exists() or not con_ventana else entorno / 'Scripts' / 'python.exe'
    return entorno / 'bin' / 'python'


def comprobar_espacio(carpeta: Path) -> None:
    existente = carpeta
    while not existente.exists() and existente != existente.parent:
        existente = existente.parent
    try:
        libre = shutil.disk_usage(str(existente)).free
    except OSError:
        return
    if libre < ESPACIO_MINIMO:
        raise ErrorArranque(f'Espacio en disco insuficiente ({libre / 1e9:.1f} GB libres).',
                            'Se necesitan al menos 1.5 GB para Python y las librerías. Libere espacio y reintente.')


def retirar_entorno(entorno: Path) -> None:
    def quitar_solo_lectura(funcion, ruta, _info):
        try:
            os.chmod(ruta, 0o700)
            funcion(ruta)
        except OSError:
            pass
    if not entorno.exists():
        return
    try:
        shutil.rmtree(entorno, onerror=quitar_solo_lectura)
    except OSError:
        pass
    if entorno.exists():
        raise ErrorArranque('No se pudo reemplazar el entorno de Python dañado.',
                            'Cierre MicroGrano Lab y otros programas que usen la carpeta «.venv» y reintente.')


def crear_entorno(base: Interprete, entorno: Path, registro: Registro) -> None:
    retirar_entorno(entorno)
    entorno.parent.mkdir(parents=True, exist_ok=True)
    registro.escribir(f'Creando el entorno con {base.ruta}')
    try:
        r = ejecutar(base.comando + ['-m', 'venv', str(entorno)], timeout=600)
    except subprocess.TimeoutExpired:
        raise ErrorArranque('La creación del entorno de Python tardó demasiado.', 'Reintente en unos minutos.')
    registro.escribir(r.stdout + r.stderr)
    if r.returncode != 0 or not python_entorno(entorno).exists():
        raise ErrorArranque('No se pudo crear el entorno de Python.', ultima_linea(r.stderr) or ultima_linea(r.stdout),
                            'reparar', r.stderr)


# ---------------------------------------------------------------------------
# Diagnóstico e instalación
# ---------------------------------------------------------------------------

COMPROBACION = r'''
import json, sys
from importlib import metadata, util
pedidos = json.loads(sys.argv[1])
salida = {"python": list(sys.version_info[:3]), "faltan": [], "distintos": [], "modulos": {}}
for nombre, version in pedidos.items():
    try:
        instalada = metadata.version(nombre)
    except metadata.PackageNotFoundError:
        salida["faltan"].append(nombre)
        continue
    if version and instalada != version:
        salida["distintos"].append([nombre, instalada, version])
for modulo in json.loads(sys.argv[2]):
    try:
        spec = util.find_spec(modulo)
        salida["modulos"][modulo] = spec.origin if spec is not None else None
    except Exception:
        salida["modulos"][modulo] = None
print(json.dumps(salida))
'''


@dataclass
class Diagnostico:
    listo: bool
    problemas: list = field(default_factory=list)
    datos: dict = field(default_factory=dict)


def evaluar_diagnostico(datos: dict, raiz: Path = RAIZ) -> Diagnostico:
    problemas = [f'Falta {nombre}.' for nombre in datos.get('faltan', [])]
    problemas += [f'{nombre} {instalada} instalado; se requiere {esperada}.'
                  for nombre, instalada, esperada in datos.get('distintos', [])]
    modulos = datos.get('modulos', {})
    problemas += [f'No se puede importar {m}.' for m, origen in modulos.items() if not origen]
    origen = modulos.get('micrograno')
    if origen and not dentro_de(Path(origen), raiz / 'src'):
        problemas.append('MicroGrano está instalado desde otra carpeta; se enlazará este repositorio.')
    return Diagnostico(not problemas, problemas, datos)


def diagnosticar(python: Path, raiz: Path = RAIZ, pedidos: dict | None = None) -> Diagnostico:
    pedidos = requisitos(raiz) if pedidos is None else pedidos
    try:
        r = ejecutar([python, '-c', COMPROBACION, json.dumps(pedidos), json.dumps(MODULOS)], timeout=120, cwd=raiz)
    except (OSError, subprocess.SubprocessError) as exc:
        return Diagnostico(False, [f'No se pudo ejecutar el Python del entorno: {exc}'])
    if r.returncode != 0:
        return Diagnostico(False, ['El Python del entorno falló: ' + (ultima_linea(r.stderr) or 'sin detalle')])
    try:
        datos = json.loads(ultima_linea(r.stdout))
    except ValueError:
        return Diagnostico(False, ['Respuesta inesperada al comprobar el entorno.'])
    return evaluar_diagnostico(datos, raiz)


def version_pip(python: Path) -> tuple:
    try:
        r = ejecutar([python, '-m', 'pip', '--version'], timeout=120)
    except (OSError, subprocess.SubprocessError):
        return ()
    m = re.search(r'pip (\d+)\.(\d+)', r.stdout or '')
    return (int(m.group(1)), int(m.group(2))) if r.returncode == 0 and m else ()


def nombre_paquete(archivo: str) -> str:
    base = archivo.rsplit('/', 1)[-1]
    partes = base.split('-')
    return f'{partes[0]} {partes[1]}' if len(partes) > 1 and partes[1][:1].isdigit() else partes[0]


class LectorPip:
    """Convierte la salida de pip en mensajes de progreso comprensibles."""

    def __init__(self, ui):
        self.ui = ui
        self.buscados = 0

    def leer(self, linea: str) -> bool:
        """Actualiza la interfaz; devuelve False para líneas que no se registran."""
        m = re.match(r'Progress (\d+) of (\d+)', linea)
        if m:
            total = int(m.group(2))
            if total > 0:
                self.ui.progreso(int(m.group(1)) / total)
            return False
        m = re.match(r'\s*Collecting (\S+)', linea)
        if m:
            self.buscados += 1
            self.ui.estado('Buscando las librerías necesarias…', f'{self.buscados} · {m.group(1)}')
            return True
        m = re.match(r'\s*Downloading (\S+) \(([^)]+)\)', linea)
        if m and not m.group(1).endswith('.metadata'):
            self.ui.estado('Descargando librerías…', f'{nombre_paquete(m.group(1))} · {m.group(2)}')
            self.ui.progreso(0.0)
            return True
        m = re.match(r'\s*Using cached (\S+)', linea)
        if m and not m.group(1).endswith('.metadata'):
            self.ui.estado('Usando librerías ya descargadas…', nombre_paquete(m.group(1)))
            return True
        if linea.startswith('Installing collected packages:'):
            cantidad = len(linea.split(':', 1)[1].split(','))
            self.ui.estado(f'Instalando {cantidad} paquetes…', 'Este paso puede tardar uno o dos minutos.')
            self.ui.progreso(None)
            return True
        if 'editable' in linea and ('Building' in linea or 'Preparing' in linea):
            self.ui.estado('Enlazando MicroGrano con este repositorio…')
            return True
        return True


def error_de_pip(texto: str) -> ErrorArranque:
    t = texto.lower()
    if any(x in t for x in ('newconnectionerror', 'failed to establish a new connection', 'getaddrinfo failed',
                            'temporary failure in name resolution', 'could not resolve host', 'max retries exceeded',
                            'no connection could be made', 'network is unreachable', 'read timed out',
                            'connection aborted', 'proxyerror')):
        return ErrorArranque('No hay conexión con el índice de paquetes de Python (PyPI).',
                             'Compruebe la conexión a Internet o la configuración del proxy y pulse Reintentar. '
                             'Lo ya descargado se conserva.', None, texto)
    if 'certificate_verify_failed' in t or 'sslerror' in t:
        return ErrorArranque('La conexión segura con PyPI fue rechazada (certificados).',
                             'Suele deberse a un proxy o antivirus que intercepta HTTPS. Consulte a su soporte '
                             'técnico o pruebe desde otra red.', None, texto)
    if 'no space left' in t or 'errno 28' in t:
        return ErrorArranque('El disco se llenó durante la instalación.', 'Libere al menos 1.5 GB y reintente.',
                             None, texto)
    if any(x in t for x in ('permission denied', 'access is denied', 'acceso denegado', 'winerror 5', 'winerror 32')):
        return ErrorArranque('Un archivo del entorno está en uso o protegido.',
                             'Cierre MicroGrano Lab y otras ventanas de Python y pulse Reintentar.', 'reparar', texto)
    if 'no matching distribution' in t or 'could not find a version that satisfies' in t:
        return ErrorArranque('No hay paquetes compatibles con esta versión de Python o de sistema.',
                             'Use Python 3.13 de 64 bits con GIL y pulse Reparar.', 'reparar', texto)
    if 'microsoft visual c++' in t or 'subprocess-exited-with-error' in t or 'failed building wheel' in t:
        return ErrorArranque('Una librería intentó compilarse desde el código fuente y falló.',
                             'Suele ocurrir con versiones de Python muy nuevas. Use Python 3.13 y pulse Reparar.',
                             'reparar', texto)
    return ErrorArranque('La instalación de las librerías falló.', ultima_linea(texto) or 'Consulte el registro.',
                         'reparar', texto)


def asegurar_pip(python: Path, ui, registro: Registro) -> tuple:
    version = version_pip(python)
    if version:
        return version
    ui.estado('Instalando pip en el entorno…')
    r = ejecutar([python, '-m', 'ensurepip', '--upgrade'], timeout=600)
    registro.escribir(r.stdout + r.stderr)
    version = version_pip(python)
    if not version:
        raise ErrorArranque('El entorno no tiene pip y no se pudo instalar.', ultima_linea(r.stderr), 'reparar',
                            r.stderr)
    return version


def instalar(python: Path, raiz: Path, ui, registro: Registro, cancelacion: threading.Event,
             forzar: bool = False) -> None:
    pip = asegurar_pip(python, ui, registro)
    comando = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input',
               '-c', 'constraints.txt', '-e', '.[gui]']
    if forzar:
        comando.append('--force-reinstall')
    if pip >= (24, 1):
        comando += ['--progress-bar', 'raw']
    registro.escribir('$ ' + ' '.join(comando))
    entorno = entorno_limpio()
    entorno['PIP_NO_COLOR'] = '1'
    proceso = subprocess.Popen(comando, cwd=str(raiz), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace',
                               bufsize=1, env=entorno, creationflags=SIN_VENTANA)
    ui.proceso = proceso
    lector = LectorPip(ui)
    lineas: list[str] = []
    try:
        assert proceso.stdout is not None
        for linea in proceso.stdout:
            if cancelacion.is_set():
                break
            linea = linea.rstrip()
            if lector.leer(linea):
                lineas.append(linea)
                registro.escribir(linea)
                ui.registrar(linea)
    finally:
        if cancelacion.is_set() and proceso.poll() is None:
            proceso.terminate()
        codigo = proceso.wait()
        ui.proceso = None
    if cancelacion.is_set():
        raise Cancelado()
    if codigo != 0:
        raise error_de_pip('\n'.join(lineas[-80:]))


def guardar_estado(estado: Path, entorno: Path, interprete: Interprete | None) -> None:
    try:
        estado.mkdir(parents=True, exist_ok=True)
        (estado / 'entorno.json').write_text(json.dumps({
            'firma': firma(), 'entorno': str(entorno), 'repositorio': str(RAIZ),
            'python': interprete.texto if interprete else None, 'lanzador': VERSION_LANZADOR,
            'fecha': datetime.now().isoformat(timespec='seconds')}, ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Apertura de la interfaz
# ---------------------------------------------------------------------------

def abrir_interfaz(entorno: Path, estado: Path, archivos, registro: Registro, cancelacion: threading.Event) -> None:
    """Inicia MicroGrano Lab y espera a que su ventana esté visible (o a que falle)."""
    ejecutable = python_entorno(entorno, con_ventana=True)
    estado.mkdir(parents=True, exist_ok=True)
    senal = estado / f'listo-{os.getpid()}.txt'
    try:
        senal.unlink()
    except OSError:
        pass
    variables = entorno_limpio()
    variables['MICROGRANO_SENAL_LISTO'] = str(senal)
    opciones = {}
    if ES_WINDOWS:
        opciones['creationflags'] = (getattr(subprocess, 'DETACHED_PROCESS', 0x8)
                                     | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200))
    else:
        opciones['start_new_session'] = True
    salida = open(estado / 'interfaz.log', 'w', encoding='utf-8', errors='replace')
    comando = [str(ejecutable), '-m', 'micrograno_lab'] + [str(x) for x in archivos]
    registro.escribir('$ ' + ' '.join(comando))
    try:
        proceso = subprocess.Popen(comando, cwd=str(RAIZ), stdout=salida, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, env=variables, close_fds=True, **opciones)
    finally:
        salida.close()
    limite = time.monotonic() + ESPERA_VENTANA
    while time.monotonic() < limite and not cancelacion.is_set():
        if senal.exists():
            try:
                senal.unlink()
            except OSError:
                pass
            registro.escribir('La ventana de MicroGrano Lab está abierta.')
            return
        codigo = proceso.poll()
        if codigo is not None:
            if codigo == 0:
                return
            try:
                detalle = (estado / 'interfaz.log').read_text(encoding='utf-8', errors='replace')[-6000:]
            except OSError:
                detalle = ''
            registro.escribir(detalle)
            raise ErrorArranque('MicroGrano Lab se cerró al iniciar.',
                                ultima_linea(detalle) or 'Pulse Reparar para reinstalar las librerías.', 'reparar',
                                detalle)
        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Proceso completo
# ---------------------------------------------------------------------------

@dataclass
class Opciones:
    consola: bool = False
    solo_instalar: bool = False
    comprobar: bool = False
    reparar: bool = False
    archivos: list = field(default_factory=list)


def corriendo_desde(entorno: Path) -> bool:
    return dentro_de(Path(sys.executable), entorno)


def preparar(op: Opciones, ui, cancelacion: threading.Event) -> int:
    """Comprueba, instala si hace falta y abre la interfaz. Devuelve el código de salida."""
    entorno, estado = ubicaciones(RAIZ)
    registro = Registro(estado / 'lanzador.log')
    ui.ruta_registro = registro.ruta
    try:
        ui.estado('Comprobando el entorno…')
        ui.progreso(None)
        if not (RAIZ / 'pyproject.toml').is_file() or not (RAIZ / 'src' / 'micrograno_lab').is_dir():
            raise ErrorArranque('No se encontró el código de MicroGrano junto al lanzador.',
                                'Mantenga la carpeta «lanzador» dentro del repositorio completo y, si lo descargó '
                                'como .zip, extraiga todo su contenido antes de abrirlo.')
        pedidos = requisitos(RAIZ)
        registro.escribir(f'Repositorio: {RAIZ}\nEntorno: {entorno}\nRequisitos: {pedidos}')
        python = python_entorno(entorno)
        actual = sondear([python]) if python.exists() else None
        if actual is not None:
            registro.escribir(f'Entorno existente con Python {actual.texto}')
        # Un entorno en uso por este mismo proceso no puede borrarse: se reparan sus paquetes.
        recrear = actual is None or not actual.compatible or (op.reparar and not corriendo_desde(entorno))
        forzar = op.reparar and not recrear
        if recrear:
            if op.comprobar:
                ui.fin_ok('Falta crear el entorno de Python; se creará al abrir MicroGrano Lab.', exito=False)
                return 1
            if corriendo_desde(entorno):
                raise ErrorArranque('El entorno incompatible está en uso por este lanzador.',
                                    'Cierre este proceso y abra el archivo de inicio de su sistema, '
                                    'o ejecute arranque.py con un Python 3.13 externo a «.venv». '
                                    'Así podrá reemplazarse el entorno sin borrar el intérprete en uso.')
            ui.estado('Buscando una versión compatible de Python…')
            base = elegir_interprete(registro, excluir=entorno)
            if cancelacion.is_set():
                raise Cancelado()
            comprobar_espacio(entorno.parent)
            ui.estado(f'Creando el entorno con Python {base.texto}…', 'Solo ocurre la primera vez.')
            crear_entorno(base, entorno, registro)
            actual = sondear([python])
        diagnostico = diagnosticar(python, RAIZ, pedidos)
        registro.escribir('Diagnóstico: ' + ('completo' if diagnostico.listo else '; '.join(diagnostico.problemas)))
        if not diagnostico.listo or forzar:
            if op.comprobar:
                ui.fin_ok('Faltan componentes: ' + '; '.join(diagnostico.problemas[:5]), exito=False)
                return 1
            comprobar_espacio(entorno.parent)
            faltan = len(diagnostico.datos.get('faltan', []))
            if forzar:
                detalle = 'Se reinstalan todas las librerías del entorno.'
            elif faltan > 3:
                detalle = 'La primera vez se descargan unos 400 MB; puede tardar varios minutos.'
            else:
                detalle = 'Actualizando componentes…'
            ui.estado('Instalando las librerías necesarias…', detalle)
            instalar(python, RAIZ, ui, registro, cancelacion, forzar=forzar)
            diagnostico = diagnosticar(python, RAIZ, pedidos)
            registro.escribir('Diagnóstico tras instalar: ' + ('completo' if diagnostico.listo
                                                                 else '; '.join(diagnostico.problemas)))
            if not diagnostico.listo:
                raise ErrorArranque('La instalación terminó, pero el entorno sigue incompleto.',
                                    '; '.join(diagnostico.problemas[:4]), 'reparar')
        guardar_estado(estado, entorno, actual)
        if op.comprobar:
            ui.fin_ok('El entorno está completo.')
            return 0
        if op.solo_instalar:
            ui.fin_ok('MicroGrano Lab está listo para usarse.')
            return 0
        ui.estado('Abriendo MicroGrano Lab…', 'La primera apertura puede tardar un poco más.')
        ui.progreso(None)
        abrir_interfaz(entorno, estado, op.archivos, registro, cancelacion)
        if cancelacion.is_set():
            raise Cancelado()
        ui.fin_ok('MicroGrano Lab está abierto.')
        return 0
    except Cancelado:
        registro.escribir('Cancelado por el usuario.')
        ui.fin_cancelado()
        return 2
    except ErrorArranque as exc:
        registro.escribir(f'ERROR: {exc.mensaje} | {exc.sugerencia}\n{exc.detalle}')
        ui.fin_error(exc)
        return 1
    except Exception as exc:  # Defensa final: nunca cerrar sin explicar el motivo.
        detalle = traceback.format_exc()
        registro.escribir(detalle)
        ui.fin_error(ErrorArranque('Error inesperado del lanzador.', str(exc), 'reparar', detalle))
        return 1
    finally:
        registro.cerrar()


def instalar_python(ui, cancelacion: threading.Event) -> None:
    """Instala Python 3.13 para el usuario actual con winget (Windows)."""
    winget = shutil.which('winget') if ES_WINDOWS else None
    if not winget:
        abrir_en_sistema(URL_PYTHON)
        raise ErrorArranque('Instale Python 3.13 desde python.org y vuelva a abrir MicroGrano Lab.',
                            'En Windows, marque «Add python.exe to PATH» durante la instalación.')
    ui.estado('Instalando Python 3.13 con winget…', 'Puede tardar unos minutos; no requiere administrador.')
    ui.progreso(None)
    comando = [winget, 'install', '-e', '--id', 'Python.Python.3.13', '--scope', 'user', '--silent',
               '--accept-package-agreements', '--accept-source-agreements']
    proceso = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               text=True, encoding='utf-8', errors='replace', creationflags=SIN_VENTANA)
    ui.proceso = proceso
    texto = []
    assert proceso.stdout is not None
    for linea in proceso.stdout:
        linea = linea.strip()
        if linea and not set(linea) <= set('-\\|/ █▒░'):
            texto.append(linea)
            ui.registrar(linea)
        if cancelacion.is_set():
            proceso.terminate()
            break
    codigo = proceso.wait()
    ui.proceso = None
    if cancelacion.is_set():
        raise Cancelado()
    if codigo != 0 and not any(i.compatible for i in (sondear(c) for c in candidatos())):
        raise ErrorArranque('winget no pudo instalar Python 3.13.', ultima_linea('\n'.join(texto)), 'instalar_python',
                            '\n'.join(texto))


# ---------------------------------------------------------------------------
# Interfaz de consola
# ---------------------------------------------------------------------------

class InterfazConsola:
    def __init__(self):
        for flujo in (sys.stdout, sys.stderr):
            try:
                flujo.reconfigure(errors='replace')  # type: ignore[union-attr]
            except Exception:
                pass
        self.proceso = None
        self.ruta_registro = None
        self.ultimo_error: ErrorArranque | None = None
        self._ultimo = None
        self._porcentaje = -1

    def estado(self, texto: str, detalle: str = '') -> None:
        # Cada etapa se muestra una vez; las descargas, una línea por archivo.
        if texto == self._ultimo and not texto.startswith('Descargando'):
            return
        print(f'» {texto}' + (f'  ({detalle})' if detalle else ''), flush=True)
        self._ultimo = texto
        self._porcentaje = -1

    def progreso(self, fraccion) -> None:
        if fraccion is None:
            return
        pct = min(100, int(fraccion * 100) // 25 * 25)
        if pct > self._porcentaje and pct > 0:
            print(f'   {pct} %', flush=True)
            self._porcentaje = pct

    def registrar(self, linea: str) -> None:
        pass

    def fin_ok(self, texto: str, exito: bool = True) -> None:
        print(f'{"✓" if exito else "•"} {texto}', flush=True)

    def fin_cancelado(self) -> None:
        print('Preparación cancelada. Podrá continuarla la próxima vez.', flush=True)

    def fin_error(self, error: ErrorArranque) -> None:
        self.ultimo_error = error
        print(f'\n✗ {error.mensaje}', flush=True)
        if error.sugerencia:
            print(f'  {error.sugerencia}', flush=True)
        if self.ruta_registro:
            print(f'  Registro detallado: {self.ruta_registro}', flush=True)


def ejecutar_en_consola(op: Opciones) -> int:
    ui = InterfazConsola()
    cancelacion = threading.Event()
    print('MicroGrano Lab · preparación del entorno\n', flush=True)
    try:
        codigo = preparar(op, ui, cancelacion)
        error = ui.ultimo_error
        interactiva = sys.stdin is not None and sys.stdin.isatty()
        if codigo == 1 and error is not None and error.accion == 'instalar_python' and ES_WINDOWS \
                and interactiva and shutil.which('winget'):
            respuesta = input('\n¿Instalar Python 3.13 ahora con winget (solo para su usuario)? [s/N] ')
            if respuesta.strip().lower() in ('s', 'si', 'sí', 'y', 'yes'):
                try:
                    instalar_python(ui, cancelacion)
                except ErrorArranque as exc:
                    ui.fin_error(exc)
                    return 1
                ui.ultimo_error = None
                codigo = preparar(op, ui, cancelacion)
        return codigo
    except KeyboardInterrupt:
        cancelacion.set()
        if ui.proceso is not None and ui.proceso.poll() is None:
            ui.proceso.terminate()
        print('\nCancelado.')
        return 2


# ---------------------------------------------------------------------------
# Ventana de progreso (tkinter)
# ---------------------------------------------------------------------------

CLARO = {'fondo': '#F5F5F7', 'texto': '#1D1D1F', 'texto2': '#6E6E73', 'acento': '#007AFF',
         'acento_hover': '#1A86FF', 'pista': '#DCDCE1', 'codigo': '#FFFFFF', 'borde': '#D1D1D6',
         'error': '#D70015', 'ok': '#1E7B34', 'boton': '#FFFFFF', 'boton_hover': '#EFEFF2'}
OSCURO = {'fondo': '#1E1E20', 'texto': '#F5F5F7', 'texto2': '#A1A1A6', 'acento': '#0A84FF',
          'acento_hover': '#3396FF', 'pista': '#3A3A3D', 'codigo': '#161618', 'borde': '#46464B',
          'error': '#FF6961', 'ok': '#4CD964', 'boton': '#333336', 'boton_hover': '#3E3E42'}


def sistema_oscuro() -> bool:
    try:
        if ES_WINDOWS:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as clave:
                return winreg.QueryValueEx(clave, 'AppsUseLightTheme')[0] == 0
        if ES_MAC:
            r = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True,
                               timeout=5)
            return 'dark' in r.stdout.lower()
    except Exception:
        pass
    return False


class VentanaProgreso:
    """Ventana pequeña con el estado de la preparación; se cierra al abrir la interfaz."""

    def __init__(self, op: Opciones):
        import tkinter as tk
        from tkinter import font as tkfont
        self.tk = tk
        self.op = op
        if ES_WINDOWS:
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self.c = OSCURO if sistema_oscuro() else CLARO
        self.escala = max(1.0, self.raiz.winfo_fpixels('1i') / 96.0)
        familias = set(tkfont.families(self.raiz))
        base = next((f for f in ('Segoe UI Variable Display', 'Segoe UI', 'SF Pro Text', '.AppleSystemUIFont',
                                 'Helvetica Neue', 'Cantarell', 'Noto Sans', 'DejaVu Sans') if f in familias),
                    'TkDefaultFont')
        mono = next((f for f in ('Cascadia Mono', 'Consolas', 'SF Mono', 'Menlo', 'DejaVu Sans Mono')
                     if f in familias), 'TkFixedFont')
        self.f_titulo = (base, 15, 'bold')
        self.f_estado = (base, 11, 'bold')
        self.f_texto = (base, 10)
        self.f_pie = (base, 9)
        self.f_mono = (mono, 8)
        self.cola: queue.Queue = queue.Queue()
        self.cancelacion = threading.Event()
        self.proceso = None
        self.ruta_registro = None
        self.codigo = 1
        self.trabajando = False
        self._ultimo_error: ErrorArranque | None = None
        self._construir()
        self.raiz.protocol('WM_DELETE_WINDOW', self._pedir_cierre)
        self.raiz.bind('<Escape>', lambda _e: self._pedir_cierre())
        self.raiz.after(40, self._procesar_cola)

    # -- API usada por el hilo de trabajo (a través de la cola) -----------

    def estado(self, texto: str, detalle: str = '') -> None:
        self.cola.put(('estado', texto, detalle))

    def progreso(self, fraccion) -> None:
        self.cola.put(('progreso', fraccion))

    def registrar(self, linea: str) -> None:
        self.cola.put(('registro', linea))

    def fin_ok(self, texto: str, exito: bool = True) -> None:
        self.cola.put(('ok', texto))

    def fin_cancelado(self) -> None:
        self.cola.put(('cancelado',))

    def fin_error(self, error: ErrorArranque) -> None:
        self.cola.put(('error', error))

    # -- Construcción ---------------------------------------------------------

    def s(self, valor: float) -> int:
        return int(round(valor * self.escala))

    def _construir(self):
        tk, c = self.tk, self.c
        r = self.raiz
        r.title('MicroGrano Lab')
        r.configure(bg=c['fondo'])
        r.resizable(False, False)
        self._icono_ventana()
        marco = tk.Frame(r, bg=c['fondo'], padx=self.s(26), pady=self.s(22))
        marco.pack(fill='both', expand=True)
        cabecera = tk.Frame(marco, bg=c['fondo'])
        cabecera.pack(fill='x')
        self._imagen = self._cargar_imagen(self.s(56))
        if self._imagen is not None:
            tk.Label(cabecera, image=self._imagen, bg=c['fondo']).pack(side='left', padx=(0, self.s(14)))
        textos = tk.Frame(cabecera, bg=c['fondo'])
        textos.pack(side='left', fill='x', expand=True)
        tk.Label(textos, text='MicroGrano Lab', font=self.f_titulo, fg=c['texto'], bg=c['fondo'],
                 anchor='w').pack(fill='x')
        tk.Label(textos, text='Análisis reproducible de micrografías metalográficas', font=self.f_pie,
                 fg=c['texto2'], bg=c['fondo'], anchor='w').pack(fill='x')
        ancho = self.s(470)
        self.l_estado = tk.Label(marco, text='Preparando…', font=self.f_estado, fg=c['texto'], bg=c['fondo'],
                                 anchor='w', justify='left', wraplength=ancho)
        self.l_estado.pack(fill='x', pady=(self.s(22), 0))
        self.l_detalle = tk.Label(marco, text='', font=self.f_pie, fg=c['texto2'], bg=c['fondo'], anchor='w',
                                  justify='left', wraplength=ancho)
        self.l_detalle.pack(fill='x', pady=(self.s(3), 0))
        self.barra = BarraTk(marco, c, self.escala, ancho)
        self.barra.pack(fill='x', pady=(self.s(12), 0))
        pie = tk.Frame(marco, bg=c['fondo'])
        pie.pack(fill='x', pady=(self.s(16), 0))
        self.l_detalles = tk.Label(pie, text='Mostrar detalles', font=self.f_pie, fg=c['acento'], bg=c['fondo'],
                                   cursor='hand2')
        self.l_detalles.pack(side='left')
        self.l_detalles.bind('<Button-1>', lambda _e: self._alternar_detalles())
        self.botones = tk.Frame(pie, bg=c['fondo'])
        self.botones.pack(side='right')
        self.texto = tk.Text(marco, height=10, bg=c['codigo'], fg=c['texto2'], font=self.f_mono, relief='flat',
                             highlightthickness=1, highlightbackground=c['borde'], highlightcolor=c['borde'],
                             wrap='word', padx=self.s(8), pady=self.s(6), state='disabled')
        self._detalles_visibles = False
        self._poner_botones([('Cancelar', self._pedir_cierre, False)])

    def _icono_ventana(self):
        try:
            if ES_WINDOWS and (RECURSOS / 'micrograno.ico').is_file():
                self.raiz.iconbitmap(default=str(RECURSOS / 'micrograno.ico'))
            elif (RECURSOS / 'micrograno-128.png').is_file():
                self._icono = self.tk.PhotoImage(file=str(RECURSOS / 'micrograno-128.png'))
                self.raiz.iconphoto(True, self._icono)
        except Exception:
            pass

    def _cargar_imagen(self, lado: int):
        for tam in (64, 128):
            ruta = RECURSOS / f'micrograno-{tam}.png'
            if ruta.is_file() and tam >= lado * 0.8:
                try:
                    imagen = self.tk.PhotoImage(file=str(ruta))
                    factor = max(1, int(tam // max(lado, 1)))
                    return imagen.subsample(factor) if factor > 1 else imagen
                except Exception:
                    return None
        return None

    def _poner_botones(self, definiciones):
        for hijo in self.botones.winfo_children():
            hijo.destroy()
        for texto, accion, primario in definiciones:
            BotonTk(self.botones, texto, accion, primario, self.c, self.f_texto, self.escala).pack(
                side='left', padx=(self.s(8), 0))

    def _alternar_detalles(self):
        self._detalles_visibles = not self._detalles_visibles
        if self._detalles_visibles:
            self.texto.pack(fill='both', expand=True, pady=(self.s(12), 0))
            self.l_detalles.configure(text='Ocultar detalles')
        else:
            self.texto.pack_forget()
            self.l_detalles.configure(text='Mostrar detalles')

    def _escribir(self, linea: str):
        self.texto.configure(state='normal')
        self.texto.insert('end', linea + '\n')
        if int(self.texto.index('end-1c').split('.')[0]) > 600:
            self.texto.delete('1.0', '200.0')
        self.texto.see('end')
        self.texto.configure(state='disabled')

    def _modo_oscuro_titulo(self):
        if not ES_WINDOWS or self.c is not OSCURO:
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.raiz.winfo_id())
            valor = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(valor), ctypes.sizeof(valor))
        except Exception:
            pass

    def _centrar(self):
        self.raiz.update_idletasks()
        w, h = self.raiz.winfo_reqwidth(), self.raiz.winfo_reqheight()
        x = (self.raiz.winfo_screenwidth() - w) // 2
        y = (self.raiz.winfo_screenheight() - h) // 3
        self.raiz.geometry(f'+{max(0, x)}+{max(0, y)}')

    # -- Ciclo de trabajo -------------------------------------------------

    def ejecutar(self) -> int:
        self._centrar()
        self.raiz.deiconify()
        self._modo_oscuro_titulo()
        self.raiz.lift()
        self._iniciar()
        self.raiz.mainloop()
        return self.codigo

    def _iniciar(self, accion_previa: str | None = None):
        self.cancelacion = threading.Event()
        self.trabajando = True
        self._poner_botones([('Cancelar', self._pedir_cierre, False)])
        self.l_estado.configure(fg=self.c['texto'])
        self.barra.establecer(None)

        def trabajo():
            try:
                if accion_previa == 'instalar_python':
                    instalar_python(self, self.cancelacion)
                codigo = preparar(self.op, self, self.cancelacion)
            except Cancelado:
                self.fin_cancelado()
                codigo = 2
            except ErrorArranque as exc:
                self.fin_error(exc)
                codigo = 1
            except Exception as exc:
                self.fin_error(ErrorArranque('Error inesperado del lanzador.', str(exc), None,
                                             traceback.format_exc()))
                codigo = 1
            self.cola.put(('terminado', codigo))

        threading.Thread(target=trabajo, daemon=True).start()

    def _procesar_cola(self):
        try:
            while True:
                evento = self.cola.get_nowait()
                tipo = evento[0]
                if tipo == 'estado':
                    self.l_estado.configure(text=evento[1], fg=self.c['texto'])
                    self.l_detalle.configure(text=evento[2])
                elif tipo == 'progreso':
                    self.barra.establecer(evento[1])
                elif tipo == 'registro':
                    self._escribir(evento[1])
                elif tipo == 'ok':
                    self.barra.establecer(1.0)
                    self.l_estado.configure(text=evento[1], fg=self.c['texto'])
                    self.l_detalle.configure(text='')
                elif tipo == 'cancelado':
                    self.l_estado.configure(text='Preparación cancelada.')
                    self.l_detalle.configure(text='Podrá continuarla la próxima vez que abra MicroGrano Lab.')
                elif tipo == 'error':
                    self._mostrar_error(evento[1])
                elif tipo == 'terminado':
                    self._terminado(evento[1])
                    return
        except queue.Empty:
            pass
        self.raiz.after(40, self._procesar_cola)

    def _terminado(self, codigo: int):
        self.trabajando = False
        self.codigo = codigo
        if codigo == 0 and not (self.op.solo_instalar or self.op.comprobar):
            self.raiz.destroy()
            return
        if codigo == 2:
            self.raiz.destroy()
            return
        if codigo == 0:
            self._poner_botones([('Cerrar', self.raiz.destroy, True)])
        self.raiz.after(40, self._procesar_cola)

    def _mostrar_error(self, error: ErrorArranque):
        self._ultimo_error = error
        self.barra.establecer(0.0)
        self.l_estado.configure(text=error.mensaje, fg=self.c['error'])
        self.l_detalle.configure(text=error.sugerencia)
        if error.detalle:
            self._escribir(error.detalle.strip()[-4000:])
        botones = []
        if self.ruta_registro:
            botones.append(('Ver registro', lambda: abrir_en_sistema(self.ruta_registro), False))
        if error.accion == 'instalar_python':
            if ES_WINDOWS and shutil.which('winget'):
                botones.append(('Instalar Python 3.13', lambda: self._iniciar('instalar_python'), True))
            else:
                botones.append(('Descargar Python', lambda: abrir_en_sistema(URL_PYTHON), True))
        elif error.accion == 'reparar':
            botones.append(('Reparar', self._reparar, False))
            botones.append(('Reintentar', lambda: self._iniciar(), True))
        else:
            botones.append(('Reintentar', lambda: self._iniciar(), True))
        botones.append(('Cerrar', self.raiz.destroy, False))
        self._poner_botones(botones)

    def _reparar(self):
        self.op.reparar = True
        self._iniciar()

    def _pedir_cierre(self):
        if not self.trabajando:
            self.raiz.destroy()
            return
        from tkinter import messagebox
        if messagebox.askyesno('Cancelar la preparación',
                               '¿Desea cancelar? Lo ya descargado se conserva y la preparación continuará '
                               'la próxima vez que abra MicroGrano Lab.', parent=self.raiz):
            self.cancelacion.set()
            if self.proceso is not None and self.proceso.poll() is None:
                try:
                    self.proceso.terminate()
                except OSError:
                    pass
            self.l_estado.configure(text='Cancelando…')


try:
    import tkinter as _tk
except Exception:  # Python sin Tk: se usará la consola.
    _tk = None


class BarraTk(_tk.Canvas if _tk else object):  # type: ignore[misc]
    """Barra de progreso en forma de cápsula, determinada o con animación."""

    def __init__(self, padre, c, escala, ancho):
        self.alto = max(4, int(round(6 * escala)))
        super().__init__(padre, height=self.alto, width=ancho, bg=c['fondo'], highlightthickness=0, bd=0)
        self.c = c
        self.valor = None
        self.fase = 0.0
        self._animando = False
        self.bind('<Configure>', lambda _e: self._dibujar())

    def establecer(self, valor):
        self.valor = valor
        if valor is None:
            if not self._animando:
                self._animando = True
                self._animar()
        else:
            self._animando = False
            self._dibujar()

    def _animar(self):
        if not self._animando:
            return
        self.fase = (self.fase + 0.011) % 1.0
        self._dibujar()
        self.after(16, self._animar)

    def _capsula(self, x0, x1, color):
        h = self.alto
        if x1 - x0 < h:
            x1 = x0 + h
        self.create_line(x0 + h / 2, h / 2, x1 - h / 2, h / 2, width=h, capstyle='round', fill=color)

    def _dibujar(self):
        self.delete('all')
        w = max(self.winfo_width(), 10)
        self._capsula(0, w, self.c['pista'])
        if self.valor is None:
            segmento = w * 0.3
            x = (w + segmento) * self.fase - segmento
            x0, x1 = max(0.0, x), min(float(w), x + segmento)
            if x1 - x0 > self.alto:
                self._capsula(x0, x1, self.c['acento'])
        elif self.valor > 0:
            self._capsula(0, w * min(1.0, float(self.valor)), self.c['acento'])


class BotonTk(_tk.Canvas if _tk else object):  # type: ignore[misc]
    """Botón redondeado al estilo de macOS dibujado en un lienzo de Tk."""

    def __init__(self, padre, texto, accion, primario, c, fuente, escala):
        from tkinter import font as tkfont
        medida = tkfont.Font(font=fuente).measure(texto)
        self.ancho = medida + int(30 * escala)
        self.alto = int(30 * escala)
        super().__init__(padre, width=self.ancho, height=self.alto, bg=c['fondo'], highlightthickness=0, bd=0,
                         cursor='hand2')
        self.texto, self.accion, self.primario, self.c, self.fuente, self.escala = texto, accion, primario, c, fuente, escala
        self._dibujar(False)
        self.bind('<Enter>', lambda _e: self._dibujar(True))
        self.bind('<Leave>', lambda _e: self._dibujar(False))
        self.bind('<ButtonRelease-1>', self._pulsado)

    def _dibujar(self, encima: bool):
        self.delete('all')
        c = self.c
        if self.primario:
            relleno = c['acento_hover'] if encima else c['acento']
            borde, color = relleno, '#FFFFFF'
        else:
            relleno = c['boton_hover'] if encima else c['boton']
            borde, color = c['borde'], c['texto']
        r = int(7 * self.escala)
        w, h = self.ancho - 1, self.alto - 1
        puntos = [1 + r, 1, w - r, 1, w, 1, w, 1 + r, w, h - r, w, h, w - r, h, 1 + r, h, 1, h, 1, h - r, 1, 1 + r, 1, 1]
        self.create_polygon(puntos, smooth=True, splinesteps=16, fill=relleno, outline=borde)
        self.create_text(self.ancho / 2, self.alto / 2, text=self.texto, fill=color, font=self.fuente)

    def _pulsado(self, evento):
        if 0 <= evento.x <= self.ancho and 0 <= evento.y <= self.alto:
            self.accion()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def analizar_argumentos(argv=None) -> Opciones:
    p = argparse.ArgumentParser(prog='arranque', description='Prepara el entorno de Python y abre MicroGrano Lab.')
    p.add_argument('--consola', action='store_true', help='mostrar el progreso en la consola, sin ventana')
    p.add_argument('--solo-instalar', action='store_true', help='preparar el entorno sin abrir la interfaz')
    p.add_argument('--comprobar', action='store_true', help='informar del estado sin instalar ni abrir nada')
    p.add_argument('--reparar', action='store_true', help='recrear el entorno de Python desde cero')
    p.add_argument('archivos', nargs='*', help='imágenes o sesiones que se abrirán en la interfaz')
    a = p.parse_args(argv)
    return Opciones(a.consola, a.solo_instalar, a.comprobar, a.reparar, a.archivos)


def reabrir_en_consola(argv) -> int:
    """Sin consola ni Tk (pythonw sin Tk): se reabre el lanzador en una consola nueva."""
    python = Path(sys.executable).with_name('python.exe')
    if ES_WINDOWS and python.is_file():
        subprocess.Popen([str(python), str(Path(__file__).resolve()), '--consola'] + list(argv or sys.argv[1:]),
                         creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0x10))
        return 0
    return 1


def main(argv=None) -> int:
    op = analizar_argumentos(argv)
    if not op.consola and _tk is not None:
        try:
            ventana = VentanaProgreso(op)
        except Exception:
            ventana = None
        if ventana is not None:
            return ventana.ejecutar()
    if sys.stdout is None:
        return reabrir_en_consola(argv)
    codigo = ejecutar_en_consola(op)
    if codigo == 1 and sys.stdin is not None and sys.stdin.isatty() and os.environ.get('MICROGRANO_SIN_PAUSA') != '1':
        try:
            input('\nPulse Intro para cerrar…')
        except (EOFError, KeyboardInterrupt):
            pass
    return codigo


if __name__ == '__main__':
    sys.exit(main())
