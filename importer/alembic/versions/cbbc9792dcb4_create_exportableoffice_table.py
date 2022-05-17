"""create ExportableOffice table

Revision ID: 512434a29bd5
Revises: 
Create Date: 2022-05-11 14:05:08.704348

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '512434a29bd5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('etablissements_raw',
                    sa.Column('siret', sa.String(length=191), nullable=False),
                    sa.Column('raisonsociale', sa.String(length=191), nullable=False),
                    sa.Column('enseigne', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('codenaf', sa.String(length=8), nullable=False),
                    sa.Column('numerorue', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('libellerue', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('codecommune', sa.String(length=191), nullable=False),
                    sa.Column('codepostal', sa.String(length=8), nullable=False),
                    sa.Column('email', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('tel', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('departement', sa.String(length=8), nullable=False),
                    sa.Column('trancheeffectif', sa.String(length=2), nullable=True),
                    sa.Column('website', sa.String(length=191), server_default='', nullable=False),
                    sa.Column('flag_poe_afpr', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('flag_pmsmp', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('social_network', mysql.TINYTEXT(), nullable=True),
                    sa.Column('email_alternance', mysql.TINYTEXT(), server_default='', nullable=True),
                    sa.Column('phone_alternance', mysql.TINYTEXT(), nullable=True),
                    sa.Column('website_alternance', mysql.TINYTEXT(), nullable=True),
                    sa.Column('contact_mode', mysql.TINYTEXT(), nullable=True),
                    sa.Column('flag_alternance', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('flag_junior', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('flag_senior', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('flag_handicap', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.Column('score', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('score_alternance', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('coordinates_x', sa.Float(), nullable=True),
                    sa.Column('coordinates_y', sa.Float(), nullable=True),
                    sa.Column('has_multi_geolocations', sa.Boolean(), server_default=sa.text('false'), nullable=False),
                    sa.PrimaryKeyConstraint('siret')
                    )
    op.create_index('_departement', 'etablissements_raw', ['departement'], unique=False)
    op.create_index('_email', 'etablissements_raw', ['email'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('_email', table_name='etablissements_raw')
    op.drop_index('_departement', table_name='etablissements_raw')
    op.drop_table('etablissements_raw')
    # ### end Alembic commands ###