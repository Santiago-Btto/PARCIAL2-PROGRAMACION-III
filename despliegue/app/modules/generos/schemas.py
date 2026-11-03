from sqlmodel import Field, SQLModel


class GeneroCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=60)


class GeneroRead(SQLModel):
    id: int
    nombre: str
