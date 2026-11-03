from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, model_validator
from sqlmodel import Field, SQLModel

from app.core.parametros import MAX_ID
from app.modules.clientes.schemas import ClienteResumen
from app.modules.ventas.models import Venta


class RenglonCreate(SQLModel):
    """Composición: viajan los DATOS de la parte, que nace con la venta.
    El precio NO viaja: lo copia el servidor desde el libro (RN-06)."""

    model_config = ConfigDict(extra="forbid")

    libro_id: int = Field(ge=1, le=MAX_ID)
    cantidad: int = Field(gt=0, le=10_000)


class VentaCreate(SQLModel):
    """Asociación con el cliente: viaja su id. No viajan fecha, total ni precios (RN-06, RN-07).
    extra="forbid": si el cliente intenta mandar total o precio_unitario, recibe 422."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: int = Field(ge=1, le=MAX_ID)
    renglones: list[RenglonCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def renglones_validos(self) -> "VentaCreate":
        # RN-05: al menos un renglón y ningún libro repetido.
        if not self.renglones:
            raise ValueError("La venta necesita al menos un renglón.")
        libros = [r.libro_id for r in self.renglones]
        if len(libros) != len(set(libros)):
            raise ValueError("Un mismo libro no puede aparecer en dos renglones.")
        return self


class RenglonRead(SQLModel):
    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaListado(SQLModel):
    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteResumen


class VentaRead(VentaListado):
    """Venta con cliente y renglones."""

    renglones: list[RenglonRead]

    @classmethod
    def desde(cls, venta: Venta) -> "VentaRead":
        return cls(
            id=venta.id,  # type: ignore[arg-type]
            fecha=venta.fecha,
            total=venta.total,
            cliente=ClienteResumen.model_validate(venta.cliente),
            renglones=[
                RenglonRead(
                    libro_id=r.libro_id,
                    titulo=r.libro.titulo if r.libro else "",
                    cantidad=r.cantidad,
                    precio_unitario=r.precio_unitario,
                    subtotal=r.precio_unitario * r.cantidad,
                )
                for r in venta.renglones
            ],
        )
