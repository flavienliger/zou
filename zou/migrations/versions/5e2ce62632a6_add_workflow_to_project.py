"""add workflow to project

Revision ID: 5e2ce62632a6
Revises: c68c2a62cfac
Create Date: 2020-07-14 01:35:24.759248

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
import sqlalchemy_utils
import uuid

# revision identifiers, used by Alembic.
revision = '5e2ce62632a6'
down_revision = 'c68c2a62cfac'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_asset_type_link',
    sa.Column('project_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.Column('asset_type_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.ForeignKeyConstraint(['asset_type_id'], ['entity_type.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('project_id', 'asset_type_id')
    )
    op.create_table('project_task_status_link',
    sa.Column('project_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.Column('task_status_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['task_status_id'], ['task_status.id'], ),
    sa.PrimaryKeyConstraint('project_id', 'task_status_id')
    )
    op.create_table('project_task_type_link',
    sa.Column('project_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.Column('task_type_id', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['task_type_id'], ['task_type.id'], ),
    sa.PrimaryKeyConstraint('project_id', 'task_type_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('project_task_type_link')
    op.drop_table('project_task_status_link')
    op.drop_table('project_asset_type_link')
    # ### end Alembic commands ###
