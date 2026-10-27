"""Entidad pura del Bounded Context Préstamos con sus reglas de negocio."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional


@dataclass
class Prestamo:
    id: Optional[int] = None
    fecha_prestamo: date = field(default_factory=date.today)
    fecha_limite: Optional[date] = None
    fecha_devolucion: Optional[date] = None
    multa: float = 0.0
    libro_id: Optional[int] = None
    usuario_id: Optional[int] = None
    libro: Optional[Any] = field(default=None, repr=False)
    usuario: Optional[Any] = field(default=None, repr=False)
    _orm_model: Optional[Any] = field(default=None, repr=False)

    DIAS_PRESTAMO = {"estudiante": 8, "docente": 15, "externo": 5}
    VALOR_MULTA_DIA = 1000  # pesos por día de retraso

    @staticmethod
    def calcular_fecha_limite(tipo_usuario: str, desde: Optional[date] = None) -> date:
        desde = desde or date.today()
        dias = Prestamo.DIAS_PRESTAMO.get(tipo_usuario, 8)
        return desde + timedelta(days=dias)

    def calcular_multa(self, fecha_actual: Optional[date] = None) -> float:
        fecha_actual = fecha_actual or date.today()
        if self.fecha_limite and fecha_actual > self.fecha_limite:
            dias_retraso = (fecha_actual - self.fecha_limite).days
            self.multa = dias_retraso * self.VALOR_MULTA_DIA
        return self.multa

    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        if name != "_orm_model" and hasattr(self, "_orm_model") and self._orm_model is not None:
            if hasattr(self._orm_model, name):
                setattr(self._orm_model, name, value)
