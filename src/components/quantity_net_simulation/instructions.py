import datetime
from collections import Counter
from typing import Type, Any

from src.components.log_elements.object import Object, Status, BindingFunction, MultisetObject
from src.components.net_elements.object_place import ObjectPlace


# from components.log_elements.Event import Event

class Instruction:

    def __init__(self, time_until_execution: datetime.timedelta):
        self.timedelta = time_until_execution


class InstructionObjectCreation(Instruction):

    def __init__(self, timedelta: datetime.timedelta,
                 object_type: Type[Object] | str,
                 initial_attributes: dict = None,
                 quantities: Counter = None,
                 location: set[ObjectPlace] | None = None,
                 add_to_binding: bool = False,
                 o2o: dict[Object: str] = None):
        super().__init__(time_until_execution=timedelta)
        self.object_type = object_type
        self.initial_attributes = initial_attributes if initial_attributes else {}
        self.initial_quantities = quantities if quantities else Counter()
        self.location = location if location else None
        self.add_to_binding = add_to_binding
        self.o2o = o2o if o2o else dict()

    def __str__(self):
        return f"Object Creation {self.object_type.object_type_name} {self.timedelta}"

    def __repr__(self):
        return f"Object Creation {self.object_type.object_type_name} {self.timedelta}"


class InstructionExecuteEvent(Instruction):

    def __init__(self, time_until_execution: datetime.timedelta,
                 activity: Any,
                 input_binding_function: BindingFunction = None,
                 duration: datetime.timedelta = None):
        super().__init__(time_until_execution=time_until_execution)
        self.activity = activity
        self.input_binding_function: BindingFunction = input_binding_function if input_binding_function else BindingFunction()
        self.event_duration = duration if duration else None
        self._event = None
        self._additional_objects = MultisetObject()
        self._final_binding_function: BindingFunction = BindingFunction()

    def __str__(self):
        return f"Start Event {self.activity.name}"

    def __repr__(self):
        return f"Start Event {self.activity.name}"

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, event: Any):
        self._event = event

    @property
    def additional_objects(self):
        return self._additional_objects

    @property
    def final_binding_function(self):
        return self._final_binding_function

    def add_objects(self, objects: MultisetObject | set):

        if self.event:
            pass
        else:
            raise ValueError("Event has to be created before adding objects.")

        # print(f"Adding object to current binding function, set of additional objects (pre): {self._additional_objects}")
        self._additional_objects.union_update(objects)
        # print(f"Added object {objects} to current binding function, current set of additional objects (post): {self._additional_objects}")

    def create_final_binding_function(self):
        final_binding_function = self.input_binding_function.copy()
        # print(f"Objects to add to final binding function: {self.additional_objects}")

        object_types = {obj.object_type for obj in self.additional_objects}

        for object_type in object_types:
            objects_of_object_type = MultisetObject({obj for obj in self.additional_objects if obj.object_type == object_type})

            final_binding_function[object_type] = objects_of_object_type

        # print("Final binding function: ", final_binding_function)
        self._final_binding_function = final_binding_function


class InstructionTerminateEvent(Instruction):

    def __init__(self, event: Any,
                 execution: Any):
        super().__init__(time_until_execution=event.duration)
        self.event = event
        self.execution = execution

    def __str__(self):
        return f"End Event {self.event.activity.name}"

    def __repr__(self):
        return f"End Event {self.event.activity.name}"


class InstructionObjectStatusUpdate(Instruction):

    def __init__(self, timedelta: datetime.timedelta,
                 object: Object,
                 new_status: Status):
        super().__init__(time_until_execution=timedelta)
        self.object = object
        self.new_status = new_status

    def __str__(self):
        return f"Object Status {self.object.object_type_name}"

    def __repr__(self):
        return f"Object Status {self.object.object_type_name}"


class InstructionObjectAttributeUpdate(Instruction):

    def __init__(self, timedelta: datetime.timedelta, object: Object, attribute_values: dict[str: Any]):
        super().__init__(time_until_execution=timedelta)
        self.object = object
        self.attribute_changes = attribute_values

    def __str__(self):
        return f"Attribute Change {self.object.object_type_name} {self.attribute_changes}"

    def __repr__(self):
        return f"Attribute Change {self.object.object_type_name} {self.attribute_changes}"


class InstructionObjectQuantityUpdate(Instruction):

    def __init__(self, timedelta: datetime.timedelta, object: Object, quantity_changes: Counter):
        super().__init__(time_until_execution=timedelta)
        self.object = object
        self.quantity_changes = quantity_changes

