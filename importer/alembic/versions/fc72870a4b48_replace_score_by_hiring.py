"""replace score by hiring

Revision ID: fc72870a4b48
Revises: 512434a29bd5
Create Date: 2022-06-27 08:20:05.356025

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fc72870a4b48'
down_revision = '512434a29bd5'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('etablissements_raw', 'score', new_column_name='hiring', existing_type=sa.Integer(),
                    server_default='0', nullable=False)


def downgrade():
    op.alter_column('etablissements_raw', 'hiring', new_column_name='score', existing_type=sa.Integer(),
                    server_default='0', nullable=False)
