"""Eliminar tabla nomina

Revision ID: <nuevo_id>
Revises: 9900426dd936
Create Date: 2026-04-10 10:55:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '<nuevo_id>'
down_revision = '9900426dd936'
branch_labels = None
depends_on = None

def upgrade():
    # ⚠️ CAMBIO: eliminar tabla nomina
    op.drop_table('nomina')

def downgrade():
    # ⚠️ CAMBIO: recrear tabla nomina si se revierte
    op.create_table(
        'nomina',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('sueldo', sa.Float, nullable=False)
    )
