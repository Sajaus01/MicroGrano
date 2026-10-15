# Uso de MicroGrano Lab

MicroGrano Lab guía el análisis de una imagen mediante diez pasos. Cada paso recibe automáticamente la salida del anterior. El original, los recortes, las máscaras y los demás resultados se conservan; consultar una versión no cambia los datos que procesa el asistente.

## Abrir y avanzar

Abra `MicroGrano Lab.exe` en Windows, `iniciar_mac.command` en macOS o `iniciar_linux.sh` en Linux. El lanzador prepara el entorno cuando hace falta; los detalles están en [la documentación del lanzador](../lanzador/README.md). Con el entorno instalado también puede ejecutar `python -m micrograno_lab`, seguido opcionalmente de una imagen o un archivo `sesion.json`.

Pulse **Abrir imagen** o **Probar con una imagen de ejemplo**. La barra izquierda indica el paso actual y los pasos completados. Use el botón principal para calcular, confirmar o continuar, según lo que indique. **Anterior** permite revisar un paso ya realizado. La aplicación impide avanzar mientras falte un resultado o la confirmación de la ROI.

Al entrar por primera vez en Grises, Preparar, Crear la máscara, Revisar la máscara e Identificar objetos, el asistente calcula la opción inicial. Las medidas también se calculan al entrar si hay escala. La aplicación muestra el resultado antes de continuar. Si cambia una opción, pulse **Actualizar resultado** para aplicarla.

La indicación sobre el visor identifica la entrada del paso. No hay un selector de imagen de trabajo: la cadena de datos la establece el recorrido. La rueda amplía o reduce la vista y el doble clic ajusta la imagen al espacio disponible.

## Los diez pasos

| Paso | Acción y resultado que continúa |
|---|---|
| 1. Imagen original | Importe una micrografía. Sus píxeles quedan conservados como fuente del análisis. |
| 2. Escala | Dibuje una referencia de longitud conocida e indique su valor en µm, o continúe sin escala. La imagen conserva sus dimensiones. |
| 3. Escala de grises | `convertir_grises` genera las intensidades normalizadas que recibe el recorte. |
| 4. Región de interés | `extraer_roi` recorta los grises. Revise y confirme esta ROI antes de avanzar. |
| 5. Preparar la ROI | Se conserva la ROI. Si activa **Reducir ruido con mediana**, continúa la salida de mediana con radio de 1 px. |
| 6. Crear la máscara | `umbralizar` calcula Otsu. Elija si el primer plano corresponde a regiones claras u oscuras. Continúa la máscara Otsu. |
| 7. Revisar la máscara | `limpiar_mascara` conserva inicialmente todos los componentes y los huecos. Los ajustes opcionales permiten retirar componentes pequeños o rellenar huecos cerrados. Continúa la máscara limpia. |
| 8. Identificar objetos | `etiquetar_componentes` asigna identificadores con conectividad de ocho vecinos. **Separar objetos que se tocan** permite emplear watershed. Continúan las etiquetas. |
| 9. Medir objetos | Con escala, `medir_objetos` produce la tabla y conserva todos los objetos de al menos un píxel, incluidos los del marco. Sin escala, puede continuar sin medidas físicas. |
| 10. Exportar resultados | **Exportar análisis completo** guarda todas las versiones, las tablas y la sesión necesaria para reabrir el recorrido. |

La preparación y la medición sin escala tienen decisiones explícitas para continuar. No necesita seleccionar una salida de cada función. Las salidas auxiliares, como las máscaras de píxeles agregados o eliminados, también se guardan, pero no sustituyen la salida que alimenta al paso siguiente.

## Calibración y ROI

Calibre antes de recortar la barra de escala. Dibuje una línea sobre una distancia conocida del original, introduzca la longitud física documentada en micrómetros y pulse **Calibrar y continuar**. El factor es la longitud física dividida por la distancia en píxeles. Debe corresponder a esa imagen y configuración de adquisición; una indicación como «200X» no permite obtener µm/px. Los extremos de la línea y ambas longitudes se guardan; al reabrir, la referencia vuelve a mostrarse sobre el original.

**Continuar sin escala** permite procesar y exportar la imagen, las máscaras y las etiquetas. En ese caso, el paso de medición no genera longitudes, áreas ni densidades físicas. Puede volver a Escala y calibrar; los pasos posteriores deberán recorrerse de nuevo para que hereden el factor correcto.

La conversión a grises normaliza los enteros por el rango de almacenamiento de su tipo y convierte RGB a una intensidad ponderada. No estira cada imagen según su mínimo y máximo. Las imágenes flotantes deben estar en [0, 1] y contener valores finitos. RGBA con transparencia exige componer previamente un fondo explícito.

En Región de interés, dibuje un rectángulo y pulse **Crear y revisar ROI**. También puede elegir **Usar toda la imagen**. En ambos casos se crea una versión de ROI para revisar. Marque **Confirmo la región de análisis** cuando haya comprobado que no contiene barra de escala, texto ni anotaciones y pulse **Confirmar ROI y continuar**. La aplicación no detecta esas anotaciones automáticamente.

El recorte conserva el tamaño de píxel y registra su posición respecto del original. Las coordenadas finales de fila y columna quedan excluidas, como en `imagen[r0:r1, c0:c1]`. Si la región no es adecuada, use **Volver a dibujar el recorte** antes de continuar.

## Revisar máscaras, objetos y medidas

Por defecto no se aplica filtrado. La mediana opcional puede reducir ruido y también eliminar detalles metalográficos pequeños. Revise su efecto sobre la ROI antes de aceptarla.

En la máscara, blanco indica primer plano y negro indica fondo. La elección **Las regiones claras / Las regiones oscuras** decide qué intensidades quedan en blanco. Compruebe que corresponden al objeto de interés. Un umbral de intensidad no identifica por sí solo un grano, una fase o un material.

La limpieza empieza con área mínima de 1 px² y relleno de huecos desactivado. **Ajustar limpieza de la máscara** muestra dos valores: el área mínima inclusiva de los componentes conservados y el área máxima inclusiva de los huecos cerrados que se rellenan. Los cambios quedan registrados junto con las máscaras de píxeles retirados y agregados.

Cada identificador positivo de la etapa siguiente representa una región conectada; cero es fondo. Watershed utiliza una separación mínima entre picos de 12 px y conserva componentes desde 1 px². Puede dividir regiones que se tocan, pero también separar en exceso un mismo objeto. Sus semillas y separaciones deben corresponder a la microestructura antes de interpretar el conteo como número de granos.

**Comparar el resultado con la ROI** muestra el resultado a la izquierda y el recorte de referencia a la derecha en las etapas de máscara, limpieza, objetos y medición. Esta comparación solo cambia la vista.

**Mostrar tabla de medidas** permite consultar áreas, perímetros, centroides y descriptores de forma. La tabla indica qué objetos tocan el marco; esos perfiles pueden estar truncados. Las medidas son bidimensionales, dependen de la segmentación y no constituyen por sí mismas un procedimiento ASTM completo ni una estimación del número G.

## Consultar la biblioteca y conservar versiones

**Qué hace y cómo se usa** abre la documentación de la función del paso. El diálogo permite consultar las 39 funciones de la biblioteca, sus entradas, parámetros, ejemplos sintéticos y código fuente mediante **Ver implementación**. Es una consulta: elegir una función allí no la ejecuta ni altera el recorrido. El asistente utiliza una selección de funciones para construir este análisis; no aplica todo el catálogo a una imagen.

**Versiones** abre una galería de solo lectura con originales, grises, recortes, máscaras, etiquetas y salidas auxiliares. Muestra sus dimensiones, tipo y procedencia. Seleccionar una versión cambia únicamente la vista de la galería. Al cerrarla, el asistente conserva su paso y sus entradas.

Volver con **Anterior** tampoco modifica resultados. Si recalcula un paso con otra opción o cambia el recorte, el asistente deja pendientes los pasos que dependían de ese resultado. Al continuar, los calcula sobre la nueva cadena. Las versiones anteriores permanecen en la sesión y en la exportación; el índice del recorrido identifica cuáles forman parte del análisis vigente.

El ejemplo disponible en la bienvenida es sintético. **Usar escala del ejemplo**, en Escala, aplica la convención de 100 px = 50 µm. No es una calibración instrumental ni una prueba de validez para una micrografía real.

## Guardar, reabrir y exportar

**Guardar** permite conservar el avance en una carpeta nueva. La sesión contiene `sesion.json`, los arreglos exactos en `datos/`, `reproducir.py` y `recorrido.json`, que registra el paso actual y las salidas utilizadas. **Abrir sesión** lee `sesion.json`, verifica los datos y restablece el recorrido guardado.

Las sesiones anteriores que carecen de `recorrido.json` se abren en la galería para consulta. La aplicación no infiere una imagen de trabajo a partir de sus ramas. Para analizarlas con el asistente, inicie un análisis desde la imagen original.

**Exportar análisis completo**, en el último paso, crea una carpeta nueva con:

- `datos/`: NPY exactos de todas las versiones y TIFF cuando las dimensiones y el tipo numérico son compatibles.
- `vistas/`: PNG de 8 bits para consulta. Las etiquetas se colorean y algunos mapas se reescalan; la transformación queda documentada. No sustituyen los datos para medir.
- `tablas/`: CSV de los pasos que producen tablas.
- `versiones.json`: inventario con hashes, procedencia, parámetros, metadatos, resúmenes y advertencias de todas las versiones.
- `recorrido_activo.json`: etapas y salidas que forman la cadena vigente, diferenciadas de los cálculos anteriores.
- `sesion_reabrible/`: sesión completa con `sesion.json`, `recorrido.json`, datos exactos y `reproducir.py`. Abra su `sesion.json` para retomar el trabajo.

La exportación incluye las salidas auxiliares y los resultados de recalculaciones anteriores. Una tabla de medidas físicas solo está presente si se realizó la medición con escala. Los vectores y ciertos tipos numéricos no generan una vista PNG o TIFF; el índice registra esas omisiones y NPY conserva el dato exacto.

La exportación se realiza en segundo plano y se informa cuando termina. Durante el cálculo y la exportación se bloquean los controles que modificarían la sesión. Los archivos se escriben en una carpeta temporal y la entrega se publica al completar la escritura.

Para recalcular una sesión desde sus fuentes, use el intérprete del entorno instalado:

```bash
python -m micrograno reproducir carpeta/sesion.json
```

La reproducción compara arreglos, tablas y resúmenes. La coincidencia computacional verifica la repetición del cálculo, no la validez metalográfica de la segmentación.
