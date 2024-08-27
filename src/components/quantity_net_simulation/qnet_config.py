from typing import Type, Any, Callable, Counter

from src.components.base_element import BaseElement
from src.components.log_elements.event import Event, CollectionCounter
from src.components.log_elements.object import Object, MultisetObject
from src.components.net_elements.guard import QuantityGuardSmallstockConfig, QuantityGuard
from src.components.net_elements.qalculator import Qalculator
from src.components.net_elements.transition import BindingFunction


class QnetConfig(BaseElement):
    def __init__(self, net_structure: set | list[tuple[str, str]] = None, place_types: dict[str: str] = None,
                 quantity_net_name: str = None,
                 name: str = None, properties: dict = None, label: str = None):

        super().__init__(name=name, properties=properties, label=label)

        # ## Object types define object types with a name and a dict of attribute names and a default value,
        # object type classes are created automatically from passed parameters (optional)
        self.object_types_attributes: dict[str: dict[str: Any]] = {} # {object_type_name: default_attributes}
        # pass created classes for object types (optional)
        self.object_types_classes: list[Type[Object]] = [] # list of object classes

        ### Quantity net
        # specify some optional general properties of the qnet (all optional)
        self.quantity_net_name: Any = quantity_net_name if quantity_net_name else "quantity_net"
        self.quantity_net_label: str | None = None
        self.quantity_net_properties: dict | None = None
        # define the structure of the quantity net. Must be a set of tuples with two strings, representing the source
        # and target of arcs. places must begin with "p", transitions with "t" and counters with "c" (mandatory)
        self.net_structure: set[tuple[str, str]] = net_structure if net_structure else set()

        ## Places
        # set of initial places (place names are sufficient)(optional)
        self.initial_places: set[str] = set()
        # set of initial places (place names are sufficient) (optional)
        self.final_places: set[str] = set()
        # dict specifying the object type each place is assigned to (mandatory, if object types should be considered)
        self.place_types: dict[str: Type[Object] | str] = place_types if place_types else {}

        ### Counter
        # names of the counters (mandatory, if counter should be part of the log)
        self.collection_point_labels: dict[str: str] = {} # {collection_point_name: label}

        ### Transitions
        # transition labels (equivalent to activity names) (mandatory, if activities should be assigned to transitions)
        self.transition_labels: dict[str: str] = {}
        # transition specifying what combinations of objects or what object attribute-value combinations are allowed
        # for firing this transition. (optional)
        self.transition_object_guard: dict[str: Callable[[BindingFunction], bool]] = {}
        # guard considering the item levels of connected counters to consider whether the transition is enabled or
        # not. (optional)
        self.transition_quantity_guard: dict[str: Callable[[BindingFunction, CollectionCounter], bool] | QuantityGuard] = {}
        # function defining the exact number of objects of the involved object types for a valid binding functions
        # wrt variable arcs. (zero means no specific defined number of objects) (optional)
        self.binding_function_quantities: dict[str: dict[Type[Object]: int]] = {}
        # function specifying the maximum number of objects of the involved object types for valid the binding
        # functions wrt variable arcs. (zero means no specific defined number of objects) (optional)
        self.maximum_binding_function_quantities: dict[str: dict[Type[Object]: int]] = None
        # function specifying the minimum number of objects of the involved object types for valid the binding
        # functions wrt variable arcs. (zero means no specific defined number of objects) (optional)
        self.minimum_binding_function_quantities: dict[str: dict[Type[Object]: int]] = None
        # Qalculator object to calculate the quantity operations involved in the firing of the transition (optional)
        self.quantity_calculators: dict[str: Qalculator] = {} # {transition_name: quantity_calculator}
        # explicitly setting transitions with a label (aka an activity) to silent (optional)
        self.silent_transitions: set[str] = set() # {transition_name}
        # create small stock guards for transitions (optional)
        self.small_stock_guards: dict[str: QuantityGuardSmallstockConfig] = {} # {transition_name: small_stock_guard_config}
        self.manually_initiated_transitions = {} # {transition_name: bool}
        self.transition_binding_selection: dict[str: Callable] = {} # {transition_name: Callable}}

        # ## Activities define activities with a name and a dict of attribute names and a default value,
        # activity classes are created automatically from passed parameters (optional)
        self.activity_attributes: dict[str: dict[str: Any]] = {}
        # pass created classes for activities (optional)
        self.activity_classes: list[Type[Event]] = []
        # set activities to silent (not logged)
        self.silent_activities: set[str] = set()


        ### Markings
        # provide a set of objects to be added to the initial places of the corresponding object types (optional)
        self.initial_objects: set[Object] = set()
        # provide a mapping of objects to be added to specific places (optional)
        self.initial_objects_in_places: dict[str: MultisetObject] = {} # {place: objects}
        # specify the number of initial objects to be added to the initial places of the corresponding object types (
        # object type can be a class or just indicated by name) (optional)
        self.initial_marking_object_types: dict[str | Type[Object]: int] = {} # {object_type: number_initial_objects}
        # specify the number of initial objects to be added to specific places (optional)
        self.initial_marking_object_places: dict[str | Type[Object]: int] = {} # {place: number of objects}
        # specify the initial item quantities for the counters (optional)
        self.initial_marking_collection_points: dict[str: Counter] = {} # {cp: initial_marking}
        # for every object type, provide a list of sets of places each specifiying the final marking of the
        # corresponding object type (optional)
        self.final_markings: dict[str: list[set[str]]] = {} # {object_type_name: [set of places]}
