# Lanzador de MicroGrano Lab

El lanzador permite abrir MicroGrano Lab con un doble clic justo después de descargar el repositorio. Prepara el entorno de Python cuando hace falta y no contiene lógica científica.

## Archivos

| Archivo | Función |
|---|---|
| `../MicroGrano Lab.exe` | Lanzador de Windows. Busca Python y ejecuta `arranque.py` sin consola. |
| `../iniciar_windows.bat` | Alternativa de Windows. Hace lo mismo y muestra el progreso en una consola. |
| `../iniciar_mac.command` | Lanzador de macOS (doble clic en Finder). |
| `../iniciar_linux.sh` | Lanzador de Linux (`sh iniciar_linux.sh`). |
| `arranque.py` | Preparador común. Solo usa la biblioteca estándar de Python. |
| `MicroGranoLab.cs`, `MicroGranoLab.manifest` | Código fuente y manifiesto de `MicroGrano Lab.exe`. |
| `compilar_lanzador.bat` | Compila el `.exe` con el compilador de C# incluido en Windows (.NET Framework 4). |
| `generar_iconos.py`, `recursos/` | Generan y guardan los iconos (ICO y PNG) a partir del icono de la aplicación. |

## Qué hace `arranque.py`

1. **Python.** Busca Python 3.13 de 64 bits, correspondiente al entorno de dependencias fijado en `constraints.txt`. Descarta otras versiones, las variantes sin GIL y los alias de Microsoft Store que abrirían la tienda. En Windows consulta el lanzador `py` con `-3.13` y las carpetas habituales. Si no encuentra un intérprete compatible, ofrece instalar Python 3.13 con `winget` (solo para el usuario actual).
2. **Entorno.** Usa `.venv` dentro del repositorio. Si la carpeta no admite escritura, usa una carpeta del perfil del usuario. Recrea el entorno si su Python no funciona o no es compatible.
3. **Librerías.** Compara las versiones instaladas con `pyproject.toml` (dependencias y extra `gui`) y con `constraints.txt`. También comprueba que `micrograno` esté instalado en modo editable desde esta carpeta. Si falta algo, ejecuta:
   `python -m pip install -c constraints.txt -e ".[gui]"`
   y muestra el avance de cada descarga.
4. **Apertura.** Ejecuta `python -m micrograno_lab` sin consola y espera la señal de ventana visible (`MICROGRANO_SENAL_LISTO`). Si la aplicación se cierra al iniciar, muestra el error y ofrece **Reparar**.

Si `tkinter` está disponible, el progreso aparece en una ventana pequeña en modo claro u oscuro según el sistema. Si no, aparece en la consola.

## Opciones

```text
python lanzador/arranque.py [opciones] [archivos...]

  --consola        mostrar el progreso en la consola, sin ventana
  --solo-instalar  preparar el entorno sin abrir la interfaz
  --comprobar      informar del estado sin instalar ni abrir nada (código 0 = listo)
  --reparar        recrear el entorno; si se ejecuta desde él, reinstala sus librerías
  archivos         imágenes o sesiones que se abrirán al iniciar
```

Las mismas opciones se pueden pasar a `iniciar_windows.bat`, `iniciar_mac.command`, `iniciar_linux.sh` y `MicroGrano Lab.exe`.

Si un entorno antiguo contiene otra versión de Python, use el archivo de inicio de su sistema o un Python 3.13 externo a `.venv`. El preparador evita reemplazar un entorno incompatible mientras se ejecuta desde su propio intérprete.

## Registros

- `.micrograno/lanzador.log`: decisiones del preparador y salida de pip.
- `.micrograno/interfaz.log`: salida de la aplicación durante el último inicio.
- `.micrograno/entorno.json`: Python usado y firma de `pyproject.toml` y `constraints.txt`.

La carpeta `.micrograno/` está excluida en `.gitignore`.

## Compilar el ejecutable

```bat
lanzador\compilar_lanzador.bat
```

No requiere instalar nada: usa `csc.exe` de .NET Framework 4, presente en Windows 10 y 11. El ejecutable no está firmado digitalmente, por lo que SmartScreen puede pedir confirmación la primera vez que se abre un archivo descargado de Internet. Para regenerar los iconos después de cambiar el diseño del icono de la aplicación:

```bat
.venv\Scripts\python.exe lanzador\generar_iconos.py
```

## Pruebas

`tests/test_lanzador.py` comprueba la lectura de requisitos, la elección de Python, el diagnóstico del entorno, los mensajes de error de pip y que `--comprobar` no modifica el repositorio. Las pruebas no instalan paquetes ni abren ventanas.
