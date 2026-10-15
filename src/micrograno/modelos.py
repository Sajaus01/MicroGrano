"""Contratos compartidos: una salida conserva sus datos, unidades y advertencias."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
import math
import numpy as np
import pandas as pd

TIPOS = {"imagen", "gris", "mascara", "limites", "etiquetas", "clases", "marcadores", "mapa", "valores", "distribucion"}

@dataclass(frozen=True)
class EscalaEspacial:
    """Escala isotrópica de la imagen analizada; no se infiere de su aumento nominal."""
    um_por_px: float
    incertidumbre_um_por_px: float | None = None
    referencia: str = ""

    def __post_init__(self):
        if isinstance(self.um_por_px, (bool, np.bool_)):
            raise TypeError("La escala no puede ser booleana.")
        if not math.isfinite(self.um_por_px) or self.um_por_px <= 0:
            raise ValueError("La escala debe ser finita y mayor que cero (µm/px).")
        u = self.incertidumbre_um_por_px
        if u is not None and (not math.isfinite(u) or u < 0):
            raise ValueError("La incertidumbre estándar debe ser finita y no negativa.")

    def longitud_um(self, longitud_px: float) -> float:
        if not math.isfinite(longitud_px) or longitud_px < 0:
            raise ValueError("La longitud debe ser finita y no negativa.")
        return float(longitud_px * self.um_por_px)

    def area_um2(self, area_px2: float) -> float:
        if not math.isfinite(area_px2) or area_px2 < 0:
            raise ValueError("El área debe ser finita y no negativa.")
        return float(area_px2 * self.um_por_px**2)

    def como_dict(self) -> dict:
        return asdict(self)

@dataclass
class Resultado:
    """Salida uniforme. Las claves de datos y tipos coinciden; no son fases físicas.

    datos: arreglos de inspección o resultados reutilizables.
    tabla: medidas con unidades en los nombres de columna.
    resumen: escalares y decisiones del cálculo.
    advertencias: límites de interpretación específicos de la operación.
    """
    datos: dict[str, np.ndarray] = field(default_factory=dict)
    tipos: dict[str, str] = field(default_factory=dict)
    tabla: pd.DataFrame = field(default_factory=pd.DataFrame)
    resumen: dict[str, Any] = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.datos.keys() != self.tipos.keys():
            raise ValueError("Cada arreglo debe tener un tipo declarado.")
        for clave, valor in self.datos.items():
            if self.tipos[clave] not in TIPOS:
                raise ValueError(f"Tipo desconocido: {self.tipos[clave]}")
            a = np.array(valor, copy=True)
            if a.dtype.kind not in "buif":
                raise TypeError("Solo se admiten arreglos numéricos reales.")
            a.setflags(write=False)
            self.datos[clave] = a
        self.tabla = self.tabla.copy(deep=True)
