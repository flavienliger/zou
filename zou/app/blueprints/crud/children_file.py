from zou.app.models.children_file import ChildrenFile
from zou.app.models.entity import Entity
from zou.app.models.project import Project
from zou.app.services import user_service, entities_service
from zou.app.utils import permissions

from .base import BaseModelsResource, BaseModelResource


class ChildrenFilesResource(BaseModelsResource):
    def __init__(self):
        BaseModelResource.__init__(self, ChildrenFile)

    def check_read_permissions(self):
        user_service.block_access_to_vendor()
        return True


class ChildrenFileResource(BaseModelResource):
    def __init__(self):
        BaseModelResource.__init__(self, ChildrenFile)

    def check_read_permissions(self, instance):
        entity = entities_service.get_entity(instance["parent_file"]["entity_id"])
        user_service.check_project_access(entity["project_id"])
        user_service.check_entity_access(entity["id"])
        return True

    def check_update_permissions(self, output_file, data):
        if permissions.has_manager_permissions():
            return True
        return False