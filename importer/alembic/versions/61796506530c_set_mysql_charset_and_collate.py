"""Set mysql charset and collate

Revision ID: 61796506530c
Revises: fc72870a4b48
Create Date: 2022-10-13 17:07:46.823952

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '61796506530c'
down_revision = 'fc72870a4b48'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE etablissements_raw CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")


def downgrade():
    pass
