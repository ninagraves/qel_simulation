import datetime
from typing import Type, Any

from qel_simulation.components.base_element import BaseElement
from qel_simulation.simulation.event import Event, create_activity
from qel_simulation.simulation.object import Object, create_object_type, StatusActive, StatusTerminated, MultisetObject, BindingFunction
from qel_simulation.components.collection_point import CollectionPoint
from qel_simulation.components.collection_counter import CollectionCounter
from qel_simulation.qnet_elements.guard import QuantityGuardSmallStock
from qel_simulation.components.quantity_event_log import QuantityEventLog
from qel_simulation.components.quantity_net import QuantityNet
from qel_simulation.simulation.instructions import (InstructionExecuteEvent, Instruction,
                                                    InstructionTerminateEvent,
                                                    InstructionObjectCreation)
from qel_simulation.simulation.qnet_config import QnetConfig


def check_object_status_in_enabled_binding(binding_function: BindingFunction) -> bool:
    """Check if all objects in binding function are in the net."""

    objects = set().union(*binding_function.values())
    for obj in objects:
        if obj.status_active:
            pass
        else:
            return False

    return True


class QuantityNetExecution(BaseElement):

    def __init__(self, name: str, qnet_config: QnetConfig, label: str = None, properties: dict = None):

        super().__init__(name=name, label=label, properties=properties)

        # base elements
        self._quantity_net = None
        self._quantity_log = QuantityEventLog(name=f"{name}_log")
        self._configuration = qnet_config

        self._object_type_names_classes = {}
        self._activity_names_classes = {}

        self.default_timestamp = datetime.datetime(month=10, year=2019, day=12, hour=12, minute=21)

        # instantiation according to configuration
        self._add_object_types_from_config()
        self.create_quantity_net()
        self._add_activities_from_config()
        self.update_final_markings()

    @property
    def quantity_net(self) -> QuantityNet:
        return self._quantity_net

    @quantity_net.setter
    def quantity_net(self, quantity_net: QuantityNet):
        self._quantity_net = quantity_net

    @property
    def event_log(self) -> QuantityEventLog:
        return self._quantity_log

    @property
    def object_types(self) -> set[Type[Object]]:
        return set(self._object_type_names_classes.values())

    @property
    def object_type_names(self) -> set[str]:
        return set(self._object_type_names_classes.keys())

    @property
    def config(self):
        return self._configuration

    @config.setter
    def config(self, configuration: QnetConfig):
        self._configuration = configuration

    @property
    def activities(self) -> set[Type[Event]]:
        return set(self._activity_names_classes.values())

    @property
    def activity_names(self) -> set[str]:
        return set(self._activity_names_classes.keys())

    @property
    def object_type_names_classes(self) -> dict[str, Type[Object]]:
        return self._object_type_names_classes

    @property
    def state(self):
        return self.quantity_net.marking

    def provided_initial_objects(self):
        """Return objects provided in the configuration."""

        provided_objects = {}
        if self.config.initial_objects:

            for object_type in self.object_types:
                # get all objects of that type
                provided_objects[object_type] = {obj for obj in self.config.initial_objects if
                                                 obj.object_type == object_type}

        else:
            pass

        return provided_objects

    def provided_objects_specified_places(self):

        provided_objects = {}
        if self.config.initial_objects_in_places:

            for place, objects in self.config.initial_objects_in_places.items():

                place_type = self.get_type_of_place(place_name=place)

                if place_type in provided_objects.keys():
                    provided_objects[place_type].update(objects)
                else:
                    provided_objects[place_type] = objects
        else:
            pass

        return provided_objects

    def _add_object_type(self, object_type: Type[Object]):
        self.object_type_names_classes[object_type.object_type_name] = object_type

        print(f"Object type {object_type.object_type_name} added to {self.name}.")

    def _add_object_types_from_config(self):
        """Add described and created object classes to this structure."""

        for object_type, default_attributes in self.config.object_types_attributes.items():
            object_type_class = self.create_object_type(object_type_name=object_type,
                                                        default_attribute_values=default_attributes)
            self._add_object_type(object_type=object_type_class)

        for object_class in self.config.object_types_classes:

            if object_class in self.object_types:
                raise ValueError(f"Object type {object_class.object_type_name} already exists.")
            else:
                pass

            self._add_object_type(object_type=object_class)

    def create_object_type(self, object_type_name: str, default_attribute_values: dict = None):
        """Returns an Object-class to create objects based on passed parameters."""

        if object_type_name in self.object_types:
            raise ValueError(f"Object type {object_type_name} already exists.")
        else:
            pass

        object_type = create_object_type(object_type_name=object_type_name,
                                         default_attribute_values=default_attribute_values)

        return object_type

    def _add_activities_from_config(self):
        """Add described and created object classes to this structure."""

        # add existing activity classes
        for activity_class in self.config.activity_classes:

            if activity_class.activity_name in self.activity_names:
                raise ValueError(f"Activity {activity_class.__name__} already defined.")
            else:
                self._add_activity(activity=activity_class)

        # create specified activities
        for activity, default_attributes in self.config.activity_attributes.items():
            activity_class = self.create_activity(activity_name=activity, default_attribute_values=default_attributes)
            self._add_activity(activity=activity_class)

        # creat potentially missing activities from transition labels
        self.add_missing_activities(pot_mission_activity_names=self.get_transition_labels())

        # create activities for silent transitions / set activities to non-logged
        self.create_silent_activities()

    def create_silent_activities(self):
        """Create activities for silent transitions according to config."""

        for transition in self.quantity_net.silent_transitions:
            if transition.label in self.activity_names or transition.name in self.activity_names:
                activity_class = self.identify_activity(activity_name=transition.label)
                activity_class.log_activity = False
            else:
                activity_class = create_activity(activity_name=transition.name, default_attribute_values={},
                                                 log_activity=False)
                self._add_activity(activity=activity_class)

    def create_silent_object_types(self):
        """Create activities for silent transitions according to config."""

        for object_type in self.config.silent_object_types:
            object_type_class = self.identify_object_type(object_type_name=object_type)
            if object_type_class:
                object_type_class.log_object_type = False
            else:
                object_type_class = create_object_type(object_type_name=object_type, default_attribute_values={}, log_object_type=False)
                self._add_object_type(object_type=object_type_class)

    def get_silent_activities(self) -> set[Type[Event]]:
        """Return set of silent activities."""

        return {activity for activity in self.activities if activity.log_activity is False}

    def create_activity(self, activity_name: str, default_attribute_values: dict = None):
        """Returns an Activity class to create events based on passed parameters."""

        if activity_name in self.activity_names:
            raise ValueError(f"Activity {activity_name} already exists.")
        else:
            pass

        activity_class = create_activity(activity_name=activity_name,
                                         default_attribute_values=default_attribute_values)

        return activity_class

    def add_missing_activities(self, pot_mission_activity_names: set[str]):
        """Add activities that are missing from the config."""

        # create non-specified activities
        activities_to_create = pot_mission_activity_names - self.activity_names
        for activity in activities_to_create:
            activity_class = self.create_activity(activity_name=activity, default_attribute_values={})
            self._add_activity(activity=activity_class)


    def _add_activity(self, activity: Type[Event]):
        self._activity_names_classes[activity.activity_name] = activity
        print(f"Activity {activity.activity_name} added to {self.name}.")

    def identify_activity(self, activity_name: str | Type[Event]) -> Type[Event]:
        """Pass object type or object type name and receive object type class."""

        if activity_name in self.activities:
            activity = activity_name
        elif activity_name in self.activity_names:
            activity = self._activity_names_classes[activity_name]
        else:
            raise ValueError(f"Passed activity {activity_name} cannot be identified within simulation.")

        return activity

    def get_transition_labels(self) -> set[str]:
        return set(self.config.transition_labels.values())

    def create_quantity_net(self):
        """Created Quantity Net object according to specifications made in associated configuration."""

        self.quantity_net = QuantityNet(name=self.config.quantity_net_name, label=self.config.quantity_net_label,
                                        properties=self.config.quantity_net_properties)

        _, _ = self.quantity_net.set_net_structure(arcs=self.config.net_structure)
        self.quantity_net.set_initial_places(initial_places=self.config.initial_places)
        self.quantity_net.set_final_places(final_places=self.config.final_places)
        self.quantity_net.set_transition_labels(self.config.transition_labels)
        self.quantity_net.set_manually_initiated_transitions(self.config.manually_initiated_transitions)
        self.quantity_net.set_collection_point_labels(self.config.collection_point_labels)
        self.quantity_net.set_qalculator(self.config.quantity_calculators)
        self.quantity_net.set_silent_transitions(self.config.silent_transitions)

        # rewrite place type specification with object type classes
        new_place_type_mapping = {}
        for place, object_type_name in self.config.place_types.items():
            object_type = self.identify_object_type(object_type_name=object_type_name)
            if object_type is None:
                object_type_class = self.create_object_type(object_type_name=object_type_name,
                                                            default_attribute_values=None)
                self._add_object_type(object_type=object_type_class)
            else:
                pass
            new_place_type_mapping[place] = object_type

        # add place mapping to quantity net
        self.quantity_net.set_place_types(new_place_type_mapping)

        # add transition guards
        for transition, object_guard in self.config.transition_object_guard.items():
            self.quantity_net.set_object_guard(transition=transition, object_guard=object_guard)
        for transition, quantity_guard in self.config.transition_quantity_guard.items():
            self.quantity_net.set_quantity_guard(transition=transition, quantity_guard=quantity_guard)
        for transition, small_stock_guard_config in self.config.small_stock_guards.items():
            self.set_small_stock_guard(transition=transition, small_stock_guard_config=small_stock_guard_config)

        # add transition binding specifications to quantity net
        self.quantity_net.set_binding_function_specification(self.identify_elements_of_binding_function_from_config(self.config.binding_function_quantities))
        if self.config.maximum_binding_function_quantities:
            identified_function = self.identify_elements_of_binding_function_from_config(self.config.maximum_binding_function_quantities)
            self.quantity_net.set_maximum_binding_function_specification(identified_function)
        else:
            pass
        if self.config.minimum_binding_function_quantities:
            identified_function = self.identify_elements_of_binding_function_from_config(self.config.minimum_binding_function_quantities)
            self.quantity_net.set_minimum_binding_function_specification(identified_function)
        else:
            pass

        # set arcs to variable explicitly and specify variable constraints per arc
        self.quantity_net.make_arcs_variable(variable_arcs=self.config.variable_arcs)
        self.quantity_net.set_maximum_object_tokens_variable_arc(self.config.maximum_variable_arc_object_quantities)
        self.quantity_net.set_minimum_object_tokens_variable_arc(self.config.minimum_variable_arc_object_quantities)
        self.quantity_net.specify_number_of_object_tokens_variable_arc(self.config.specify_variable_arc_object_tokens)


        # add transition binding selection functions
        self.quantity_net.set_transition_binding_selection(self.config.transition_binding_selection)

        print(f"Quantity net {self.quantity_net.name} successfully created according to {self.config.name}.")

    def identify_elements_of_binding_function_from_config(self, binding_function_specification: dict[str: dict[Type[
                                                                                                                   Object]: int]]):

        # create transition binding function with object classes
        new_transition_binding_function_specification = {}
        for transition, binding_function in binding_function_specification.items():

            new_binding_function_specification = {}
            for object_type_name, object_quantity in binding_function.items():
                object_type = self.identify_object_type(object_type_name=object_type_name)
                if object_type is None:
                    raise ValueError(f"Object type {object_type_name} not found.")
                else:
                    new_binding_function_specification[object_type] = object_quantity

            new_transition_binding_function_specification[transition] = new_binding_function_specification
        return new_transition_binding_function_specification

    def get_number_required_objects_per_type(self):

        required_objects = {}

        if self.config.initial_marking_object_types:

            for object_type_name, requested_objects in self.config.initial_marking_object_types.items():
                object_type = self.identify_object_type(object_type_name=object_type_name)
                if object_type:
                    required_objects[object_type] = requested_objects
                else:
                    raise ValueError(f"Object type {object_type_name} not found.")

        else:
            pass

        if self.config.initial_marking_object_places:

            for place, requested_objects in self.config.initial_marking_object_places.items():
                object_type = self.get_type_of_place(place_name=place)
                if object_type in required_objects.keys():
                    required_objects[object_type] += requested_objects
                else:
                    required_objects[object_type] = requested_objects

        else:
            pass

        return required_objects

    def add_number_of_objects_to_net_according_to_config(self, objects_per_type: dict[Type[Object]: MultisetObject]):
        """Add objects to net according to configuration after required number of objects were created."""

        if self.config.initial_marking_object_types:
            for object_type, requested_objects in self.config.initial_marking_object_types.items():
                # take required number of objects to add to initial markings
                all_objects_of_type = list(objects_per_type[object_type])
                objects_to_add = set(all_objects_of_type[:requested_objects])

                # add objects to initial places of object type
                self.add_objects_to_initial_places(objects_per_type={object_type: objects_to_add})

                # update provided objects
                objects_per_type[object_type] = objects_per_type[object_type] - objects_to_add

        else:
            pass

        if self.config.initial_marking_object_places:

            for place, requested_objects in self.config.initial_marking_object_places.items():
                place_type = self.get_type_of_place(place_name=place)

                # take required number of objects to add to initial markings
                all_objects_of_type = list(objects_per_type[place_type])
                objects_to_add = set(all_objects_of_type[:requested_objects])

                # add objects to initial places of object type
                self.add_objects_to_places(object_marking={place: objects_to_add})

                # update provided objects
                objects_per_type[place_type] = objects_per_type[place_type] - objects_to_add

        else:
            pass

        if set().union(*objects_per_type.values()):
            print(objects_per_type)
            raise ValueError(f"Not all objects provided in configuration were added to the net.")
        else:
            pass

    def identify_object_type(self, object_type_name: str | Type[Object]) -> Type[Object] | None:
        """Pass object type or object type name and receive object type class."""

        if object_type_name in self.object_types:
            object_type = object_type_name
        elif object_type_name in self.object_type_names:
            object_type = self.object_type_names_classes[object_type_name]
        else:
            return None

        return object_type

    def add_object_to_specified_places_according_to_config(self, objects_per_type: dict[Type[Object]: set[Object]]):

        if self.config.initial_objects_in_places:

            tokens_for_marking = {}

            for place, objects in self.config.initial_objects_in_places.items():

                place_type = self.get_type_of_place(place_name=place)

                # check if all objects in registered objects
                if objects.issubset(objects_per_type[place_type]):
                    tokens_for_marking[place] = objects
                else:
                    raise ValueError(f"Objects {objects} are not registered in the simulation.")

            self.add_objects_to_places(object_marking=tokens_for_marking)

        else:
            pass

    def add_objects_to_initial_places(self, objects_per_type: dict[Type[Object]: MultisetObject]):
        """Add objects to initial places of the object type in the net."""

        for object_type, objects in objects_per_type.items():
            # get initial places of object type
            initial_places = self.quantity_net.get_initial_places_object_type(object_type=object_type)

            # define marking
            required_marking = dict(zip(list(initial_places), [objects] * len(initial_places)))

            # add marking to net
            self.add_objects_to_places(object_marking=required_marking)

    def get_type_of_place(self, place_name: str) -> Type[Object]:
        """Pass place, get associated object type"""

        object_type_name = self.config.place_types[place_name]
        object_type = self.identify_object_type(object_type_name=object_type_name)

        return object_type

    def set_initial_marking_collection_points(self):
        self.mark_collection_points(self.config.initial_marking_collection_points)

        initial_markings_to_log = {}
        for cp, initial_marking in self.config.initial_marking_collection_points.items():
            cp_element = self.quantity_net.identify_node(cp)
            if cp_element.silent:
                pass
            else:
                self._quantity_log.add_quantity_operation(event=None, quantity_operation=initial_marking, collection_point=cp_element)

    def mark_collection_points(self, collection_point_marking: CollectionCounter):
        """Pass marking for collection points to be added to the net."""

        self.quantity_net.update_markings_collection_points(collection_point_marking)

    def add_objects_to_places(self, object_marking: dict[Any: MultisetObject]):
        """pass dict with places and objects for marking in the net."""

        self.quantity_net.add_objects_to_places(object_marking=object_marking)
        for obj in MultisetObject().union(*object_marking.values()):
            self.log_object(obj=obj)
            self.set_object_status_active(obj=obj)

    def set_object_status_active(self, obj: Object):
        obj.status = StatusActive()

    def set_object_status_terminated(self, obj: Object):
        obj.status = StatusTerminated()

    def log_object(self, obj: Object):
        """Add object to log."""

        self.event_log.add_object_to_log(obj=obj)

    def get_enabled_activities(self) -> dict[Type[Event]: list[None] | list[dict[Type[Object]: set[Object]]]]:
        transition_bindings = self.quantity_net.get_enabled_bindings_all_transitions_for_input_types()
        activity_bindings_names = {(transition.label if transition.label else transition.name): bindings
                                   for transition, bindings in transition_bindings.items()}
        activity_bindings = {self.identify_activity(activity): bindings
                             for activity, bindings in activity_bindings_names.items()}
        active_bindings = {}
        for activity, bindings in activity_bindings.items():
            binding_list = [binding for binding in bindings if
                            check_object_status_in_enabled_binding(binding_function=binding)]
            if binding_list:
                active_bindings[activity] = binding_list
            else:
                pass
        return active_bindings

    def execute_event_start(self, event_instruction: InstructionExecuteEvent) -> list[Instruction]:
        """Start execution of event. Execute event start method and begin firing of transition."""

        # get quantity state before the execution of the event
        quantity_state = self.quantity_net.quantity_state

        # set all objects to active that are involved in binding
        for obj in set().union(*event_instruction.final_binding_function.values()):
            self.set_object_status_active(obj=obj)

        # fire transition
        execution = self.quantity_net.start_firing_transition(transition=event_instruction.activity.activity_name,
                                                              binding_function=event_instruction.final_binding_function)

        # set event's collected quantity operation
        event_instruction.event.quantity_operations = execution.transition_execution.collected_quantity_operations

        # execute event start method
        returned_instructions = event_instruction.event.start_event(
            binding_function=event_instruction.final_binding_function, quantity_state=quantity_state)

        # create instructions for termination of event
        end_event_instruction = InstructionTerminateEvent(event=event_instruction.event,
                                                          execution=execution)

        # ensure passed activities and object types are correctly identified
        for instruction in returned_instructions:
            if isinstance(instruction, InstructionExecuteEvent):
                instruction.activity = self.identify_activity(instruction.activity)
            elif isinstance(instruction, InstructionObjectCreation):
                instruction.object_type = self.identify_object_type(instruction.object_type)
            else:
                pass

        returned_instructions.append(end_event_instruction)

        return returned_instructions

    def execute_event_termination(self, termination: InstructionTerminateEvent) -> list[Instruction]:

        # execute event end method
        returned_instructions = termination.event.end_event(execution=termination.execution)

        # ensure passed activities and object types are correctly identified
        for instruction in returned_instructions:
            if isinstance(instruction, InstructionExecuteEvent):
                instruction.activity = self.identify_activity(instruction.activity)
            elif isinstance(instruction, InstructionObjectCreation):
                instruction.object_type = self.identify_object_type(instruction.object_type)
            else:
                pass

        # end firing of transition
        self.quantity_net.end_firing_transition(execution=termination.execution)

        # add event to log
        self._log_event_execution(event=termination.event)

        # check if objects are in final marking and set terminated
        for obj in MultisetObject().union(*termination.execution.transition_execution.binding_function.values()):
            if self.check_if_object_in_final_marking(obj=obj):
                self.set_object_status_terminated(obj=obj)
            else:
                pass

        return returned_instructions

    def execute_object_creation(self, obj_to_add: Object, instruction: InstructionObjectCreation):

        if instruction.location:
            obj_locations = list(instruction.location)
            marking = dict(zip(obj_locations, [obj_to_add] * len(obj_locations)))
            self.add_objects_to_places(object_marking=marking)
        else:
            self.add_objects_to_initial_places(objects_per_type={obj_to_add.object_type: {obj_to_add}})

    def _log_event_execution(self, event: Event):
        """Log execution of event."""
        self.event_log.add_event_to_log(event=event)

    def get_additional_requirements_for_bindings(self) -> dict[Type[Object]: int]:
        """Pass transition or transition label and identify additional objects required for firing."""

        transition_overview = self.quantity_net.transitions_output_types_not_input

        activity_overview_names = {(transition.label if transition.label else transition.name): additional_objects
                                   for transition, additional_objects in transition_overview.items()}

        activity_overview_names = {self.identify_activity(activity_name): additional_objects
                                   for activity_name, additional_objects in activity_overview_names.items()}

        activities_with_requirements = {activity: additional_objects for activity, additional_objects in
                                        activity_overview_names.items() if additional_objects}

        return activities_with_requirements

    def update_final_markings(self):
        """Update configuration of specification of final markings per object type."""

        defined_object_types = self.object_types.copy()
        new_config_final_marking = {}

        if self.config.final_markings:

            for object_type, final_markings in self.config.final_markings.items():
                object_type_element = self.identify_object_type(object_type_name=object_type)
                new_config_final_marking[object_type_element] = final_markings
        else:
            pass

        object_types_not_specified = defined_object_types - set(new_config_final_marking.keys())

        if object_types_not_specified:
            for object_type in object_types_not_specified:
                final_markings = []
                final_places_ot = self.quantity_net.get_final_places_object_type(object_type=object_type)
                for place in final_places_ot:
                    final_markings.append({place.name})
                new_config_final_marking[object_type] = final_markings
        else:
            pass

        self.config.final_markings = new_config_final_marking

    def get_location_of_object(self, obj: Object) -> set[str]:
        """Return names of places object is part of marking."""

        obj_locations = self.quantity_net.get_locations_of_object(obj=obj)
        obj_locations_names = {place.name for place in obj_locations}

        return obj_locations_names

    def check_if_object_in_final_marking(self, obj: Object) -> bool:
        """Check if object has completed process."""

        if self.get_location_of_object(obj=obj) in self.config.final_markings[obj.object_type]:
            return True
        else:
            return False

    def identify_collection_point(self, collection_point: str | CollectionPoint) -> CollectionPoint:
        """Get name, label or object of collection points and return collection point object."""

        # get collection points in simulation model
        collection_points = self.quantity_net.collection_points

        if isinstance(collection_point, CollectionPoint):
            if collection_point in collection_points:
                return collection_point
            else:
                raise ValueError(f"Collection point {collection_point} not found in simulation model.")
        elif isinstance(collection_point, str):
            cp_elements = [cp for cp in collection_points if
                           cp.name == collection_point or cp.label == collection_point]
            if len(cp_elements) == 1:
                return cp_elements[0]
            else:
                raise ValueError(f"Collection point {collection_point} could not be uniquely identified within model.")
        else:
            raise ValueError("Collection point has to be of type CollectionPoint or str.")

    def set_small_stock_guard(self, transition, small_stock_guard_config):
        """Set small stock guard for transition."""
        # update counter thresholds by replacing strings with counters
        new_counter_threshold = CollectionCounter()
        for counter, threshold in small_stock_guard_config.counter_threshold.items():
            counter_element = self.identify_collection_point(counter)
            new_counter_threshold[counter_element] = threshold

        # update counter all item types by replacing strings with counters
        new_counter_all_item_types = dict()
        if small_stock_guard_config.counter_all_item_types:
            for counter, all_item_types in small_stock_guard_config.counter_all_item_types.items():
                counter_element = self.identify_collection_point(counter)
                new_counter_all_item_types[counter_element] = all_item_types
        else:
            pass

        # instantiate small stock guard
        small_stock_guard = QuantityGuardSmallStock(counter_threshold=new_counter_threshold,
                                                    counter_all_item_types=new_counter_all_item_types,
                                                    all_counter_condition=small_stock_guard_config.all_counter_condition)
        # set small stock guard for transition
        self.quantity_net.set_quantity_guard(transition=transition, quantity_guard=small_stock_guard)

