"""Fix etablissements columns collation name

Revision ID: f9d537971656
Revises: 61796506530c
Create Date: 2022-10-20 07:04:43.290940

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f9d537971656'
down_revision = '61796506530c'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(table_name='etablissements_raw',
                    column_name='siret',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='raisonsociale',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='enseigne',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='codenaf',
                    type_=sa.String(length=8, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='numerorue',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='libellerue',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='codecommune',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='codepostal',
                    type_=sa.String(length=8, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='email',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='tel',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='departement',
                    type_=sa.String(length=8, collation='utf8mb4_unicode_ci'),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='trancheeffectif',
                    type_=sa.String(length=2, collation='utf8mb4_unicode_ci'),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='website',
                    type_=sa.String(length=191, collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='social_network',
                    type_=mysql.TINYTEXT(collation='utf8mb4_unicode_ci'),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='email_alternance',
                    type_=mysql.TINYTEXT(collation='utf8mb4_unicode_ci'),
                    server_default='',
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='phone_alternance',
                    type_=mysql.TINYTEXT(collation='utf8mb4_unicode_ci'),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='website_alternance',
                    type_=mysql.TINYTEXT(collation='utf8mb4_unicode_ci'),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='contact_mode',
                    type_=mysql.TINYTEXT(collation='utf8mb4_unicode_ci'),
                    nullable=True)


def downgrade():
    op.alter_column(table_name='etablissements_raw', column_name='siret', type_=sa.String(length=191), nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='raisonsociale',
                    type_=sa.String(length=191),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='enseigne',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw', column_name='codenaf', type_=sa.String(length=8), nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='numerorue',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='libellerue',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='codecommune',
                    type_=sa.String(length=191),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='codepostal',
                    type_=sa.String(length=8),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='email',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='tel',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='departement',
                    type_=sa.String(length=8),
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='trancheeffectif',
                    type_=sa.String(length=2),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='website',
                    type_=sa.String(length=191),
                    server_default='',
                    nullable=False)
    op.alter_column(table_name='etablissements_raw',
                    column_name='social_network',
                    type_=mysql.TINYTEXT(),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='email_alternance',
                    type_=mysql.TINYTEXT(),
                    server_default='',
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='phone_alternance',
                    type_=mysql.TINYTEXT(),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw',
                    column_name='website_alternance',
                    type_=mysql.TINYTEXT(),
                    nullable=True)
    op.alter_column(table_name='etablissements_raw', column_name='contact_mode', type_=mysql.TINYTEXT(), nullable=True)
