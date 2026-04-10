"""Agregar columna reservado a Inventario

Revision ID: e494805347e7
Revises: bd8b40359ee3
Create Date: 2026-04-09 21:15:25.176372

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e494805347e7'
down_revision = 'bd8b40359ee3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('inventario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reservado', sa.Integer(), nullable=False, server_default='0'))



def downgrade():
    with op.batch_alter_table('inventario', schema=None) as batch_op:
        batch_op.drop_column('reservado')
