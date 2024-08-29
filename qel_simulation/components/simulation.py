import datetime
from collections import Counter
from typing import Type

import numpy as np
import pandas as pd

from qel_simulation.components.base_element import BaseElement
from qel_simulation.components.log_elements.event import Event
from qel_simulation.components.log_elements.object import Object, StatusActive, StatusInactive, StatusTerminated, Status, \
    BindingFunction, MultisetObject
from qel_simulation.components.quantity_net_simulation.execution_queue import (ExecutionQueue, ObjectCreation, ObjectQuantityChange,
                                                                    ObjectAttributeChange, EndEvent, StartEvent,
                                                                    ObjectStatusChange, ScheduleTypeFixed,
                                                                    ScheduleTypeArrivalRate, ScheduleType)
from qel_simulation.components.quantity_net_simulation.instructions import (InstructionObjectCreation, InstructionExecuteEvent,
                                                                 InstructionTerminateEvent)
from qel_simulation.components.quantity_net_simulation.quantity_net_execution import QuantityNetExecution
from qel_simulation.components.quantity_net_simulation.simulation_config import SimulationConfig
from qel_simulation.components.quantity_net_simulation.triggers import NetElementTrigger, MultiTrigger


class Simulation(BaseElement):

    def __init__(self, name: str, config: SimulationConfig, label: str = None,
                 properties: dict = None):

        super().__init__(name=name, label=label, properties=properties)
        self.config = config
        self.execution = QuantityNetExecution(name=f"{name}_execution", qnet_config=config.qnet_config)
        self.queue = ExecutionQueue(self.config.queue_config)
        self.object_overview = []
        self.event_overview = []
        self.rng = np.random.default_rng(seed=self.config.random_seed)
        self._step_counter = 0

        self.register_and_add_objects_from_config()
        self.set_initial_marking_collection_points()
        self.update_duration_specifications_in_config()
        self.update_frequent_object_creations_in_config()
        self.update_triggered_object_creation_in_config()
        self.update_activity_priorities_in_config()
        self.execute_initial_schedules()

    @property
    def activities(self):
        return self.execution.activities

    @property
    def step_counter(self):
        return self._step_counter

    @property
    def object_types(self):
        return self.execution.object_types

    @property
    def state(self):
        return self.execution.state

    @property
    def terminated_objects(self):
        return {obj for obj in self.object_overview if isinstance(obj.status, StatusTerminated)}

    def get_terminated_objects_of_type(self, object_type: Type[Object]):
        return {obj for obj in self.terminated_objects
                if isinstance(obj, self.execution.identify_object_type(object_type_name=object_type))}

    def register_and_add_objects_from_config(self):
        self.add_provided_objects_to_model()
        self.add_provided_specified_location_objects_to_model()
        required_objects = self.get_initial_number_of_required_objects_per_type()
        self.add_number_of_objects_to_net_according_to_config(objects_per_type=required_objects)

    def set_initial_marking_collection_points(self):
        self.execution.set_initial_marking_collection_points()

    def get_initial_number_of_required_objects_per_type(self):

        required_objects_per_types = self.execution.get_number_required_objects_per_type()
        objects_of_type = {}

        for object_type, number in required_objects_per_types.items():
            objects_of_type[object_type] = self.create_required_number_of_objects(object_type=object_type,
                                                                                  requested_objects=number)

        return objects_of_type

    def add_number_of_objects_to_net_according_to_config(self, objects_per_type: dict[Type[Object]: set[Object]]):

        self.execution.add_number_of_objects_to_net_according_to_config(objects_per_type=objects_per_type)

    def create_required_number_of_objects(self, object_type: Type[Object], requested_objects: int = 1) -> set[Object]:
        """Pass object type and receive logged object of this type"""

        if object_type in self.object_types:
            pass
        else:
            raise ValueError(f"Object you are trying to create is not of a type associated with the simulation model.")

        objects = set()
        for i in np.arange(requested_objects):
            qitem = ObjectCreation(execution_time=self.queue.time, object_type=object_type)
            obj = self.create_object(qitem)
            objects.add(obj)

        return objects

    def create_object(self, object_creation: ObjectCreation) -> Object:
        """Pass object type and receive logged object of this type"""

        if isinstance(object_creation.object_type, str):
            object_type = self.execution.identify_object_type(object_type_name=object_creation.object_type)
            object_creation.object_type = object_type
        else:
            pass

        if object_creation.object_type in self.object_types:
            pass
        else:
            raise ValueError(f"Object you are trying to create is not of a type associated with the simulation model.")

        if object_creation.execution_time == self.queue.time:
            pass
        else:
            raise ValueError("Object creation has to be scheduled for the current time.")

        obj = object_creation.object_type(timestamp=self.queue.time, quantities=object_creation.initial_quantities,
                                          o2o=object_creation.o2o, **object_creation.initial_attributes)
        self._register_object(object_to_add=obj)

        return obj

    def add_provided_objects_to_model(self):

        # get provided objects from execution
        provided_objects = self.execution.provided_initial_objects()

        # add objects to active objects
        self._register_objects(objects_to_add=provided_objects)

        # add objects to execution
        self.pass_objects_to_add_to_initial_places(objects_per_type=provided_objects)

    def add_provided_specified_location_objects_to_model(self):

        provided_objects = self.execution.provided_objects_specified_places()

        # add objects to active objects
        self._register_objects(objects_to_add=provided_objects)

        # add objects to execution considering the specification in configuration
        self.execution.add_object_to_specified_places_according_to_config(objects_per_type=provided_objects)

    def _register_objects(self, objects_to_add: dict[Type[Object]: set[Object]]):

        for obj in set().union(*objects_to_add.values()):
            self._register_object(object_to_add=obj)

    def _register_object(self, object_to_add: Object):

        self.ensure_object_timestamp_in_accordance_with_simulation_model(obj=object_to_add)

        self.object_overview.append(object_to_add)

    def ensure_object_timestamp_in_accordance_with_simulation_model(self, obj: Object):
        if obj.last_change_attributes > self.queue.time:
            obj.last_change_attributes = self.queue.time
        else:
            pass

        if obj.last_change_quantities > self.queue.time:
            obj.last_change_quantities = self.queue.time
        else:
            pass

    def pass_objects_to_add_to_initial_places(self, objects_per_type: dict[Type[Object]: set[Object]]):
        self.execution.add_objects_to_initial_places(objects_per_type=objects_per_type)

    def execute_steps(self, steps: int):
        """Executes the specified number of time steps."""
        for i in np.arange(steps):
            self.execute_simulation_step()

    def execute_until_number_terminated(self, terminated_objects: int):
        """Executes time steps until the specified number of objects have been terminated."""
        while len(self.terminated_objects) < terminated_objects:
            self.execute_simulation_step()

    def execute_until_time(self, time: datetime.datetime):
        """Executes time steps until the specified time."""
        while self.queue.time < time:
            self.execute_simulation_step()

    def execute_until_number_terminated_object_type(self, object_type: Type[Object], terminated_objects: int):
        """Executes time steps until the specified number of objects of the specified type have been terminated."""
        while len(self.get_terminated_objects_of_type(object_type=object_type)) < terminated_objects:
            self.execute_simulation_step()

    def get_enabled_activity_bindings(self) -> dict[Type[Event]: list[None] | list[dict[Type[Object]: set[Object]]]]:
        """Returns all activity-object combinations that are enabled according to the current state of the quantity net.
        Does not take only object outputs into account."""

        # get all enabled activity bindings
        enabled_bindings = self.execution.get_enabled_activities()

        return enabled_bindings

    def set_object_status_active(self, obj: Object):
        obj.status = StatusActive()

    def set_object_status_inactive(self, obj: Object):
        obj.status = StatusInactive()

    def get_enabled_non_silent_activity_bindings(self):

        all_activities = self.get_enabled_activity_bindings()

        # filter so only non-silent activities are included
        non_silent_bindings = {activity: bindings for activity, bindings in all_activities.items()
                               if activity.log_activity}

        return non_silent_bindings

    def select_enabled_activity(self, enabled_activities: list[Type[Event]]) -> Type[Event]:
        """Selects an activity from the set of enabled activities."""

        prioritised_activity = self.select_prioritised_activity(enabled_activities=enabled_activities)
        if prioritised_activity:
            return prioritised_activity
        else:
            pass

        selected_activity = self.rng.choice(a=np.array(enabled_activities))

        return selected_activity

    def select_prioritised_activity(self, enabled_activities: list[Type[Event]]) -> Type[Event] | None:
        """Selects an activity from the set of enabled activities."""

        # check if at least one prioritised activity is enabled
        if set(enabled_activities).intersection(self.config.activity_priority):
            pass
        else:
            return None

        # draw if priority is considered
        if self.rng.choice(a=[True, False], p=[self.config.priority_probability, 1 - self.config.priority_probability]):
            pass
        else:
            # print("Don't select prioritised activity.")
            return None

        for activity in self.config.activity_priority:
            if activity in enabled_activities:
                selected_activity = activity
                # print("Selected prioritised activity.")
                return selected_activity
            else:
                continue
        # print("Don't select prioritised activity.")
        return None

    def select_enabled_activity_binding(self, enabled_bindings: list[BindingFunction]) \
            -> dict[Type[Object]: set[Object]]:
        """Selects an activity from the set of enabled activities."""
        if enabled_bindings:
            selected_binding = self.rng.choice(a=np.array(enabled_bindings))
        else:
            selected_binding = BindingFunction()
        return selected_binding

    def select_enabled_binding(self):

        # get all enabled bindings
        enabled_bindings = self.get_enabled_activity_bindings()
        if enabled_bindings:
            pass
        else:
            return

        # select activity at random
        selected_activity = self.select_enabled_activity(enabled_activities=list(enabled_bindings.keys()))

        # select binding at random
        possible_bindings = enabled_bindings[selected_activity]
        selected_binding = self.select_enabled_activity_binding(enabled_bindings=possible_bindings)

        execution = InstructionExecuteEvent(time_until_execution=datetime.timedelta(0),
                                            activity=selected_activity,
                                            input_binding_function=selected_binding)

        self.queue.add_instruction(instruction=execution)

    def prepare_event_execution(self, start_event_item: StartEvent) -> InstructionExecuteEvent:

        if self.queue.time == start_event_item.execution_time:
            pass
        else:
            raise ValueError("Event execution time does not match current time.")

        event_instruction = InstructionExecuteEvent(time_until_execution=datetime.timedelta(0),
                                                    activity=start_event_item.activity,
                                                    input_binding_function=start_event_item.input_binding,
                                                    duration=start_event_item.event_duration)

        # create event
        event = start_event_item.activity(timestamp=self.queue.time, duration=start_event_item.event_duration)

        # add event to overview
        self.add_event_to_overview(event=event)

        # update duration according to config specifications
        if event.duration == datetime.timedelta(0):
            new_duration = self.get_specified_duration(activity=start_event_item.activity)
            event.add_duration(new_duration)
        else:
            pass

        # add event to instruction
        event_instruction.event = event

        # execute function for potential object creations
        creation_instructions = event.create_objects_for_binding(input_binding=start_event_item.input_binding)

        # create queue items for object creations and add to instruction
        for instruction in creation_instructions:
            if isinstance(instruction, InstructionObjectCreation):
                pass
            else:
                raise ValueError("Method to create object creation instructions returned at least one "
                                 "non-object-creation-instruction.")

            if instruction.add_to_binding:
                pass
            else:
                raise ValueError("If object should be used in binding for event, add_to_binding has to be True. "
                                 "Please note that the method 'create_objects_for_binding' is only for the creation of "
                                 "objects that should be added to the binding. Any other objects that should be created "
                                 "in connection with this event should be added in 'execute_event_start' or "
                                 "'execute_event_end'.")

            if instruction.timedelta == datetime.timedelta(0):
                pass
            else:
                raise ValueError("If object should be used in binding for event, timedelta has to be 0. "
                                 "If the log should show the creation at a later point in time, "
                                 "add an empty attribute change for any time during the execution time of event, "
                                 "as logging only happens after events have been completed.")

            # transform instruction to q item
            qitem = self.queue.transform_object_creation_instruction_to_queue_item(object_creation=instruction)

            # create object
            obj = self.create_object(object_creation=qitem)

            # add to event instruction
            event_instruction.add_objects(MultisetObject([obj]))

        # ensure binding is valid
        self.add_missing_objects_to_execution(event_execution_instruction=event_instruction)

        # create final binding for event execution
        event_instruction.create_final_binding_function()

        return event_instruction

    def add_event_to_overview(self, event: Event):
        self.event_overview.append(event)

    def execute_simulation_step(self):

        # check for triggered object creations
        self.execute_triggered_object_creations()

        # select enabled binding from current state and begin executing and adding timestamps to the queue
        self.select_enabled_binding()

        # execute an instruction from the queue
        self.execute_next_queue_instructions()

        # update time
        self.queue.update_time()

        # increase step counter
        self._step_counter += 1

    def execute_next_queue_instructions(self):
        execution_items = self.queue.get_and_remove_current_items()

        # print("Execution items: ", execution_items)

        for item in execution_items:
            # print(f"Executed Queue Item: {item}")
            if isinstance(item, ObjectCreation):
                self.execute_object_creation(object_creation=item)
            elif isinstance(item, StartEvent):
                self.execute_event(start_event=item)
            elif isinstance(item, EndEvent):
                self.execute_event_termination(event_ending=item)
            elif isinstance(item, ObjectStatusChange):
                self.execute_object_status_update(object_status_update=item)
            elif isinstance(item, ObjectAttributeChange):
                self.execute_object_attribute_update(object_attribute_update=item)
            elif isinstance(item, ObjectQuantityChange):
                self.execute_object_quantity_update(object_quantity_update=item)
            else:
                raise ValueError("Queue item is of unknown type.")

    def execute_object_status_update(self, object_status_update: ObjectStatusChange):

        if self.queue.time == object_status_update.execution_time:
            pass
        else:
            raise ValueError("Object status update time does not match current time.")

        # get object
        obj = self._identify_object(obj=object_status_update.object)

        if isinstance(object_status_update.status, Status):
            pass
        else:
            raise ValueError("New object status has to be of type Status.")

        # update object status
        obj.status = object_status_update.status

    def execute_object_attribute_update(self, object_attribute_update: ObjectAttributeChange):

        if self.queue.time == object_attribute_update.execution_time:
            pass
        else:
            raise ValueError("Object attribute update time does not match current time.")

        # get object
        obj = self._identify_object(obj=object_attribute_update.object)

        # update object attributes
        obj.change_object_attributes(timestamp_of_change=self.queue.time,
                                     new_attribute_values=object_attribute_update.attribute_changes)

        self.execution.log_object(obj=obj)

    def execute_object_quantity_update(self, object_quantity_update: ObjectQuantityChange):

        if self.queue.time == object_quantity_update.execution_time:
            pass
        else:
            raise ValueError("Object quantity update time does not match current time.")

        # get object
        obj = self._identify_object(obj=object_quantity_update.object)

        # update object quantities
        obj.change_object_quantity(timestamp_of_change=self.queue.time,
                                   quantity_operation=object_quantity_update.quantity_changes)

        self.execution.log_object(obj=obj)

    def execute_event(self, start_event: StartEvent):

        # get event instruction with valid binding
        event_instruction = self.prepare_event_execution(start_event_item=start_event)

        # execute event in model
        returned_instructions = self.execution.execute_event_start(event_instruction=event_instruction)

        # define variable to check if some instructions should be executed immediately
        execute_now = False

        # add all instructions to queue
        for instruction in returned_instructions:
            if instruction.timedelta == datetime.timedelta(0):
                execute_now = True
            else:
                pass
            self.queue.add_instruction(instruction=instruction)

        # execute instructions that should be executed immediately
        if execute_now:
            self.execute_next_queue_instructions()
        else:
            pass

    def execute_event_termination(self, event_ending: EndEvent):

        if self.queue.time == event_ending.execution_time:
            pass
        else:
            raise ValueError("Event termination time does not match current time.")

        # set end timestamp
        event_ending.event.add_end_timestamp(timestamp=self.queue.time)

        # create termination instruction
        termination_instruction = InstructionTerminateEvent(event=event_ending.event,
                                                            execution=event_ending.execution)

        # execute event termination in model
        returned_instructions = self.execution.execute_event_termination(termination=termination_instruction)

        # define variable to check if some instructions should be executed immediately
        execute_now = False

        # add all instructions to queue
        for instruction in returned_instructions:
            if instruction.timedelta == datetime.timedelta(0):
                execute_now = True
            else:
                pass
            self.queue.add_instruction(instruction=instruction)

        # execute instructions that should be executed immediately
        if execute_now:
            self.execute_next_queue_instructions()
        else:
            pass

    def execute_object_creation(self, object_creation: ObjectCreation):

        if self.queue.time == object_creation.execution_time:
            pass
        else:
            raise ValueError("Object creation time does not match current time.")

        if object_creation.add_to_binding:
            raise ValueError("If object should be added to binding, object may not be in the queue.")
        else:
            pass

        # create object
        obj = self.create_object(object_creation=object_creation)

        # create object creation instruction
        instruction = InstructionObjectCreation(timedelta=datetime.timedelta(0),
                                                object_type=object_creation.object_type,
                                                initial_attributes=object_creation.initial_attributes,
                                                quantities=object_creation.initial_quantities,
                                                location=object_creation.location,
                                                add_to_binding=object_creation.add_to_binding,
                                                o2o=object_creation.o2o)

        # add object to model
        self.execution.execute_object_creation(obj_to_add=obj, instruction=instruction)

        if isinstance(object_creation.schedule_type, ScheduleTypeFixed):
            self._add_new_automated_object_creation_instruction_to_queue(object_type=object_creation.object_type,
                                                                         schedule_type=ScheduleTypeFixed())
        elif isinstance(object_creation.schedule_type, ScheduleTypeArrivalRate):
            self._add_new_automated_object_creation_instruction_to_queue(object_type=object_creation.object_type,
                                                                         schedule_type=ScheduleTypeArrivalRate())
        else:
            pass

    def _add_new_automated_object_creation_instruction_to_queue(self, object_type: Type[Object],
                                                                schedule_type: ScheduleType,
                                                                specific_time: datetime.datetime = None):
        """Receive object type and add object creation queue item to queue."""

        # get duration until next object has to be created
        if isinstance(schedule_type, ScheduleTypeFixed):
            param_from_config = self.config.object_creation_fixed_time_interval[object_type]
            if isinstance(param_from_config, (int, float)):
                duration = datetime.timedelta(hours=param_from_config)
            elif isinstance(param_from_config, datetime.timedelta):
                duration = param_from_config
            else:
                raise ValueError("Duration has to be of type datetime.timedelta, int or float.")

        elif isinstance(schedule_type, ScheduleTypeArrivalRate):
            param_from_config = self.config.object_creation_frequencies_arrival_rates[object_type]
            objects_per_day = self.draw_from_poisson_distribution(lam=param_from_config)
            if objects_per_day == 0:
                duration = datetime.timedelta(days=1)
            else:
                duration = datetime.timedelta(days=1) / objects_per_day

        else:
            raise ValueError("Schedule type has to be of type ScheduleTypeFixed or ScheduleTypeArrivalRate.")

        if specific_time:
            duration = specific_time - self.queue.time
        else:
            pass

        # create object creation instruction
        instruction = InstructionObjectCreation(timedelta=duration,
                                                object_type=object_type,
                                                initial_attributes={},
                                                quantities=None,
                                                location=None,
                                                add_to_binding=False,
                                                o2o=None)

        # add instruction to queue
        self.queue.add_object_creation(object_creation=instruction, schedule_type=schedule_type)

    def add_missing_objects_to_execution(self, event_execution_instruction: InstructionExecuteEvent):

        activity = event_execution_instruction.activity
        additional_objects_created = event_execution_instruction.additional_objects.copy()

        # check if selected activity requires additional object creations
        additional_objects_required = self.get_activities_with_additional_requirements()
        # print(f"All additional objects created: {event_execution_instruction.additional_objects}")

        # check if this activity requires additional objects
        if event_execution_instruction.activity in additional_objects_required.keys():

            additional_object_types_created = dict(Counter([obj.object_type for obj in additional_objects_created]))

            for object_type in additional_objects_required[activity].keys():

                # check if at least one object of missing types were created yet
                if object_type in additional_object_types_created.keys():

                    # check if enough objects were created
                    if (additional_object_types_created[object_type]
                            >= additional_objects_required[activity][object_type]):
                        # print(f"Enough objects available for event {event_execution_instruction.event}!")
                        pass
                    else:
                        # find out how many additional objects are required
                        number_additional_objects_required = (additional_objects_required[activity][object_type]
                                                              - additional_object_types_created[object_type])

                        # create additional objects
                        new_objects = self.create_required_number_of_objects(object_type=object_type,
                                                                             requested_objects=
                                                                             number_additional_objects_required)

                        # add objects to event execution instruction
                        event_execution_instruction.add_objects(new_objects)

                else:
                    # create additional objects
                    new_objects = self.create_required_number_of_objects(object_type=object_type,
                                                                         requested_objects=
                                                                         additional_objects_required[activity][
                                                                             object_type])

                    # add objects to event execution instruction
                    event_execution_instruction.add_objects(new_objects)

    def get_activities_with_additional_requirements(self):
        return self.execution.get_additional_requirements_for_bindings()

    def _identify_object(self, obj: Object | str) -> Object:

        if isinstance(obj, Object):
            if obj in self.object_overview:
                return obj
            else:
                raise ValueError(f"Object {obj} not found in simulation model.")
        elif isinstance(obj, str):
            for known_obj in self.object_overview:
                if known_obj.name == obj:
                    return known_obj
            else:
                raise ValueError(f"Object with name {obj} not found in simulation model.")
        else:
            raise ValueError("Object has to be of type Object or str.")

    def check_if_object_in_final_marking(self, obj: Object | str) -> bool:
        obj = self._identify_object(obj=obj)
        return self.execution.check_if_object_in_final_marking(obj=obj)

    def draw_from_normal_distribution(self, mean: float, std: float):
        return self.rng.normal(loc=mean, scale=std)

    def draw_from_uniform_distribution(self, low: float, high: float):
        return self.rng.uniform(low=low, high=high)

    def draw_from_poisson_distribution(self, lam: float):
        return self.rng.poisson(lam=lam)

    def draw_from_exponential_distribution(self, scale: float):
        return self.rng.exponential(scale=scale)

    def draw_from_beta_distribution(self, a: float, b: float):
        return self.rng.beta(a=a, b=b)

    def draw_from_gamma_distribution(self, shape: float, scale: float):
        return self.rng.gamma(shape=shape, scale=scale)

    def _get_activity_from_name(self, activity_name: str | Type[Event]) -> Type[Event]:
        """Passes activity name on to QnetExecution's method of identifying activities."""
        activity = self.execution.identify_activity(activity_name=activity_name)
        return activity

    def update_duration_specifications_in_config(self):
        """overwrites activity names with the actual activity elements of the programme. Iterated through all durations
        specifications in the config and exchanges activity names for activity elements."""

        # fixed durations
        new_durations_fixed = {}
        for activity_name, duration in self.config.durations_fixed.items():
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self._get_activity_from_name(activity_name=activity_name)
            new_durations_fixed[activity] = duration

        self.config.durations_fixed = new_durations_fixed

        # uniform distribution duration
        new_durations_uniform = {}
        for activity_name, duration in self.config.durations_min_uniform.items():
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self._get_activity_from_name(activity_name=activity_name)
            new_durations_uniform[activity] = duration

        self.config.durations_min_uniform = new_durations_uniform

        # normal distribution duration
        new_durations_normal = {}
        for activity_name, duration in self.config.durations_min_normal.items():
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self._get_activity_from_name(activity_name=activity_name)
            new_durations_normal[activity] = duration

        self.config.durations_min_normal = new_durations_normal

        # beta distribution duration
        new_durations_beta = {}
        for activity_name, duration in self.config.durations_beta.items():
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self._get_activity_from_name(activity_name=activity_name)
            new_durations_beta[activity] = duration

        self.config.durations_beta = new_durations_beta

        # gamma distribution duration
        new_durations_gamma = {}
        for activity_name, duration in self.config.durations_gamma.items():
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self._get_activity_from_name(activity_name=activity_name)
            new_durations_gamma[activity] = duration

        self.config.durations_gamma = new_durations_gamma

    def get_specified_duration(self, activity: Type[Event]) -> datetime.timedelta:
        """Draws a duration for an event as specified in config.
        Checks in the order: fixed duration, uniform, normal, beta, gamma."""

        duration = datetime.timedelta(minutes=-1)
        tries = 0  # to avoid infinite loops

        while duration < datetime.timedelta(0) or tries < 50:
            if activity in self.config.durations_fixed.keys():
                duration = self.config.durations_fixed[activity]
                if isinstance(duration, datetime.timedelta):
                    pass
                elif isinstance(duration, (int, float)):
                    duration = datetime.timedelta(minutes=duration)
                else:
                    raise ValueError("Duration has to be of type datetime.timedelta, int or float.")
            elif activity in self.config.durations_min_uniform:
                params = self.config.durations_min_uniform[activity]
                minutes = self.draw_from_uniform_distribution(low=params[0], high=params[1])
                duration = datetime.timedelta(minutes=minutes)
            elif activity in self.config.durations_min_normal:
                params = self.config.durations_min_normal[activity]
                minutes = self.draw_from_normal_distribution(mean=params[0], std=params[1])
                duration = datetime.timedelta(minutes=minutes)
            elif activity in self.config.durations_beta:
                params = self.config.durations_beta[activity]
                minutes = self.draw_from_beta_distribution(a=params[0], b=params[1])
                duration = datetime.timedelta(minutes=minutes)
            elif activity in self.config.durations_gamma:
                params = self.config.durations_gamma[activity]
                minutes = self.draw_from_gamma_distribution(shape=params[0], scale=params[1])
                duration = datetime.timedelta(minutes=minutes)
            else:
                minutes = self.draw_from_normal_distribution(mean=self.config.durations_default_normal_min_params[0],
                                                             std=self.config.durations_default_normal_min_params[1])
                duration = datetime.timedelta(minutes=minutes)

            tries += 1

        if duration < datetime.timedelta(0):
            raise ValueError("The provided parameters for drawing a duration did not achieve a positive duration in 50 "
                             "tries. Provide different parameters and try again..")
        else:
            pass

        return duration

    def get_event_by_name(self, event_name: Event | str) -> Event:
        event = [event for event in self.event_overview if event.name == event_name][0]
        return event

    def update_frequent_object_creations_in_config(self):
        """exchange object type names for the actual object types in config"""

        new_creation_frequency_arrival_rates = {}

        for object_type_name, frequency in self.config.object_creation_frequencies_arrival_rates.items():
            if object_type_name in self.object_types:
                object_type = object_type_name
            else:
                object_type = self.execution.identify_object_type(object_type_name=object_type_name)
            new_creation_frequency_arrival_rates[object_type] = frequency

        self.config.object_creation_frequencies_arrival_rates = new_creation_frequency_arrival_rates

        new_creation_frequencies_fixed_duration = {}

        for object_type_name, duration in self.config.object_creation_fixed_time_interval.items():
            if object_type_name in self.object_types:
                object_type = object_type_name
            else:
                object_type = self.execution.identify_object_type(object_type_name=object_type_name)
            new_creation_frequencies_fixed_duration[object_type] = duration

        self.config.object_creation_fixed_time_interval = new_creation_frequencies_fixed_duration

    def export_simulated_log(self, path_to_folder: str = None):
        """pass path to folder where log should be saved.
        If no path is passed, log is saved in a folder called 'event_logs'."""

        self.execution.event_log.save_event_logs_to_sql_lite(path_to_folder=path_to_folder)

    def update_triggered_object_creation_in_config(self):
        """exchange strings for actual transition / cp / place elements in config as well
        as object types for object type names."""

        new_triggered_object_creation = {}

        for trigger, object_type_name in self.config.object_creation_triggered.items():

            # get object type
            if object_type_name in self.object_types:
                object_type = object_type_name
            else:
                object_type = self.execution.identify_object_type(object_type_name=object_type_name)

            # update trigger
            if isinstance(trigger, MultiTrigger):
                for trigger_element in trigger.triggers:
                    trigger_element.net_element = self.execution.quantity_net.identify_node(
                        node=trigger_element.net_element)
            elif isinstance(trigger, NetElementTrigger):
                trigger.net_element = self.execution.quantity_net.identify_node(node=trigger.net_element)
            else:
                raise ValueError("Trigger has to be of type Trigger.")

            # add to new dict
            new_triggered_object_creation[trigger] = object_type

        self.config.object_creation_triggered = new_triggered_object_creation

    def execute_triggered_object_creations(self):
        for trigger, object_type in self.config.object_creation_triggered.items():
            if trigger.check_triggering():
                # print("Object creation triggered: ", object_type)
                # create object creation instruction
                instruction = InstructionObjectCreation(timedelta=datetime.timedelta(0),
                                                        object_type=object_type,
                                                        initial_attributes={},
                                                        quantities=None,
                                                        location=None,
                                                        add_to_binding=False,
                                                        o2o={})

                # add instruction to queue
                self.queue.add_object_creation(object_creation=instruction)
            else:
                pass

    def update_activity_priorities_in_config(self):
        """exchange activity names for actual activity elements in config"""

        new_activity_priority = []

        for activity_name in self.config.activity_priority:
            if activity_name in self.activities:
                activity = activity_name
            else:
                activity = self.execution.identify_activity(activity_name=activity_name)
            new_activity_priority.append(activity)

        self.config.activity_priority = new_activity_priority

    def execute_initial_schedules(self):
        """exchange object type names for the actual object types in config"""

        all_scheduled_types = (set(self.config.object_creation_frequencies_arrival_rates.keys()) |
                               set(self.config.object_creation_fixed_time_interval.keys()))

        all_scheduled_types_names = {s_type.object_type_name for s_type in all_scheduled_types}

        scheduled_types_specified_initial_executions = set()

        for specified_initial_executions, execution_time in self.config.initial_scheduled_executions.items():

            # identify corresponding activity or object type
            if specified_initial_executions in all_scheduled_types:
                scheduled_type = specified_initial_executions
            elif specified_initial_executions in all_scheduled_types_names:
                scheduled_type = \
                    [s_type for s_type in all_scheduled_types if s_type.object_type_name == specified_initial_executions][0]
            else:
                raise ValueError("Specified initial execution has to be defined as a scheduled execution type.")

            # identify schedule type
            if scheduled_type in self.config.object_creation_frequencies_arrival_rates.keys():
                schedule_type = ScheduleTypeArrivalRate()
            else:
                schedule_type = ScheduleTypeFixed()

            # add initial entry to queue
            self._add_new_automated_object_creation_instruction_to_queue(object_type=scheduled_type,
                                                                         schedule_type=schedule_type,
                                                                         specific_time=execution_time)

            scheduled_types_specified_initial_executions.add(scheduled_type)

        # add initial executions for entries without specified initial executions to queue
        for scheduled_type in all_scheduled_types - scheduled_types_specified_initial_executions:
            # identify schedule type
            if scheduled_type in self.config.object_creation_frequencies_arrival_rates.keys():
                schedule_type = ScheduleTypeArrivalRate()
            else:
                schedule_type = ScheduleTypeFixed()

            # add initial entry to queue
            self._add_new_automated_object_creation_instruction_to_queue(object_type=scheduled_type,
                                                                         schedule_type=schedule_type)

    def print_enabled_bindings(self):

        enabled_bindings = self.get_enabled_activity_bindings()
        for activity, bindings_list in enabled_bindings.items():
            print(f"######### {activity.activity_name} ###########")
            for binding in bindings_list:
                binding_readable = {object_type.object_type_name: objects for object_type, objects in binding.items()}
                print(f"  {binding_readable}")
            print("\n")

    def overview_quantity_state(self) -> pd.DataFrame:
        """Get overview of quantity state in an easily readable manner"""
        qty_state = self.execution.quantity_net.quantity_state
        qty_state_dict = {counter.name: dict(item_quantity) for counter, item_quantity in qty_state.items()}
        qty_state_overview = pd.DataFrame.from_dict(qty_state_dict, orient='index')
        qty_state_overview = qty_state_overview.fillna(0)
        return qty_state_overview

    def start_simulation(self):
        start_time = self.queue.time  # apparently no copy needed, as datetime objects are immutable
        end_time = self.config.max_simulation_time + start_time

        c1 = lambda: self.step_counter < self.config.max_execution_steps
        c2 = lambda: self.queue.time <= end_time
        c3 = lambda: len(self.terminated_objects) <= self.config.max_objects
        c4 = lambda: len(self.event_overview) <= self.config.max_events

        while c1() and c2() and c3() and c4():
            # print(f"Simulation Step: {self.step_counter}")
            # print(f"Time: {self.queue.time}")
            # print(f"Number of terminated objects: {len(self.terminated_objects)}")
            # print(f"Number of events: {len(self.event_overview)}")
            self.execute_simulation_step()
