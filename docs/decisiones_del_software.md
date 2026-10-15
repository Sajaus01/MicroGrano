# Decisiones del software y su publicación

MicroGrano 1.0.0 reúne la biblioteca científica de 39 operaciones desarrollada para este libro y MicroGrano Lab, su interfaz de escritorio. La aplicación utiliza las funciones de la biblioteca a través de un catálogo compartido; no mantiene una implementación científica independiente. El autor es Andrés Felipe Saavedra Sajaus, en relación con su proyecto de maestría en Instrumentación Física de la Universidad Tecnológica de Pereira.

El inicio actual abre `VentanaAsistente`, definida en `src/micrograno_lab/asistente.py`. Sus diez pasos tienen entradas establecidas por el recorrido. La galería de versiones y la consulta de las funciones no ejecutan código libre ni cambian la entrada del análisis. El código mostrado por la ayuda es de solo lectura. La API completa permanece disponible desde Python.

| Afirmación | Archivo de referencia |
|---|---|
| El catálogo cubre la API científica | `src/micrograno/nucleo.py`, `src/micrograno/catalogo.py`, `tests/test_catalogo.py` |
| Cada operación tiene ayuda y ejemplo | `docs/api.md`, `tests/test_cli_documentacion.py` |
| La interfaz utiliza la biblioteca | `src/micrograno_lab/asistente.py`, `src/micrograno_lab/recorrido.py` |
| La consulta de código es de solo lectura | `src/micrograno_lab/consulta.py` |
| Las sesiones conservan datos y parámetros | `src/micrograno/sesion.py`, `tests/test_sesion_archivos.py` |
| La exportación conserva el recorrido activo | `src/micrograno_lab/exportacion.py`, `tests/test_exportacion_versiones.py` |

La distribución publicada admite Python 3.13 de 64 bits. Este alcance se ajusta a las versiones fijadas de las dependencias y evita presentar otros intérpretes como entornos equivalentes sin una instalación compatible de ese conjunto.

La revisión documentada del asistente aprobó 333 pruebas en Windows con Python 3.13.3 y PySide6 6.10.2. Ese resultado corresponde a una comprobación local de software, principalmente con datos sintéticos; no acredita identificación de granos ni validación metalográfica. Los registros y capturas voluminosos de desarrollo no forman parte del repositorio. Las pruebas se incluyen para poder volver a ejecutarlas. La configuración de GitHub Actions no convierte ese resultado histórico en una ejecución remota: cada ejecución conserva su propio registro.

Las micrografías del estudio son propias del autor. Este repositorio distribuye las entradas sintéticas de demostración; las micrografías se conservan en el paquete independiente del experimento. No se incorporan metadatos instrumentales ausentes.

El destino de publicación es [Sajaus01/MicroGrano](https://github.com/Sajaus01/MicroGrano). El código se publica con todos los derechos reservados, sin licencia de reutilización; las condiciones se recogen en [LICENSE.txt](../LICENSE.txt). La visibilidad del código permite examinar la implementación, pero no acredita su validez para una muestra ni constituye una licencia abierta. Las contribuciones no modifican este régimen por sí mismas.

Los identificadores numéricos de capítulos en el catálogo son referencias históricas; se conserva el nombre de cada función como identificador estable. El archivo bibliográfico incluido pertenece al inventario del software y no sustituye la bibliografía revisada de la edición del libro.
