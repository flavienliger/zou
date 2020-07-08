from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType

from zou.app import db
from zou.app.models.serializer import SerializerMixin
from zou.app.models.base import BaseMixin
from zou.app.models.output_file import dependent_table

from sqlalchemy.dialects.postgresql import JSONB


class DependentFile(db.Model, BaseMixin, SerializerMixin):
    """
    Describe a file generated from a CG artist scene. 
    It aims to know the dependencies of an outputfile.
    """
    __tablename__ = "dependent_file"
    source_output_file_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("output_file.id"), nullable=True
    )
    size = db.Column(db.Integer())
    checksum = db.Column(db.String(32))
    extension = db.Column(db.String(10))
    path = db.Column(db.String(400), unique=True)
    used_by = relationship(
        "OutputFile", secondary=dependent_table, back_populates="dependent_files"
    )
    project_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("project.id")
    )
    temporal_entity_id = db.Column(
        UUIDType(binary=False),
        db.ForeignKey("entity.id"),
        default=None,
        nullable=True,
    )

    def __repr__(self):
        return "<DependentFile %s>" % self.id
