# Historial de desarrollo de MicroGrano 1.0.0

La versión declarada del paquete es 1.0.0. Este historial conserva revisiones de desarrollo; las descripciones de interfaces anteriores no son instrucciones del asistente actual de diez pasos.

La biblioteca científica (`src/micrograno`) y sus resultados no cambian. Los cambios afectan a la interfaz, al modo de abrirla y a la documentación.

## Publicación en GitHub — 15 de octubre de 2026

- Repositorio de distribución: https://github.com/Sajaus01/MicroGrano.
- Derechos reservados según la decisión del autor; aviso incluido en `LICENSE.txt`, sin licencia de reutilización concedida.
- Instalación reproducible limitada a Python 3.13 de 64 bits con GIL, conforme a las versiones fijadas. El lanzador y sus mensajes utilizan el mismo requisito.
- Metadatos de paquete y citación, instrucciones de instalación, incidencias y seguridad revisados para la distribución pública.
- Distribución de fuentes con documentación, restricciones de dependencias, ejemplos, pruebas y fuentes del lanzador. Se excluyen entornos, cachés, resultados locales y documentos del manuscrito.
- El núcleo científico mantiene sus archivos originales. Se retira un marcador editorial pendiente de la información de la ventana histórica, sin cambiar cálculos.

## Asistente guiado de diez pasos

- El inicio habitual abre un asistente con una cadena fija: original, escala, grises, ROI, preparación, máscara Otsu, limpieza, etiquetas, medición y exportación. Cada etapa recibe exclusivamente la salida de la anterior.
- Se eliminan del recorrido los selectores de imagen de trabajo, entradas y salidas. La barra izquierda muestra el progreso; los controles principales permiten continuar o revisar el paso anterior.
- La ROI se crea y se presenta para confirmación antes de cualquier procesamiento posterior. La aplicación conserva su escala, dimensiones y posición respecto del original.
- Preparación sin filtro y limpieza sin eliminación ni relleno como opciones iniciales. Mediana, polaridad, ajustes de limpieza y separación watershed se presentan en sus etapas correspondientes. Las medidas conservan los objetos del marco y requieren escala; continuar sin ella no genera unidades físicas ficticias.
- La galería **Versiones** es de solo lectura. Consultar un resultado o una función no cambia la entrada del análisis. **Qué hace y cómo se usa** mantiene accesibles la documentación, los ejemplos Python y las implementaciones de las 39 funciones.
- Recalcular una etapa deja pendientes sus dependientes y conserva los resultados históricos. `recorrido.json` guarda el paso actual y las salidas que forman la cadena para reabrirla sin deducir una imagen activa.
- **Exportar análisis completo** reúne todas las versiones, máscaras, tablas, procedencia y `recorrido_activo.json`, además de una sesión completa en `sesion_reabrible/`. Las sesiones antiguas sin información de recorrido se consultan sin modificar sus datos.
- Guía de interfaz y README actualizados. Los registros de verificación anteriores se identifican como evidencia de las interfaces previas; no se presentan como validación del nuevo asistente.

## Revisión anterior de aprendizaje: ocho etapas

- Recorrido en ocho etapas según las dependencias del análisis: Imagen, Escala, Grises y ROI, Preparar (opcional), Segmentar, Refinar y separar, Medir y Exportar. La calibración precede al recorte y la creación de máscaras precede a su limpieza.
- **Aprender con un ejemplo** inicia el recorrido con una sola imagen RGB sintética, escala convencional de 0.5 µm/px y ROI pendiente. El conjunto completo de ocho datos sigue disponible en **Archivo › Conjunto completo para explorar el catálogo**.
- Barra lateral con **Pasos**, **Versiones** y **Catálogo**. Pulsar una etapa abre una función adecuada al contexto; **Exportar** oculta el inspector y muestra las acciones de entrega. El catálogo conserva acceso a las 39 funciones.
- Inspector con **Aplicar**, **Aprender** y **Python**: entradas y parámetros, explicación de las salidas, ejemplo sintético ejecutable e implementación de la biblioteca. Los requisitos pendientes se explican antes de ejecutar.
- Versiones numeradas con procedencia y entradas de origen. **Continuar con esta versión** activa la salida elegida y abre una función siguiente compatible; se conservan el original y las otras ramas.
- Cambiar la versión de trabajo actualiza la entrada principal. Las propuestas automáticas se limitan a versiones de la misma imagen fuente, región y dimensiones; las referencias requieren selección expresa. El botón **Resultados** del lienzo muestra u oculta las tablas y demás resultados.
- **Exportar todas las versiones** genera NPY exactos, TIFF compatibles, vistas PNG, tablas CSV y `versiones.json` con parámetros y contexto. Se ejecuta en un hilo separado, con los controles de modificación bloqueados durante la escritura. **Guardar sesión** sigue siendo una acción separada y conserva `sesion.json` y `reproducir.py`.
- Guía de interfaz y secciones de uso del README actualizadas para este recorrido. Esta revisión local no introduce un número de versión publicado.

## Interfaz MicroGrano Lab rediseñada

- **Aspecto.** Estética de macOS con modo claro u oscuro (sigue al sistema o se elige en **Ver › Apariencia**), iconos vectoriales propios y tipografía del sistema.
- **Bienvenida y guía.** Pantalla de bienvenida con el flujo de trabajo en siete pasos y una «Guía» que indica qué falta para el dato activo.
- **Organización de la ventana.**
  - Barra lateral con herramientas agrupadas y buscables, y una lista de datos con miniaturas.
  - Inspector con descripciones claras, parámetros con nombre, unidad, intervalo, deslizador y ayuda, y entradas compatibles preseleccionadas.
  - Panel de resultados con resumen, tabla ordenable y filtrable, gráfica, historial y script.
- **Visor.** Zoom con la rueda, cuadrícula de píxeles al acercar, ROI con atenuación exterior, regla con longitud en px y µm, perfil, comparación lado a lado con zoom sincronizado y cortina de comparación.
- **Herramientas nuevas.**
  - Tira de salidas con miniaturas.
  - Sugerencias del siguiente paso.
  - Vista previa en vivo, que no se registra en la sesión.
  - Reutilizar los parámetros de un paso.
  - Errores con acciones de solución, como «Confirmar ROI…» o «Calibrar escala…».
  - Búsqueda global (Ctrl+K), arrastrar y soltar, y sesiones recientes.

## Lanzador

- `MicroGrano Lab.exe` (Windows), `iniciar_windows.bat`, `iniciar_mac.command` e `iniciar_linux.sh`.
- `lanzador/arranque.py` busca un Python compatible, crea `.venv`, instala solo las librerías que faltan según `constraints.txt` y abre la interfaz con una ventana de progreso. En Windows ofrece instalar Python 3.13 con winget si no hay ninguno compatible.
- Pruebas nuevas en `tests/test_lanzador.py`. En Windows 11 con Python 3.13.3 se aprobaron 224 pruebas.

# MicroGrano 1.0.0

Entrega unificada del software del libro. Contiene una biblioteca independiente, un catálogo de 39 operaciones y la interfaz MicroGrano Lab en PySide6. Los ejemplos, la documentación y las pruebas usan esa misma implementación.

La API científica tiene una entrada estable en `micrograno.nucleo`. La sesión conserva entradas, salidas, región, calibración, anotaciones y parámetros. Se incluyen datos sintéticos y programas de reproducción.

Las decisiones técnicas y los límites actuales se describen en [docs/decisiones_del_software.md](docs/decisiones_del_software.md). Los registros voluminosos de desarrollo se conservan fuera del repositorio público.
