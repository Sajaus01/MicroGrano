// MicroGrano Lab.exe: lanzador para Windows.
//
// Busca un intérprete de Python y ejecuta lanzador\arranque.py, que comprueba el entorno,
// instala las librerías que falten y abre la interfaz. Si el equipo no tiene Python,
// ofrece instalar Python 3.13 para el usuario actual con winget.
//
// No contiene lógica científica ni descarga nada por sí mismo. Se compila con el
// compilador de C# incluido en Windows: lanzador\compilar_lanzador.bat
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("MicroGrano Lab")]
[assembly: AssemblyDescription("Prepara el entorno de Python y abre MicroGrano Lab")]
[assembly: AssemblyCompany("MicroGrano")]
[assembly: AssemblyProduct("MicroGrano Lab")]
[assembly: AssemblyCopyright("Andrés Felipe Saavedra Sajaus")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace MicroGrano
{
    internal static class Lanzador
    {
        private const string Titulo = "MicroGrano Lab";
        private const string Prueba = "-c \"import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var('Py_GIL_DISABLED') and getattr(sys, '_is_gil_enabled', lambda: True)() else 3)\"";
        private const string UrlPython = "https://www.python.org/downloads/";

        [STAThread]
        private static int Main(string[] argumentos)
        {
            Application.EnableVisualStyles();
            string raiz = Path.GetDirectoryName(Application.ExecutablePath);
            string arranque = Path.Combine(Path.Combine(raiz, "lanzador"), "arranque.py");
            if (!File.Exists(arranque))
            {
                Avisar("No se encontró «lanzador\\arranque.py» junto al ejecutable.\n\n" +
                       "Mantenga «MicroGrano Lab.exe» dentro de la carpeta del repositorio. Si lo abrió " +
                       "directamente desde el archivo .zip, extraiga primero todo su contenido " +
                       "(clic derecho › Extraer todo).", MessageBoxIcon.Error);
                return 1;
            }

            string[] python = BuscarPython(raiz);
            if (python == null)
            {
                if (!OfrecerInstalacion())
                {
                    return 1;
                }
                python = BuscarPython(raiz);
                if (python == null)
                {
                    Avisar("Python se instaló, pero todavía no está disponible para este programa.\n\n" +
                           "Cierre este mensaje y abra de nuevo MicroGrano Lab.", MessageBoxIcon.Information);
                    return 1;
                }
            }

            StringBuilder linea = new StringBuilder();
            for (int i = 1; i < python.Length; i++)
            {
                linea.Append(python[i]).Append(' ');
            }
            linea.Append(Citar(arranque));
            foreach (string argumento in argumentos)
            {
                linea.Append(' ').Append(Citar(argumento));
            }

            ProcessStartInfo inicio = new ProcessStartInfo(python[0], linea.ToString());
            inicio.WorkingDirectory = raiz;
            inicio.UseShellExecute = false;
            inicio.CreateNoWindow = true;
            try
            {
                Process.Start(inicio);
            }
            catch (Exception ex)
            {
                Avisar("No se pudo iniciar Python:\n\n" + ex.Message, MessageBoxIcon.Error);
                return 1;
            }
            return 0;
        }

        // Devuelve { ejecutable sin consola, argumentos previos... } o null si no hay Python.
        private static string[] BuscarPython(string raiz)
        {
            string entorno = Path.Combine(Path.Combine(Path.Combine(raiz, ".venv"), "Scripts"), "python.exe");
            if (Funciona(entorno, ""))
            {
                return new string[] { SinConsola(entorno) };
            }
            foreach (string carpeta in CarpetasLanzadorPy())
            {
                string py = Path.Combine(carpeta, "py.exe");
                if (File.Exists(py) && Funciona(py, "-3.13"))
                {
                    string pyw = Path.Combine(carpeta, "pyw.exe");
                    return new string[] { File.Exists(pyw) ? pyw : py, "-3.13" };
                }
            }
            foreach (string ejecutable in InstalacionesPython())
            {
                if (Funciona(ejecutable, ""))
                {
                    return new string[] { SinConsola(ejecutable) };
                }
            }
            return null;
        }

        private static string SinConsola(string python)
        {
            string w = Path.Combine(Path.GetDirectoryName(python), "pythonw.exe");
            return File.Exists(w) ? w : python;
        }

        private static List<string> CarpetasPath()
        {
            List<string> lista = new List<string>();
            string path = Environment.GetEnvironmentVariable("PATH") ?? "";
            foreach (string parte in path.Split(';'))
            {
                string carpeta = parte.Trim().Trim('"');
                if (carpeta.Length == 0)
                {
                    continue;
                }
                try
                {
                    if (Directory.Exists(carpeta) && !lista.Contains(carpeta))
                    {
                        lista.Add(carpeta);
                    }
                }
                catch (Exception)
                {
                }
            }
            return lista;
        }

        private static List<string> CarpetasLanzadorPy()
        {
            List<string> lista = new List<string>();
            string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
            if (!string.IsNullOrEmpty(local))
            {
                lista.Add(Path.Combine(local, @"Programs\Python\Launcher"));
            }
            string windows = Environment.GetEnvironmentVariable("WINDIR");
            if (!string.IsNullOrEmpty(windows))
            {
                lista.Add(windows);
            }
            foreach (string carpeta in CarpetasPath())
            {
                if (File.Exists(Path.Combine(carpeta, "py.exe")) && !lista.Contains(carpeta))
                {
                    lista.Add(carpeta);
                }
            }
            return lista;
        }

        private static List<string> InstalacionesPython()
        {
            List<string> posibles = new List<string>();
            string[] versiones = { "313" };
            string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
            string programas = Environment.GetEnvironmentVariable("ProgramFiles");
            foreach (string v in versiones)
            {
                if (!string.IsNullOrEmpty(local))
                {
                    posibles.Add(Path.Combine(local, @"Programs\Python\Python" + v + @"\python.exe"));
                }
                if (!string.IsNullOrEmpty(programas))
                {
                    posibles.Add(Path.Combine(programas, "Python" + v + @"\python.exe"));
                }
            }
            foreach (string carpeta in CarpetasPath())
            {
                // El alias de Microsoft Store abre la tienda si Python no está instalado.
                if (carpeta.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    continue;
                }
                posibles.Add(Path.Combine(carpeta, "python.exe"));
                posibles.Add(Path.Combine(carpeta, "python3.exe"));
            }
            List<string> existentes = new List<string>();
            foreach (string ruta in posibles)
            {
                if (File.Exists(ruta) && !existentes.Contains(ruta))
                {
                    existentes.Add(ruta);
                }
            }
            return existentes;
        }

        private static bool Funciona(string ejecutable, string prefijo)
        {
            if (!File.Exists(ejecutable))
            {
                return false;
            }
            try
            {
                ProcessStartInfo info = new ProcessStartInfo(ejecutable, (prefijo + " " + Prueba).Trim());
                info.UseShellExecute = false;
                info.CreateNoWindow = true;
                using (Process proceso = Process.Start(info))
                {
                    if (!proceso.WaitForExit(30000))
                    {
                        try
                        {
                            proceso.Kill();
                        }
                        catch (Exception)
                        {
                        }
                        return false;
                    }
                    return proceso.ExitCode == 0;
                }
            }
            catch (Exception)
            {
                return false;
            }
        }

        private static string BuscarWinget()
        {
            string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
            if (!string.IsNullOrEmpty(local))
            {
                string alias = Path.Combine(local, @"Microsoft\WindowsApps\winget.exe");
                if (File.Exists(alias))
                {
                    return alias;
                }
            }
            foreach (string carpeta in CarpetasPath())
            {
                string ruta = Path.Combine(carpeta, "winget.exe");
                if (File.Exists(ruta))
                {
                    return ruta;
                }
            }
            return null;
        }

        private static bool OfrecerInstalacion()
        {
            string winget = BuscarWinget();
            if (winget == null)
            {
                DialogResult abrir = MessageBox.Show(
                    "MicroGrano Lab necesita Python 3.13 de 64 bits con GIL y no se encontró en este equipo.\n\n" +
                    "¿Desea abrir la página de descarga de Python?\n\n" +
                    "Durante la instalación marque «Add python.exe to PATH» y después vuelva a abrir MicroGrano Lab.",
                    Titulo, MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                if (abrir == DialogResult.Yes)
                {
                    AbrirUrl(UrlPython);
                }
                return false;
            }
            DialogResult respuesta = MessageBox.Show(
                "MicroGrano Lab necesita Python 3.13 de 64 bits con GIL y no se encontró en este equipo.\n\n" +
                "¿Desea instalar Python 3.13 ahora?\n\n" +
                "Se usará winget, el gestor de paquetes de Windows. La instalación es solo para su usuario " +
                "y no requiere permisos de administrador. Verá una ventana con el progreso.",
                Titulo, MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (respuesta != DialogResult.Yes)
            {
                return false;
            }
            try
            {
                ProcessStartInfo info = new ProcessStartInfo(winget,
                    "install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements");
                info.UseShellExecute = false;
                using (Process proceso = Process.Start(info))
                {
                    proceso.WaitForExit();
                }
                return true;
            }
            catch (Exception ex)
            {
                Avisar("No se pudo ejecutar winget:\n\n" + ex.Message + "\n\nDescargue Python desde " + UrlPython,
                       MessageBoxIcon.Error);
                return false;
            }
        }

        private static void AbrirUrl(string url)
        {
            try
            {
                ProcessStartInfo info = new ProcessStartInfo(url);
                info.UseShellExecute = true;
                Process.Start(info);
            }
            catch (Exception)
            {
            }
        }

        private static void Avisar(string texto, MessageBoxIcon icono)
        {
            MessageBox.Show(texto, Titulo, MessageBoxButtons.OK, icono);
        }

        // Cita un argumento según las reglas de CommandLineToArgvW.
        private static string Citar(string argumento)
        {
            if (argumento.Length > 0 && argumento.IndexOfAny(new char[] { ' ', '\t', '"' }) < 0)
            {
                return argumento;
            }
            StringBuilder resultado = new StringBuilder("\"");
            int barras = 0;
            foreach (char caracter in argumento)
            {
                if (caracter == '\\')
                {
                    barras++;
                    continue;
                }
                if (caracter == '"')
                {
                    resultado.Append('\\', barras * 2 + 1).Append('"');
                }
                else
                {
                    resultado.Append('\\', barras).Append(caracter);
                }
                barras = 0;
            }
            resultado.Append('\\', barras * 2).Append('"');
            return resultado.ToString();
        }
    }
}
