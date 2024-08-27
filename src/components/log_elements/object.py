import datetime
from collections import Counter
from typing import Type

from multiset import Multiset

from src.components.log_elements.log_element import LogElement


# from components.log_elements.QuantityOperation import ObjectOperation

class Status:
    def __init__(self):
        super().__init__()
        self.status = ...

    def __str__(self):
        return self.status

    def __repr__(self):
        return self.status


class StatusCreated(Status):
    def __init__(self):
        super().__init__()
        self.status = "created"

class StatusActive(Status):

    def __init__(self):
        super().__init__()
        self.status = "active"


class StatusTerminated(Status):

    def __init__(self):
        super().__init__()
        self.status = "terminated"

class StatusInactive(Status):

    def __init__(self):
        super().__init__()
        self.status = "inactive"

def create_object_type(object_type_name: str, default_attribute_values: dict = None, log_object_type: bool = True):
    """Returns an Object-class to create objects based on passed parameters."""

    if default_attribute_values is None:
        default_attribute_values = {}
    else:
        pass

    object_type_name_no_space = object_type_name.replace("_", "").replace(" ", "").replace("-", "")

    # create class as subclass to ObjectType with attributes and default values as passed
    dynamic_class = type(object_type_name_no_space, (Object,), default_attribute_values)
    dynamic_class.object_type_name = object_type_name
    dynamic_class.log_object_type = log_object_type

    def init(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None, **kwargs):

        # set static variables
        Object.__init__(self, timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)

        # define attributes and their default values
        for key, value in default_attribute_values.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

    # set above method as init
    setattr(dynamic_class, '__init__', init)

    return dynamic_class


class Object(LogElement):
    object_count = 0
    default_attributes = {"_id", "_status", "_log_object", "_name", "_label", "_properties", "object_type",
                          "quantities", 'last_change_attributes', 'last_change_quantities', "o2o",
                          "changed_attributes", "object_type_name"}
    object_type_name = ""
    log_object_type = True


    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None):

        super().__init__(name=f"o-{Object.object_count}", label=label, properties=properties)
        self.object_type = type(self)
        self.object_type_name = ""
        self.quantities = quantities if quantities else Counter()
        self.last_change_attributes = timestamp
        self.changed_attributes = []
        self.last_change_quantities = timestamp
        self.o2o = o2o if o2o else dict()
        self._status = StatusCreated()
        self._log_object = type(self).log_object_type

        Object.object_count += 1

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status: Status):
        self._status = status

    @status.setter
    def status(self, status: Status):
        self._status = status

    @property
    def status_active(self):
        if isinstance(self.status, StatusActive):
            return True
        else:
            return False

    @property
    def log_object(self):
        return self._log_object

    @log_object.setter
    def log_object(self, value: bool):
        self._log_object = value

    def change_time_attributes(self, timestamp_of_change: datetime.datetime):
        self.last_change_attributes = timestamp_of_change

    def change_time_quantities(self, timestamp_of_change: datetime.datetime):
        self.last_change_quantities = timestamp_of_change

    def change_object_attributes(self, timestamp_of_change: datetime.datetime, new_attribute_values: dict):
        """Changes attribute values according to passed dict. Documents changes to values."""

        # change attributes in accordance with class attributes
        changed_attributes = []
        for attribute, new_value in new_attribute_values.items():
            if attribute in vars(self) and attribute not in Object.default_attributes:
                setattr(self, attribute, new_value)
                changed_attributes.append(attribute)
            else:
                pass

        # update last changed time
        self.change_time_attributes(timestamp_of_change)
        self.changed_attributes = changed_attributes

    def change_object_quantity(self, timestamp_of_change: datetime.datetime, quantity_operation: Counter):

        if isinstance(quantity_operation, Counter):
            pass
        else:
            raise ValueError("Quantity update must be a Counter object.")

        self.quantities.update(quantity_operation)

        # update last changed time
        self.change_time_quantities(timestamp_of_change)

    def add_o2o_relationship(self, obj: "Object", relationship: str):
        self.o2o[obj] = relationship

    def clear_changed_attributes(self):
        self.changed_attributes = []


class DefaultObject(Object):
    object_type_name = "Default Object"

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None, quantities: Counter = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, o2o=o2o, quantities=quantities)


class MultisetObject(Multiset):
    def __init__(self, iterable=None):
        if iterable is not None:
            for element in iterable:
                if not isinstance(element, Object):
                    raise ValueError("Only Objects can be added to this multiset.")
        super().__init__(iterable)

    def add(self, element, **kwargs):
        if isinstance(element, Object):
            super().add(element)
        else:
            raise ValueError("Only Objects can be added to this multiset.")


class BindingFunction(dict[Type[Object]: MultisetObject]):
    pass
