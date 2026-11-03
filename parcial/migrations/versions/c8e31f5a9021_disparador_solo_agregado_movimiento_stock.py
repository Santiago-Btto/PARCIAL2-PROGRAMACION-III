"""disparador solo agregado en movimiento_stock

Revision ID: c8e31f5a9021
Revises: 9a4e7c2b1d80
Create Date: 2026-11-03 11:00:00.000000

REVISIÓN ANTES DE APLICAR (migración escrita a mano — Ejercicio 2 y Ejercicio 7, RN-12)
---------------------------------------------------------------------------------------
- Por qué se escribe a mano: `alembic revision --autogenerate` compara tablas,
  columnas, índices y restricciones declaradas en `SQLModel.metadata`, pero no
  inspecciona funciones PL/pgSQL ni disparadores (`TRIGGER`) en el catálogo de
  PostgreSQL.
- Qué instala `upgrade()`:
    1. La función `impedir_modificacion_movimiento_stock()` que lanza una excepción
       (`RAISE EXCEPTION` con `ERRCODE = 'integrity_constraint_violation'` / `23000`
       o `restrict_violation`) ante cualquier intento de `UPDATE` o `DELETE` sobre
       filas de `movimiento_stock`.
    2. El disparador `trg_movimiento_stock_solo_agregado` (`BEFORE UPDATE OR DELETE ON
       movimiento_stock FOR EACH ROW`), que rechaza la operación venga de donde venga
       (desde la aplicación o desde una consola `psql`, Caso C-14).
    3. Nota sobre `seed.py`: en PostgreSQL un disparador `FOR EACH ROW BEFORE UPDATE OR
       DELETE` no impide `TRUNCATE TABLE`, de modo que `seed.py` puede vaciar las tablas
       al reiniciar el entorno de pruebas sin desactivar el disparador, mientras que
       cualquier `UPDATE` o `DELETE` queda bloqueado.
- Qué hace `downgrade()`:
    Elimina primero el disparador `trg_movimiento_stock_solo_agregado` sobre
    `movimiento_stock` y luego la función `impedir_modificacion_movimiento_stock()`,
    garantizando que `alembic downgrade base` y un nuevo `alembic upgrade head`
    funcionen de punta a punta.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c8e31f5a9021"
down_revision: Union[str, None] = "9a4e7c2b1d80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Instala la función y el disparador de sólo agregado sobre movimiento_stock (RN-12)."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION impedir_modificacion_movimiento_stock()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'La tabla movimiento_stock es de sólo agregado: no se permite % sobre sus filas (RN-12).',
                TG_OP
                USING ERRCODE = '23514',
                      CONSTRAINT = 'ck_movimiento_stock_solo_agregado';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_movimiento_stock_solo_agregado
        BEFORE UPDATE OR DELETE ON movimiento_stock
        FOR EACH ROW
        EXECUTE FUNCTION impedir_modificacion_movimiento_stock();
        """
    )


def downgrade() -> None:
    """Elimina el disparador y la función de sólo agregado de movimiento_stock."""
    op.execute(
        "DROP TRIGGER IF EXISTS trg_movimiento_stock_solo_agregado ON movimiento_stock;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS impedir_modificacion_movimiento_stock();"
    )
