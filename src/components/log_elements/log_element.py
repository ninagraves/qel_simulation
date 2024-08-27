import uuid
from abc import ABC


class LogElement(ABC):

    def __init__(self, name: any = None, label: str = None, properties: dict = None):
        self._id = uuid.uuid4()
        self._name = name if name else self.id
        self._label = label if label else None
        self._properties = properties if properties else None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({type(self).__name__})"

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def properties(self):
        return self._properties

    @id.setter
    def id(self, id):
        self._id = id

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label

    @properties.setter
    def properties(self, properties):
        self._properties = properties
