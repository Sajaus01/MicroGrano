# Correspondencia entre biblioteca, interfaz y libro

La tabla identifica las 39 operaciones de MicroGrano 1.0.0. La columna numérica conserva la referencia histórica del catálogo; no representa necesariamente la numeración de esta edición del libro. Los nombres de las funciones permiten localizarlas en `docs/api.md` y en el código fuente.

El asistente actual utiliza una selección del catálogo para conducir una imagen por diez pasos. La consulta permite leer explicaciones, ejemplos e implementaciones de todas las funciones, sin ejecutarlas ni modificar el recorrido. Las operaciones restantes se utilizan desde Python.

| Función | Grupo y título del catálogo | Referencia histórica del catálogo | Prueba |
|---|---|---|---|
| `explorar_imagen` | Imagen y calibración / Inspeccionar imagen | 2.1 | `test_catalogo.py` |
| `convertir_grises` | Imagen y calibración / Convertir a escala de grises | 2.5 | `test_catalogo.py` |
| `separar_canales` | Imagen y calibración / Comparar canales RGB | 2.5 | `test_catalogo.py` |
| `extraer_roi` | Imagen y calibración / Seleccionar región de interés | 2.2 | `test_catalogo.py` |
| `reducir_y_ampliar` | Imagen y calibración / Demostrar cambio de muestreo | 2.3 | `test_catalogo.py` |
| `cuantizar` | Imagen y calibración / Reducir niveles de intensidad | 2.4 | `test_catalogo.py` |
| `histograma_percentiles` | Imagen y calibración / Histograma y percentiles | 2.6 | `test_catalogo.py` |
| `perfil_intensidad` | Imagen y calibración / Perfil de intensidad | 3.3–3.5; apoyo | `test_catalogo.py` |
| `calibrar_escala` | Imagen y calibración / Calibrar escala espacial | 2.7 | `test_catalogo.py` |
| `convertir_medidas` | Imagen y calibración / Convertir longitud y área | 2.7 | `test_catalogo.py` |
| `reescalar_percentiles` | Preprocesamiento / Estirar por percentiles | 3.2 | `test_catalogo.py` |
| `variantes_contraste` | Preprocesamiento / Comparar contraste | 3.2 | `test_catalogo.py` |
| `variantes_ruido` | Preprocesamiento / Comparar filtros de ruido | 3.3 | `test_catalogo.py` |
| `agregar_ruido` | Preprocesamiento / Añadir ruido sintético | 3.3; apoyo | `test_catalogo.py` |
| `evaluar_referencia` | Preprocesamiento / PSNR y SSIM con referencia | 3.3 | `test_catalogo.py` |
| `corregir_iluminacion` | Preprocesamiento / Corregir iluminación | 3.4 | `test_catalogo.py` |
| `top_hat` | Preprocesamiento / Residuos morfológicos claro y oscuro | 3.4 | `test_catalogo.py` |
| `realzar_sobel` | Preprocesamiento / Componentes y magnitud de Sobel | 3.5 | `test_catalogo.py` |
| `variantes_morfologicas` | Máscaras y morfología / Comparar morfología | 3.6 | `test_catalogo.py` |
| `limpiar_mascara` | Máscaras y morfología / Filtrar por área y rellenar huecos | 4.4 y 5.5 | `test_catalogo.py` |
| `invertir_mascara` | Máscaras y morfología / Invertir primer plano | 4.1; apoyo | `test_catalogo.py` |
| `esqueletizar` | Máscaras y morfología / Adelgazar red de límites | 5.3; apoyo | `test_catalogo.py` |
| `umbralizar` | Segmentación / Comparar umbrales | 4.2 | `test_catalogo.py` |
| `detectar_canny` | Segmentación / Detectar límites candidatos con Canny | 4.3 | `test_catalogo.py` |
| `etiquetar_componentes` | Segmentación / Etiquetar componentes conexas | 5.2 | `test_catalogo.py` |
| `limites_a_regiones` | Segmentación / Obtener regiones de una red | 4.3–4.4; apoyo | `test_catalogo.py` |
| `separar_watershed` | Segmentación / Separar por watershed | 4.4 | `test_catalogo.py` |
| `segmentar_clases` | Segmentación / Clases de intensidad por multi-Otsu | 4.5 | `test_catalogo.py` |
| `extraer_clase` | Segmentación / Extraer una clase como máscara | 4.5; apoyo | `test_catalogo.py` |
| `obtener_limites` | Segmentación / Contornos de objetos etiquetados | 4.4 y 5.3 | `test_catalogo.py` |
| `evaluar_mascara` | Segmentación / Dice e IoU con referencia | 4.7; apoyo | `test_catalogo.py` |
| `propiedades_basicas` | Conteo y características / Medir propiedades básicas | 5.2 | `test_catalogo.py` |
| `descriptores_forma` | Conteo y características / Medir tamaño y forma | 5.6 | `test_catalogo.py` |
| `medir_objetos` | Conteo y características / Filtrar, contar y medir objetos | 5.5 | `test_catalogo.py` |
| `densidad_jeffries` | Conteo y características / Ponderación planimétrica ilustrativa | 5.3.2 | `test_catalogo.py` |
| `fracciones_area` | Conteo y características / Fracción de área por clase | 5.4 | `test_catalogo.py` |
| `intercepto_medio` | Conteo y características / Intercepción lineal | 5.3.1 | `test_catalogo.py` |
| `intervalo_bootstrap_media` | Estadística / Intervalo bootstrap de la media | 5.7 | `test_catalogo.py` |
| `reporte_fraccion_area` | Estadística / Resumen de fracciones por campo | 5.7 | `test_catalogo.py` |


## Uso en el libro

Los listados pueden importar la API mediante `from micrograno import nucleo as mg` o sus módulos temáticos. La separación por watershed recibe una máscara explícita y la medición recibe un mapa de etiquetas. La función disponible en la biblioteca no acredita, por sí misma, que haya sido utilizada en un resultado del estudio; ese uso corresponde a los parámetros y programas del experimento reproducible.

MicroGrano no incorpora un modelo de aprendizaje automático entrenado para esta investigación ni convierte sus resultados en número ASTM G. Los contratos específicos se documentan en `limites_y_contratos.md`.
