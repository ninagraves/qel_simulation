import uuid
from collections import Counter
from typing import Type, Callable

from qel_simulation.components.base_element import BaseElement, ConnectedElement
from qel_simulation.simulation.execution import Execution
from qel_simulation.simulation.object import Object
from qel_simulation.qnet_elements.arc import Arc
from qel_simulation.qnet_elements.collection_point import CollectionPoint, CollectionCounter
from qel_simulation.qnet_elements.guard import QuantityGuardSmallStock, QuantityGuard
from qel_simulation.qnet_elements.object_arc import ObjectArc
from qel_simulation.qnet_elements.object_place import ObjectPlace
from qel_simulation.qnet_elements.place import Place
from qel_simulation.qnet_elements.qalculator import Qalculator
from qel_simulation.qnet_elements.qarc import Qarc
from qel_simulation.qnet_elements.transition import Transition, BindingFunction, TransitionExecution


# assumption: Provided OCPN is well-formed.


class QuantityNet(BaseElement):
    def __init__(self, name, label: str = None, properties: dict = None):
        super().__init__(name=name, label=label, properties=properties)
        self._places = set()
        self._transitions = set()
        self._arcs = set()
        self.executions = []

    @property
    def places(self):
        return self._places

    @places.setter
    def places(self, places: set[places]):
        if isinstance(places, (set, list, tuple)):
            if all(isinstance(element, Transition) for element in places):
                self._transitions = places
            else:
                raise ValueError("Passed transitions must be a set of Transition objects.")
        else:
            raise ValueError("Passed transitions must be a set of Transition objects.")

    @property
    def object_types(self):
        return {place.object_type for place in self.places if isinstance(place, ObjectPlace)}

    @property
    def labelled_transitions(self):
        return {transition for transition in self.transitions if not transition.silent}

    @property
    def nodes(self):
        return self._places | self._transitions

    @property
    def collection_points(self):
        return {place for place in self.places if isinstance(place, CollectionPoint)}

    @property
    def object_places(self):
        return {place for place in self.places if isinstance(place, ObjectPlace)}

    @property
    def transitions(self):
        return self._transitions

    @transitions.setter
    def transitions(self, transitions: set[Transition]):
        if isinstance(transitions, (set, list, tuple)):
            if all(isinstance(element, Transition) for element in transitions):
                self._transitions = transitions
            else:
                raise ValueError("Passed transitions must be a set of Transition objects.")
        else:
            raise ValueError("Passed transitions must be a set of Transition objects.")


    @property
    def arcs(self):
        return self._arcs

    @arcs.setter
    def arcs(self, arcs: set[arcs]):
        if isinstance(arcs, (set, list, tuple)):
            if all(isinstance(element, Arc) for element in arcs):
                self._arcs = arcs
            else:
                raise ValueError("Passed arcs must be a set of Arc objects.")
        else:
            raise ValueError("Passed arcs must be a set of Arc objects.")


    @property
    def variable_arcs(self):
        return {arc for arc in self.arcs if isinstance(arc, ObjectArc) and arc.variable}

    @property
    def quantity_arcs(self):
        return {arc for arc in self.arcs if isinstance(arc, Qarc)}

    @property
    def object_arcs(self):
        return self.arcs - self.variable_arcs - self.quantity_arcs

    @property
    def transition_labels(self):
        return {transition: transition.label for transition in self.transitions if transition.label}

    @property
    def place_mapping(self):
        return {place: place.object_type for place in self.object_places}

    @property
    def silent_transitions(self):
        return {transition for transition in self.transitions if transition.silent}

    @property
    def initial_places(self):
        return {place for place in self.places if place.initial}

    @property
    def final_places(self):
        return {place for place in self.places if place.final}

    @property
    def marking(self):
        return {place: place.marking for place in self.places}

    @property
    def transitions_output_types_not_input(self) -> dict[Transition: dict[Type[Object]: int]]:
        return {transition: transition.output_types_not_input_types for transition in self.transitions}

    @property
    def quantity_transitions(self) -> set[Transition]:
        return {arc.transition for arc in self.quantity_arcs}

    @property
    def quantity_transition_labels(self) -> set[str]:
        return {transition.label for transition in self.quantity_transitions}

    @property
    def quantity_state(self) -> CollectionCounter:
        quantity_state = CollectionCounter()
        for cp in self.collection_points:
            quantity_state[cp] = cp.marking
        return quantity_state

    def set_initial_places(self, initial_places: set[Place | str]):

        for place in initial_places:
            if isinstance(place, str):
                place_element = self.identify_node(node=place, element_type="place")
                if place_element:
                    pass
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            elif isinstance(place, Place):
                if place in self.places:
                    place_element = place
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            else:
                raise ValueError(f"Passed place {place} is not a place in the net.")

            if isinstance(place_element, ObjectPlace):
                pass
            else:
                raise ValueError(f"Passed place {place} is not an ObjectPlace and cannot be set as initial place.")

            place_element.initial = True

    def set_final_places(self, final_places: set[Place | str]):

        for place in final_places:
            if isinstance(place, str):
                place_element = self.identify_node(node=place, element_type="place")
                if place_element:
                    pass
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            elif isinstance(place, Place):
                if place in self.places:
                    place_element = place
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            else:
                raise ValueError(f"Passed place {place} is not a place in the net.")

            if isinstance(place_element, ObjectPlace):
                pass
            else:
                raise ValueError(f"Passed place {place} is not an ObjectPlace and cannot be set as final place.")

            place_element.final = True

    def set_transition_labels(self, transition_labels: dict[str | Transition | uuid.UUID, str]):
        """
        Pass dict of transitions and their labels to set labels accordingly, sets labels of transitions in net.
        Iteration per entry: identify transition in net, set label attribute to passed label.
        Requirements:
        - Passed Parameter must be dict
        - Identification of transition (transition object, name, id or current label)
        - Referenced transition must be part of net
        Caught Problems: Passed parameter type (this function), node identification (identify_node),
        none-identifiable transition.
        :param transition_labels: dict {transition, label}
        :return: -
        """
        if isinstance(transition_labels, dict):
            pass
        else:
            raise ValueError("Passed transition labels must be described as dict {transition: label}")

        for transition, label in transition_labels.items():

            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            transition_element.label = label

    def set_collection_point_labels(self, cp_labels: dict[str | CollectionPoint | uuid.UUID, str]):
        """
        Pass dict of collection points and their labels to set labels accordingly, sets labels of cps in net.
        Iteration per entry: identify cp in net, set label attribute to passed label.
        Requirements:
        - Passed Parameter must be dict
        - Identification of collection point (cp object, name, id or current label)
        - Referenced cp must be part of net
        Caught Problems: Passed parameter type (this function), node identification (identify_node),
        none-identifiable transition.
        :param cp_labels: dict {cp, label}
        :return: -
        """
        if isinstance(cp_labels, dict):
            pass
        else:
            raise ValueError("Passed collection point labels must be described as dict {collection_point: label}")

        for cp, label in cp_labels.items():

            if isinstance(cp, CollectionPoint) and cp in self.collection_points:
                cp_element = cp
            else:
                cp_element = self.identify_node(node=cp, element_type="collection point")
                if isinstance(cp_element, CollectionPoint):
                    pass
                else:
                    raise ValueError(f"Passed Collection Point {cp} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            cp_element.label = label

    def set_object_guard(self, transition: Transition | str | uuid.UUID,
                         object_guard: Callable[[BindingFunction], bool]):

        if isinstance(transition, Transition) and transition in self.transitions:
            transition_element = transition
        else:
            transition_element = self.identify_node(node=transition, element_type="transition")
            if isinstance(transition_element, Transition):
                pass
            else:
                raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                 f"Define net using method 'set_net_structure'.")

        if callable(object_guard):
            transition_element.set_object_guard(object_guard)
        else:
            raise ValueError(f"Passed object guard for transition {transition} must be a function taking an object of "
                             f"class BindingFunction as input and return a boolean.")

    def set_quantity_guard(self, transition: Transition | str | uuid.UUID,
                         quantity_guard: QuantityGuard | Callable[[BindingFunction, CollectionCounter], bool]):

        if isinstance(transition, Transition) and transition in self.transitions:
            transition_element = transition
        else:
            transition_element = self.identify_node(node=transition, element_type="transition")
            if isinstance(transition_element, Transition):
                pass
            else:
                raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                 f"Define net using method 'set_net_structure'.")

        if transition_element.guard.quantity_guard:
            raise Warning(f"Transition already has a quantity guard, previous quantity guard is now being overwritten.")
        else:
            pass

        if callable(quantity_guard):
            transition_element.set_quantity_guard(quantity_guard)
        elif isinstance(quantity_guard, QuantityGuardSmallStock):
            transition_element.set_quantity_guard(quantity_guard)
        else:
            raise ValueError(f"Passed quantity guard for transition {transition} must be a function taking an objects of "
                             f"class BindingFunction and class CollectionCounter as inputs and return a boolean.")

    def set_binding_function_specification(self, transition_binding_specification: dict[
                                                                                (Transition | str | uuid.UUID): dict[
                                                                                                                Type[
                                                                                                                    Object]: int]]):

        for transition, binding_object_quantities in transition_binding_specification.items():
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            if isinstance(binding_object_quantities, dict):
                transition_element.binding_function_quantities = binding_object_quantities
            else:
                raise ValueError("Passed number of required objects per object type for transition {transition} must "
                                 "be a dict of {ObjectType: int}.")

    def set_maximum_binding_function_specification(self, transition_maximum_binding_specification: dict[
                                                                                (Transition | str | uuid.UUID): dict[
                                                                                                                Type[
                                                                                                                    Object]: int]]):

        for transition, maximum_binding_object_quantities in transition_maximum_binding_specification.items():
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            if isinstance(maximum_binding_object_quantities, dict):
                transition_element.maximum_binding_function_quantities = maximum_binding_object_quantities
            else:
                raise ValueError(f"Passed number of required objects per object type for transition {transition} must "
                                 "be a dict of {ObjectType: int}.")

    def set_minimum_binding_function_specification(self, transition_minimum_binding_specification: dict[
                                                                                (Transition | str | uuid.UUID): dict[
                                                                                                                Type[
                                                                                                                    Object]: int]]):

        for transition, minimum_binding_object_quantities in transition_minimum_binding_specification.items():
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            if isinstance(minimum_binding_object_quantities, dict):
                transition_element.minimum_binding_function_quantities = minimum_binding_object_quantities
            else:
                raise ValueError(f"Passed number of required objects per object type for transition {transition} must "
                                 "be a dict of {ObjectType: int}.")

    def set_transition_binding_selection(self, transition_binding_selection: dict[Transition | str | uuid.UUID:
                                                                                 Callable[[Transition], list[BindingFunction]]]):

        for transition, binding_selection in transition_binding_selection.items():
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")

            if isinstance(binding_selection, Callable):
                transition_element.binding_selection_function = binding_selection
            else:
                raise ValueError(f"Passed binding selection for transition {transition} must be a function.")

    def set_qalculator(self, transition_calculator: dict[Transition | str | uuid.UUID:
                                                                   Qalculator]):

        for transition, qalculator in transition_calculator.items():

            transition_element = self.identify_node(node=transition, element_type="transition")

            if isinstance(qalculator, Qalculator):
                transition_element.qalculator = qalculator
            else:
                raise ValueError(f"Passed calculator {qalculator} is not a valid calculator. "
                                 f"Must be Qalculator object.")

    def set_place_types(self, place_mapping: dict[ObjectPlace | str, Type[Object]]):
        """
        Update places according to passed dictionary of ObjectPlaces and their corresponding ObjectType (class).
        Functionality:
        Iteration per place-type pair: Identify and validate objectplaces, set object type
        Requirements:
        - Passed place must be or reference an object of type ObjectType.
        - place must be part of the net.
        - objecttype must be class
        :param place_mapping: dict {place: ObjectType} - place must be either str or object
        :return: -
        """

        for place, otype in place_mapping.items():

            # validate place object
            if isinstance(place, str):
                place_element = self.identify_node(node=place, element_type="place")
                if place_element:
                    if isinstance(place_element, ObjectPlace):
                        pass
                    else:
                        raise ValueError(f"Passed place {place} is a collection point and cannot be assigned an object "
                                         f"type.")
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            elif isinstance(place, ObjectPlace):
                if place in self.places:
                    place_element = place
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")

            else:
                raise ValueError(f"Passed place {place} is not an ObjectPlace in the net.")

            # assign object type to place
            place_element.object_type = otype

    def set_net_structure(self, arcs: set | list[tuple[str, str]]) -> (list[Transition | ObjectPlace | CollectionPoint],
                                                                       list[Qarc | ObjectArc]):
        """
        Pass set of arcs, elements will be created and list of elements will be returned.
        Functionality:
        Check if input is collection of 2-tuples, Reset net structure, iterate through 2-tuples:
        check if nodes exist in net - if yes: pass, if no: create and add to net structure; create correct type of arc;
        add arc to net structure; add arc to source's output arcs and target's input arcs; set initial and final places;
        return arc objects in order of creation.
        Adds arc for every entry - even if an arc between the same source and target already exists.
        Requirements:
        - Passed Parameter must be set/list of 2-tuples.
        - Source and target must begin with p if object-place, t if transition and c if collection point.
        - The same node must be referenced with the same name in passed set.
        - Every arc must contain exactly one element beginning with t (checked in arc creation)
        Caught Problems: Passed parameter type (function), non-specified element type by p/t/d of source and target
         (this method).
        :param arcs: set/list of 2-tuples, each entry beginning with p, d or t
        :return: List of arc objects
        """

        # reset net structure
        self._places = set()
        self._transitions = set()
        self._arcs = set()
        node_elements = []
        arc_elements = []

        # add arcs elements and arcs to net structure
        for (source, target) in arcs:

            ##### identify or create source and target objects #####

            # identify or source element if available
            if source.startswith("t"):
                source_element = self.identify_node(source, "transition")

            elif source.startswith("p"):
                source_element = self.identify_node(source, "place")

            elif source.startswith("c"):
                source_element = self.identify_node(source, "collection point")

            else:
                raise ValueError(f"Passed node names must either begin wit p (to create an object place) or "
                                 f"t (for a transition). Quantity arcs are defined separately.")

            # identify or target element if available
            if target.startswith("t"):
                target_element = self.identify_node(target, "transition")

            elif target.startswith("p"):
                target_element = self.identify_node(target, "place")

            elif target.startswith("c"):
                target_element = self.identify_node(target, "collection point")

            else:
                raise ValueError(f"Passed node names must either begin wit p (to create an object place) or "
                                 f"t (for a transition). Quantity arcs are defined separately.")

            # create and add source if needed
            if source_element:
                pass
            else:
                source_element = self.create_and_add_node(name=source)
                node_elements.append(source_element)

            # create and add target if needed
            if target_element:
                pass
            else:
                target_element = self.create_and_add_node(name=target)
                node_elements.append(target_element)

            ##### create arc #####
            c1 = isinstance(source_element, Transition) and isinstance(target_element, Place)
            c2 = isinstance(source_element, Place) and isinstance(target_element, Transition)

            if c1 or c2:
                pass
            else:
                raise ValueError(f"Every arc must contain exactly one transition.")

            if isinstance(source_element, ObjectPlace) or isinstance(target_element, ObjectPlace):
                new_arc = self.create_and_add_object_arc(source=source_element, target=target_element)
                arc_elements.append(new_arc)
            else:
                new_arc = self.create_and_add_quantity_arc(source=source_element, target=target_element)
                arc_elements.append(new_arc)

        # set initial and final places
        for place in self.object_places:
            if place.input_arcs:
                pass
            else:
                place.initial = True

            if place.output_arcs:
                pass
            else:
                place.final = True

        return node_elements, arc_elements

    def create_and_add_qarc(self, transition: Transition | str | uuid.UUID, collection_point: CollectionPoint | str | uuid.UUID):

        transition_element = self.identify_node(node=transition, element_type="transition")
        collection_point_element = self.identify_node(node=collection_point, element_type="collection point")

        _ = self.create_and_add_quantity_arc(source=transition_element, target=collection_point_element)

        return

    def set_silent_transitions(self, silent_transitions: set[Transition | str | uuid.UUID]):
        """
        Pass set of transitions, set transitions to silent.
        Functionality:
        Iterate through passed set, identify transition in net, set silent attribute to True.
        Requirements:
        - Passed Parameter must be set of transitions.
        - Transition must be part of net.
        Caught Problems: Passed parameter type (function), node identification (identify_node)"""

        for transition in silent_transitions:
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")
            transition_element.silent = True


    def set_manually_initiated_transitions(self, manually_initiated_transitions: set[Transition | str | uuid.UUID]):
        """
        Pass set of transitions, set transitions to manually initiated.
        Functionality:
        Iterate through passed set, identify transition in net, set silent attribute to True.
        Requirements:
        - Passed Parameter must be set of transitions.
        - Transition must be part of net.
        Caught Problems: Passed parameter type (function), node identification (identify_node)"""

        for transition in manually_initiated_transitions:
            if isinstance(transition, Transition) and transition in self.transitions:
                transition_element = transition
            else:
                transition_element = self.identify_node(node=transition, element_type="transition")
                if isinstance(transition_element, Transition):
                    pass
                else:
                    raise ValueError(f"Passed Transition {transition} is not part of the net. "
                                     f"Define net using method 'set_net_structure'.")
            transition_element.manually_initiated = True


    def create_and_add_quantity_arc(self, source: Transition | CollectionPoint, target: Transition | CollectionPoint):

        if isinstance(source, ConnectedElement) and isinstance(target, ConnectedElement):
            pass
        else:
            raise ValueError("Passed source and target must be objects and item types must be a set.")

        if source in list(self.nodes) and target in list(self.nodes):

            # check if collection point is attached to intended arc
            if isinstance(source, CollectionPoint) or isinstance(target, CollectionPoint):
                pass
            else:
                raise ValueError("Qarcs connnect transitions and collection points.")

            # check if transition is attached to intended arc
            if isinstance(source, Transition) or isinstance(target, Transition):
                pass
            else:
                raise ValueError("Qarcs connnect transitions and collection points.")

            qarc = Qarc(source=source, target=target)
            self._add_arc(qarc)
            return qarc
        else:
            raise ValueError("Arcs must connect existing nodes.")


    def create_and_add_node(self, name: str):
        """
        Pass object name, returns correct type of object with that name.
        Check input parameter type, create appropriate object, add object to net structure.
        Requirements:
        - Passed name must be String.
        - Passed name must begin with p, d or t.
        - If element should be transition, must begin with t, if place name must begin with p,
        if collection point name must begin with c.
        Caught Problems: Passed parameter type (this method), non-specified element type (p/t/d)
        :param name: String, must begin with p if ObjectPlace, c if CollectionPoint, t if Transition
        :return: Object
        """
        if isinstance(name, str):
            pass
        else:
            raise ValueError("Passed name for object creation isn't string.")

        if name.startswith("t"):
            element = Transition(name=name)
            self._add_transition(element)
            return element
        elif name.startswith("p"):
            element = ObjectPlace(name=name)
            self._add_object_place(element)
            return element
        elif name.startswith("c"):
            element = CollectionPoint(name=name)
            self._add_collection_point(element)
            return element
        else:
            raise ValueError(f"Specify type of node you want to create by starting name with either "
                             f"p (to create a place), t (for a transition) or cp (collection point).")

    def create_and_add_collection_point(self, name: str):
        element = CollectionPoint(name=name)
        self._add_collection_point(element)
        return element


    def create_and_add_object_arc(self, source: Transition | ObjectPlace,
                                  target: Transition | ObjectPlace):
        """
        Pass source object and target object, get corresponding added arc object.
        If the corresponding place is of type ObjectPlace ObjectArc is created,
        if corresponding place is DecouplingPoint QuantityArc is created,
        created arc is added to net, add arc to source's output and target's input.
        Requirements:
        - Source and target must be objects.
        - Source and target must be part of net.
        - One of source and target must be transition, the other either ObjectPlace or CollectionPoint.
        Caught Problems: Parameters non-objects (this method), Parameters not part of net (this method), place and
        transition in source and target (init arc), ObjectPlace xor CollectionPoint in source and target (this method)
        :param source: object Transition | ObjectPlace | CollectionPoint
        :param target: object Transition | ObjectPlace | CollectionPoint
        :return: object (ObjectArc or QuantityArc)
        """
        if isinstance(source, ConnectedElement) and isinstance(target, ConnectedElement):
            if source in list(self.nodes) and target in list(self.nodes):
                if isinstance(source, ObjectPlace) or isinstance(target, ObjectPlace):
                    new_arc = ObjectArc(source=source, target=target)
                else:
                    raise ValueError("Arc must be connected to either an object place or a collection point.")
            else:
                raise ValueError("Arcs must connect existing nodes.")

            # create arc and add to the net
            self._add_arc(new_arc)
            return new_arc

        else:
            raise ValueError("Arcs can only be created if source element and target elements are objects.")

    def _add_transition(self, transition: Transition):
        if isinstance(transition, Transition):
            self._transitions.add(transition)
        else:
            raise ValueError("Passed transition is not an object of type transition.")

    def _add_arc(self, arc: ObjectArc | Qarc):
        if isinstance(arc, (ObjectArc | Qarc)):

            source = arc.source
            target = arc.target

            # source and target must be part of net
            if source in self.nodes and target in self.nodes:
                pass
            else:
                raise ValueError(f"Source {source} and/or target {target} are not part of the net. "
                                 f"The corresponding arc cannot be added.")

            # add arc to node's input and output arcs
            arc.source.add_output_arc(arc=arc)
            arc.target.add_input_arc(arc=arc)

            # add arc to the net
            self._arcs.add(arc)
        else:
            raise ValueError("Passed arc is neither object arc nor quantity arc.")

    def _add_object_place(self, place: ObjectPlace):
        if isinstance(place, ObjectPlace):
            self._places.add(place)
        else:
            raise ValueError("Passed place is not an object of type objectplace.")

    def _add_collection_point(self, cp: CollectionPoint):
        if isinstance(cp, CollectionPoint):
            self._places.add(cp)
        else:
            raise ValueError("Passed collection point is not an object of type CollectionPoint.")

    def identify_node(self, node: uuid.UUID | str | Transition | CollectionPoint | ObjectPlace,
                      element_type: str = None):
        """
        Pass either id, name or label of a node, get corresponding object if part of net. Pass optional element type
        parameter for more targeted search (increases performance).
        If passed data type of node is object, check if object is part of net - if not: return None, else: return object.
        If data type uuid.UUID, searches for an object in the net with the same uuid.
        If data type is string, first searches for an object with corresponding name and if that does not result in
        a finding, searches in object labels. Returns either corresponding object or None.
        Requirements:
        - Node parameter must be string, uuid or object.
        - Searched object must be part of net.
        Caught Problems: Parameter input other than uuid, string or object (this method), different spellings of element
        types (search-specific methods), identification result not unique (search-specific methods)
        :param node: name, id or label of a node in the net.
        :param element_type: transition or place or collection_point
        :return: object or None
        """

        if isinstance(node, (Place, Transition)):
            if node in self.nodes:
                return node
            else:
                return None
        else:
            pass

        if isinstance(node, uuid.UUID):
            return self._identify_node_by_id(identifier=node, element_type=element_type)
        else:
            pass

        if isinstance(node, str):
            result_name = self._identify_node_by_name(name=node, element_type=element_type)
            if result_name:
                return result_name
            else:
                return self._identify_node_by_label(label=node, element_type=element_type)
        else:
            raise ValueError(f"To identify object you must pass either object, string or uuid.")

    def _identify_node_by_id(self, identifier: uuid.UUID, element_type: str = None):
        """
        Pass ID and receive object if exists, If element type known: pass to make more efficient.
        :param identifier: uuid
        :param element_type: place, transition, collection point, arc, quantity arc (optional)
        :return: object or None if doesn't exist
        """
        if element_type:
            if element_type in ["place", "places" "p", Place, "object place", "objectplace", ObjectPlace, "ObjectPlace",
                                "object_place", "collection point", "collection points", "collection_point",
                                "collection_points", "cp", "cps", CollectionPoint]:
                places = self.places
                matching_name = [element for element in places if element.id == identifier]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed id {identifier} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            elif element_type in ["transition", "transitions", "t", Transition]:
                transitions = self.transitions
                matching_name = [element for element in transitions if element.id == identifier]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed id {identifier} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            elif element_type in ["arc", "a", "objectarc", "object_arc", "ObjectArc", "quantity arc",
                                  "quantity_arc", "qa"]:
                arcs = self.arcs
                matching_name = [element for element in arcs if element.id == identifier]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed id {identifier} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            else:
                raise ValueError(f"Element type {element_type} not identified. "
                                 f"Valid types: place, transition, collection point, arc, quantity arc")

        else:
            matching_name = [element for element in (self.nodes | self.arcs) if element.id == identifier]
            if len(matching_name) == 1:
                return matching_name[0]
            elif len(matching_name) == 0:
                return None
            else:
                raise ValueError(f"Passed id {identifier} cannot be uniquely identified. "
                                 f"More than one object arc between the same two nodes in the same direction "
                                 f"does not make any sense. Define a net structure with only a single such arc.")

    def _identify_node_by_name(self, name: str, element_type: str = None):
        """
        Pass name and receive object with that label. If element type known: pass to make more efficient.
        :param name: name of object
        :param element_type: place, transition, collection point, arc, quantity arc (optional)
        :return: object or None if doesn't exist
        """
        if element_type:
            if element_type in ["place", "places" "p", Place, "object place", "objectplace", ObjectPlace, "ObjectPlace",
                                "object_place", "collection point", "collection points", "collection_point",
                                "collection_points", "cp", "cps", CollectionPoint]:
                places = self.places
                matching_name = [element for element in places if element.name == name]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed name {name} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            elif element_type in ["transition", "transitions", "t", Transition]:
                transitions = self.transitions
                matching_name = [element for element in transitions if element.name == name]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed name {name} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            else:
                raise ValueError(f"Element type {element_type} not identified. "
                                 f"Valid types: place, transition, collection point, arc, quantity arc")

        else:
            matching_name = [element for element in self.nodes if element.name == name]
            if len(matching_name) == 1:
                return matching_name[0]
            elif len(matching_name) == 0:
                return None
            else:
                raise ValueError(f"Passed name {name} cannot be uniquely identified. "
                                 f"More than one object arc between the same two nodes in the same direction "
                                 f"does not make any sense. Define a net structure with only a single such arc.")

    def _identify_node_by_label(self, label: str, element_type: str = None) -> (ConnectedElement | None):
        """
        Pass label and receive object with that label. If element type known: pass to make more efficient.
        :param label: String, label of object
        :param element_type: place, transition, collection point, arc, quantity arc (optional)
        :return: object or None if doesn't exist
        """
        if element_type:
            if element_type in ["place", "places" "p", Place, "object place", "objectplace", ObjectPlace, "ObjectPlace",
                                "object_place", "collection point", "collection points", "collection_point",
                                "collection_points", "cp", "cps", CollectionPoint]:
                places = self.places
                matching_name = [element for element in places if element.label == label]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed node {label} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            elif element_type in ["transition", "transitions" "t", Transition]:
                transitions = self.transitions
                matching_name = [element for element in transitions if element.label == label]
                if len(matching_name) == 1:
                    return matching_name[0]
                elif len(matching_name) == 0:
                    return None
                else:
                    raise ValueError(f"Passed node {label} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")
            else:
                raise ValueError(f"Element type {element_type} not identified. "
                                 f"Valid types: place, transition, collection point, arc, quantity arc")

        else:
            matching_name = [element for element in self.nodes if element.label == label]
            if len(matching_name) == 1:
                return matching_name[0]
            elif len(matching_name) == 0:
                return None
            else:
                raise ValueError(f"Passed node {label} cannot be uniquely identified. "
                                 f"More than one object arc between the same two nodes in the same direction "
                                 f"does not make any sense. Define a net structure with only a single such arc.")

    def identify_arc(self,
                     arc: tuple[ObjectPlace | CollectionPoint | Transition, ObjectPlace | CollectionPoint | Transition]
                          | uuid.UUID | Qarc | ObjectArc) -> (Arc | None):
        """
        Pass either arc object or 2-tuple (source, target), get corresponding object if part of net.
        If data type of arc is object, check if object part of net - yes: return arc, no: return None.
        If data type is uuid.UUID check if an arc with the same uuid exists in net and return object or None.
        If data type 2-tuple: Identify source and target. If both objects and part of net: Check source's output arcs
        for corresponding arc. If arc identified: return arc, else None.
        Requirements:
        - Node parameter must be string, uuid or object.
        - Source and target (if provided) must be objects of the net
        - If several arcs with the same source and target exists, ValueError that description isn't unique
        Caught Problems: Parameter input other than uuid, string or object (this method), identification result not
        unique (this method), Source and target not elements of the net (this method).
        :param arc:
        :return:
        """
        if isinstance(arc, Arc):
            if arc in self.arcs:
                return arc
            else:
                return None

        elif isinstance(arc, uuid.UUID):
            matching_name = [element for element in self.arcs if element.id == arc]
            if len(matching_name) == 1:
                return matching_name[0]
            else:
                return None

        elif isinstance(arc, tuple) and len(arc) == 2:
            source = self.identify_node(arc[0])
            target = self.identify_node(arc[1])

            if isinstance(source, ConnectedElement) and isinstance(target, ConnectedElement):

                # detect if object arc or qarc
                if isinstance(source, ObjectPlace) or isinstance(target, ObjectPlace):
                    possible_arcs = [arc for arc in source.output_arcs if arc.target == target and isinstance(arc, ObjectArc)]
                elif isinstance(source, CollectionPoint) or isinstance(target, CollectionPoint):
                    connected_transition = source if isinstance(source, Transition) else target
                    connected_cp = target if connected_transition == source else target
                    possible_arcs = [arc for arc in connected_transition.quantity_arcs
                                     if arc.source == connected_cp or arc.target == connected_cp]
                else:
                    raise ValueError(f"Source and/or target of {arc} cannot be identified as elements of the net."
                                     f"Define net using method 'set_net_structure'.")

                if len(possible_arcs) == 1:

                    # make sure arc is part of the net
                    if possible_arcs[0] in self.arcs:
                        return possible_arcs[0]
                    else:
                        return None

                elif len(possible_arcs) == 0:
                    return None

                else:
                    raise ValueError(f"Passed arc {arc} cannot be uniquely identified. "
                                     f"More than one object arc between the same two nodes in the same direction "
                                     f"does not make any sense. Define a net structure with only a single such arc.")

            else:
                raise ValueError(f"Source and/or target of {arc} cannot be identified as elements of the net."
                                 f"Define net using method 'set_net_structure'.")

        else:
            return None

    def transition_enabled(self, transition: Transition, binding_function: BindingFunction) -> bool:
        """Check if passed transition is enabled with given binding function. Returns bool."""
        if transition in self.transitions:
            return transition.enabled(binding_function=binding_function)
        else:
            raise ValueError(f"Passed transition {transition} not part of the net.")

    def start_firing_transition(self, transition: Transition | str, binding_function: BindingFunction):
        """If transition part of the net, initiate firing."""

        transition_element = self.identify_node(transition, "transition")

        if transition_element in self.transitions:
            transition_execution = transition_element.start_firing(binding_function=binding_function)
            execution = self._add_execution(transition_execution=transition_execution, transition=transition_element)
            return execution
        else:
            raise ValueError(f"Passed transition {transition} not part of the net.")

    def _add_execution(self, transition_execution: TransitionExecution, transition: Transition):
        execution = Execution(transition_execution=transition_execution, transition=transition)
        self.executions.append(execution)
        return execution

    def _remove_execution(self, execution: TransitionExecution | Execution | uuid.UUID):
        execution =  self._identify_execution(execution)
        self.executions.remove(execution)

    def _identify_execution(self, execution: TransitionExecution | Execution | uuid.UUID) -> Execution:
        if isinstance(execution, TransitionExecution):
            matching_execution = [item for item in self.executions if item.execution == execution]
            if len(matching_execution) == 1:
                return matching_execution[0]
            else:
                raise ValueError(f"Execution {execution} not part of the net.")
        elif isinstance(execution, Execution):
            return execution
        elif isinstance(execution, uuid.UUID):
            matching_execution = [item for item in self.executions if item.execution.id == execution]
            if len(matching_execution) == 1:
                return matching_execution[0]
            else:
                raise ValueError(f"Execution {execution} not part of the net.")
        else:
            raise ValueError(f"Passed execution {execution} is not a valid execution or execution item.")

    def end_firing_transition(self, execution: TransitionExecution | Execution | uuid.UUID):
        """If transition part of the net, initiate end of firing."""

        execution = self._identify_execution(execution)
        execution.transition.end_firing(execution=execution.transition_execution)

    def get_enabled_bindings_all_transitions_for_input_types(self) -> dict[Transition: list[BindingFunction]]:
        """
        Iterate through transitions of the net and get all enabled binding functions per transition. Returns dict of all
        enabled binding functions per transition.
        :return:
        """

        enabled_input_bindings = {}

        for transition in self.transitions:
            if transition.manually_initiated:
                continue
            else:
                pass
            enabled_input_binding_functions = transition.get_enabled_binding_functions_inputs()
            if enabled_input_binding_functions is not None:
                enabled_input_bindings[transition] = enabled_input_binding_functions
            else:
                pass

        return enabled_input_bindings

    # def get_enabled_bindings_non_silent_transitions_for_input_types(self) -> dict[Transition: BindingFunction]:
    #     """
    #     Iterate through transitions of the net and get all enabled binding functions per transition. Returns dict of all
    #     enabled binding functions per transition.
    #     :return:
    #     """
    #
    #     enabled_input_bindings = {}
    #
    #     for transition in self.labelled_transitions:
    #         enabled_input_binding_functions = transition.get_enabled_binding_functions_inputs()
    #         if enabled_input_binding_functions is not None:
    #             enabled_input_bindings[transition] = enabled_input_binding_functions
    #         else:
    #             pass
    #
    #     return enabled_input_bindings

    def add_objects_to_places(self, object_marking: dict[(str | ObjectPlace): (set[Object] | list[Object] | Object)]):

        for place, marking in object_marking.items():

            # validate place object
            if isinstance(place, str):
                place_element = self.identify_node(node=place, element_type="place")
                if place_element:
                    if isinstance(place_element, ObjectPlace):
                        pass
                    else:
                        raise ValueError(
                            f"Passed place {place} is a collection point and cannot be marked with objects.")
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            elif isinstance(place, ObjectPlace):
                if place in self.places:
                    place_element = place
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")

            else:
                raise ValueError(f"Passed place {place} is not a Place in the net.")

            # check if marking is of correct type
            if isinstance(marking, set):
                place_marking = marking
            elif isinstance(marking, Object):
                place_marking = {marking}
            elif isinstance(marking, list):
                place_marking = set(marking)
            else:
                raise ValueError(f"Passed marking for {place} does not match with type of place.")

            # add tokens to objectplace
            place_element.add_tokens(place_marking)

    def update_markings_collection_points(self, cp_marking: dict[(str | CollectionPoint): Counter]):

        for place, marking in cp_marking.items():

            # validate place object
            if isinstance(place, str):
                place_element = self.identify_node(node=place, element_type="place")
                if place_element:
                    if isinstance(place_element, CollectionPoint):
                        pass
                    else:
                        raise ValueError(
                            f"Passed place {place} is a object place and cannot be marked with lazy tokens.")
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")
            elif isinstance(place, CollectionPoint):
                if place in self.places:
                    place_element = place
                else:
                    raise ValueError(f"Passed place {place} cannot be identified as part of the net.")

            else:
                raise ValueError(f"Passed place {place} is not a Place in the net.")

            # check if marking is of correct type
            if isinstance(marking, Counter):
                place_marking = marking
            else:
                raise ValueError(f"Passed marking for {place} hast to be a counter.")

            # add lazy tokens to collection point
            place_element.update_marking(place_marking)

    def get_initial_places_object_type(self, object_type: Type[Object]) -> set[ObjectPlace]:
        """Pass object type and get all initial places of that object type."""
        return {place for place in self.initial_places
                if isinstance(place, ObjectPlace) and place.object_type == object_type}

    def get_final_places_object_type(self, object_type: Type[Object]) -> set[ObjectPlace]:
        """Pass object type and get all initial places of that object type."""
        return {place for place in self.final_places
                if isinstance(place, ObjectPlace) and place.object_type == object_type}

    # def get_enabled_bindings_silent_transitions(self) -> dict[Transition: list[None] | list[dict[Type[Object]: set[Object]]]]:
    #     """
    #     Iterate through silent transitions of the net and get all enabled binding functions per transition.
    #     Returns dict of all enabled binding functions per transition.
    #     :return:
    #     """
    #
    #     enabled_bindings_silent = {}
    #
    #     for transition in self.silent_transitions:
    #         enabled_input_binding_functions = transition.get_enabled_binding_functions_inputs()
    #         if enabled_input_binding_functions is not None:
    #             enabled_bindings_silent[transition] = enabled_input_binding_functions
    #         else:
    #             pass
    #
    #     return enabled_bindings_silent

    def get_locations_of_object(self, obj: Object) -> set[ObjectPlace]:
        """Pass object and get all places in which object is part of marking."""

        obj_location = set()
        for place in self.object_places:
            if obj in place.marking:
                obj_location.add(place)
            else:
                pass

        return obj_location

    def get_quantity_operations_of_execution(self, execution: TransitionExecution | Execution | uuid.UUID) -> CollectionCounter:
        """
        Pass execution and get all quantity operations of that execution.
        """

        execution = self._identify_execution(execution=execution)
        return execution.transition_execution.collected_quantity_operations


    def get_subnet_quantity_dependencies(self):

        quantity_subnet = QuantityNet(f"quantity_subnet_{self.name}")

        quantity_subnet.places = self.collection_points
        quantity_subnet.transitions = self.transitions
        quantity_subnet.arcs = self.quantity_arcs

        return quantity_subnet

    def get_subnet_ocpn(self):

        ocpn = QuantityNet(f"ocpn_subnet_{self.name}")

        ocpn.places = self.object_places
        ocpn.transitions = self.transitions
        ocpn.arcs = self.object_arcs

        return ocpn

    def identify_object_type(self, object_type_name: str) -> Type[Object]:
        """
        Pass object type name and get corresponding object type.
        """
        object_types = {object_type for object_type in self.object_types if object_type.object_type_name == object_type_name}

        if len(object_types) == 1:
            return object_types.pop()
        else:
            raise ValueError(f"Object type {object_type_name} could not be identified.")

    def make_arcs_variable(self, variable_arcs: set[ObjectArc | tuple]):

        for arc in variable_arcs:
            arc_element = self.identify_arc(arc)
            arc_element.variable = True


