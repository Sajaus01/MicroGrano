"""Apariencia de MicroGrano Lab: paletas clara y oscura, tipografía y hoja de estilo.

Solo presentación. Ningún valor de este módulo interviene en un cálculo científico.
"""
from __future__ import annotations
from pathlib import Path
from string import Template
import sys
import tempfile
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

# Colores opacos en hexadecimal; las tuplas (hex, alfa 0-255) son translúcidas.
CLARO = {
    'fondo': '#F5F5F7', 'barra': '#F7F7F9', 'lateral': '#EEEEF2', 'panel': '#FFFFFF',
    'panel_alt': '#F7F7F9', 'tarjeta': '#FFFFFF', 'lienzo': '#E3E3E8',
    'control': '#FFFFFF', 'control_hover': '#F3F3F5', 'control_presionado': '#E7E7EC',
    'control_inactivo': '#F2F2F4', 'borde': '#D1D1D6', 'borde_fuerte': '#B6B6BC',
    'separador': '#E2E2E7', 'texto': '#1D1D1F', 'texto2': '#6E6E73', 'texto3': '#A1A1A6',
    'acento': '#007AFF', 'acento_hover': '#1A86FF', 'acento_presionado': '#0062CC',
    'acento_suave': ('#007AFF', 32), 'foco': ('#007AFF', 150),
    'seleccion': '#DCDCE2', 'hover': ('#000000', 11),
    'segmento': '#E5E5EA', 'segmento_activo': '#FFFFFF', 'segmento_hover': ('#000000', 9),
    'busqueda': '#E4E4E9',
    'exito': '#34C759', 'exito_texto': '#1E7B34', 'exito_suave': ('#34C759', 38),
    'aviso': '#FF9500', 'aviso_texto': '#A65800', 'aviso_suave': ('#FF9500', 40),
    'error': '#FF3B30', 'error_texto': '#C9190B', 'error_suave': ('#FF3B30', 30),
    'info_suave': ('#007AFF', 26),
    'scroll': ('#000000', 72), 'scroll_hover': ('#000000', 125),
    'pista': '#D6D6DC', 'perilla': '#FFFFFF', 'perilla_borde': ('#000000', 48),
    'tooltip': '#FFFFFF', 'tooltip_texto': '#1D1D1F', 'tooltip_borde': '#D1D1D6',
    'hud': ('#1C1C1E', 196), 'hud_texto': '#FFFFFF',
    'codigo_fondo': '#F6F6F8', 'menu': '#FFFFFF', 'menu_borde': '#D0D0D6',
    'sombra': ('#000000', 46),
}

OSCURO = {
    'fondo': '#1C1C1E', 'barra': '#29292B', 'lateral': '#232325', 'panel': '#1E1E20',
    'panel_alt': '#242427', 'tarjeta': '#2C2C2E', 'lienzo': '#121214',
    'control': '#333336', 'control_hover': '#3B3B3E', 'control_presionado': '#46464A',
    'control_inactivo': '#29292C', 'borde': '#47474C', 'borde_fuerte': '#5C5C62',
    'separador': '#353539', 'texto': '#F5F5F7', 'texto2': '#A1A1A6', 'texto3': '#6C6C70',
    'acento': '#0A84FF', 'acento_hover': '#3396FF', 'acento_presionado': '#0070E0',
    'acento_suave': ('#0A84FF', 60), 'foco': ('#0A84FF', 175),
    'seleccion': '#3A3A3E', 'hover': ('#FFFFFF', 14),
    'segmento': '#333336', 'segmento_activo': '#5E5E63', 'segmento_hover': ('#FFFFFF', 12),
    'busqueda': '#323235',
    'exito': '#30D158', 'exito_texto': '#4CD964', 'exito_suave': ('#30D158', 46),
    'aviso': '#FF9F0A', 'aviso_texto': '#FFB340', 'aviso_suave': ('#FF9F0A', 48),
    'error': '#FF453A', 'error_texto': '#FF6961', 'error_suave': ('#FF453A', 44),
    'info_suave': ('#0A84FF', 48),
    'scroll': ('#FFFFFF', 64), 'scroll_hover': ('#FFFFFF', 115),
    'pista': '#4A4A4F', 'perilla': '#E9E9EE', 'perilla_borde': ('#000000', 110),
    'tooltip': '#3A3A3C', 'tooltip_texto': '#F5F5F7', 'tooltip_borde': '#4E4E53',
    'hud': ('#000000', 170), 'hud_texto': '#FFFFFF',
    'codigo_fondo': '#18181A', 'menu': '#2C2C2E', 'menu_borde': '#48484D',
    'sombra': ('#000000', 120),
}

# Colores de sistema de Apple para grupos e insignias; iguales en ambos modos.
SISTEMA = {
    'azul': '#0A84FF', 'morado': '#AF52DE', 'cian': '#32ADE6', 'naranja': '#FF9500',
    'verde': '#34C759', 'rosa': '#FF2D55', 'indigo': '#5856D6', 'gris': '#8E8E93',
    'amarillo': '#FFCC00', 'rojo': '#FF3B30', 'menta': '#00C7BE', 'marron': '#A2845E',
}


def qcolor(valor) -> QColor:
    """Convierte un color de la paleta (hex u (hex, alfa)) en QColor."""
    if isinstance(valor, tuple):
        c = QColor(valor[0])
        c.setAlpha(int(valor[1]))
        return c
    return QColor(valor)


def _qss(valor) -> str:
    if isinstance(valor, tuple):
        c = QColor(valor[0])
        return f'rgba({c.red()}, {c.green()}, {c.blue()}, {int(valor[1])})'
    return valor


def _familias() -> set[str]:
    try:
        return set(QFontDatabase.families())
    except Exception:
        return set()


def familia_ui() -> str:
    if sys.platform == 'darwin':
        return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    disponibles = _familias()
    for f in ('Segoe UI Variable Text', 'Segoe UI Variable', 'Segoe UI', 'Inter',
              'SF Pro Text', 'Cantarell', 'Noto Sans', 'Ubuntu', 'DejaVu Sans'):
        if f in disponibles:
            return f
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()


def familia_codigo() -> str:
    disponibles = _familias()
    for f in ('SF Mono', 'Menlo', 'Cascadia Code', 'Cascadia Mono', 'Consolas',
              'JetBrains Mono', 'DejaVu Sans Mono'):
        if f in disponibles:
            return f
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def fuente_ui(puntos: float | None = None, peso: QFont.Weight | None = None) -> QFont:
    f = QFont(familia_ui())
    if sys.platform == 'darwin':
        f.setPixelSize(13 if puntos is None else round(puntos * 1.3))
    else:
        f.setPointSizeF(10 if puntos is None else puntos)
    if peso is not None:
        f.setWeight(peso)
    f.setHintingPreference(QFont.HintingPreference.PreferVerticalHinting)
    return f


def fuente_codigo(puntos: float = 9.5) -> QFont:
    f = QFont(familia_codigo())
    f.setStyleHint(QFont.StyleHint.Monospace)
    if sys.platform == 'darwin':
        f.setPixelSize(round(puntos * 1.3))
    else:
        f.setPointSizeF(puntos)
    return f


def _directorio_recursos() -> Path:
    d = Path(tempfile.gettempdir()) / 'micrograno_lab' / 'tema_v1'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _svg_recursos(c: dict, nombre_modo: str) -> dict[str, str]:
    """Escribe flechas y marcas en SVG para la hoja de estilo (Qt no admite data URI)."""
    d = _directorio_recursos()
    gris, texto = _hex(c['texto2']), _hex(c['texto'])
    marca = ('<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
             '<path d="M2.5 6.3 L5 8.8 L9.6 3.4" fill="none" stroke="{}" stroke-width="1.8" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    archivos = {
        'flechas': (f'flechas_{nombre_modo}.svg',
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="16" viewBox="0 0 10 16">'
            f'<path d="M2 6 L5 3 L8 6 M2 10 L5 13 L8 10" fill="none" stroke="{gris}" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'),
        'check': ('check_blanco.svg', marca.format('#FFFFFF')),
        'checkmenu': (f'check_{nombre_modo}.svg', marca.format(texto)),
    }
    rutas = {}
    for clave, (nombre, contenido) in archivos.items():
        ruta = d / nombre
        try:
            if not ruta.exists() or ruta.read_text(encoding='utf-8') != contenido:
                ruta.write_text(contenido, encoding='utf-8')
        except OSError:
            pass
        rutas[clave] = ruta.as_posix()
    return rutas


_HOJA = Template(r'''
QMainWindow, QDialog { background: $fondo; }
QWidget#Raiz, QWidget#Bienvenida { background: $fondo; }
QStackedWidget#Paginas { background: $fondo; }
QToolBar#BarraSuperior { background: $barra; border: none; border-bottom: 1px solid $separador; padding: 5px 10px; spacing: 4px; }
QToolBar#BarraSuperior::separator { background: $separador; width: 1px; margin: 6px 6px; }
QWidget#BarraLateral { background: $lateral; }
QWidget#Inspector { background: $fondo; }
QWidget#PanelInferior { background: $panel; }
QWidget#CabeceraLienzo, QWidget#CabeceraPanel { background: $panel; border-bottom: 1px solid $separador; }
QWidget#Lienzo { background: $lienzo; }
QWidget#PieInspector { background: $fondo; border-top: 1px solid $separador; }
QWidget#TiraContenedor { background: $panel; border-top: 1px solid $separador; }
QFrame[clase="tarjeta"] { background: $tarjeta; border: 1px solid $separador; border-radius: 10px; }
QFrame[clase="baldosa"] { background: $tarjeta; border: 1px solid $separador; border-radius: 14px; }
QFrame[clase="baldosa"]:hover { border: 1px solid $acento; background: $control_hover; }
QFrame[clase="separador"] { background: $separador; border: none; max-height: 1px; min-height: 1px; }
QFrame[clase="separador_v"] { background: $separador; border: none; max-width: 1px; min-width: 1px; }
QLabel { color: $texto; background: transparent; }
QLabel[rol="secundario"] { color: $texto2; }
QLabel[rol="terciario"] { color: $texto3; }
QLabel[rol="pie"] { color: $texto2; font-size: 8.5pt; }
QLabel[rol="seccion"] { color: $texto2; font-size: 8pt; font-weight: 600; }
QLabel[rol="titulo"] { font-size: 14pt; font-weight: 600; }
QLabel[rol="titulo_grande"] { font-size: 24pt; font-weight: 700; }
QLabel[rol="subtitulo"] { color: $texto2; font-size: 11pt; }
QLabel[rol="cifra"] { font-size: 18pt; font-weight: 600; }
QLabel[rol="error"] { color: $error_texto; font-size: 8.5pt; }
QLabel#Hud { background: $hud; color: $hud_texto; border-radius: 6px; padding: 3px 8px; font-size: 8.5pt; }
QLabel#HudTitulo { background: $hud; color: $hud_texto; border-radius: 6px; padding: 3px 9px; font-size: 8.5pt; font-weight: 600; }
QPushButton { background: $control; color: $texto; border: 1px solid $borde; border-radius: 6px; padding: 5px 12px; }
QPushButton:hover { background: $control_hover; }
QPushButton:pressed { background: $control_presionado; }
QPushButton:disabled { color: $texto3; background: $control_inactivo; border-color: $separador; }
QPushButton:focus { outline: none; }
QPushButton[tipo="primario"] { background: $acento; color: #FFFFFF; border: 1px solid $acento; font-weight: 600; padding: 6px 14px; }
QPushButton[tipo="primario"]:hover { background: $acento_hover; border-color: $acento_hover; }
QPushButton[tipo="primario"]:pressed { background: $acento_presionado; border-color: $acento_presionado; }
QPushButton[tipo="primario"]:disabled { background: $acento_suave; border-color: transparent; color: $texto2; }
QPushButton[tipo="plano"] { background: transparent; border: none; color: $acento; padding: 3px 4px; }
QPushButton[tipo="plano"]:hover { color: $acento_hover; background: $hover; }
QPushButton[tipo="plano"]:disabled { color: $texto3; background: transparent; }
QPushButton[tipo="sutil"] { background: transparent; border: none; color: $texto; padding: 5px 9px; border-radius: 6px; }
QPushButton[tipo="sutil"]:hover { background: $hover; }
QPushButton[tipo="sutil"]:pressed { background: $control_presionado; }
QPushButton[tipo="sutil"]:disabled { color: $texto3; }
QPushButton[tipo="baldosa"] { background: $tarjeta; border: 1px solid $separador; border-radius: 12px; padding: 14px; text-align: left; font-size: 10.5pt; font-weight: 600; }
QPushButton[tipo="baldosa"]:hover { border-color: $acento; background: $control_hover; }
QPushButton[chip] { border: none; border-radius: 10px; padding: 3px 9px 3px 7px; font-size: 8.5pt; font-weight: 600; }
QPushButton[chip="ok"] { background: $exito_suave; color: $exito_texto; }
QPushButton[chip="aviso"] { background: $aviso_suave; color: $aviso_texto; }
QPushButton[chip="error"] { background: $error_suave; color: $error_texto; }
QPushButton[chip="info"] { background: $info_suave; color: $acento; }
QPushButton[chip="neutro"] { background: $segmento; color: $texto2; }
QPushButton[chip]:hover { border: 1px solid $borde; padding: 2px 8px 2px 6px; }
QToolButton { background: transparent; color: $texto; border: none; border-radius: 6px; padding: 4px; }
QToolButton:hover { background: $hover; }
QToolButton:pressed { background: $control_presionado; }
QToolButton:checked { background: $seleccion; }
QToolButton:disabled { color: $texto3; }
QToolButton[texto="true"] { padding: 4px 9px 4px 6px; }
QToolButton::menu-indicator { image: none; width: 0; }
QToolButton[popupMode="2"] { padding-right: 6px; }
QLineEdit { background: $control; color: $texto; border: 1px solid $borde; border-radius: 6px; padding: 4px 8px; selection-background-color: $acento; selection-color: #FFFFFF; }
QLineEdit:hover { border-color: $borde_fuerte; }
QLineEdit:focus { border: 2px solid $foco; padding: 3px 7px; }
QLineEdit:read-only { background: $control_inactivo; color: $texto2; }
QLineEdit:disabled { background: $control_inactivo; color: $texto3; border-color: $separador; }
QLineEdit[error="true"] { border: 2px solid $error; padding: 3px 7px; }
QLineEdit#Busqueda { background: $busqueda; border: 1px solid transparent; border-radius: 8px; padding: 5px 8px 5px 2px; }
QLineEdit#Busqueda:focus { border: 2px solid $foco; padding: 4px 7px 4px 1px; background: $control; }
QLineEdit#BusquedaPaleta { background: transparent; border: none; font-size: 14pt; padding: 6px 4px; }
QPlainTextEdit[editable="true"], QTextEdit[editable="true"] { background: $control; border: 1px solid $borde; border-radius: 6px; padding: 4px; color: $texto; }
QComboBox { background: $control; color: $texto; border: 1px solid $borde; border-radius: 6px; padding: 4px 26px 4px 9px; min-height: 18px; }
QComboBox:hover { background: $control_hover; border-color: $borde_fuerte; }
QComboBox:focus { border: 2px solid $foco; padding: 3px 25px 3px 8px; }
QComboBox:disabled { color: $texto3; background: $control_inactivo; border-color: $separador; }
QComboBox[error="true"] { border: 2px solid $error; padding: 3px 25px 3px 8px; }
QComboBox[pildora="true"] { border-radius: 8px; background: $busqueda; border: 1px solid transparent; font-weight: 600; }
QComboBox[pildora="true"]:hover { background: $control_hover; border-color: $borde; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 22px; border: none; background: transparent; }
QComboBox::down-arrow { image: url("$flechas"); width: 8px; height: 13px; }
QComboBox::down-arrow:disabled { image: none; }
QComboBox QAbstractItemView { background: $menu; color: $texto; border: 1px solid $menu_borde; padding: 4px; outline: 0; selection-background-color: $acento; selection-color: #FFFFFF; }
QComboBox QAbstractItemView::item { min-height: 26px; padding: 0 8px; border-radius: 5px; }
QComboBox QAbstractItemView::item:hover { background: $hover; }
QComboBox QAbstractItemView::item:selected { background: $acento; color: #FFFFFF; }
QCheckBox { color: $texto; spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid $borde_fuerte; background: $control; }
QCheckBox::indicator:hover { border-color: $acento; }
QCheckBox::indicator:checked { background: $acento; border-color: $acento; image: url("$check"); }
QCheckBox::indicator:disabled { background: $control_inactivo; border-color: $separador; }
QRadioButton { color: $texto; spacing: 8px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget#CuerpoInspector { background: transparent; }
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px 1px 2px 0; }
QScrollBar::handle:vertical { background: $scroll; border-radius: 3px; min-height: 30px; margin: 0 3px; }
QScrollBar::handle:vertical:hover { background: $scroll_hover; margin: 0 2px; border-radius: 4px; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 0 2px 1px 2px; }
QScrollBar::handle:horizontal { background: $scroll; border-radius: 3px; min-width: 30px; margin: 3px 0; }
QScrollBar::handle:horizontal:hover { background: $scroll_hover; margin: 2px 0; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QSlider { background: transparent; min-height: 20px; }
QSlider::groove:horizontal { height: 4px; background: $pista; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $acento; border-radius: 2px; }
QSlider::add-page:horizontal { background: $pista; border-radius: 2px; }
QSlider::handle:horizontal { background: $perilla; border: 1px solid $perilla_borde; width: 16px; height: 16px; margin: -7px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { border-color: $acento; }
QSlider::sub-page:horizontal:disabled { background: $texto3; }
QSplitter { background: transparent; }
QSplitter::handle { background: $separador; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QTreeWidget#Herramientas, QListWidget#ListaDatos, QListWidget#Historial { background: transparent; border: none; outline: 0; }
QListWidget#ListaPasos { background: transparent; border: none; outline: 0; }
QListWidget#ListaPasos::item { border-radius: 7px; padding-left: 10px; color: $texto2; }
QListWidget#ListaPasos::item:hover { background: $hover; }
QListWidget#ListaPasos::item:selected { background: $seleccion; color: $acento; font-weight: 600; }
QTreeWidget#Herramientas::item { min-height: 30px; border-radius: 7px; padding-left: 4px; color: $texto; }
QTreeWidget#Herramientas::item:hover { background: $hover; }
QTreeWidget#Herramientas::item:selected { background: $seleccion; color: $texto; }
QTreeWidget#Herramientas::branch { background: transparent; border: none; image: none; }
QListWidget#ListaDatos::item { border-radius: 8px; margin: 1px 0; }
QListWidget#ListaDatos::item:hover { background: $hover; }
QListWidget#ListaDatos::item:selected { background: $seleccion; }
QListWidget#Historial::item { border-radius: 8px; margin: 1px 4px; padding: 0; }
QListWidget#Historial::item:hover { background: $hover; }
QListWidget#Historial::item:selected { background: $seleccion; color: $texto; }
QListWidget#Tira { background: transparent; border: none; outline: 0; }
QListWidget#Tira::item { border-radius: 8px; padding: 4px 2px 2px 2px; color: $texto2; margin: 0 2px; }
QListWidget#Tira::item:hover { background: $hover; }
QListWidget#Tira::item:selected { background: $seleccion; color: $texto; }
QListWidget#ListaPaleta { background: transparent; border: none; outline: 0; }
QListWidget#ListaPaleta::item { border-radius: 7px; padding: 0 6px; min-height: 34px; color: $texto; }
QListWidget#ListaPaleta::item:selected { background: $acento; color: #FFFFFF; }
QListWidget#ListaRecientes { background: transparent; border: none; outline: 0; }
QListWidget#ListaRecientes::item { border-radius: 7px; padding: 6px 8px; color: $texto; }
QListWidget#ListaRecientes::item:hover { background: $hover; }
QListWidget#ListaRecientes::item:selected { background: $seleccion; color: $texto; }
QHeaderView { background: $panel; border: none; }
QHeaderView::section { background: $panel; color: $texto2; border: none; border-bottom: 1px solid $separador; border-right: 1px solid $separador; padding: 5px 8px; font-weight: 600; font-size: 8.5pt; }
QHeaderView::section:last { border-right: none; }
QHeaderView::up-arrow, QHeaderView::down-arrow { width: 0; height: 0; image: none; }
QTableView { background: $panel; alternate-background-color: $panel_alt; color: $texto; border: none; gridline-color: transparent; selection-background-color: $acento_suave; selection-color: $texto; outline: 0; }
QTableView QTableCornerButton::section { background: $panel; border: none; }
QMenuBar { background: $barra; color: $texto; padding: 2px 4px; }
QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 5px; }
QMenuBar::item:selected { background: $hover; }
QMenuBar::item:pressed { background: $seleccion; }
QMenu { background: $menu; color: $texto; border: 1px solid $menu_borde; border-radius: 8px; padding: 5px; }
QMenu::item { padding: 5px 26px 5px 10px; border-radius: 5px; margin: 0; }
QMenu::item:selected { background: $acento; color: #FFFFFF; }
QMenu::item:disabled { color: $texto3; background: transparent; }
QMenu::separator { height: 1px; background: $separador; margin: 4px 8px; }
QMenu::icon { padding-left: 8px; }
QMenu::indicator { width: 14px; height: 14px; left: 6px; }
QMenu::indicator:checked { image: url("$checkoscuro"); }
QMenu::right-arrow { width: 8px; height: 8px; right: 8px; }
QToolTip { background: $tooltip; color: $tooltip_texto; border: 1px solid $tooltip_borde; padding: 5px 8px; }
QTextBrowser, QPlainTextEdit { background: transparent; border: none; color: $texto; selection-background-color: $acento; selection-color: #FFFFFF; }
QPlainTextEdit#Codigo, QTextBrowser#Documento { background: $codigo_fondo; border: 1px solid $separador; border-radius: 8px; padding: 6px; }
QProgressBar { background: $pista; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; text-align: center; color: transparent; }
QProgressBar::chunk { background: $acento; border-radius: 2px; }
QFrame#Segmentado { background: $segmento; border-radius: 7px; border: none; }
QFrame#Segmentado QPushButton { background: transparent; border: 1px solid transparent; border-radius: 5px; padding: 3px 10px; color: $texto; font-weight: 500; }
QFrame#Segmentado QPushButton:hover { background: $segmento_hover; }
QFrame#Segmentado QPushButton:checked { background: $segmento_activo; border: 1px solid $separador; font-weight: 600; }
QFrame#Segmentado QPushButton:disabled { color: $texto3; }
QFrame[aviso] { border-radius: 9px; border: none; }
QFrame[aviso="info"] { background: $info_suave; }
QFrame[aviso="aviso"] { background: $aviso_suave; }
QFrame[aviso="error"] { background: $error_suave; }
QFrame[aviso="ok"] { background: $exito_suave; }
QFrame#Hoja, QFrame#Toast, QFrame#Popover, QFrame#Paleta { background: $menu; border: 1px solid $menu_borde; border-radius: 12px; }
QFrame#Toast { border-radius: 10px; }
QWidget#FilaDato, QWidget#FilaPaso { background: transparent; }
QDialogButtonBox QPushButton { min-width: 86px; }
QMessageBox { background: $fondo; }
QMessageBox QLabel { color: $texto; }
''')


def hoja_estilo(c: dict, nombre_modo: str) -> str:
    variables = {k: _qss(v) for k, v in c.items()}
    recursos = _svg_recursos(c, nombre_modo)
    variables['flechas'] = recursos['flechas']
    variables['check'] = recursos['check']
    variables['checkoscuro'] = recursos['checkmenu']
    return _HOJA.substitute(variables)


def paleta_qt(c: dict, oscuro: bool) -> QPalette:
    p = QPalette()
    R = QPalette.ColorRole
    G = QPalette.ColorGroup
    asignar = {
        R.Window: c['fondo'], R.WindowText: c['texto'], R.Base: c['control'],
        R.AlternateBase: c['panel_alt'], R.Text: c['texto'], R.Button: c['control'],
        R.ButtonText: c['texto'], R.Highlight: c['acento'], R.HighlightedText: '#FFFFFF',
        R.ToolTipBase: c['tooltip'], R.ToolTipText: c['tooltip_texto'],
        R.PlaceholderText: c['texto3'], R.Link: c['acento'], R.LinkVisited: c['acento'],
        R.BrightText: '#FFFFFF', R.Light: c['panel'], R.Midlight: c['control_hover'],
        R.Mid: c['borde'], R.Dark: c['borde_fuerte'], R.Shadow: '#000000',
    }
    for rol, valor in asignar.items():
        p.setColor(rol, qcolor(valor))
    for rol in (R.Text, R.ButtonText, R.WindowText):
        p.setColor(G.Disabled, rol, qcolor(c['texto3']))
    p.setColor(G.Inactive, R.Highlight, qcolor(c['acento']))
    return p


class GestorTema(QObject):
    """Mantiene el modo de apariencia (automático, claro u oscuro) de la aplicación."""
    cambiado = Signal()

    def __init__(self):
        super().__init__()
        self.modo = 'auto'
        self.oscuro = False
        self.c = dict(CLARO)
        self.generacion = 0
        self._conectado = False

    def color(self, nombre: str) -> QColor:
        if nombre in self.c:
            return qcolor(self.c[nombre])
        if nombre in SISTEMA:
            return QColor(SISTEMA[nombre])
        return QColor(nombre)

    def _esquema_sistema_oscuro(self, app) -> bool:
        try:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            return False

    def aplicar(self, modo: str | None = None) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if modo is not None:
            if modo not in ('auto', 'claro', 'oscuro'):
                raise ValueError('Modo de apariencia no admitido.')
            self.modo = modo
        hints = app.styleHints()
        if not self._conectado:
            try:
                hints.colorSchemeChanged.connect(self._sistema_cambio)
            except Exception:
                pass
            self._conectado = True
        try:
            if self.modo == 'auto':
                hints.unsetColorScheme()
            else:
                hints.setColorScheme(Qt.ColorScheme.Dark if self.modo == 'oscuro' else Qt.ColorScheme.Light)
        except Exception:
            pass
        self.oscuro = self._esquema_sistema_oscuro(app) if self.modo == 'auto' else self.modo == 'oscuro'
        self.c = dict(OSCURO if self.oscuro else CLARO)
        if app.style().name().lower() != 'fusion':
            app.setStyle('Fusion')
        app.setPalette(paleta_qt(self.c, self.oscuro))
        app.setStyleSheet(hoja_estilo(self.c, 'oscuro' if self.oscuro else 'claro'))
        app.setProperty('micrograno_tema', True)
        self.generacion += 1
        self.cambiado.emit()

    def _sistema_cambio(self, *_):
        if self.modo == 'auto':
            app = QApplication.instance()
            if app is not None and self._esquema_sistema_oscuro(app) != self.oscuro:
                self.aplicar()


_GESTOR: GestorTema | None = None


def tema() -> GestorTema:
    global _GESTOR
    if _GESTOR is None:
        _GESTOR = GestorTema()
    return _GESTOR


def asegurar_tema() -> GestorTema:
    """Aplica el tema una sola vez si la aplicación aún no lo tiene."""
    app = QApplication.instance()
    t = tema()
    if app is not None and not app.property('micrograno_tema'):
        app.setFont(fuente_ui())
        t.aplicar()
    return t


def rc_matplotlib() -> dict:
    """Parámetros de Matplotlib para gráficas de la interfaz (no para figuras editoriales)."""
    t = tema()
    c = t.c
    return {
        'font.family': [familia_ui(), 'Segoe UI', 'DejaVu Sans'],
        'font.size': 9,
        'axes.edgecolor': _hex(c['borde_fuerte']),
        'axes.labelcolor': _hex(c['texto2']),
        'axes.titlecolor': _hex(c['texto']),
        'axes.facecolor': _hex(c['panel']),
        'figure.facecolor': _hex(c['panel']),
        'xtick.color': _hex(c['texto2']),
        'ytick.color': _hex(c['texto2']),
        'grid.color': _hex(c['separador']),
        'text.color': _hex(c['texto']),
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'axes.grid.axis': 'y',
        'axes.axisbelow': True,
        'legend.frameon': False,
        'savefig.facecolor': _hex(c['panel']),
    }


def _hex(valor) -> str:
    return valor[0] if isinstance(valor, tuple) else valor
