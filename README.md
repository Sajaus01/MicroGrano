# MicroGrano 1.0.0

MicroGrano es la biblioteca de Python desarrollada por Andrés Felipe Saavedra Sajaus específicamente para este libro, en relación con su proyecto de maestría en Instrumentación Física de la Universidad Tecnológica de Pereira. Reúne 39 operaciones de imagen, calibración, preparación, máscaras, segmentación, medición y estadística. MicroGrano Lab es su interfaz de escritorio en PySide6 y utiliza las mismas funciones de la biblioteca.

Repositorio de publicación: [Sajaus01/MicroGrano](https://github.com/Sajaus01/MicroGrano). La versión del código y del paquete es 1.0.0. El historial documenta revisiones de desarrollo dentro de esa versión.

El código se hace visible con **todos los derechos reservados**. Su publicación no concede una licencia de reutilización; consulte [LICENSE.txt](LICENSE.txt) y [AVISO_DISTRIBUCION.md](AVISO_DISTRIBUCION.md). Las dependencias conservan sus propias licencias.

## Biblioteca, interfaz y código

La biblioteca puede importarse desde un programa de Python. El asistente de MicroGrano Lab conduce una imagen por diez pasos: Imagen original → Escala → Escala de grises → Región de interés → Preparar la ROI → Crear la máscara → Revisar la máscara → Identificar objetos → Medir objetos → Exportar resultados.

La interfaz ejecuta una selección de funciones mediante controles guiados. Permite revisar resultados, comparar máscaras con la ROI, consultar medidas, conservar versiones y guardar o reabrir sesiones. **Qué hace y cómo se usa** muestra explicaciones, ejemplos y la implementación de las 39 funciones en modo de solo lectura. No es un editor ni un ejecutor de código Python libre. Para modificar ejemplos, combinar operaciones o ejecutar el experimento completo se usan programas externos con la biblioteca instalada. La guía de los controles está en [docs/guia_interfaz.md](docs/guia_interfaz.md).

## Requisitos

Esta distribución requiere Python 3.13 de 64 bits, con las versiones de dependencias fijadas en `constraints.txt`. La revisión del asistente se comprobó en Windows con Python 3.13.3 y PySide6 6.10.2. No se presenta esa comprobación como una prueba de macOS o Linux.

`pyproject.toml` declara las dependencias y `constraints.txt` fija sus versiones. Se necesita conexión al índice de paquetes para la primera instalación. La aplicación procesa las imágenes localmente. El repositorio no contiene un entorno virtual ni las dependencias de terceros.

## Instalación en Windows

Descargue el repositorio como ZIP y extraiga todo su contenido, o utilice una copia obtenida con Git. Abra una terminal en la carpeta que contiene `pyproject.toml` y ejecute:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[gui]"
.\.venv\Scripts\python.exe -m micrograno_lab
```

No es necesario activar el entorno: los comandos invocan su intérprete. El primer comando utiliza el lanzador `py` de Python para seleccionar la versión 3.13. También puede abrir `MicroGrano Lab.exe` o `iniciar_windows.bat`; ambos preparan el entorno y después abren la aplicación. El archivo `.exe` es un lanzador, no una aplicación autónoma con Python incluido. Si no encuentra Python 3.13 de 64 bits, el lanzador de Windows ofrece instalarlo mediante `winget`. Los detalles están en [lanzador/README.md](lanzador/README.md).

## Instalación manual en macOS o Linux

Desde la carpeta que contiene `pyproject.toml`:

```bash
python3.13 -m venv .venv
./.venv/bin/python -m pip install -c constraints.txt -e ".[gui]"
./.venv/bin/python -m micrograno_lab
```

Se incluyen `iniciar_mac.command` e `iniciar_linux.sh` como alternativas de arranque. Su inclusión no acredita una prueba de la interfaz en esas plataformas.

Para instalar solo la biblioteca, sustituya `".[gui]"` por `.` en el comando de instalación. Para añadir las herramientas de pruebas use `".[gui,dev]"`. El extra `dev` no es necesario para analizar imágenes.

## Primer uso y ejemplos

En la bienvenida, **Probar con una imagen de ejemplo** carga datos sintéticos. **Usar escala del ejemplo** aplica una convención artificial de 0,5 µm/px. Para una imagen propia, calibre sobre una longitud documentada antes de recortar la barra. Confirme que la ROI excluye rótulos y anotaciones. La aplicación también permite continuar sin escala; en ese caso no genera medidas físicas.

La preparación conserva inicialmente la ROI y ofrece una mediana de radio 1 px. La máscara utiliza Otsu con elección de regiones claras u oscuras. La limpieza y la separación por watershed son opciones revisables. Las regiones segmentadas no se identifican automáticamente como granos, fases o materiales.

Los archivos de `ejemplos/` muestran llamadas desde Python. La siguiente demostración recorre el catálogo con datos sintéticos, en ramas de prueba distintas; no es una receta que deba aplicarse completa a una micrografía:

```powershell
.\.venv\Scripts\python.exe -m micrograno demo --salida prueba_micrograno
.\.venv\Scripts\python.exe -m micrograno reproducir prueba_micrograno/sesion.json
```

La carpeta de salida debe ser nueva. Para ejecutar las pruebas, instale el extra `dev` y utilice el intérprete del entorno:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

En macOS o Linux, el intérprete equivalente es `./.venv/bin/python`.

## Contenido y resultados

`src/micrograno/` contiene la biblioteca y `src/micrograno_lab/` la interfaz. `docs/` reúne la API, la guía y los contratos; `ejemplos/` contiene programas; `tests/` contiene pruebas; `datos/sinteticos/` conserva las entradas artificiales; `lanzador/` contiene el preparador del entorno y las fuentes del lanzador. `.github/workflows/` contiene la configuración de pruebas automatizadas. Su presencia no acredita una ejecución satisfactoria: los resultados de cada ejecución deben consultarse en GitHub Actions.

Una sesión guarda los datos exactos, los parámetros, la calibración, la ROI, las relaciones entre resultados y el recorrido activo. La exportación produce NPY, TIFF compatibles, vistas PNG, tablas CSV e índices de procedencia. La reproducción recalcula y compara datos; no constituye validación metalográfica.

Las micrografías del estudio son propias del autor, según su confirmación. Se conservan en el paquete separado del experimento reproducible; este repositorio incluye datos sintéticos y no añade metadatos instrumentales que no estén documentados. Tampoco contiene documentos privados, registros voluminosos ni entornos de trabajo.

Los identificadores numéricos de capítulos que aparecen en ayudas o ejemplos conservan la correspondencia histórica del catálogo. Para localizar una operación use su nombre y `docs/api.md`; esos números no sustituyen el índice de la edición del libro.

## Errores y propuestas

Para comunicar errores o proponer mejoras, utilice las [incidencias del repositorio](https://github.com/Sajaus01/MicroGrano/issues) y siga [CONTRIBUTING.md](CONTRIBUTING.md). Incluya un ejemplo mínimo con datos sintéticos y omita imágenes privadas, credenciales y datos personales. Las propuestas y contribuciones no cambian el régimen de derechos reservados. Para problemas de seguridad, consulte [SECURITY.md](SECURITY.md).

Los ajustes documentales para esta publicación se describen en [REGISTRO_EDICION.txt](REGISTRO_EDICION.txt).
