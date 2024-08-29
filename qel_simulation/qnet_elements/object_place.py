from typing import Type

from qel_simulation.simulation.object import Object, DefaultObject, MultisetObject
from qel_simulation.qnet_elements.place import Place


class ObjectPlace(Place):
    def __init__(self, name, object_type: Type = None, label: str = None,
                 properties: dict = None):

        super().__init__(name=name, label=label, properties=properties)

        self._object_type = object_type if object_type else DefaultObject
        self._marking = MultisetObject()

    def __repr__(self):
        return f"{self.name} ({self._object_type.__name__})"

    @property
    def object_type(self):
        return self._object_type

    @object_type.setter
    def object_type(self, object_type: Type[Object]):
        self._object_type = object_type

    def add_token(self, obj: Object):
        # make sure passed element is an object of the correct type
        if isinstance(obj, self.object_type):
            self._marking.add(obj)
        else:
            raise ValueError(f"Variable passed to changes marking of ObjectPlace is not an object of the correct type.")

    def remove_token(self, obj: Object):
        # remove element if it exists in marking
        if obj in self.marking:
            self._marking.remove(obj)
        else:
            raise ValueError(f"Passed object is not part of place's marking.")

    def remove_tokens(self, objs: set[Object]):
        for obj in objs:
            self.remove_token(obj)

    def add_tokens(self, objs: set[Object]):
        for obj in objs:
            self.add_token(obj)
