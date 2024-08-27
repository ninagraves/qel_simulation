import uuid
from itertools import combinations, product
from typing import Type, Callable

from src.components.base_element import ConnectedElement
from src.components.log_elements.object import Object, BindingFunction, MultisetObject
from src.components.net_elements.collection_point import CollectionPoint, CollectionCounter
from src.components.net_elements.guard import Guard
from src.components.net_elements.object_arc import ObjectArc
from src.components.net_elements.object_place import ObjectPlace
from src.components.net_elements.qalculator import Qalculator, DefaulQalculator
from src.components.net_elements.qarc import Qarc


class TransitionExecution:

    def __init__(self, binding_function: BindingFunction, collected_quantity_operations: CollectionCounter):
        self.execution_id = uuid.uuid4()
        self.binding_function = binding_function
        self.collected_quantity_operations = collected_quantity_operations

class Transition(ConnectedElement):

    def __init__(self, name, label: str = None, properties: dict = None, qalculator: Qalculator = None):

        super().__init__(name, label, properties)
        self._silent = False if label else None
        self._executions = []
        self._guard = Guard()
        self._binding_function_quantities = None
        self._maximum_binding_function_quantities = None
        self._minimum_binding_function_quantities = None
        self._qalculator = None
        self._has_qalculator = False
        self._enabled_bindings_cache = None
        self.binding_recalculation_default = True # TODO: Binding Specification config
        self.return_single_binding = True # TODO: Binding Selection config
        self._binding_selection_function = None
        self.qalculator = qalculator if qalculator else DefaulQalculator()
        self._manually_initiated = False

    def __repr__(self):
        return f"{self.name} ({self.label})"

    @property
    def binding_selection_function(self):
        return True if self._binding_selection_function else False

    @binding_selection_function.setter
    def binding_selection_function(self, binding_selection_function: Callable):
        self._binding_selection_function = binding_selection_function

    @property
    def qalculator(self) -> Qalculator:
        return self._qalculator

    @qalculator.setter
    def qalculator(self, qalculator: Qalculator):
        if isinstance(self.qalculator, DefaulQalculator):
            self._has_qalculator = False
        else:
            pass

        qalculator.connected_counters = self.connected_counters
        self._qalculator = qalculator

    @property
    def manually_initiated(self):
        return self._manually_initiated

    @manually_initiated.setter
    def manually_initiated(self, manually_initiated: bool):
        self._manually_initiated = manually_initiated

    @property
    def has_qalculator(self):
        return self._has_qalculator

    @has_qalculator.setter
    def has_qalculator(self, has_qalculator: bool):
        self._has_qalculator = has_qalculator

    @property
    def quantity_state(self):
        return CollectionCounter({cp: cp.marking for cp in self.connected_counters})

    @property
    def silent(self):
        if self._silent is None:
            if self.label:
                return False
            else:
                return True
        else:
            return self._silent

    @silent.setter
    def silent(self, silent: bool):
        self._silent = silent

    @property
    def executions(self) -> list[TransitionExecution]:
        return self._executions

    @property
    def object_types(self) -> set[Type[Object]]:
        surrounding_places = list(self.input_places | self.output_places)
        return {place.object_type for place in surrounding_places}

    @property
    def input_object_types(self) -> set[Type[Object]]:
        return {place.object_type for place in self.inputs if isinstance(place, ObjectPlace)}

    @property
    def output_object_types(self) -> set[Type[Object]]:
        return {place.object_type for place in self.outputs if isinstance(place, ObjectPlace)}

    @property
    def quantity_arcs(self) -> set[Qarc]:
        return {arc for arc in self.arcs if isinstance(arc, Qarc)}

    @property
    def object_arcs(self) -> set[ObjectArc]:
        return {arc for arc in self.arcs if isinstance(arc, ObjectArc)}

    @property
    def variable_object_types(self) -> set[Type[Object]]:
        return {otype for otype, required_objects in self.binding_function_quantities.items() if
                not required_objects == 1}

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        if label:
            self.silent = False
            self._label = label
        else:
            self.silent = True

    @property
    def guard(self) -> Guard:
        return self._guard

    def set_object_guard(self, object_guard: Callable[[BindingFunction], bool]):
        self._guard.object_guard = object_guard

    def set_quantity_guard(self, quantity_guard: Callable[[BindingFunction, CollectionCounter], bool]):
        self._guard.quantity_guard = quantity_guard

    @property
    def input_places(self) -> set[ObjectPlace]:
        return {place for place in self.inputs if isinstance(place, ObjectPlace)}

    @property
    def input_counters(self) -> set[CollectionPoint]:
        return {place for place in self.inputs if isinstance(place, CollectionPoint)}

    @property
    def output_counters(self) -> set[CollectionPoint]:
        return {place for place in self.outputs if isinstance(place, CollectionPoint)}

    @property
    def connected_counters(self) -> set[CollectionPoint]:
        return set.union(self.input_counters, self.output_counters)

    @property
    def output_places(self) -> set[ObjectPlace]:
        return {place for place in self.outputs if isinstance(place, ObjectPlace)}

    @property
    def output_types_not_input_types(self) -> dict[Type[Object], int]:
        return {object_type: self.binding_function_quantities[object_type]
                for object_type in self.object_types.difference(self.input_object_types)}

    @property
    def binding_function_quantities(self):

        if self._binding_function_quantities:
            return self._binding_function_quantities
        else:
            object_types_list = list(self.object_types)
            one_per_object_type = dict(zip(object_types_list, [1] * len(object_types_list)))
            return one_per_object_type

    @binding_function_quantities.setter
    def binding_function_quantities(self, binding_object_quantities: dict[Type[Object]: int]):

        if set(binding_object_quantities.keys()) == self.object_types:
            self._binding_function_quantities = binding_object_quantities
        else:
            raise ValueError("Object types referred to in passed binding object quantities does not match with "
                             "transition object types.")

    @property
    def maximum_binding_function_quantities(self):

        if self._maximum_binding_function_quantities:
            return self._maximum_binding_function_quantities
        else:
            return self.binding_function_quantities

    @maximum_binding_function_quantities.setter
    def maximum_binding_function_quantities(self, maximum_binding_object_quantities: dict[Type[Object]: int]):

        if set(maximum_binding_object_quantities.keys()) == self.object_types:
            if all([maximum_binding_object_quantities[object_type] >= self.binding_function_quantities[object_type]
                    for object_type in self.object_types]):
                self._maximum_binding_function_quantities = maximum_binding_object_quantities
            else:
                raise ValueError("Maximum binding quantities must be greater or equal to the binding quantities.")
        else:
            raise ValueError("Object types referred to in passed binding object quantities does not match with "
                             "transition object types.")

    @property
    def minimum_binding_function_quantities(self):
        if self._minimum_binding_function_quantities:
            return self._minimum_binding_function_quantities
        else:
            return self.binding_function_quantities

    @minimum_binding_function_quantities.setter
    def minimum_binding_function_quantities(self, minimum_binding_object_quantities: dict[Type[Object]: int]):

        if set(minimum_binding_object_quantities.keys()) == self.object_types:
            if all([minimum_binding_object_quantities[object_type] <= self.maximum_binding_function_quantities[object_type]
                    for object_type in self.object_types if not self.maximum_binding_function_quantities[object_type] == 0]):
                self._minimum_binding_function_quantities = minimum_binding_object_quantities
            else:
                raise ValueError("Maximum binding quantities must be greater or equal to the binding quantities.")
        else:
            raise ValueError("Object types referred to in passed binding object quantities does not match with "
                             "transition object types.")

    def get_input_places_of_otype(self, object_type: Type[Object]) -> set[ObjectPlace]:
        return {oplace for oplace in self.input_places if oplace.object_type == object_type}

    def get_output_places_of_otype(self, object_type: Object) -> set[ObjectPlace]:
        return {oplace for oplace in self.output_places if oplace.object_type == object_type}

    def determine_new_binding_functions(self):
        """Returns all possible binding functions that are enabled under the current marking of the input places.
                Functionality: Iterate through input object types: get set of tokens available in all places of
                the same type. Check if required number of tokens available. Create all possible combinations to fulfill
                requirements per object type. Create all possible combinations from all object types. Check if resulting binding
                function is enabled in light of guard.
                Check if bindings are also enabled considering the connected quantity conditions using the quantity calculator.
                If the quantity calculator is an IndependentWeight of the binding, quantity conditions are independent of the
                object binding. In that case, checking quantity conditions in the beginning is sufficient. If quantity
                conditions are not met the calculation of possible object bindings can be skipped, returning no enabled bindings.
                If the are, no checking for each binding is necessary. For Dependent weights, the quantity conditions are
                checked for every possible binding and only quantity enabled bindings are returned."""
        # print("#####", self.label)

        object_type_sets = dict()
        # print(f"Input object types: {self.input_object_types}")

        for object_type in self.input_object_types:
            object_sets = []
            required_objects = self.binding_function_quantities[object_type]
            minimum_objects = self.minimum_binding_function_quantities[object_type]
            maximum_objects = self.maximum_binding_function_quantities[object_type]
            # print(f"Object type: {object_type.object_type_name}, required: {required_objects}, min: {minimum_objects}, max: {maximum_objects}")

            # get objects that are part of all input places of that type
            marking_intersection = self._input_places_marking_intersection(object_type=object_type)
            marking_intersection_active = {obj for obj in marking_intersection if obj.status_active}
            # print(f"Marking intersection of {object_type.object_type_name}: {marking_intersection_active}")

            # create all combinations of subsets of available objects required length
            if len(marking_intersection_active) >= required_objects:  # make sure enough are available of this type
                # print(f"Enough objects of {object_type.object_type_name} available.")
                if required_objects == 0:
                    if maximum_objects == 0:  # if truly variable requirement: all subsets of all possible sizes
                        for subset_size in range(minimum_objects, len(marking_intersection_active) + 1):
                            subsets = [set(combination) for combination in
                                       combinations(marking_intersection_active, subset_size)]
                            object_sets.extend(subsets)
                        if minimum_objects == 0:
                            object_sets.append(set())
                        else:
                            pass
                    else:  # if maximum number of objects is set, create all subsets up to maximum size
                        for subset_size in range(minimum_objects, maximum_objects + 1):
                            subsets = [set(combination) for combination in
                                       combinations(marking_intersection_active, subset_size)]
                            object_sets.extend(subsets)
                        if minimum_objects == 0:
                            object_sets.append(set())
                        else:
                            pass
                else:  # create all subsets of required size
                    subsets = [set(combination) for combination in
                               combinations(marking_intersection_active, required_objects)]
                    object_sets.extend(subsets)

                object_type_sets[object_type] = object_sets

            else:
                # not enough input objects means that no binding function can be enabled
                return None
            # print(f"Object sets of {object_type.object_type_name}: {object_sets}")

        if not object_type_sets:
            possibly_enabled_binding_functions = [BindingFunction()]
        else:
            # create all possible sets of tokens containing one subset of available tokens for each object type
            object_type_keys = list(object_type_sets.keys())

            # select one subset per dict entry
            all_combinations = product(*(object_type_sets[key] for key in object_type_keys))

            # create new dict per possible combination
            possibly_enabled_binding_functions = [BindingFunction((zip(object_type_keys, combination)))
                                                  for combination in all_combinations]

        # check if binding fulfills guard requirements - object and quantity conditions
        enabled_bindings = [binding_function for binding_function in possibly_enabled_binding_functions
                            if self.guard(binding_function=binding_function,
                                          quantity_state=self.quantity_state)]

        if enabled_bindings:
            return enabled_bindings
        else:
            return None

    def get_enabled_binding_functions_inputs(self) -> list[BindingFunction] | None:
        """Save processing time by returning cached enabled bindings. If no cached bindings are available, determine new
                bindings. Also creates a pseudo-first-in-first-out order of bindings if FIFO binding selection is enabled."""

        if self.binding_selection_function:
            return self._binding_selection_function(self)
        else:
            pass

        if self.binding_recalculation_default:
            # check if the cached bindings are still enabled. If yes, return them.
            if self.return_single_binding:
                if self._enabled_bindings_cache is not None:
                    # remove bindings as long as an enabled binding is found and return it.
                    while len(self._enabled_bindings_cache) > 0:
                        binding_function = self._enabled_bindings_cache.pop(0)
                        if self.enabled(binding_function=binding_function, only_input=True):
                            return [binding_function]
                        else:
                            pass

                else:
                    pass

                enabled_bindings = self.determine_new_binding_functions()
                if enabled_bindings:
                    if len(enabled_bindings) > 1:
                        binding_function = enabled_bindings.pop(0)
                        self._enabled_bindings_cache = enabled_bindings
                        return [binding_function]
                    else:
                        self._enabled_bindings_cache = None
                else:
                    self._enabled_bindings_cache = None

                return enabled_bindings

            else:
                if self._enabled_bindings_cache is not None:
                    enabled_bindings = [binding_function for binding_function in self._enabled_bindings_cache if
                                    self.enabled(binding_function=binding_function, only_input=True)]

                    if len(enabled_bindings) > 0:
                        self._enabled_bindings_cache = enabled_bindings
                        return enabled_bindings
                    else:
                        pass
                else:
                    pass

                enabled_bindings = self.determine_new_binding_functions()
                self._enabled_bindings_cache = enabled_bindings
                return enabled_bindings

        else:
            return self.determine_new_binding_functions()

    def _input_places_marking_intersection(self, object_type: Type[Object]) -> set[Object] | set[None]:
        """Pass object type, returns set of objects which are part of the marking of all input places of this type."""

        places_of_type = self.get_input_places_of_otype(object_type=object_type)
        markings_of_places = [place.marking for place in places_of_type]
        marking_intersection = MultisetObject.intersection(*markings_of_places)

        return marking_intersection


    def _binding_enabled(self, binding_function: BindingFunction, only_input: bool = False) -> bool:
        """
        Checks whether a provided binding function dict {object_type: set of objects} can be executed with regard to the
        validity of the binding function and the availability of objects.

        Iterates through all connected object types (if dict does not contain a key value referring to one of these
        types, the programme is halted): 1) checks whether the corresponding set contains exactly one element (if not,
        only continues if object type is variable), 2) creates intersection of all input places of the corresponding
        input type, 3) checks the set of object is a subset of the place markings. Returns True only if 3) is True for all
        object types.
        Requirements:
        - binding function uses the classes of the ObjectTypes as keys and has a set of objects as value.
        - All none-variable object types refer to a set containing exactly one object.
        - binding function refers to every one of the object types the transition is connected to. If no object of a
        variable object type should be considered, the set is empty.
        :param binding_function:
        :return: True if binding function can be executed, False if not.
        """

        object_types_to_consider = self.input_object_types if only_input else self.object_types
        for object_type in object_types_to_consider:
            if object_type in binding_function.keys():
                objects = binding_function[object_type]
            else:
                raise ValueError(f"Passed binding function must contain every object type the transition refers to. This is not the case for {self.name} with object types {self.object_types} and binding function {binding_function}.")

            # make sure binding function contains at least required number of objects per type.
            if self.binding_function_quantities[object_type] == 0:
                if self.maximum_binding_function_quantities[object_type] == 0:
                    pass
                else:
                    # make sure it doesn't have more than maximum number of objects of that type
                    if len(objects) > self.maximum_binding_function_quantities[object_type]:
                        return False
                    else:
                        pass
                    # make sure it has at least minimum number of objects of that type
                    if len(objects) < self.minimum_binding_function_quantities[object_type]:
                        return False
                    else:
                        pass
            elif len(objects) != self.binding_function_quantities[object_type]:
                return False
            else:
                pass

            # marking check must only be done for input object types.
            if object_type in self.input_object_types:
                pass
            else:
                continue

            # get intersection of all markings of places of corresponding object type
            marking_intersection = self._input_places_marking_intersection(object_type=object_type)

            # make sure that the referenced objects are part of all places of that type
            if objects.issubset(marking_intersection):
                pass
            else:
                return False

        return True

    def enabled(self, binding_function: BindingFunction, only_input: bool = False) -> bool:
        """ Returns True if quantity net is enabled under provided binding function."""

        if self._binding_enabled(binding_function=binding_function, only_input=only_input):
            if self.guard(binding_function=binding_function, quantity_state=self.quantity_state):
                return True
            else:
                return False
        else:
            return False

    def start_firing(self, binding_function: BindingFunction):
        """Check if passed binding function is enabled. If so, remove objects from input places, and remove items from
        collection points. Store binding function, to keep track of begun functions."""

        # check binindng is really enabled
        if self.enabled(binding_function=binding_function):
            pass
        else:
            raise ValueError(f"Binding function {binding_function} is not enabled for transition {self.name}.")

        # OCPN firing
        for object_type, objects in binding_function.items():
            places_of_type = self.get_input_places_of_otype(object_type=object_type)

            for place in places_of_type:
                place.remove_tokens(objects)

        # Execute quantity operations
        quantity_operations = self.qalculator.determine_quantity_operations(binding_function=binding_function,
                                                                                      quantity_state=self.quantity_state)
        # print(f"Quantity operation of {self} with {binding_function}: {quantity_operations}")

        self.execute_quantity_operations(quantity_operations=quantity_operations)

        # add binding to active executions
        transition_execution = self._add_execution(binding_function=binding_function,
                            collected_quantity_operations=quantity_operations)

        return transition_execution

    def end_firing(self, execution: uuid.UUID | TransitionExecution):
        """Release objects into output places and items into collection points if binding function was used to begin firing."""

        execution = self._identify_execution(transition_execution=execution)

        # OCPN firing
        for object_type, objects in execution.binding_function.items():
            places_of_type = self.get_output_places_of_otype(object_type=object_type)

            for place in places_of_type:
                place.add_tokens(objects)

        # remove binding from active executions
        self._remove_execution(transition_execution=execution)

    def _add_execution(self, binding_function: BindingFunction, collected_quantity_operations: CollectionCounter):
        transition_execution = TransitionExecution(binding_function=binding_function, collected_quantity_operations=collected_quantity_operations)
        self._executions.append(transition_execution)
        return transition_execution

    def _remove_execution(self, transition_execution: TransitionExecution):
        if transition_execution in self.executions:
            self._executions.remove(transition_execution)
        else:
            raise ValueError(f"No active execution {transition_execution} in transition {self.name}.")

    def _identify_execution(self, transition_execution: uuid.UUID | TransitionExecution) -> TransitionExecution:

        if transition_execution in self.executions:
            return transition_execution
        elif isinstance(transition_execution, uuid.UUID):
            for ex in self.executions:
                if ex.execution_id == transition_execution:
                    return ex
                else:
                    raise ValueError(f"No execution with id {transition_execution} is a active in transition {self.name}.")
        else:
            raise ValueError(f"Execution {transition_execution} cannot be identified -- passed element must be execution id "
                             f"(uuid) or execution object.")

    def execute_complete_firing(self, binding_function: BindingFunction):
        """Execute start and end of firing of transition."""

        execution = self.start_firing(binding_function=binding_function)
        self.end_firing(execution = execution)

    def execute_quantity_operations(self, quantity_operations: CollectionCounter):
        """Execute quantity operations on connected counters."""
        for counter, operation in quantity_operations.items():
            # print(f"Executing quantity operation {operation} on {counter}")
            # print(f"  Marking before operation: {counter.marking}")
            counter.update_marking(quantity_update=operation)
            # print(f"  Marking before operation: {counter.marking}")
