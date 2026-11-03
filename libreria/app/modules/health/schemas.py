from sqlmodel import SQLModel


class EstadoVivo(SQLModel):
    estado: str


class EstadoBase(SQLModel):
    estado: str
    base: str
