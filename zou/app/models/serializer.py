from sqlalchemy.inspection import inspect
from sqlalchemy.orm.collections import InstrumentedList
from zou.app.utils.fields import serialize_value


class SerializerMixin(object):
    """
    Helpers to facilitate JSON serialization of models.
    """

    def is_join(self, attr):
        return isinstance(getattr(self, attr), InstrumentedList)

    def serialize(self, obj_type=None, relations=False, ignores=[]):
        attrs = inspect(self).attrs.keys()
        attrs = [attr for attr in attrs if attr not in ignores]
        obj_dict = {}

        if relations:
            for attr in attrs:
                current = getattr(self, attr)
                if type(current) == InstrumentedList:
                    obj_dict[attr] = [el.serialize() for el in current]
                else:
                    obj_dict[attr] = serialize_value(current)
        else:
            obj_dict = {
                attr: serialize_value(getattr(self, attr))
                for attr in attrs
                if not self.is_join(attr)
            }
        obj_dict["type"] = obj_type or type(self).__name__
        return obj_dict

    @staticmethod
    def serialize_list(models, obj_type=None, relations=False):
        return [
            model.serialize(obj_type=obj_type, relations=relations)
            for model in models
        ]


class OutputFileSerializer(object):
    """
    Helpers to JSON serialization of OutputFile with ignore some fields.
    """

    def is_join(self, attr):
        return isinstance(getattr(self, attr), InstrumentedList)
        
    def serialize(self, obj_type=None, relations=False):
        attrs = inspect(self).attrs.keys()
        obj_dict = {}

        if relations:
            for attr in attrs:
                current = getattr(self, attr)
                if type(current) == InstrumentedList:
                    ignores = []
                    if attr == "children_files":
                        ignores = ["parent_file"]
                    obj_dict[attr] = [el.serialize(ignores=ignores) for el in current]
                else:
                    obj_dict[attr] = serialize_value(current)
        else:
            obj_dict = {
                attr: serialize_value(getattr(self, attr))
                for attr in attrs
                if not self.is_join(attr) and attr != "source_file"
            }
        obj_dict["type"] = obj_type or type(self).__name__
        return obj_dict