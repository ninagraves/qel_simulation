import datetime
from collections import Counter
from typing import Type

from qel_simulation.simulation.event import Event
from qel_simulation.simulation.object import Object, Status
from qel_simulation.qnet_elements.object_place import ObjectPlace
from qel_simulation.simulation.instructions import (InstructionExecuteEvent, InstructionObjectCreation,
                                                    Instruction, InstructionTerminateEvent,
                                                    InstructionObjectStatusUpdate,
                                                    InstructionObjectQuantityUpdate,
                                                    InstructionObjectAttributeUpdate)
from qel_simulation.simulation.queue_config import QueueConfig


class ScheduleType(str):

        def __init__(self):
            super().__init__()
            self.schedule_type = ...

        def __str__(self):
            return self.schedule_type

        def __repr__(self):
            return self.schedule_type

class ScheduleTypeFixed(ScheduleType):
    def __init__(self):
        super().__init__()
        self.schedule_type = "fixed"

class ScheduleTypeArrivalRate(ScheduleType):
    def __init__(self):
        super().__init__()
        self.schedule_type = "arrival_rate"


class QueueItem:

    def __init__(self, execution_time: datetime.datetime):
        self.execution_time = execution_time

class EndEvent(QueueItem):

    def __init__(self, execution_time: datetime.datetime,
                 event: Event,
                 execution):
        super().__init__(execution_time)
        self.event = event
        self.execution = execution

    def __str__(self):
        return f"End Event '{self.event.activity.activity_name}'"

    def __repr__(self):
        return f"End Event '{self.event.activity.activity_name}'"

class StartEvent(QueueItem):

    def __init__(self, execution_time: datetime.datetime,
                 activity: Type[Event],
                 input_binding: dict[Type[Object]: set[Object]],
                 event_duration: datetime.timedelta = None):
        super().__init__(execution_time)
        self.activity = activity
        self.input_binding = input_binding
        self.event_duration = event_duration

    def __str__(self):
        return f"Start Event '{self.activity.activity_name}'"

    def __repr__(self):
        return f"Start Event '{self.activity.activity_name}'"


class ObjectCreation(QueueItem):

        def __init__(self, execution_time: datetime.datetime, object_type: Type[Object] | str, initial_attributes: dict = None,
                     quantities: Counter = None, location: set[ObjectPlace] | set[str] = None, add_to_binding: bool = False,
                     schedule_type: ScheduleType = None, o2o: dict[Object: str] = None):
            super().__init__(execution_time)
            self.object_type = object_type
            self.initial_attributes = initial_attributes if initial_attributes else {}
            self.initial_quantities = quantities if quantities else Counter()
            self.o2o = o2o if o2o else {}
            self.location = location if location else None
            self.add_to_binding = add_to_binding if add_to_binding else False
            self.schedule_type = schedule_type

        def __str__(self):
            return f"Object Creation '{self.object_type.object_type_name}'"

        def __repr__(self):
            return f"Object Creation '{self.object_type.object_type_name}'"

class ObjectAttributeChange(QueueItem):
    """Entry defining the changing of object attributes at specified time."""

    def __init__(self, execution_time: datetime.datetime, object: Object, attribute_changes: dict):
        super().__init__(execution_time)
        self.object = object
        self.attribute_changes = attribute_changes

    def __str__(self):
        return f"Attribute Change '{self.object}': {self.attribute_changes}"

    def __repr__(self):
        return f"Attribute Change '{self.object}': {self.attribute_changes}"

class ObjectQuantityChange(QueueItem):
    """Entry defining the changing of object quantities at specified time."""

    def __init__(self, execution_time: datetime.datetime, object: Object, quantity_changes: Counter):
        super().__init__(execution_time)
        self.object = object
        self.quantity_changes = quantity_changes

class ObjectStatusChange(QueueItem):
    """Entry defining the changing of object status at specified time."""

    def __init__(self, execution_time: datetime.datetime, object: Object, status: Status):
        super().__init__(execution_time)
        self.object = object
        self.status = status

    def __str__(self):
        return f"Object Status -> {self.status} '{self.object}'"

    def __repr__(self):
        return f"Object Status -> {self.status} '{self.object}'"


class ExecutionQueue:

    def __init__(self, config: QueueConfig):
        self._queue = []
        self.config: QueueConfig = config
        self._current_time = self.config.initial_time


    @property
    def time(self):
        return self._current_time

    @property
    def queue(self):
        return sorted(self._queue, key=lambda x: x.execution_time)

    def add_entry_to_queue(self, queue_item: QueueItem):
        # time_new_item = queue_item.execution_time
        # if time_new_item in self.get_all_execution_times_in_queue():
        #     time_new_item += datetime.timedelta(seconds=uniform(1, 600))
        #     queue_item.execution_time = time_new_item
        self._queue.append(queue_item)

    def update_time(self):
        self._current_time = min([item.execution_time for item in self._queue]) if self._queue else self._current_time

    def get_current_items(self) -> set[QueueItem]:
        relevant_items = {item for item in self._queue if item.execution_time == self.time}
        return relevant_items

    def get_and_remove_current_items(self) -> set[QueueItem]:
        items = self.get_current_items()
        self.remove_items_from_queue(items)
        return items

    # def get_and_remove_current_object_creations(self) -> set[ObjectCreation]:
    #     items = self.get_current_items()
    #     object_creations = {item for item in items if isinstance(item, ObjectCreation)}
    #     self.remove_items_from_queue(object_creations)
    #     return object_creations

    def remove_items_from_queue(self, items: set[QueueItem]):
        self._queue = list(set(self._queue) - items)

    def determine_timestamp_from_duration(self, duration: datetime.timedelta) -> datetime.datetime:
        return self.time + duration

    def add_object_creation(self, object_creation: InstructionObjectCreation, schedule_type: ScheduleType = None):

        qitem = self.transform_object_creation_instruction_to_queue_item(object_creation)

        if isinstance(schedule_type, ScheduleType):
            qitem.schedule_type = schedule_type
        else:
            pass

        self.add_entry_to_queue(qitem)

    def transform_object_creation_instruction_to_queue_item(self, object_creation: InstructionObjectCreation) -> ObjectCreation:

        execution_timestamp = self.determine_timestamp_from_duration(object_creation.timedelta)

        qitem = ObjectCreation(execution_time=execution_timestamp,
                               object_type=object_creation.object_type,
                               initial_attributes=object_creation.initial_attributes,
                               quantities=object_creation.initial_quantities,
                               location=object_creation.location,
                               add_to_binding=object_creation.add_to_binding,
                               o2o=object_creation.o2o)

        return qitem

    def add_event_start(self, event_instruction: InstructionExecuteEvent):

        qitem = self.transform_event_start_instruction_to_queue_item(event_instruction)

        self.add_entry_to_queue(qitem)

    def transform_event_start_instruction_to_queue_item(self, event_instruction: InstructionExecuteEvent) -> StartEvent:

        execution_timestamp = self.determine_timestamp_from_duration(event_instruction.timedelta)

        qitem = StartEvent(execution_time=execution_timestamp,
                           activity=event_instruction.activity,
                           input_binding=event_instruction.input_binding_function,
                           event_duration=event_instruction.event_duration)

        return qitem

    def add_end_queue_item(self, termination_instruction: InstructionTerminateEvent):

        execution_timestamp = self.determine_timestamp_from_duration(duration=termination_instruction.timedelta)

        qitem = EndEvent(execution_time=execution_timestamp,
                         event=termination_instruction.event,
                         execution=termination_instruction.execution)

        self.add_entry_to_queue(qitem)

    # def get_and_remove_current_event_starts(self) -> set[StartEvent]:
    #     items = self.get_current_items()
    #     event_starts = {item for item in items if isinstance(item, StartEvent)}
    #     self.remove_items_from_queue(event_starts)
    #     return event_starts

    def add_instruction(self, instruction: Instruction, schedule_type: ScheduleType = None):

        if isinstance(instruction, InstructionExecuteEvent):
            self.add_event_start(instruction)
        elif isinstance(instruction, InstructionObjectCreation):
            self.add_object_creation(instruction, schedule_type=schedule_type)
        elif isinstance(instruction, InstructionTerminateEvent):
            self.add_end_queue_item(instruction)
        elif isinstance(instruction, InstructionObjectStatusUpdate):
            self.add_status_change_item(instruction)
        elif isinstance(instruction, InstructionObjectAttributeUpdate):
            self.add_attribute_change_item(instruction)
        elif isinstance(instruction, InstructionObjectQuantityUpdate):
            self.add_quantity_change_item(instruction)
        else:
            raise ValueError("Instruction type not supported.")

    def add_status_change_item(self, instruction: InstructionObjectStatusUpdate):

        execution_timestamp = self.determine_timestamp_from_duration(duration=instruction.timedelta)
        item = ObjectStatusChange(execution_time=execution_timestamp, object=instruction.object,
                                  status=instruction.new_status)
        self.add_entry_to_queue(item)

    def add_attribute_change_item(self, instruction: InstructionObjectAttributeUpdate):

        execution_timestamp = self.determine_timestamp_from_duration(duration=instruction.timedelta)
        item = ObjectAttributeChange(execution_time=execution_timestamp, object=instruction.object,
                                  attribute_changes=instruction.attribute_changes)
        self.add_entry_to_queue(item)

    def add_quantity_change_item(self, instruction: InstructionObjectQuantityUpdate):

        execution_timestamp = self.determine_timestamp_from_duration(duration=instruction.timedelta)
        item = ObjectQuantityChange(execution_time=execution_timestamp, object=instruction.object,
                                    quantity_changes=instruction.quantity_changes)
        self.add_entry_to_queue(item)

    def get_all_execution_times_in_queue(self) -> set[datetime.datetime]:
        return {item.execution_time for item in self.queue}


