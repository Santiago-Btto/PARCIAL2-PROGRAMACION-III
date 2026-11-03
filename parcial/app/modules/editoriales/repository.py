from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial


class EditorialRepository(BaseRepository[Editorial]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Editorial)
