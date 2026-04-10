"""Crear tablas venta y nomina

Revision ID: 6f045d63f32f
Revises: e494805347e7
Create Date: 2026-04-10 09:54:26.654560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f045d63f32f'
down_revision = 'e494805347e7'
branch_labels = None
depends_on = None


def upgrade():
    # La tabla nomina ya existe, no se vuelve a crear
    # La tabla venta ya existe, no se vuelve a crear

    with op.batch_alter_table('inventario', schema=None) as batch_op:
        batch_op.alter_column('reservado',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text("'0'"))


def downgrade():
    with op.batch_alter_table('inventario', schema=None) as batch_op:
        batch_op.alter_column('reservado',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text("'0'"))

    # No se eliminan las tablas venta ni nomina porque ya existían antes
