from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType

from zou.app import db
from zou.app.models.serializer import OutputFileSerializer
from zou.app.models.base import BaseMixin

from sqlalchemy.dialects.postgresql import JSONB


dependent_table = db.Table(
    "dependent_link", 
    db.Column(
        "output_file_id",
        UUIDType(binary=False),
        db.ForeignKey("output_file.id"),
        nullable=False
    ),
    db.Column(
        "dependent_file_id",
        UUIDType(binary=False),
        db.ForeignKey("dependent_file.id"),
        primary_key=True,
    )
)


class OutputFile(db.Model, BaseMixin, OutputFileSerializer):
    """
    Describe a file generated from a CG artist scene. It's the result of a
    publication.
    It is linked to a working/ children/ dependent file, an entity and a task type.
    """
    __tablename__ = "output_file"

    shotgun_id = db.Column(db.String(50))

    name = db.Column(db.String(250), nullable=False)
    canceled = db.Column(db.Boolean(), default=False, nullable=False) # surement une forme d'"omit"
    size = db.Column(db.Integer())
    checksum = db.Column(db.String(32))
    description = db.Column(db.Text())
    comment = db.Column(db.Text())
    extension = db.Column(db.String(10))
    revision = db.Column(db.Integer(), nullable=False) # version
    representation = db.Column(db.String(20), index=True) # une manière de regrouper (ex: par extension)
    nb_elements = db.Column(db.Integer(), default=1) # à refaire, pas de start-end
    source = db.Column(db.String(40)) # permet de dire d'où ça vient (ex: muster)
    path = db.Column(db.String(400))
    data = db.Column(JSONB)

    file_status_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("file_status.id"), nullable=False
    )
    entity_id = db.Column(UUIDType(binary=False), db.ForeignKey("entity.id"))
    asset_instance_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("asset_instance.id"), index=True
    )
    output_type_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("output_type.id"), index=True
    )
    task_type_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("task_type.id"), index=True
    )
    person_id = db.Column(UUIDType(binary=False), db.ForeignKey("person.id"))
    render_info = db.Column(db.String(200))
    source_file_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("working_file.id")
    )
    render_info = db.Column(db.String(200))
    source_file = relationship(
        "WorkingFile", 
        lazy="joined", 
        back_populates="outputs"
    )
    children_files = relationship(
        "ChildrenFile", 
        lazy="joined", 
        backref="parent_file"
    )
    # TODO: by default not serialize it
    dependent_files = relationship(
        "DependentFile",
        secondary=dependent_table,
        back_populates="used_by"
    )
    temporal_entity_id = db.Column(
        UUIDType(binary=False),
        db.ForeignKey("entity.id"),
        default=None,
        nullable=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "name",
            "entity_id",
            "asset_instance_id",
            "output_type_id",
            "task_type_id",
            "temporal_entity_id",
            "representation",
            "revision",
            name="output_file_uc",
        ),
    )

    def __repr__(self):
        return "<OutputFile %s>" % self.id
