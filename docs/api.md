# API científica de MicroGrano 1.0.0

Importación estable: `from micrograno import nucleo as mg`. Las 39 funciones que siguen constituyen la API científica; no hay una implementación paralela dentro de la interfaz. Los métodos de entrada/salida y `Sesion` son servicios de soporte y están descritos al final de este documento.

Salvo `calibrar_escala`, que devuelve `EscalaEspacial`, las funciones devuelven `Resultado`: `datos` contiene arreglos inmutables, `tipos` declara su significado computacional, `tabla` contiene un `DataFrame`, `resumen` registra decisiones y magnitudes, y `advertencias` conserva límites de interpretación. Los nombres de salida que se indican abajo forman parte del contrato. Una tabla puede estar vacía sin representar un fallo, por ejemplo cuando no hay objetos.

Las entradas de intensidad son imágenes bidimensionales normalizadas en [0,1], salvo las operaciones iniciales que aceptan imágenes sin convertir. Las máscaras deben ser booleanas. Los objetos deben tener identificadores enteros no negativos, con cero como fondo. Las clases de intensidad también son enteras, pero la clase cero participa en las fracciones. Los parámetros por defecto son valores de inicio del software, no valores validados para el material del libro.

Los números de sección conservan la correspondencia histórica del catálogo y pueden diferir del índice de esta edición del libro. El nombre de la función es su identificador estable. Las claves bibliográficas pertenecen al inventario del software; la bibliografía del libro se presenta por separado.


## `explorar_imagen`

Inspeccionar imagen. Grupo: Imagen y calibración. Correspondencia: 2.1.

```python
explorar_imagen(imagen: 'np.ndarray') -> 'Resultado'
```

Inspecciona la representación original sin normalizar ni modificar píxeles.

### Entradas

- `imagen`: imagen, gris. Entrada imagen: imagen, gris

### Parámetros


### Salidas

Arreglos: `original` (imagen).

Columnas: ninguna.

Claves del resumen: `forma`, `tipo_dato`, `minimo`, `maximo`, `pixeles`, `bytes_por_elemento`, `convencion`.

Referencias del proyecto: `HarrisEtAl2020` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.explorar_imagen(
    imagen=datos['rgb']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `convertir_grises`

Convertir a escala de grises. Grupo: Imagen y calibración. Correspondencia: 2.5.

```python
convertir_grises(imagen: 'np.ndarray') -> 'Resultado'
```

Normaliza enteros por su tipo y convierte RGB a gris. RGBA exige alfa opaco.

### Entradas

- `imagen`: imagen, gris. Entrada imagen: imagen, gris

### Parámetros


### Salidas

Arreglos: `gris` (gris).

Columnas: ninguna.

Claves del resumen: `intervalo`, `normalizacion`.

Referencias del proyecto: `VanDerWaltEtAl2014` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.convertir_grises(
    imagen=datos['rgb']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `separar_canales`

Comparar canales RGB. Grupo: Imagen y calibración. Correspondencia: 2.5.

```python
separar_canales(imagen: 'np.ndarray') -> 'Resultado'
```

Devuelve R, G, B y la conversión ponderada a gris con el mismo rango [0,1].

### Entradas

- `imagen`: imagen, gris. Entrada imagen: imagen, gris

### Parámetros


### Salidas

Arreglos: `rojo` (gris), `verde` (gris), `azul` (gris), `gris` (gris).

Columnas: ninguna.

Claves del resumen: ninguna.

Referencias del proyecto: `GonzalezWoods2018` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.separar_canales(
    imagen=datos['rgb']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `extraer_roi`

Seleccionar región de interés. Grupo: Imagen y calibración. Correspondencia: 2.2.

```python
extraer_roi(imagen: 'np.ndarray', r0: 'int', r1: 'int', c0: 'int', c1: 'int') -> 'Resultado'
```

Recorta [r0:r1, c0:c1], límites finales excluidos; no redimensiona.

### Entradas

- `imagen`: imagen, gris. Entrada imagen: imagen, gris

### Parámetros

- `r0` (obligatorio): Fila inicial; incluida en la ROI.
- `r1` (obligatorio): Fila final; excluida de la ROI (en perfiles es un centro de píxel).
- `c0` (obligatorio): Columna inicial; incluida en la ROI.
- `c1` (obligatorio): Columna final; excluida de la ROI (en perfiles es un centro de píxel).

### Salidas

Arreglos: `roi` (imagen).

Columnas: ninguna.

Claves del resumen: `roi_rc`, `origen_local_en_imagen`, `conserva_escala`.

Referencias del proyecto: `AaronChew2021` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.extraer_roi(
    imagen=datos['gris'],
    r0=8,
    r1=120,
    c0=8,
    c1=152
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `reducir_y_ampliar`

Demostrar cambio de muestreo. Grupo: Imagen y calibración. Correspondencia: 2.3.

```python
reducir_y_ampliar(imagen: 'np.ndarray', factor: 'int' = 4) -> 'Resultado'
```

Demostración de pérdida de muestreo, no una mejora de resolución óptica.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `factor` (4): Factor entero de reducción, al menos 2; demostración, no mejora óptica.

### Salidas

Arreglos: `reducida` (gris), `ampliada` (gris).

Columnas: ninguna.

Claves del resumen: `factor_solicitado`, `forma_original`, `razon_filas`, `razon_columnas`.

Referencias del proyecto: `Shannon1949` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.reducir_y_ampliar(
    imagen=datos['gris'],
    factor=4
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `cuantizar`

Reducir niveles de intensidad. Grupo: Imagen y calibración. Correspondencia: 2.4.

```python
cuantizar(imagen: 'np.ndarray', bits_salida: 'int' = 4) -> 'Resultado'
```

Cuantiza a 2**bits_salida niveles normalizados; conserva el tamaño espacial.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `bits_salida` (4): Número de bits simulados, entre 1 y 16.

### Salidas

Arreglos: `cuantizada` (gris).

Columnas: ninguna.

Claves del resumen: `bits_salida`, `niveles_posibles`.

Referencias del proyecto: `GonzalezWoods2018` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.cuantizar(
    imagen=datos['gris'],
    bits_salida=4
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `histograma_percentiles`

Histograma y percentiles. Grupo: Imagen y calibración. Correspondencia: 2.6.

```python
histograma_percentiles(imagen: 'np.ndarray', bins: 'int' = 256) -> 'Resultado'
```

Histograma en [0,1] y percentiles de la imagen de intensidades normalizada.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `bins` (256): Número de intervalos del histograma en [0,1].

### Salidas

Arreglos: ninguno.

Columnas: `intensidad`, `conteo`, `fraccion`.

Claves del resumen: `p1`, `p99`, `minimo`, `maximo`, `numero_pixeles`, `bins`.

Referencias del proyecto: `GonzalezWoods2018` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.histograma_percentiles(
    imagen=datos['gris'],
    bins=256
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `perfil_intensidad`

Perfil de intensidad. Grupo: Imagen y calibración. Correspondencia: 3.3–3.5; apoyo.

```python
perfil_intensidad(imagen: 'np.ndarray', r0: 'float', c0: 'float', r1: 'float', c1: 'float') -> 'Resultado'
```

Muestrea un segmento entre centros de píxel con interpolación bilineal.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `r0` (obligatorio): Fila inicial; incluida en la ROI.
- `c0` (obligatorio): Columna inicial; incluida en la ROI.
- `r1` (obligatorio): Fila final; excluida de la ROI (en perfiles es un centro de píxel).
- `c1` (obligatorio): Columna final; excluida de la ROI (en perfiles es un centro de píxel).

### Salidas

Arreglos: ninguno.

Columnas: `distancia_px`, `fila_px`, `columna_px`, `intensidad`.

Claves del resumen: `longitud_px`, `extremos_rc`.

Referencias del proyecto: `AaronChew2021` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.perfil_intensidad(
    imagen=datos['gris'],
    r0=25.0,
    c0=4.0,
    r1=88.0,
    c1=140.0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `calibrar_escala`

Calibrar escala espacial. Grupo: Imagen y calibración. Correspondencia: 2.7.

```python
calibrar_escala(referencia_um: 'float', referencia_px: 'float', incertidumbre_um: 'float | None' = None, incertidumbre_px: 'float | None' = None, referencia: 'str' = '') -> 'EscalaEspacial'
```

Calcula µm/px; propagación de primer orden con entradas independientes.

Las dos incertidumbres estándar se proporcionan juntas o ambas se omiten.
Omitir no equivale a incertidumbre cero. Se supone escala isotrópica.

### Entradas

No necesita un arreglo de entrada; los datos se introducen como parámetros.

### Parámetros

- `referencia_um` (obligatorio): Longitud física documentada de la referencia en µm.
- `referencia_px` (obligatorio): Distancia en píxeles entre los extremos medidos.
- `incertidumbre_um` (None): Incertidumbre estándar de la referencia física, no expandida; opcional.
- `incertidumbre_px` (None): Incertidumbre estándar de la distancia en píxeles; opcional.
- `referencia` (''): Identificador del patrón, configuración o procedencia de la escala.

### Salidas

Objeto `EscalaEspacial`: `um_por_px`, `incertidumbre_um_por_px` y `referencia`. Métodos `longitud_um`, `area_um2` y `como_dict`. El catálogo adapta esta salida para su presentación, sin recalcular la calibración.

Referencias del proyecto: `ASTM_E1951_2019`, `JCGM1002008` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.calibrar_escala(
    referencia_um=50.0,
    referencia_px=100.0,
    referencia='Referencia sintética',
    incertidumbre_um=None,
    incertidumbre_px=None
)
print(resultado.como_dict())
```


## `convertir_medidas`

Convertir longitud y área. Grupo: Imagen y calibración. Correspondencia: 2.7.

```python
convertir_medidas(s_um_px: 'float', longitud_px: 'float' = 1.0, area_px2: 'float' = 1.0, incertidumbre_s: 'float | None' = None) -> 'Resultado'
```

Convierte longitud y área; la incertidumbre mostrada es solo la de escala.

### Entradas

No necesita un arreglo de entrada; los datos se introducen como parámetros.

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.
- `longitud_px` (1.0): Longitud en píxeles a convertir.
- `area_px2` (1.0): Área en píxeles cuadrados a convertir.
- `incertidumbre_s` (None): Incertidumbre estándar de la escala en µm/px; opcional.

### Salidas

Arreglos: ninguno.

Columnas: ninguna.

Claves del resumen: `longitud_um`, `area_um2`.

Referencias del proyecto: `JCGM1002008` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.convertir_medidas(
    s_um_px=0.5,
    longitud_px=25.0,
    area_px2=100.0,
    incertidumbre_s=None
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `reescalar_percentiles`

Estirar por percentiles. Grupo: Preprocesamiento. Correspondencia: 3.2.

```python
reescalar_percentiles(imagen: 'np.ndarray', p_bajo: 'float' = 2.0, p_alto: 'float' = 98.0) -> 'Resultado'
```

Estira el contraste; si los percentiles coinciden, conserva la entrada.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `p_bajo` (2.0): Percentil inferior, entre 0 y 100.
- `p_alto` (98.0): Percentil superior, mayor que el inferior.

### Salidas

Arreglos: `estirada` (gris).

Columnas: ninguna.

Claves del resumen: `intensidad_inferior`, `intensidad_superior`, `p_bajo`, `p_alto`.

Referencias del proyecto: `GonzalezWoods2018` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.reescalar_percentiles(
    imagen=datos['gris'],
    p_bajo=2.0,
    p_alto=98.0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `variantes_contraste`

Comparar contraste. Grupo: Preprocesamiento. Correspondencia: 3.2.

```python
variantes_contraste(imagen: 'np.ndarray', p_bajo: 'float' = 2.0, p_alto: 'float' = 98.0, tile: 'int' = 64, clip_limit: 'float' = 0.02) -> 'Resultado'
```

Compara percentiles, ecualización global y CLAHE sobre la misma entrada.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `p_bajo` (2.0): Percentil inferior, entre 0 y 100.
- `p_alto` (98.0): Percentil superior, mayor que el inferior.
- `tile` (64): Lado de la región local de CLAHE, en píxeles.
- `clip_limit` (0.02): Límite normalizado del histograma en CLAHE.

### Salidas

Arreglos: `estirada` (gris), `ecualizacion_global` (gris), `clahe` (gris).

Columnas: ninguna.

Claves del resumen: `intensidad_inferior`, `intensidad_superior`, `p_bajo`, `p_alto`.

Referencias del proyecto: `PizerEtAl1987`, `Zuiderveld1994` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.variantes_contraste(
    imagen=datos['gris'],
    p_bajo=2.0,
    p_alto=98.0,
    tile=64,
    clip_limit=0.02
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `variantes_ruido`

Comparar filtros de ruido. Grupo: Preprocesamiento. Correspondencia: 3.3.

```python
variantes_ruido(imagen: 'np.ndarray', radio_px: 'int' = 1, sigma: 'float' = 1.0, sigma_color: 'float' = 0.08, sigma_spatial: 'float' = 3.0) -> 'Resultado'
```

Media en disco, gaussiano, mediana y bilateral sin cuantización a 8 bits.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `radio_px` (1): Radio del disco en píxeles. El diámetro es 2*radio+1.
- `sigma` (1.0): Desviación estándar del suavizado en px; en ruido sintético, unidades de intensidad.
- `sigma_color` (0.08): Tolerancia de intensidad del bilateral para entradas [0,1].
- `sigma_spatial` (3.0): Escala espacial del bilateral en píxeles.

### Salidas

Arreglos: `media` (gris), `gaussiano` (gris), `mediana` (gris), `bilateral` (gris).

Columnas: ninguna.

Claves del resumen: `radio_media_mediana_px`.

Referencias del proyecto: `TomasiManduchi1998` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.variantes_ruido(
    imagen=datos['gris'],
    radio_px=1,
    sigma=1.0,
    sigma_color=0.08,
    sigma_spatial=3.0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `agregar_ruido`

Añadir ruido sintético. Grupo: Preprocesamiento. Correspondencia: 3.3; apoyo.

```python
agregar_ruido(imagen: 'np.ndarray', sigma: 'float' = 0.03, semilla: 'int' = 2026) -> 'Resultado'
```

Añade ruido gaussiano sintético con semilla y recorta a [0,1].

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `sigma` (0.03): Desviación estándar del suavizado en px; en ruido sintético, unidades de intensidad.
- `semilla` (2026): Semilla entera para repetir exactamente el muestreo.

### Salidas

Arreglos: `con_ruido` (gris).

Columnas: ninguna.

Claves del resumen: `sigma`, `semilla`, `pixeles_recortados`.

Referencias del proyecto: `WangEtAl2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.agregar_ruido(
    imagen=datos['gris'],
    sigma=0.03,
    semilla=2026
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `evaluar_referencia`

PSNR y SSIM con referencia. Grupo: Preprocesamiento. Correspondencia: 3.3.

```python
evaluar_referencia(referencia: 'np.ndarray', candidata: 'np.ndarray') -> 'Resultado'
```

PSNR y SSIM sobre imágenes alineadas con referencia conocida en [0,1].

### Entradas

- `referencia`: gris. Entrada referencia: gris
- `candidata`: gris. Entrada candidata: gris

### Parámetros


### Salidas

Arreglos: `ssim_local` (mapa).

Columnas: ninguna.

Claves del resumen: `psnr_db`, `ssim`, `error_cuadratico_medio`, `ventana_ssim`, `data_range`.

Referencias del proyecto: `WangEtAl2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.evaluar_referencia(
    referencia=datos['gris'],
    candidata=datos['gris']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `corregir_iluminacion`

Corregir iluminación. Grupo: Preprocesamiento. Correspondencia: 3.4.

```python
corregir_iluminacion(imagen: 'np.ndarray', radio: 'float' = 15.0) -> 'Resultado'
```

Bola rodante: fondo inferior y correcciones aditiva/divisiva normalizadas.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `radio` (15.0): Radio de la bola rodante en píxeles. El coste aumenta con radio e imagen.

### Salidas

Arreglos: `fondo` (gris), `aditiva` (gris), `divisiva` (gris).

Columnas: ninguna.

Claves del resumen: `radio_px`, `percentiles_salida`, `limites_aditiva`, `limites_divisiva`, `pixeles_denominador_protegido`.

Referencias del proyecto: `Sternberg1983` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.corregir_iluminacion(
    imagen=datos['gris'],
    radio=6.0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `top_hat`

Residuos morfológicos claro y oscuro. Grupo: Preprocesamiento. Correspondencia: 3.4.

```python
top_hat(imagen: 'np.ndarray', radio_px: 'int' = 10) -> 'Resultado'
```

Residuos morfológicos claro (blanco) y oscuro (negro), sin asignarles fase.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `radio_px` (10): Radio del disco en píxeles. El diámetro es 2*radio+1.

### Salidas

Arreglos: `claro` (gris), `oscuro` (gris).

Columnas: ninguna.

Claves del resumen: ninguna.

Referencias del proyecto: `Soille2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.top_hat(
    imagen=datos['gris'],
    radio_px=4
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `realzar_sobel`

Componentes y magnitud de Sobel. Grupo: Preprocesamiento. Correspondencia: 3.5.

```python
realzar_sobel(imagen: 'np.ndarray', sigma: 'float' = 1.0) -> 'Resultado'
```

Derivadas en fila y columna y magnitud; respuestas firmadas no son intensidades.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `sigma` (1.0): Desviación estándar del suavizado en px; en ruido sintético, unidades de intensidad.

### Salidas

Arreglos: `suavizada` (gris), `derivada_fila` (mapa), `derivada_columna` (mapa), `magnitud` (mapa).

Columnas: ninguna.

Claves del resumen: ninguna.

Referencias del proyecto: `GonzalezWoods2018` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.realzar_sobel(
    imagen=datos['gris'],
    sigma=1.0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `variantes_morfologicas`

Comparar morfología. Grupo: Máscaras y morfología. Correspondencia: 3.6.

```python
variantes_morfologicas(mascara: 'np.ndarray', radio_px: 'int' = 1) -> 'Resultado'
```

Compara cuatro operaciones sobre una máscara booleana con el mismo disco.

### Entradas

- `mascara`: mascara, limites. Entrada mascara: mascara, limites

### Parámetros

- `radio_px` (1): Radio del disco en píxeles. El diámetro es 2*radio+1.

### Salidas

Arreglos: `erosion` (mascara), `dilatacion` (mascara), `apertura` (mascara), `cierre` (mascara).

Columnas: ninguna.

Claves del resumen: `radio_px`.

Referencias del proyecto: `Serra1982`, `Soille2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.variantes_morfologicas(
    mascara=datos['mascara'],
    radio_px=1
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `limpiar_mascara`

Filtrar por área y rellenar huecos. Grupo: Máscaras y morfología. Correspondencia: 4.4 y 5.5.

```python
limpiar_mascara(mascara: 'np.ndarray', area_minima: 'int' = 20, hueco_maximo: 'int' = 0, conectividad: 'int' = 2) -> 'Resultado'
```

Conserva componentes con área >= area_minima y rellena huecos <= hueco_maximo.

### Entradas

- `mascara`: mascara, limites. Entrada mascara: mascara, limites

### Parámetros

- `area_minima` (20): Se conservan áreas de este número de píxeles o mayores.
- `hueco_maximo` (0): Se rellenan huecos cerrados de este tamaño o menores; 0 desactiva.
- `conectividad` (2): 1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.

### Salidas

Arreglos: `limpia` (mascara), `eliminados` (mascara), `agregados` (mascara).

Columnas: ninguna.

Claves del resumen: `area_minima_inclusiva_px`, `hueco_maximo_inclusivo_px`, `conectividad`, `pixeles_eliminados`, `pixeles_agregados`.

Referencias del proyecto: `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.limpiar_mascara(
    mascara=datos['mascara'],
    area_minima=20,
    hueco_maximo=0,
    conectividad=2
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `invertir_mascara`

Invertir primer plano. Grupo: Máscaras y morfología. Correspondencia: 4.1; apoyo.

```python
invertir_mascara(mascara: 'np.ndarray') -> 'Resultado'
```

Intercambia verdadero y falso; la elección de primer plano es explícita.

### Entradas

- `mascara`: mascara, limites. Entrada mascara: mascara, limites

### Parámetros


### Salidas

Arreglos: `invertida` (mascara).

Columnas: ninguna.

Claves del resumen: ninguna.

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.invertir_mascara(
    mascara=datos['mascara']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `esqueletizar`

Adelgazar red de límites. Grupo: Máscaras y morfología. Correspondencia: 5.3; apoyo.

```python
esqueletizar(limites: 'np.ndarray') -> 'Resultado'
```

Adelgaza una red binaria; no cierra discontinuidades ni valida su identidad.

### Entradas

- `limites`: mascara, limites. Entrada limites: mascara, limites

### Parámetros


### Salidas

Arreglos: `esqueleto` (limites).

Columnas: ninguna.

Claves del resumen: ninguna.

Referencias del proyecto: `Soille2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.esqueletizar(
    limites=datos['limites']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `umbralizar`

Comparar umbrales. Grupo: Segmentación. Correspondencia: 4.2.

```python
umbralizar(imagen: 'np.ndarray', manual: 'float' = 0.5, bloque: 'int' = 51, desplazamiento: 'float' = 0.02, polaridad: 'str' = 'clara') -> 'Resultado'
```

Compara umbral manual, Otsu y media local. Clara: I>T; oscura: I<=T.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `manual` (0.5): Umbral global de intensidad normalizada.
- `bloque` (51): Lado impar de la ventana de media local, en píxeles.
- `desplazamiento` (0.02): Se resta de la media local: T = media - desplazamiento.
- `polaridad` ('clara'): Clara: I>T; oscura: I<=T. Compruebe qué representa el primer plano.

### Salidas

Arreglos: `manual` (mascara), `otsu` (mascara), `adaptativa` (mascara), `umbral_local` (mapa).

Columnas: ninguna.

Claves del resumen: `umbral_otsu`, `umbral_manual`, `polaridad`, `regla_igualdad`.

Referencias del proyecto: `Otsu1979` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.umbralizar(
    imagen=datos['gris'],
    manual=0.5,
    bloque=51,
    desplazamiento=0.02,
    polaridad='clara'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `detectar_canny`

Detectar límites candidatos con Canny. Grupo: Segmentación. Correspondencia: 4.3.

```python
detectar_canny(imagen: 'np.ndarray', sigma: 'float' = 1.0, bajo: 'float' = 0.08, alto: 'float' = 0.18) -> 'Resultado'
```

Detecta transiciones; devuelve límites candidatos, no objetos etiquetados.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `sigma` (1.0): Desviación estándar del suavizado en px; en ruido sintético, unidades de intensidad.
- `bajo` (0.08): Umbral inferior de Canny en la representación normalizada.
- `alto` (0.18): Umbral superior de Canny, mayor que el inferior.

### Salidas

Arreglos: `canny` (limites).

Columnas: ninguna.

Claves del resumen: ninguna.

Referencias del proyecto: `Canny1986` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.detectar_canny(
    imagen=datos['gris'],
    sigma=1.0,
    bajo=0.08,
    alto=0.18
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `etiquetar_componentes`

Etiquetar componentes conexas. Grupo: Segmentación. Correspondencia: 5.2.

```python
etiquetar_componentes(mascara: 'np.ndarray', conectividad: 'int' = 2) -> 'Resultado'
```

Etiqueta componentes conexas: 1 indica cuatro vecinos; 2, ocho vecinos.

### Entradas

- `mascara`: mascara, limites. Entrada mascara: mascara, limites

### Parámetros

- `conectividad` (2): 1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.

### Salidas

Arreglos: `etiquetas` (etiquetas).

Columnas: ninguna.

Claves del resumen: `numero_objetos`, `conectividad`.

Referencias del proyecto: `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.etiquetar_componentes(
    mascara=datos['mascara'],
    conectividad=2
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `limites_a_regiones`

Obtener regiones de una red. Grupo: Segmentación. Correspondencia: 4.3–4.4; apoyo.

```python
limites_a_regiones(limites: 'np.ndarray', area_minima: 'int' = 20, excluir_abiertas: 'bool' = True, conectividad: 'int' = 1) -> 'Resultado'
```

Etiqueta el complemento de una red; puede excluir regiones que llegan al marco.

No rellena huecos de la red ni inventa uniones. Una abertura real puede comunicar
varios interiores y producir una sola región; se muestra para revisión.

### Entradas

- `limites`: mascara, limites. Entrada limites: mascara, limites

### Parámetros

- `area_minima` (20): Se conservan áreas de este número de píxeles o mayores.
- `excluir_abiertas` (True): Descarta regiones conectadas al marco; puede excluir perfiles truncados válidos.
- `conectividad` (1): 1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.

### Salidas

Arreglos: `etiquetas` (etiquetas), `regiones_en_marco` (mascara).

Columnas: ninguna.

Claves del resumen: `numero_objetos`, `excluir_abiertas`, `conectividad`.

Referencias del proyecto: `Soille2004` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.limites_a_regiones(
    limites=datos['limites'],
    area_minima=20,
    excluir_abiertas=True,
    conectividad=1
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `separar_watershed`

Separar por watershed. Grupo: Segmentación. Correspondencia: 4.4.

```python
separar_watershed(mascara: 'np.ndarray', min_distance: 'int' = 12, area_minima: 'int' = 20, conectividad: 'int' = 2, marcadores: 'np.ndarray | None' = None) -> 'Resultado'
```

Separa una máscara explícita por distancia y marcadores; no umbraliza a escondidas.

Marcadores opcionales: enteros no negativos, cero sin semilla. Cada componente
debe contener una semilla. Sin marcadores se generan picos y se añade un máximo
a cualquier componente sin pico, incluidos los que tocan el marco.

### Entradas

- `mascara`: mascara, limites. Entrada mascara: mascara, limites
- `marcadores`: marcadores, etiquetas. Opcional. Entrada marcadores: marcadores, etiquetas

### Parámetros

- `min_distance` (12): Separación mínima entre picos candidatos en píxeles; no es diámetro de grano.
- `area_minima` (20): Se conservan áreas de este número de píxeles o mayores.
- `conectividad` (2): 1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.

### Salidas

Arreglos: `mascara` (mascara), `distancia` (mapa), `marcadores` (marcadores), `etiquetas` (etiquetas), `limites` (limites).

Columnas: ninguna.

Claves del resumen: `numero_objetos`, `numero_marcadores`, `marcadores_automaticos_rescate`, `min_distance_px`, `conectividad`, `marcadores_proporcionados`.

Referencias del proyecto: `Meyer1994`, `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.separar_watershed(
    mascara=datos['mascara'],
    min_distance=10,
    area_minima=20,
    conectividad=2
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `segmentar_clases`

Clases de intensidad por multi-Otsu. Grupo: Segmentación. Correspondencia: 4.5.

```python
segmentar_clases(imagen: 'np.ndarray', clases: 'int' = 3) -> 'Resultado'
```

Multi-Otsu: clases de intensidad 0..K-1, sin identidad metalúrgica asignada.

### Entradas

- `imagen`: gris. Entrada imagen: gris

### Parámetros

- `clases` (3): Número de clases de intensidad, 2 a 4; ninguna se identifica automáticamente.

### Salidas

Arreglos: `clases` (clases).

Columnas: ninguna.

Claves del resumen: `umbrales`, `numero_clases`.

Referencias del proyecto: `LiaoChenChung2001` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.segmentar_clases(
    imagen=datos['gris'],
    clases=3
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `extraer_clase`

Extraer una clase como máscara. Grupo: Segmentación. Correspondencia: 4.5; apoyo.

```python
extraer_clase(clases: 'np.ndarray', clase: 'int' = 0) -> 'Resultado'
```

Extrae una clase como máscara sin unirla semánticamente a las otras clases.

### Entradas

- `clases`: clases. Entrada clases: clases

### Parámetros

- `clase` (0): Identificador de la clase que se convertirá en máscara; cero puede ser válido.

### Salidas

Arreglos: `mascara` (mascara).

Columnas: ninguna.

Claves del resumen: `clase`.

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.extraer_clase(
    clases=datos['clases'],
    clase=0
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `obtener_limites`

Contornos de objetos etiquetados. Grupo: Segmentación. Correspondencia: 4.4 y 5.3.

```python
obtener_limites(etiquetas: 'np.ndarray', conectividad: 'int' = 2, modo: 'str' = 'thick') -> 'Resultado'
```

Obtiene la representación de contornos de instancias ya etiquetadas.

### Entradas

- `etiquetas`: etiquetas. Entrada etiquetas: etiquetas

### Parámetros

- `conectividad` (2): 1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.
- `modo` ('thick'): Grosor/localización del contorno: thick, inner u outer.

### Salidas

Arreglos: `limites` (limites).

Columnas: ninguna.

Claves del resumen: `modo`.

Referencias del proyecto: `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.obtener_limites(
    etiquetas=datos['etiquetas'],
    conectividad=2,
    modo='thick'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `evaluar_mascara`

Dice e IoU con referencia. Grupo: Segmentación. Correspondencia: 4.7; apoyo.

```python
evaluar_mascara(referencia: 'np.ndarray', candidata: 'np.ndarray') -> 'Resultado'
```

Compara máscaras binarias alineadas mediante conteos, Dice e IoU.

### Entradas

- `referencia`: mascara, limites. Entrada referencia: mascara, limites
- `candidata`: mascara, limites. Entrada candidata: mascara, limites

### Parámetros


### Salidas

Arreglos: `falsos_positivos` (mascara), `falsos_negativos` (mascara).

Columnas: ninguna.

Claves del resumen: `verdaderos_positivos`, `falsos_positivos`, `falsos_negativos`, `verdaderos_negativos`, `iou`, `dice`, `convencion_vacias`.

Referencias del proyecto: `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.evaluar_mascara(
    referencia=datos['mascara'],
    candidata=datos['mascara']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `propiedades_basicas`

Medir propiedades básicas. Grupo: Conteo y características. Correspondencia: 5.2.

```python
propiedades_basicas(etiquetas: 'np.ndarray', s_um_px: 'float') -> 'Resultado'
```

Medidas por instancia conservando identificadores; cero representa fondo.

### Entradas

- `etiquetas`: etiquetas. Entrada etiquetas: etiquetas

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.

### Salidas

Arreglos: `etiquetas` (etiquetas).

Columnas: `etiqueta`, `area_px2`, `area_um2`, `perimetro_um`, `centroide_fila_px`, `centroide_columna_px`, `toca_marco`.

Claves del resumen: `numero_objetos`, `s_um_px`, `area_roi_um2`.

Referencias del proyecto: `ScikitImageDocs2026` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.propiedades_basicas(
    etiquetas=datos['etiquetas'],
    s_um_px=0.5
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `descriptores_forma`

Medir tamaño y forma. Grupo: Conteo y características. Correspondencia: 5.6.

```python
descriptores_forma(etiquetas: 'np.ndarray', s_um_px: 'float') -> 'Resultado'
```

Área, perímetros, diámetro equivalente, ejes, orientación y Feret máximo.

Circularidad usa el perímetro de contorno de regionprops, no Crofton.
No se recorta a [0,1]: la discretización puede producir valores superiores a 1.
Orientación: convención de regionprops, desde el eje de filas, en radianes.

### Entradas

- `etiquetas`: etiquetas. Entrada etiquetas: etiquetas

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.

### Salidas

Arreglos: `etiquetas` (etiquetas).

Columnas: `etiqueta`, `area_px2`, `area_um2`, `perimetro_um`, `perimetro_crofton_um`, `centroide_fila_px`, `centroide_columna_px`, `diametro_equivalente_um`, `eje_mayor_um`, `eje_menor_um`, `orientacion_rad`, `circularidad`, `relacion_aspecto`, `feret_max_um`, `solidez`, `toca_marco`.

Claves del resumen: `s_um_px`, `numero_objetos`, `perimetro_circularidad`, `orientacion`.

Referencias del proyecto: `RussNeal2016` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.descriptores_forma(
    etiquetas=datos['etiquetas'],
    s_um_px=0.5
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `medir_objetos`

Filtrar, contar y medir objetos. Grupo: Conteo y características. Correspondencia: 5.5.

```python
medir_objetos(etiquetas: 'np.ndarray', s_um_px: 'float', area_minima: 'int' = 20, regla_marco: 'str' = 'excluir') -> 'Resultado'
```

Filtra instancias ya separadas sin fusionarlas. Registra objetos descartados.

### Entradas

- `etiquetas`: etiquetas. Entrada etiquetas: etiquetas

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.
- `area_minima` (20): Se conservan áreas de este número de píxeles o mayores.
- `regla_marco` ('excluir'): Conservar o excluir instancias que tocan el marco de la ROI.

### Salidas

Arreglos: `aceptadas` (etiquetas), `descartadas` (etiquetas).

Columnas: `etiqueta`, `area_px2`, `area_um2`, `perimetro_um`, `perimetro_crofton_um`, `centroide_fila_px`, `centroide_columna_px`, `diametro_equivalente_um`, `eje_mayor_um`, `eje_menor_um`, `orientacion_rad`, `circularidad`, `relacion_aspecto`, `feret_max_um`, `solidez`, `toca_marco`, `aceptado`, `motivo`.

Claves del resumen: `numero_objetos_entrada`, `numero_objetos_aceptados`, `numero_objetos_descartados`, `area_roi_mm2`, `densidad_objetos_aceptados_mm2`, `fraccion_area_entrada`, `fraccion_area_aceptada`, `regla_marco`, `area_minima_inclusiva_px`.

Referencias del proyecto: `RussNeal2016` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.medir_objetos(
    etiquetas=datos['etiquetas'],
    s_um_px=0.5,
    area_minima=20,
    regla_marco='excluir'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `densidad_jeffries`

Ponderación planimétrica ilustrativa. Grupo: Conteo y características. Correspondencia: 5.3.2.

```python
densidad_jeffries(etiquetas: 'np.ndarray', s_um_px: 'float') -> 'Resultado'
```

Ponderación ilustrativa ni + 0.5*nb en una ROI rectangular; no número ASTM.

### Entradas

- `etiquetas`: etiquetas. Entrada etiquetas: etiquetas

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.

### Salidas

Arreglos: `etiquetas` (etiquetas).

Columnas: `etiqueta`, `toca_marco`, `peso`.

Claves del resumen: `interiores`, `en_marco`, `conteo_ponderado`, `area_roi_mm2`, `densidad_ponderada_mm2`, `geometria`.

Referencias del proyecto: `ASTM_E112_2025`, `ASTM_E1382_2023` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.densidad_jeffries(
    etiquetas=datos['etiquetas'],
    s_um_px=0.5
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `fracciones_area`

Fracción de área por clase. Grupo: Conteo y características. Correspondencia: 5.4.

```python
fracciones_area(clases: 'np.ndarray', roi: 'np.ndarray | None' = None) -> 'Resultado'
```

Proporciones por clase sobre un dominio explícito. Incluye la clase cero.

### Entradas

- `clases`: clases. Entrada clases: clases
- `roi`: mascara. Opcional. Entrada roi: mascara

### Parámetros


### Salidas

Arreglos: `dominio` (mascara).

Columnas: `clase`, `pixeles`, `fraccion_area`, `porcentaje_area`.

Claves del resumen: `pixeles_roi`, `pixeles_excluidos`, `denominador`.

Referencias del proyecto: `Underwood1970` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.fracciones_area(
    clases=datos['clases']
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `intercepto_medio`

Intercepción lineal. Grupo: Conteo y características. Correspondencia: 5.3.1.

```python
intercepto_medio(limites: 'np.ndarray', s_um_px: 'float', numero_lineas: 'int' = 8, orientaciones: 'str' = 'ambas', extremos: 'str' = 'excluir') -> 'Resultado'
```

Longitud de prueba entre centros extremos / corridas de límite por línea.

Se cuentan corridas contiguas, no todos los píxeles del trazo. Horizontales y
verticales se reportan por separado. No corrige tangencias, dobles trazos ni
uniones triples; no calcula número G de ASTM.

### Entradas

- `limites`: mascara, limites. Entrada limites: mascara, limites

### Parámetros

- `s_um_px` (obligatorio): Factor isotrópico verificado en µm/px. No use el aumento nominal.
- `numero_lineas` (8): Número de líneas por orientación, sin duplicados.
- `orientaciones` ('ambas'): Direcciones de prueba; se conservan sus resultados separados.
- `extremos` ('excluir'): Tratamiento de corridas que alcanzan el extremo de una línea.

### Salidas

Arreglos: `lineas_prueba` (limites), `intersecciones` (mascara).

Columnas: `orientacion`, `posicion_px`, `longitud_px`, `longitud_um`, `intersecciones`, `corridas_extremas_excluidas`.

Claves del resumen: `longitud_total_um`, `intersecciones_totales`, `longitud_media_um`, `por_orientacion`, `regla_extremos`, `convencion_longitud`.

Referencias del proyecto: `ASTM_E112_2025`, `ASTM_E1382_2023` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.intercepto_medio(
    limites=datos['limites'],
    s_um_px=0.5,
    numero_lineas=8,
    orientaciones='ambas',
    extremos='excluir'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `intervalo_bootstrap_media`

Intervalo bootstrap de la media. Grupo: Estadística. Correspondencia: 5.7.

```python
intervalo_bootstrap_media(valores: 'np.ndarray', repeticiones: 'int' = 10000, semilla: 'int' = 2026, confianza: 'float' = 0.95, unidad_analisis: 'str' = 'campo') -> 'Resultado'
```

Intervalo percentil de la media; muestreo con reemplazo y memoria acotada.

Se necesitan al menos dos valores finitos. La unidad experimental y la
independencia son decisiones del estudio, no verificaciones del programa.

### Entradas

- `valores`: valores. Entrada valores: valores

### Parámetros

- `repeticiones` (10000): Número de remuestreos; al menos 100.
- `semilla` (2026): Semilla entera para repetir exactamente el muestreo.
- `confianza` (0.95): Cobertura nominal del intervalo, por ejemplo 0.95; no es una garantía de exactitud.
- `unidad_analisis` ('campo'): Unidad que aporta cada valor; su independencia debe venir del diseño del estudio.

### Salidas

Arreglos: `medias_remuestreadas` (distribucion).

Columnas: ninguna.

Claves del resumen: `numero_unidades`, `unidad_analisis`, `media`, `desviacion_estandar_muestral`, `intervalo_percentil`, `confianza`, `repeticiones`, `semilla`.

Referencias del proyecto: `EfronTibshirani1993` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.intervalo_bootstrap_media(
    valores=datos['valores'],
    repeticiones=1000,
    semilla=2026,
    confianza=0.95,
    unidad_analisis='campo'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## `reporte_fraccion_area`

Resumen de fracciones por campo. Grupo: Estadística. Correspondencia: 5.7.

```python
reporte_fraccion_area(valores: 'np.ndarray', repeticiones: 'int' = 10000, semilla: 'int' = 2026, confianza: 'float' = 0.95, unidad_analisis: 'str' = 'campo') -> 'Resultado'
```

Resume fracciones por campo/probeta en [0,1], no porcentajes de 0 a 100.

### Entradas

- `valores`: valores. Entrada valores: valores

### Parámetros

- `repeticiones` (10000): Número de remuestreos; al menos 100.
- `semilla` (2026): Semilla entera para repetir exactamente el muestreo.
- `confianza` (0.95): Cobertura nominal del intervalo, por ejemplo 0.95; no es una garantía de exactitud.
- `unidad_analisis` ('campo'): Unidad que aporta cada valor; su independencia debe venir del diseño del estudio.

### Salidas

Arreglos: `medias_remuestreadas` (distribucion).

Columnas: ninguna.

Claves del resumen: `numero_unidades`, `unidad_analisis`, `media`, `desviacion_estandar_muestral`, `intervalo_percentil`, `confianza`, `repeticiones`, `semilla`, `mensurando`, `unidad`.

Referencias del proyecto: `EfronTibshirani1993`, `GundersenJensen1987` [POR VERIFICAR: contenido y pertinencia bibliográfica].

### Ejemplo ejecutable

```python
from micrograno import nucleo as mg
from micrograno.sinteticos import crear_conjunto

# Prueba sintética: no son parámetros ni resultados de una micrografía real.
# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.
datos = crear_conjunto()
resultado = mg.reporte_fraccion_area(
    valores=datos['valores'],
    repeticiones=1000,
    semilla=2026,
    confianza=0.95,
    unidad_analisis='campo'
)
print(resultado.resumen)
print(list(resultado.datos))
print(resultado.tabla.head())
```


## Servicios de soporte

`micrograno.archivos` proporciona `cargar_imagen`, `cargar_mascara`, `cargar_etiquetas`, `cargar_valores`, `guardar_resultado`, `exportar_figura`, `metadatos_entorno`, `escribir_json` y `sha256_archivo`. La interfaz usa estas funciones para importar, guardar y exportar; no tienen botones redundantes dentro del catálogo científico. Consulte sus firmas y comentarios en el archivo fuente.

`micrograno.sesion.Sesion` conserva `artefactos`, `pasos`, `resultados`, `fuentes` y `eventos`. `agregar` devuelve un identificador de entrada. `confirmar_roi`, `establecer_escala`, `anotar` y `asociar_fuente` registran contexto. `ejecutar` devuelve `(Resultado, identificadores_de_salida)`. `guardar` escribe una carpeta nueva; `abrir` verifica integridad, y `reproducir` recalcula y compara. `codigo` genera llamadas explícitas a la API científica.

`micrograno.catalogo.CATALOGO` es el registro único de formularios, entradas, parámetros, ayuda y correspondencia. `verificar_catalogo` comprueba que coincida con `nucleo.__all__`. `micrograno.sinteticos.demostrar_catalogo` ejecuta todas las operaciones sobre datos de prueba. `micrograno.visualizacion` prepara contornos e identificadores para presentación, no para producir nuevas medidas.
