from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.autores.models import Autor


class AutorRepository(BaseRepository[Autor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Autor)
