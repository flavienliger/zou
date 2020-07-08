from zou.app.models.dependent_file import DependentFile
from zou.app.services import user_service, entities_service
from zou.app.utils import permissions

from .base import BaseModelsResource, BaseModelResource


class DependentFilesResource(BaseModelsResource):
    def __init__(self):
        BaseModelResource.__init__(self, DependentFile)

    def check_read_permissions(self):
        user_service.block_access_to_vendor()
        return True


class DependentFileResource(BaseModelResource):
    def __init__(self):
        BaseModelResource.__init__(self, DependentFile)

    def check_read_permissions(self, instance):
        if instance["project_id"]:
            user_service.check_project_access(instance["project_id"])
        user_service.block_access_to_vendor()
        return True
