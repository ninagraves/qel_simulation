import datetime
from abc import ABC, abstractmethod, update_abstractmethods
from typing import Type

import numpy as np

from qel_simulation.components.log_elements.log_element import LogElement
from qel_simulation.components.log_elements.object import Object, MultisetObject, BindingFunction
from qel_simulation.components.net_elements.collection_point import CollectionCounter
from qel_simulation.components.quantity_net import Execution
from qel_simulation.components.quantity_net_simulation.instructions import Instruction, InstructionObjectCreation

rng = np.random.default_rng(seed=42)


def create_activity(activity_name: str, default_attribute_values: dict = None, log_activity: bool = True):
    """Returns an Object-class to create objects based on passed parameters."""

    def _execute_event_start(self, binding_function: dict[Type[Object]: set[Object]],
                             quantity_state: CollectionCounter = None) -> list[Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        return []

    def create_objects_for_binding(self, input_binding: dict[Type[Object]: set[Object]]) \
            -> list[InstructionObjectCreation]:
        return []

    if default_attribute_values is None:
        default_attribute_values = {}
    else:
        pass

    activity_name_no_space = activity_name.replace("_", "").replace(" ", "").replace("-", "")

    # create class as subclass to ObjectType with attributes and default values as passed
    dynamic_class = type(activity_name_no_space, (Event,), default_attribute_values)
    dynamic_class.activity_name = activity_name
    dynamic_class.log_activity = log_activity



    def init(self, timestamp: datetime.datetime, label: str = None,
             properties: dict = None, duration: datetime.timedelta = None, **kwargs):

        # set static variables
        Event.__init__(self, timestamp=timestamp, label=label, properties=properties, duration=duration)

        # define attributes and their default values
        for key, value in default_attribute_values.items():
            setattr(self, key, value)

        for key, value in kwargs.items():
            setattr(self, key, value)

    # set above method as init
    setattr(dynamic_class, '__init__', init)

    # set abstract methods
    setattr(dynamic_class, '_execute_event_start', _execute_event_start)
    setattr(dynamic_class, '_execute_event_end', _execute_event_end)
    setattr(dynamic_class, 'create_objects_for_binding', create_objects_for_binding)
    update_abstractmethods(dynamic_class)

    return dynamic_class


class Event(LogElement, ABC):
    event_count = 0
    default_attributes = {"activity", "_log_event", "timestamp", "_duration", "_objects", "_event_to_object", "_id",
                          "_name", "_properties", "_label", "_quantity_operations", "activity_name", "triggered"}
    activity_name = ""
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(name=f"ev-{Event.event_count}", label=label, properties=properties)

        self.activity = type(self)
        self.timestamp = timestamp
        self._objects = set()
        self._event_to_object = dict()
        self._quantity_operations = CollectionCounter()
        self._end_timestamp = None
        self._duration = duration if duration else datetime.timedelta()
        self._log_event = type(self).log_activity

        Event.event_count += 1

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({self.activity_name})"

    @property
    def log_event(self):
        return self._log_event

    @log_event.setter
    def log_event(self, log_event: bool):
        self._log_event = log_event

    @property
    def objects(self):
        return self._objects

    def add_object(self, obj: Object):
        self._objects.add(obj)

    @property
    def qualified_relationship(self):
        return self._event_to_object

    @qualified_relationship.setter
    def qualified_relationship(self, e2o_relationships: dict[Object: str]):
        self._event_to_object = e2o_relationships

    @abstractmethod
    def create_objects_for_binding(self, input_binding: BindingFunction) -> list[
        InstructionObjectCreation]:
        """This method is called before the event is executed. If required, redefine this method in the subclass,
        to create any objects that might be required for firing the corresponding transition."""
        ...

    @property
    def quantity_operations(self) -> CollectionCounter:
        return self._quantity_operations

    @quantity_operations.setter
    def quantity_operations(self, quantity_operations: CollectionCounter):
        self._quantity_operations = quantity_operations

    def add_end_timestamp(self, timestamp: datetime.datetime):
        self._end_timestamp = timestamp

    @property
    def duration(self):
        return self._duration

    def add_duration(self, duration: datetime.timedelta):
        self._duration = duration

    @property
    def end_timestamp(self):
        return self._end_timestamp

    def start_event(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[Instruction]:

        # set event to object relationship
        for obj in MultisetObject().union(*binding_function.values()):
            self.add_object(obj)

        instructions_start_event = self._execute_event_start(binding_function=binding_function,
                                                             quantity_state=quantity_state)

        return instructions_start_event

    def end_event(self, execution: Execution):

        # validity check: no E2O changes
        objects = MultisetObject().union(*execution.transition_execution.binding_function.values())

        if self.objects.issubset(objects) and objects.issubset(self.objects):
            pass
        else:
            raise ValueError("Binding function used to terminate event does not contain the same objects "
                             "as the one used to initiate the event.")

        # set collected quantity operations
        self.quantity_operations = execution.transition_execution.collected_quantity_operations

        # end event
        instructions_end_event = self._execute_event_end(execution=execution)

        return instructions_end_event

    @abstractmethod
    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[Instruction]:
        ...

    @abstractmethod
    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        ...

    def draw_from_normal_distribution(self, mean: float, std: float):
        return rng.normal(loc=mean, scale=std)

    def draw_from_uniform_distribution(self, min: float, max: float):
        return rng.uniform(low=min, high=max)



class DefaultEvent(Event):
    activity_name = "Default Activity"
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=duration)

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        return []

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        return []
