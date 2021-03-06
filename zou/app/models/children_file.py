from sqlalchemy.orm import relationship
from sqlalchemy_utils import UUIDType

from zou.app import db
from zou.app.models.serializer import SerializerMixin
from zou.app.models.base import BaseMixin

from sqlalchemy.dialects.postgresql import JSONB


class ChildrenFile(db.Model, BaseMixin, SerializerMixin):
    """
    Describes the generated file based on a output_file, for example a Review/ Proxy.
    """
    __tablename__ = "children_file"

    size = db.Column(db.Integer())
    path = db.Column(db.String(400), unique=True)
    parent_file_id = db.Column(
        UUIDType(binary=False), db.ForeignKey('output_file.id')
    )
    output_type_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("output_type.id"), index=True
    )
    output_type = relationship(
        "OutputType", 
        lazy="joined"
    )
    file_status_id = db.Column(
        UUIDType(binary=False), db.ForeignKey("file_status.id"), nullable=False
    )
    render_info = db.Column(db.String(200))
    file_status = relationship(
        "FileStatus",
        lazy="joined"
    )
    render_info = db.Column(db.String(200))
    data = db.Column(JSONB)
    temporal_entity_id = db.Column(
        UUIDType(binary=False),
        db.ForeignKey("entity.id"),
        default=None,
        nullable=True,
    )
    
    __table_args__ = (
        db.UniqueConstraint(
            "parent_file_id",
            "output_type_id",
            name="children_file_uc",
        ),
    )

    def __repr__(self):
        return "<ChildrenFile %s>" % self.id
