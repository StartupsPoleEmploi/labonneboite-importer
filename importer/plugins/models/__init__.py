from labonneboite_common.models.office_mixin import FinalOfficeMixin
from sqlalchemy import PrimaryKeyConstraint, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ExportableOffice(FinalOfficeMixin, Base):
    """
    Final output table of the importer jobs, typically storing only 500K offices
    which are selected by the importers jobs as having the highest hiring
    potential amongst all existing 10M offices stored in the raw office table.

    This model is exactly similar to the main Office model, the only difference
    is that they are stored in two different tables.

    When a new dataset built by the importer is deployed, the content of this
    table will replace the content of the main Office table.
    """
    __tablename__ = 'etablissements_raw'

    __table_args__ = (
        PrimaryKeyConstraint('siret'),

        # Improve performance of create_index.py parallel jobs
        # by quickly fetching all offices of any given departement.
        Index('_departement', 'departement'),

        # Improve performance of create_index.py remove_scam_emails()
        # by quickly locating offices having a given scam email.
        Index('_email', 'email'),
    ) + FinalOfficeMixin.__table_args__


# class Geolocation(Base):
#     """
#     cache each full_address <=> coordinates(longitude, latitude) match
#     managed by geocoding process
#     """
#     __tablename__ = "geolocations"
#     full_address = Column(String(191), primary_key=True)
#     x = Column('coordinates_x', Float)  # longitude
#     y = Column('coordinates_y', Float)  # latitude
