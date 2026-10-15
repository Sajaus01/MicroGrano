# Ejemplos ejecutables sin interfaz

Instale primero la biblioteca. Ejecute los comandos desde la raíz del repositorio utilizando el intérprete de su entorno virtual. Las carpetas de salida deben ser nuevas.

```bash
python ejemplos/01_flujo_sintetico.py --salida salidas_flujo
python ejemplos/02_sesion_reproducible.py --salida salidas_sesion
python ejemplos/04_resumen_campos.py --csv datos/sinteticos/campos_sinteticos.csv --unidad campo --salida salidas_campos
```

El primer ejemplo muestra llamadas directas de máscara a características. El segundo ejecuta las 39 operaciones en ramas apropiadas, guarda la sesión y comprueba su reproducción. El cuarto utiliza valores artificiales del CSV; no representan campos de una probeta.

`03_analizar_imagen.py` requiere un archivo propio, coordenadas de ROI, polaridad y nota de revisión. Consulte sus argumentos con:

```bash
python ejemplos/03_analizar_imagen.py --help
```

La escala física es opcional y exige una referencia documentada. Sin escala se guardan segmentaciones e histogramas, pero no medidas físicas. Los parámetros iniciales de este ejemplo solo permiten ejecutar la comparación; no declaran que el resultado sea un conteo correcto de granos. Antes de adoptar parámetros para la investigación, deben revisarse sobre sus datos y su mensurando.

Los 39 ejemplos breves de `docs/api.md` son ejecutables independientemente con el conjunto sintético y también forman parte de las pruebas automatizadas.
