import datetime
from collections import Counter
from itertools import combinations, product

import binpacking
import numpy as np

from qel_simulation.simulation.event import Event, BindingFunction
from qel_simulation.qnet_elements.collection_point import CollectionCounter
from qel_simulation.simulation.execution import Execution
from qel_simulation.simulation.object import Object, StatusInactive, StatusActive, StatusTerminated, MultisetObject
from qel_simulation.qnet_elements.guard import QuantityGuardSmallstockConfig, QuantityGuard
from qel_simulation.qnet_elements.qalculator import Qalculator
from qel_simulation.simulation.instructions import (InstructionObjectCreation, InstructionObjectStatusUpdate,
                                                    Instruction, InstructionObjectAttributeUpdate,
                                                    InstructionExecuteEvent)
from qel_simulation.simulation.qnet_config import QnetConfig

rng = np.random.default_rng(seed=42)


def counter_projection(counter: Counter, item_subset: set) -> Counter:
    """Projects the counter on the passed item subset."""
    return Counter({item: counter[item] for item in item_subset.intersection(set(dict(counter).keys()))})

def get_abs_counter(counter: Counter) -> Counter:
    """Returns a Counter object with absolute values."""
    return Counter({key: abs(counter[key]) for key in counter})


def determine_remaining_demand(possible_demand: Counter, full_demand: Counter) -> Counter:
    """Provide possible demand and full demand and get the remaining open demand."""
    remaining_demand = full_demand.copy()
    remaining_demand.subtract(possible_demand)
    return remaining_demand


########### PARAMETERS & FUNCTIONS ###########
items_other_brands = {"Bell", "Saddle", "Speedometer", "Helmet", "Handles (2)", "Pedal", "Brake Shoes (4)",
                      "Brake Cable (2)",
                      "Tire", "Tube", "Front Light", "Back Light", "Box"}
items_PADS = {"PADS Brake Shoes (2)", "PADS Brake Cable (2)", "PADS Tire", "PADS Tube"}
items = items_other_brands | items_PADS

# Distributions for lead times per supplier
# lead_time_distributions_days = {
#     "TU/e": {"loc": 4, "scale": 1},
#     "PADS": {"loc": 2, "scale": 0.5},
#     "QUT": {"loc": 9, "scale": 3},
#     "KU Leuven": {"loc": 4, "scale": 1.21}
# }
lead_time_distributions_days = {
    "TU/e": {"loc": 3, "scale": 1},
    "PADS": {"loc": 2, "scale": 0.5},
    "QUT": {"loc": 6, "scale": 3},
    "KU Leuven": {"loc": 4, "scale": 1.21}
}

# number of loading bays
loading_bays = 6

### Demand Customer Orders
# expected_customer_orders_per_day = 50
expected_customer_orders_per_day = 5

## Item Demand Customer Orders
frequent_item_sets = {
    "Helmet": {"values": [Counter({"Helmet": 1}), Counter({"Helmet": 2})], "probabilities": [0.9, 0.1]},
    "Brake Equipment": {
        "values": [Counter({"Brake Shoes (4)": 1}), Counter({"Brake Shoes (4)": 1, "Brake Cable (2)": 1}),
                   Counter({"PADS Brake Shoes (2)": 1}), Counter({"PADS Brake Shoes (2)": 2}),
                   Counter({"PADS Brake Shoes (2)": 2, "PADS Brake Cable (2)": 1}),
                   Counter({"PADS Brake Shoes (2)": 2, "Brake Cable (2)": 1}),
                   Counter({"PADS Brake Shoes (2)": 1, "Brake Shoes (4)": 1})
                   ],
        "probabilities": [0.1, 0.1,
                          0.15, 0.3,
                          0.2,
                          0.1,
                          0.05]},
    "Wheels": {"values": [Counter({"Tube": 1}), Counter({"Tire": 2, "Tube": 2}), Counter({"Tube": 2}),
                          Counter({"PADS Tube": 1}), Counter({"PADS Tire": 2, "PADS Tube": 2}),
                          Counter({"PADS Tube": 2}), Counter({"PADS Tube": 1, "Tube": 1}),
                          Counter({"Tire": 2, "PADS Tube": 2})],
               "probabilities": [0.2, 0.05, 0.05,
                                 0.35, 0.1,
                                 0.1, 0.05,
                                 0.1]},
    "Pedal": {"values": [Counter({"Pedal": 1}), Counter({"Pedal": 2}), Counter({"Pedal": 3}), Counter({"Pedal": 4})],
              "probabilities": [0.25, 0.6, 0.05, 0.1]},
    "Saddle": {"values": [Counter({"Saddle": 1}), Counter({"Saddle": 2})], "probabilities": [0.9, 0.1]},
    "Light": {"values": [Counter({"Front Light": 1}), Counter({"Back Light": 1}), Counter({"Front Light": 2}),
                         Counter({"Front Light": 1, "Back Light": 1}), Counter({"Back Light": 2}),
                         Counter({"Front Light": 2, "Back Light": 2})],
              "probabilities": [0.225, 0.225, 0.05,
                                0.35, 0.05,
                                0.1]},
    "Handles": {"values": [Counter({"Handles (2)": 1}), Counter({"Handles (2)": 2})], "probabilities": [0.95, 0.05]},
    "Handlebar": {"values": [Counter({"Bell": 1}), Counter({"Speedometer": 1}), Counter({"Bell": 1, "Speedometer": 1}),
                             Counter({"Bell": 2}), Counter({"Speedometer": 2}), Counter({"Bell": 2, "Speedometer": 1}),
                             Counter({"Bell": 2, "Speedometer": 2})],
                  "probabilities": [0.7, 0.03, 0.15,
                                    0.06, 0.01, 0.01,
                                    0.04]},
}

# number of frequent itemsets drawn
number_frequent_itemsets = {"values": [1, 2, 3, 4, 5, 6, 7, 8],
                            "probabilities": [0.325, 0.275, 0.2, 0.1, 0.05, 0.03, 0.01, 0.01]}

# likelihood of frequent itemset category being drawn
likelihood_frequent_itemset_category = {
    "Helmet": 0.05,
    "Brake Equipment": 0.15,
    "Wheels": 0.3,
    "Pedal": 0.1,
    "Saddle": 0.12,
    "Light": 0.2,
    "Handles": 0.02,
    "Handlebar": 0.06
}


def draw_demand_customer_order():
    """Draws the ordered items for a customer order.
    Functionality: 1. Draw the number of frequent itemsets
                    2. Draw the frequent itemset categories
                    3. Draw the frequent itemsets
                    4. Compose new counter describing the complete customer order"""

    demand_co = Counter()

    # draw number of frequent itemsets
    number_draws = rng.choice(a=number_frequent_itemsets["values"], p=number_frequent_itemsets["probabilities"])

    # draw frequent itemset categories
    categories = rng.choice(a=list(likelihood_frequent_itemset_category.keys()),
                            p=list(likelihood_frequent_itemset_category.values()),
                            size=number_draws,
                            replace=False)

    # draw frequent itemsets and add to demand
    for category in categories:
        frequent_itemset = rng.choice(a=frequent_item_sets[category]["values"],
                                      p=frequent_item_sets[category]["probabilities"])
        demand_co.update(frequent_itemset)

    return demand_co


### Logistics Parameters

# warehouse capacity
# warehouse_capacity = {
#     "cp1": Counter({
#         "Helmet": 200,
#         "Saddle": 450,
#         "Tire": 150,
#         "Other": 3000
#     })
# }
warehouse_capacity = {
    "cp1": Counter({
        "Helmet": 20,
        "Saddle": 25,
        "Tire": 25,
        "Other": 400
    })
}


joint_warehouse_capacity = {"Bell", "Speedometer", "Handles (2)", "Pedal", "Brake Shoes (4)", "Brake Cable (2)",
                            "Tube", "Front Light", "Back Light"}

## number of items per palette
# items_per_palette = {
#     "Helmet": 5,
#     "Bell": 20,
#     "Saddle": 20,
#     "Speedometer": 20,
#     "Handles (2)": 10,
#     "Pedal": 50,
#     "Brake Shoes (4)": 20,
#     "Brake Cable (2)": 10,
#     "Tire": 25,
#     "Tube": 30,
#     "Front Light": 30,
#     "Back Light": 30,
#     "PADS Brake Shoes (2)": 100,
#     "PADS Brake Cable (2)": 100,
#     "PADS Tire": 15,
#     "PADS Tube": 100,
#     "Box": 100,
#     "mixed": 20
# }
items_per_palette = {
    "Helmet": 2,
    "Bell": 5,
    "Saddle": 2,
    "Speedometer": 10,
    "Handles (2)": 4,
    "Pedal": 4,
    "Brake Shoes (4)": 10,
    "Brake Cable (2)": 5,
    "Tire": 2,
    "Tube": 6,
    "Front Light": 8,
    "Back Light": 5,
    "PADS Brake Shoes (2)": 8,
    "PADS Brake Cable (2)": 5,
    "PADS Tire": 2,
    "PADS Tube": 4,
    "Box": 5,
    "mixed": 2
}


speed_of_unloading_palette = {"min": 30, "max": 170}
speed_of_picking_items = {"min": 2, "max": 4}

### Replenishment

# Replenishment trigger
stock_based_replenishment_items = {"Brake Shoes (4)", "Tube", "Back Light", "Front Light", "Tire", "Pedal"}
# small_stock = Counter({"Brake Shoes (4)": 36,
#                        "Tube": 200,
#                        "Back Light": 170,
#                        "Front Light": 230,
#                        "Tire": 90,
#                        "Pedal": 250,
#                        "Box": 200})
small_stock = Counter({"Brake Shoes (4)": 5,
                       "Tube": 5,
                       "Back Light": 7, #7
                       "Front Light": 15,
                       "Tire": 3,
                       "Pedal": 10,
                       "Box": 21})

time_based_replenishment_items = {"Handles (2)", "Bell", "Helmet", "Speedometer", "Brake Cable (2)", "Saddle"}

# Replenishment lots
# fixed_lotsizes = {"Brake Shoes (4)": 75,
#                   "Tube": 230,
#                   "Bell": 150,
#                   "Brake Cable (2)": 100,
#                   "Helmet": 200,
#                   "Speedometer": 50}
fixed_lotsizes = {"Brake Shoes (4)": 17,
                  "Tube": 21,
                  "Bell": 7,
                  "Brake Cable (2)": 3,
                  "Helmet": 6,
                  "Speedometer": 2}
# large_stock = {"Pedal": 750,
#                "Front Light": 650,
#                "Back Light": 650,
#                "Saddle": 500,
#                "Tire": 300,
#                "Handles (2)": 100,
#                "Box": 1200}
large_stock = {"Pedal": 50,
               "Front Light": 25,
               "Back Light": 28,
               "Saddle": 25,
               "Tire": 23,
               "Handles (2)": 9,
               "Box": 100}

# PADS_small_stock = Counter({"PADS Brake Shoes (2)": 60, "PADS Brake Cable (2)": 5, "PADS Tire": 15, "PADS Tube": 90})
# PADS_large_stock = Counter(
#     {"PADS Brake Shoes (2)": 450, "PADS Brake Cable (2)": 60, "PADS Tire": 120, "PADS Tube": 600})
PADS_small_stock = Counter({"PADS Brake Shoes (2)": 2, "PADS Brake Cable (2)": 1, "PADS Tire": 2, "PADS Tube": 4})
PADS_large_stock = Counter(
    {"PADS Brake Shoes (2)": 16, "PADS Brake Cable (2)": 13, "PADS Tire": 15, "PADS Tube": 25})

# initial_item_level_PADS = Counter(
#     {"PADS Brake Shoes (2)": 100, "PADS Brake Cable (2)": 20, "PADS Tire": 21, "PADS Tube": 250})
initial_item_level_PADS = Counter(
    {"PADS Brake Shoes (2)": 10, "PADS Brake Cable (2)": 8, "PADS Tire": 8, "PADS Tube": 13})
# # initial_item_level_PADS = Counter({"PADS Brake Shoes (2)": 0, "PADS Brake Cable (2)": 0, "PADS Tire": 0, "PADS Tube": 0})
# initial_item_level_other = Counter({"Brake Shoes (4)": 45,
#                                     "Tube": 230,
#                                     "Bell": 120,
#                                     "Brake Cable (2)": 70,
#                                     "Helmet": 96,
#                                     "Speedometer": 30,
#                                     "Pedal": 260,
#                                     "Front Light": 300,
#                                     "Back Light": 202,
#                                     "Saddle": 221,
#                                     "Tire": 121,
#                                     "Handles (2)": 71,
#                                     "Box": 621})
initial_item_level_other = Counter({"Brake Shoes (4)": 5,
                                    "Tube": 23,
                                    "Bell": 9,
                                    "Brake Cable (2)": 6,
                                    "Helmet": 9,
                                    "Speedometer": 30,
                                    "Pedal": 26,
                                    "Front Light": 23,
                                    "Back Light": 18,
                                    "Saddle": 15,
                                    "Tire": 12,
                                    "Handles (2)": 5,
                                    "Box": 42})

# MOQ for replenishment orders
# not implemented yet #

# Lotsizes
# lotsizes = {
#     "Helmet": 1,
#     "Bell": 10,
#     "Saddle": 1,
#     "Speedometer": 25,
#     "Handles (2)": 1,
#     "Pedal": 10,
#     "Brake Shoes (4)": 5,
#     "Brake Cable (2)": 10,
#     "Tire": 5,
#     "Tube": 10,
#     "Front Light": 1,
#     "Back Light": 10,
#     "PADS Brake Shoes (2)": 1,
#     "PADS Brake Cable (2)": 1,
#     "PADS Tire": 1,
#     "PADS Tube": 1,
#     "Box": 100
# }
# Lotsizes
lotsizes = {
    "Helmet": 1,
    "Bell": 1,
    "Saddle": 1,
    "Speedometer": 2,
    "Handles (2)": 1,
    "Pedal": 5,
    "Brake Shoes (4)": 4,
    "Brake Cable (2)": 3,
    "Tire": 1,
    "Tube": 2,
    "Front Light": 1,
    "Back Light": 3,
    "PADS Brake Shoes (2)": 1,
    "PADS Brake Cable (2)": 1,
    "PADS Tire": 1,
    "PADS Tube": 1,
    "Box": 20
}


########### OBJECT TYPES ###########

class WarehouseEmployees(Object):
    remaining_objects_to_create = ["Viki Peeva", "Nina Graves", "Tsunghao Huang", "Wil van der Aalst",
                                   "Tobias Brockhoff", "Benedikt Knopp", "Christian Rennert"]
    object_type_name = "Warehouse Employee"
    log_object_type = True

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None,
                 o2o: dict[Object: str] = None):
        super().__init__(timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)
        if len(WarehouseEmployees.remaining_objects_to_create) > 0:
            self.resource_name = WarehouseEmployees.remaining_objects_to_create[0]
            WarehouseEmployees.remaining_objects_to_create.remove(WarehouseEmployees.remaining_objects_to_create[0])
        else:
            raise ValueError(f"No more objects intended to be created.")


class AdministrativeEmployees(Object):
    remaining_objects_to_create = ["István Koren", "Mara Nischke", "Christine Dobbert", "Niklas Adams",
                                   "Mahsa Pourbafrani", "Christopher Schwanen"]
    object_type_name = "Administrative Employee"
    log_object_type = True

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None,
                 o2o: dict[Object: str] = None):
        super().__init__(timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)
        if len(AdministrativeEmployees.remaining_objects_to_create) > 0:
            self.resource_name = AdministrativeEmployees.remaining_objects_to_create[0]
            AdministrativeEmployees.remaining_objects_to_create.remove(
                AdministrativeEmployees.remaining_objects_to_create[0])
        else:
            raise ValueError(f"No more objects intended to be created.")


class ReplenishmentOrder(Object):
    object_type_name = "Replenishment Order"

    def __init__(self, timestamp: datetime.datetime, quantities: Counter, order_type: str = None, label: str = None,
                 properties: dict = None,
                 o2o: dict[Object: str] = None):
        super().__init__(timestamp=timestamp, quantities=quantities, properties=properties, o2o=o2o, label=label)

        potential_suppliers = np.array(["TU/e", "QUT", "KU Leuven"])
        self.supplier = rng.choice(potential_suppliers)
        self.order_type = order_type


class Delivery(Object):
    object_type_name = "Incoming Delivery"

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None,
                 o2o: dict[Object: str] = None, supplier: str = None):
        super().__init__(timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)

        if o2o:
            self.supplier = supplier
        else:
            self.supplier = "PADS"


class CustomerOrder(Object):
    object_type_name = "Customer Order"

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None, o2o: dict[Object: str] = None):

        if quantities:
            ordered_quantity = quantities
        else:
            ordered_quantity = Counter()
            ordered_quantity.subtract(draw_demand_customer_order())  # negative, as CO describes demand / lack of items

        super().__init__(timestamp=timestamp, quantities=ordered_quantity, properties=properties, o2o=o2o, label=label)

        customer_ids = np.arange(2156, 21210)
        self.customer_id = f"005922{int(rng.choice(a=customer_ids))}"
        self.customer_order_accepted = None


class RemainingCO(Object):
    object_type_name = "Remaining Customer Order"
    log_object_type = False

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None, o2o: dict[Object: str] = None):
        super().__init__(timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)


class Palette(Object):
    object_type_name = "Palette"

    def __init__(self, timestamp: datetime.datetime, quantities: Counter = None, label: str = None,
                 properties: dict = None, o2o: dict[Object: str] = None):
        super().__init__(timestamp=timestamp, quantities=quantities, label=label, properties=properties, o2o=o2o)


class LoadingBay(Object):
    object_type_name = "Loading Bay"
    log_object_type = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None, quantities: Counter = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, o2o=o2o, quantities=quantities)


class TimingReplenishmentOrder(Object):
    object_type_name = "Timing Replenishment Order"
    log_object_type = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None, quantities: Counter = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, o2o=o2o, quantities=quantities)


class TimingPADSDelivery(Object):
    object_type_name = "Timing PADS Delivery"
    log_object_type = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 o2o: dict["Object": str] = None, quantities: Counter = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, o2o=o2o, quantities=quantities)


######## TRANSITION & ACTIVITY ##########
### t11: Initiate Replenishment Order (SmallStock) ###

def identify_difference_to_threshold(item_level: Counter, threshold: Counter) -> Counter:
    # only consider item level of relevant item types
    item_level_of_threshold_types = set(threshold.keys()) - items_PADS
    relevant_item_level = counter_projection(item_level, item_level_of_threshold_types)

    # determine difference between item level and threshold
    delta = relevant_item_level.copy()
    delta.subtract(threshold)

    return delta


## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
quantity_guard_t11_config = QuantityGuardSmallstockConfig(
    counter_threshold={"cp5": Counter({"initiated replenishment order": 0}),
                       "cp2": small_stock})


# def quantity_guard_t11(binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
#     """ Transition has a quantity connection to cp2, hence the quantity state is a collection counter only referring
#     to cp2, the binding function is empty, as the transition has no input object types.
#     Transition is only enabled if the item level of one or more of the non-PADS items sinks below small stock s."""
#
#     # get correct collection point element
#     cp2 = [cp for cp in quantity_state.keys() if cp.name == "cp2"][0]
#     cp5 = [cp for cp in quantity_state.keys() if cp.name == "cp5"][0]
#
#     if quantity_state[cp5] == Counter({"initiated replenishment order": 1}):
#         return False
#     else:
#         pass
#
#     # determine difference between item level and threshold
#     delta_lvl_small_stock = identify_difference_to_threshold(quantity_state[cp2], small_stock)
#
#     # if there are negative entries in delta_lvl_small_stock so the positive mirroring of the negative counter part is
#     # positive for at least one item, at least one item level is below small stock level
#     if -delta_lvl_small_stock == Counter():
#         return False
#     else:
#         return True

## Quantity Calculator
class InitialisedReplenishments(Qalculator):
    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        # identify counter indicating the number of in progress orders:
        cp5 = [cp for cp in quantity_state.keys() if cp.name == "cp5"][0]

        return CollectionCounter({cp5: Counter({"initiated replenishment order": 1})})


## Event
class InitiateReplenishmentOrderSmallStock(Event):
    activity_name = "Initiate Replenishment Order (SmallStock)"

    log_activity = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=datetime.timedelta(0))

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        return []

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        """Create Replenishment Order which is then added to binding. Quantities are added after quantity operations
        were determined by Qalculator."""
        objects_for_binding = InstructionObjectCreation(timedelta=datetime.timedelta(), object_type=ReplenishmentOrder,
                                                        quantities=Counter(), add_to_binding=True,
                                                        initial_attributes={"order_type": "stock based"})
        return [objects_for_binding]


### t13: Initiate Replenishment Order (TimeBased) ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]

## Guards

## Quantity Calculator
# none

# Event
class InitiateReplenishmentOrderTimeBased(Event):
    activity_name = "Initiate Replenishment Order (TimeBased)"

    log_activity = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=datetime.timedelta(0))

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        return []

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        """Create Replenishment Order which is then added to binding. Quantities are added after quantity operations
        were determined by Qalculator."""
        objects_for_binding = InstructionObjectCreation(timedelta=datetime.timedelta(), object_type=ReplenishmentOrder,
                                                        quantities=Counter(), add_to_binding=True,
                                                        initial_attributes={"order_type": "time based"})
        return [objects_for_binding]


### t12: Initiate PADS Delivery (TimeBased) ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
# none

## Quantity Calculator
class TimeBasedPADSDelivery(Qalculator):
    """Calculates the number of items that have to be ordered if at least one item level is below the small stock level."""

    log_activity = False

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Determine the number of items that has to be ordered and add it to the planning-double of the vendor managed
        inventory (cp3) to indicate that a process ordering these quantities has been initiates. Determined by delta to
        large stock."""

        # threshold
        quantity_update = PADS_large_stock.copy() # +

        # get correct collection point element
        cp3 = [cp for cp in quantity_state.keys() if cp.name == "cp3"][0] # +

        # determine difference between item level and large stock level
        quantity_update.subtract(quantity_state[cp3]) # state: pos,

        # only order items of item types below the large stock level
        quantity_update = +quantity_update
        item_types_to_reorder = set(quantity_update.keys())

        # determine required order quantity for item types that have to be reordered
        order_quantity = counter_projection(PADS_large_stock, item_types_to_reorder)
        order_quantity.subtract(quantity_update)

        # add small stock of reorder item types as safety stock
        small_stock_to_add = counter_projection(PADS_small_stock, item_types_to_reorder)
        order_quantity.update(small_stock_to_add)

        return CollectionCounter({cp3: order_quantity})


## Event
class InitiatePADSDeliveryTimeBased(Event):
    activity_name = "Initiate PADS Delivery (TimeBased)"

    log_activity = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=datetime.timedelta(0))

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        """1) Update involved delivery item by adding the determined quantities to it. The quantities are determined by
         the quantity operation to cp3 (the planning duplicate of PADS inventory). 2) The status of the object is
         set to inactive to indicate that the delivery has not yet arrived so that it is not considered for any bindings.
         3) Add instruction to change object status to active after lead time."""

        # identitfy delivery object
        do = [obj for obj in self.objects if isinstance(obj, Delivery)][0]

        # determine object quantity of delivery (quantity operation to cp3)
        oqty = self.quantity_operations[[cp for cp in self.quantity_operations.keys() if cp.name == "cp3"][0]]

        if +oqty:
            do.quantities = oqty
        else:
            do.quantities = oqty
            do.status = StatusTerminated()
            return []

        # draw lead time
        lead_time = datetime.timedelta(days=-1)
        while lead_time < datetime.timedelta(days=0):
            lead_time = rng.normal(**lead_time_distributions_days["PADS"]) * datetime.timedelta(days=1)

        # set status of delivery to inactive
        do.status = StatusInactive()

        # add status change to queue
        status_update = InstructionObjectStatusUpdate(timedelta=lead_time, object=do, new_status=StatusActive())

        return [status_update]

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        """Create Replenishment Order which is then added to binding. Quantities are added after quantity operations
        were determined by Qalculator."""
        objects_for_binding = InstructionObjectCreation(timedelta=datetime.timedelta(), object_type=Delivery,
                                                        quantities=Counter(), add_to_binding=True)
        return [objects_for_binding]


### t14: Initiate PADS Delivery (SmallStock) ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards

quantity_guard_t14_config = QuantityGuardSmallstockConfig(counter_threshold={"cp3": PADS_small_stock})


# def quantity_guard_t14(binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
#     """ Transition has a quantity connection to cp3, hence the quantity state is be a collection counter only referring
#     to cp3, the binding function is empty, as the transition has no input object types."""
#
#     # get correct collection point element
#     cp3 = [cp for cp in quantity_state.keys() if cp.name == "cp3"][0]
#
#     # determine difference between item level and small stock level
#     delta = quantity_state[cp3].copy()
#     delta.subtract(PADS_small_stock)
#
#
#     # check if item level of at least one item type is below the small stock level => return that transition is enabled
#     if -delta:
#         return True
#     else:
#         return False

## Quantity Calculator
class SmallStockPADSDelivery(Qalculator):
    """Calculates the number of items that have to be ordered if at least one item level is below the small stock level."""

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Determine the number of items that has to be ordered and add it to the planning-double of the vendor managed
        inventory (cp3) to indicate that a process ordering these quantities has been initiates. Determined by delta to
        large stock."""
        # threshold
        quantity_update = PADS_small_stock.copy()  # +

        # get correct collection point element
        cp3 = [cp for cp in quantity_state.keys() if cp.name == "cp3"][0]  # +

        # determine difference between item level and small stock level
        quantity_update.subtract(quantity_state[cp3])  # state: pos,

        # only order items of item types below or equal the small stock level
        item_types_to_reorder = {key for key, count in quantity_update.items() if count >= 0}
        quantity_update = counter_projection(quantity_update, item_types_to_reorder)


        # determine required order quantity for item types that have to be reordered
        order_quantity = counter_projection(PADS_large_stock, item_types_to_reorder)
        order_quantity.subtract(quantity_update)

        # add small stock of reorder item types as safety stock
        small_stock_to_add = counter_projection(PADS_small_stock, item_types_to_reorder)
        order_quantity.update(small_stock_to_add)

        return CollectionCounter({cp3: order_quantity})


## Event
class InitiatePADSDeliverySmallStock(Event):
    activity_name = "Initiate PADS Delivery (SmallStock)"

    log_activity = False

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=datetime.timedelta(0))

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        """1) Update involved delivery item by adding the determined quantities to it. The quantities are determined by
         the quantity operation to cp3 (the planning duplicate of PADS inventory). 2) The status of the object is
         set to inactive to indicate that the delivery has not yet arrived so that it is not considered for any bindings.
         3) Add instruction to change object status to active after lead time."""

        # identitfy delivery object
        do = [obj for obj in self.objects if isinstance(obj, Delivery)][0]
        cp3 = [cp for cp in self.quantity_operations.keys() if cp.name == "cp3"][0]

        ### 1. Update object quantity of delivery ###
        # determine object quantity of delivery (quantity operation to cp3)
        obj_qty = self.quantity_operations[cp3]
        do.quantities = obj_qty

        ### 2. Draw Lead Time ###
        lead_time = datetime.timedelta(days=-1)
        while lead_time < datetime.timedelta(days=0):
            lead_time = rng.normal(**lead_time_distributions_days["PADS"]) * datetime.timedelta(days=1)

        ### 3. Schedule change of delivery status to active ###
        # set current status of delivery to inactive
        do.status = StatusInactive()
        # add status change to queue
        status_update_active = InstructionObjectStatusUpdate(timedelta=lead_time, object=do, new_status=StatusActive())

        return [status_update_active]

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        """Create Replenishment Order which is then added to binding. Quantities are added after quantity operations
        were determined by Qalculator."""
        objects_for_binding = InstructionObjectCreation(timedelta=datetime.timedelta(), object_type=Delivery,
                                                        quantities=Counter(), add_to_binding=True)
        return [objects_for_binding]


### t0: Place Replenishment Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
# none

## Quantity Calculator
class ReplenishmentOrderQualculator(Qalculator):
    """Calculates the number of items that have to be ordered if at least one item level is below the small stock level."""

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Determine the number of items that has to be ordered and add it to the planning-double of the company's
        warehouse to indicate that a process ordering these quantities has bee initiates. Identify all item types where
        the item level of cp2 is smaller or equal the small stock."""
        quantity_operation = Counter()

        # get correct collection point element
        cp2 = [cp for cp in quantity_state.keys() if cp.name == "cp2"][0]
        cp5 = [cp for cp in quantity_state.keys() if cp.name == "cp5"][0]

        # get replenishment order object
        ro = list(binding_function[ReplenishmentOrder])[0]

        # small stock based calculation:
        if ro.order_type == "stock based":
            for item_type in items_other_brands.intersection(set(small_stock.keys())):
                if quantity_state[cp2][item_type] <= small_stock[item_type]:
                    if item_type in fixed_lotsizes.keys():
                        quantity_operation[item_type] = fixed_lotsizes[item_type]
                    elif item_type in large_stock.keys():
                        demand = large_stock[item_type] - quantity_state[cp2][item_type] # correct both if ilvl negative and positive
                        if demand % lotsizes[item_type] == 0:
                            quantity_operation[item_type] = demand
                        else:
                            # always round up demand to the next full lot size
                            full_lot_sizes = demand // lotsizes[item_type]
                            quantity_operation[item_type] = (full_lot_sizes + 1) * lotsizes[item_type]
                    else:
                        raise ValueError(
                            f"Item type {item_type} found neither in fixed lotsizes or large stock -> required "
                            f"quantity operation can't be determined.")
                else:
                    pass
            quantity_operations = CollectionCounter({cp2: quantity_operation,
                                                     cp5: Counter({"initiated replenishment order": -1})})

        # time based calculation
        elif ro.order_type == "time based":
            for item_type in items_other_brands.intersection(time_based_replenishment_items):
                if item_type in fixed_lotsizes.keys():
                    quantity_operation[item_type] = fixed_lotsizes[item_type]
                elif item_type in large_stock.keys():
                    demand = large_stock[item_type] - quantity_state[cp2][item_type]
                    if demand % lotsizes[item_type] == 0:
                        quantity_operation[item_type] = demand
                    else:
                        # always round up demand to the next full lot size
                        full_lot_sizes = demand // lotsizes[item_type]
                        quantity_operation[item_type] = (full_lot_sizes + 1) * lotsizes[item_type]
                else:
                    raise ValueError(
                        f"Item type {item_type} found neither in fixed lotsizes or large stock -> required "
                        f"quantity operation can't be determined.")
            quantity_operations = CollectionCounter({cp2: quantity_operation})
        else:
            raise ValueError(f"Order type {ro.order_type} is neither time based nor stock based.")

        return quantity_operations


## Event
class PlaceReplenishmentOrder(Event):
    activity_name = "Place Replenishment Order"
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):

        # duration roundabout 10 minutes
        minutes = -1
        while minutes < 0:
            minutes = self.draw_from_normal_distribution(mean=10, std=1)
        duration = datetime.timedelta(minutes=minutes)

        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=duration)

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        """Specify delivery that will be arriving in the future.
        Functionality:
        1. Update object quantity of replenishment order involved in event
        2. Draw lead time
        3. Determine delivered quantities (positive mirror of the replenishment order)
        4. Create delivery creation instruction with o2o relationship to corresponding replenishment order.
        """

        # get relevant quantity update
        collection_point = [cp for cp in self.quantity_operations.keys() if cp.name == "cp2"][0]
        quantity_update_cp2 = self.quantity_operations[collection_point]  # positive, as adds to cp2

        # identify involved replenishment order
        ro = [obj for obj in self.objects if isinstance(obj, ReplenishmentOrder)][0]
        # print(f"Initial replenishment order quantities {ro.quantities}")

        # update object quantity of replenishment order involved in event
        ro.quantities.subtract(quantity_update_cp2)  # negative, as RO describes demand / lack of available items
        # print(f"Adjusted replenishment order quantities {ro.quantities}")

        # draw lead time
        lead_time = datetime.timedelta(days=-1)
        while lead_time < datetime.timedelta(days=0):
            lead_time = rng.normal(**lead_time_distributions_days[ro.supplier]) * datetime.timedelta(days=1)

        # determine object quantity
        # => ro is demand, delivery is availability => delivery must have positive quantities
        quantity = Counter()
        quantity.subtract(ro.quantities)

        # create delivery object
        delivery_instruction = InstructionObjectCreation(timedelta=lead_time, object_type=Delivery,
                                                         quantities=quantity, add_to_binding=False,
                                                         o2o={ro: "delivery"},
                                                         initial_attributes={"supplier": ro.supplier})
        return [delivery_instruction]

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        return []


### t1: Identify incoming Delivery ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# added below

## Guards
def object_guard_t1(binding_function: BindingFunction) -> bool:
    delivery = list(binding_function[Delivery])[0]

    # if supplier is PADS, then t1 is only enabled if binding does not refer to a RO
    if delivery.supplier == "PADS":
        if len(binding_function[ReplenishmentOrder]) == 0:
            return True
        else:
            return False
    else:
        # otherwise, t1 is only enabled if binding refers to exactly one RO...
        if len(binding_function[ReplenishmentOrder]) == 1:
            ro = list(binding_function[ReplenishmentOrder])[0]

            # and this ro must be mentioned in the delivery's o2o relationship
            if ro in delivery.o2o.keys():
                return True
            else:
                return False
        else:
            return False


## Quantity Calculator
# none

## Event
# none

### t2: Unload Delivery ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
#addded below

## Guards
# none

## Quantity Calculator
# none

## Event
class UnloadDelivery(Event):
    activity_name = "Unpack Incoming Delivery"
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):
        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=duration)

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:

        number_of_palettes = len(binding_function[Palette])
        number_of_employees = len(binding_function[WarehouseEmployees])
        duration_per_palette = rng.uniform(low=speed_of_unloading_palette["min"],
                                           high=speed_of_unloading_palette["max"])
        self.add_duration(datetime.timedelta(seconds=(number_of_palettes * duration_per_palette / number_of_employees)))

        # enter loading bay as event attribute
        loading_bay = list(binding_function[LoadingBay])[0]
        self.loading_bay = loading_bay.name

        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        return []

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        """Distribute the items of the delivery to palettes. The majority of handling units only contain are be
        single-variety item type. Misalignment in the number of items of a particular type in the delivery and the
        capacity of single-variant handling units are be handled by creating a mixed handling units (greedy strategy)."""

        # identify delivery object
        do = list(input_binding[Delivery])[0]

        # create necessary variables
        delivered_quantities = do.quantities
        instructions_palettes = []
        additional_items = {}

        # determine number of palettes
        for item_type in set(delivered_quantities.elements()):  # Counter.elements() only considers positive quantities
            number_of_palettes = delivered_quantities[item_type] // items_per_palette[item_type]
            for i in range(number_of_palettes):
                palette = InstructionObjectCreation(timedelta=datetime.timedelta(0), object_type=Palette,
                                                    quantities=Counter({item_type: items_per_palette[item_type]}),
                                                    add_to_binding=True, o2o={do: "Palette part of Delivery"})
                instructions_palettes.append(palette)
            if delivered_quantities[item_type] % items_per_palette[item_type] > 0:
                additional_items[item_type] = delivered_quantities[item_type] % items_per_palette[item_type]
            else:
                pass

        if len(additional_items) == 0:
            return instructions_palettes
        else:
            pass

        # create additional mixed palette for remaining items
        mixed_item_palettes = binpacking.to_constant_volume(additional_items, items_per_palette["mixed"])
        for palette_quantity in mixed_item_palettes:
            if Counter(palette_quantity):
                palette = InstructionObjectCreation(timedelta=datetime.timedelta(0), object_type=Palette,
                                                    quantities=Counter(palette_quantity), add_to_binding=True,
                                                    o2o={do: "Palette part of Delivery"})
                instructions_palettes.append(palette)
            else:
                pass

        return instructions_palettes


### t3: Place delivered Items into Inventory ###

## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
def quantity_guard_t3(binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
    """ Transition has a quantity connection to cp0 and cp1, hence the quantity state is be a collection counter only
    referring to cp0 and cp1, the binding function only refers to a single palette and a single employee. As each
    palette belongs to a single delivery, PADS items are not mixed with other brands. So if the palette contains
    non-brand items, it does not also contain PADS items. PADS items are put into cp0 (VMI) and all other brands are
    placed in Warehouse cp1.
    The transition is only enabled if the object quantity of the entire palette can be placed in stock. PADS items can
    always be placed in stock, as cp0 has no capacity restraints. The collection point cp1 reserves some space for
    particularly bulky items which can only be used for items of these types. Any additional space is shared but jointly
    restricted."""
    palette = list(binding_function[Palette])[0]
    object_quantity = palette.quantities.copy()
    delivered_item_types = set(object_quantity.elements())

    if delivered_item_types.issubset(items_PADS):
        return True
    else:
        # identify warehouse and get current item level
        cp1 = [cp for cp in quantity_state.keys() if cp.name == "cp1"][0]

        # item types with dedicated space
        item_types_dedicated_space = set(dict(warehouse_capacity["cp1"]).keys()) - {"Other"}

        # capacity used before event
        used_capacity_dedicated_space = counter_projection(quantity_state[cp1], item_types_dedicated_space)
        used_capacity_joint_space = counter_projection(quantity_state[cp1], joint_warehouse_capacity).total()

        # create a counter according to space restrictions
        used_capacity = used_capacity_dedicated_space.copy()
        used_capacity.update(Counter({"Other": used_capacity_joint_space}))

        # determine delta through adding palette to inventory
        dedicated_space_addition = counter_projection(object_quantity, item_types_dedicated_space)
        joint_space_addition = counter_projection(object_quantity, joint_warehouse_capacity)
        capacity_used_by_palette = dedicated_space_addition.copy()
        capacity_used_by_palette.update(Counter({"Other": joint_space_addition.total()}))

        # check if adding palette does not exceed capacity
        space_taken_with_palette = used_capacity.copy()
        space_taken_with_palette.update(capacity_used_by_palette)

        if space_taken_with_palette <= warehouse_capacity["cp1"]:
            return True
        else:
            return False


## Quantity Calculator
class DistributePaletteToInventory(Qalculator):
    """Number of items placed into the corresponding collection point."""

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Items from Handling Unit / Palette are placed into Warehouse and Vendor Managed Inventory (VMI).
        As transition is only enabled if available capacity is sufficient and a palette either contains only PADS item
        types or only other brands (it can never be mixed), the quantity update is simply the object
        quantity of the palette. The collection point is determined by the item types on the palette."""

        object_quantity = list(binding_function[Palette])[0].quantities
        delivered_item_types = set(object_quantity.elements())
        quantity_update = Counter()

        if delivered_item_types.issubset(items_PADS):
            cp0 = [cp for cp in quantity_state.keys() if cp.name == "cp0"][0]
            quantity_update.update(object_quantity)
            return CollectionCounter({cp0: quantity_update})
        else:
            cp1 = [cp for cp in quantity_state.keys() if cp.name == "cp1"][0]
            quantity_update.update(object_quantity)
            return CollectionCounter({cp1: quantity_update})

## Binding Selection Function
def prioritise_boxes(transition):
    """When determining the palettes to place into storage, prioritise palettes carrying boxes."""

    all_palettes = transition._input_places_marking_intersection(object_type=Palette)
    active_palettes = {obj for obj in all_palettes if obj.status_active}
    if active_palettes:
        pass
    else:
        return None

    select_box_palettes = {palette for palette in active_palettes if palette.quantities == Counter(
        {"Box": items_per_palette["Box"]})}

    if select_box_palettes:
        object_type_sets = {Palette: [{select_box_palettes.pop()}]}
    else:
        select_box_palettes = {palette for palette in active_palettes if "Box" in palette.quantities}
        if select_box_palettes:
            object_type_sets = {Palette: [{select_box_palettes.pop()}]}
        else:
            object_type_sets = {Palette: [{active_palettes.pop()}]}

    for object_type in transition.input_object_types - {Palette}:
        object_sets = []
        required_objects = transition.binding_function_quantities[object_type]
        minimum_objects = transition.minimum_binding_function_quantities[object_type]
        maximum_objects = transition.maximum_binding_function_quantities[object_type]
        # print(f"Object type: {object_type.object_type_name}, required: {required_objects}, min: {minimum_objects}, max: {maximum_objects}")

        # get objects that are part of all input places of that type
        marking_intersection = transition._input_places_marking_intersection(object_type=object_type)
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
                        if transition.guard(binding_function=binding_function,
                                            quantity_state=transition.quantity_state)]

    if enabled_bindings:
        return enabled_bindings
    else:
        return None


## Event
# none

### t4: Register incoming Customer Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
# none

# Quantity Calculator
class RegisterQuantitiesOfAcceptedOrders(Qalculator):
    """Register the demand for all items of customer orders that can be accepted."""

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Binding function refers to an employee and a customer order. The quantity state describes the item levels of
        the VMI (cp0), the reservation count of PADS items (cp4), and the planning duplicate of the company warehouse (cp1).
        Functionality: 1) Determine whether customer order can be accepted. COs are accepted if all required PADS items
        are available => check if all PADS items of the customer order are available in the VMI under consideration of
        the still available, yet reserved items.
        2) If CO can't be accepted, no quantity operations are executed. 3) If CO can be accepted, the all PADS items
        required for this customer order are added as reserved in cp4. Additionally, the demand for
        all non-PADS items is booked in the planning duplicate of the company's warehouse (cp1), by removing the
        corresponding item quantities."""

        quantity_operations = CollectionCounter()

        # identify all definitely needed collection points
        co = list(binding_function[CustomerOrder])[0]
        cp0 = [cp for cp in quantity_state.keys() if cp.name == "cp0"][0]
        cp4 = [cp for cp in quantity_state.keys() if cp.name == "cp4"][0]
        cp2 = [cp for cp in quantity_state.keys() if cp.name == "cp2"][0]

        # determine PADS demand and other items
        pads_demand = counter_projection(co.quantities, items_PADS)  # negative
        required_pads_items = -pads_demand  # positive
        other_demand = counter_projection(co.quantities, items_other_brands)  # negative

        ### 1. check if customer order is accepted ###
        # get relevant item levels and available items
        relevant_reserved_items_pads = counter_projection(quantity_state[cp4], set(pads_demand.keys()))  # positive
        available_pads_items = counter_projection(quantity_state[cp0], set(pads_demand.keys()))  # positive
        available_pads_items.subtract(relevant_reserved_items_pads)  # positive

        # if all enough unreserved PADS items are available, we can accept the customer order
        if required_pads_items <= available_pads_items:
            pass
        else:
            return quantity_operations

        ### 2. determine quantity operations to PADS inventories ###
        # reserve required PADS items
        quantity_operations[cp4] = required_pads_items  # positive

        ### 3. determine quantity operations to company's warehouse ###
        # remove the demand for the non-PADS items from the planning duplicate of the company's warehouse (cp1)
        quantity_update_cp2 = Counter({"Box": -1})  # always remove a box
        quantity_update_cp2.update(other_demand)  # - + - = -
        quantity_operations[cp2] = quantity_update_cp2  # negative, as removes from cp2

        return quantity_operations


# Event
class RegisterIncomingCustomerOrder(Event):
    activity_name = "Register incoming Customer Order"
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):

        # duration roundabout 12 minutes
        minutes = -1
        while minutes < 0:
            minutes = self.draw_from_normal_distribution(mean=12, std=1)
        duration = datetime.timedelta(minutes=minutes)

        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=duration)

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        """If CO is accepted, there will be at least one quantity operation (to cp4 with reserved PADS items and/or from
        cp2 booking the demand of non-PADS items). If CO is not accepted, no quantity operations are executed.
        If the CO is accepted, set the status of the CO to accepted. If the CO is not accepted, the status of the CO
        is set to rejected."""

        # identify customer order
        co = [obj for obj in self.objects if isinstance(obj, CustomerOrder)][0]

        # draw time until attribute change
        timedelta = self.duration * rng.uniform(0, 0.99)

        if self.quantity_operations == CollectionCounter():
            # print(f"CO not accepted, as quantity operations: {self.quantity_operations}")
            change_object_attribute = InstructionObjectAttributeUpdate(timedelta=timedelta, object=co,
                                                                       attribute_values={
                                                                           "customer_order_accepted": False})
        else:
            # print(f"CO accepted, as quantity operations: {self.quantity_operations}")
            change_object_attribute = InstructionObjectAttributeUpdate(timedelta=timedelta, object=co,
                                                                       attribute_values={
                                                                           "customer_order_accepted": True})
        return [change_object_attribute]

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        """If CO is accepted, customer_order_accepted is set to True. If CO is not accepted, customer_order_accepted is
        False. If the CO is accepted, create a RemainingCO object with the demand of the CO.
        """
        # identify co
        co = [obj for obj in self.objects if isinstance(obj, CustomerOrder)][0]

        if co.customer_order_accepted:
            # create remaining CO object
            remaining_co = InstructionObjectCreation(timedelta=datetime.timedelta(0), object_type=RemainingCO,
                                                     quantities=co.quantities, o2o={co: "Full Demand"})
            # create parcel object
            time_until_parcel_creation = self.draw_from_uniform_distribution(min=2, max=30)
            parcel = InstructionObjectCreation(timedelta=datetime.timedelta(minutes=time_until_parcel_creation),
                                               object_type="Parcel", quantities=Counter(),
                                               o2o={co: "Corresponding Order"})
            return [remaining_co, parcel]
        else:
            time_until_execution = self.draw_from_uniform_distribution(min=20, max=600)
            instruction_order_cancellation = InstructionExecuteEvent(time_until_execution=datetime.timedelta(seconds=time_until_execution),
                                                                     activity="Cancel Customer Order",
                                                                     input_binding_function=BindingFunction({CustomerOrder: MultisetObject(
                                                                         {co})}))
            return [instruction_order_cancellation]

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        return []


### t5: Pick and pack items for Customer Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
def object_guard_t5(binding_function: BindingFunction) -> bool:
    """Transition is only enabled if the order is accepted and if binding refers to corresponding Customer Order and
    RemainingCO objects."""
    rco = list(binding_function[RemainingCO])[0]
    co = list(binding_function[CustomerOrder])[0]

    # order is accepted
    if co.customer_order_accepted:
        pass
    else:
        return False

    # rco refers to co
    if co in rco.o2o.keys():
        return True
    else:
        return False

class QuardT5(QuantityGuard):

    def __init__(self):
        super().__init__()

    def check_quantity_enablement(self, binding_function: BindingFunction, quantity_state: CollectionCounter):
        """Enabled if the following conditions are fulfilled:
        1. At least one box is available in cp1.
        2. The full demand for PADS items can be fulfilled.
        3. If the remaining demand is a partial demand, the entire remaining demand can be fulfilled."""

        # identify involved collection points
        cp0 = [cp for cp in quantity_state.keys() if cp.name == "cp0"][0]  # VMI
        cp1 = [cp for cp in quantity_state.keys() if cp.name == "cp1"][0]  # Warehouse

        # identify involved objects
        co = list(binding_function[CustomerOrder])[0]
        rco = list(binding_function[RemainingCO])[0]

        # identify pads demand and other demand
        pads_demand = counter_projection(rco.quantities, items_PADS)
        other_demand = counter_projection(rco.quantities, items_other_brands)
        demanded_pads_item_types = set(pads_demand.keys())
        demanded_other_item_types = set(other_demand.keys())
        # print("PADS demand: ", pads_demand)
        # print("Other demand: ", other_demand)

        # get projected quantity states
        quantity_state_cp0 = counter_projection(quantity_state[cp0], demanded_pads_item_types)
        quantity_state_cp1 = counter_projection(quantity_state[cp1], demanded_other_item_types)

        ### 1. Check if at least one box is available in cp1 ###
        # print(f"At least one box: {quantity_state[cp1]}")
        if quantity_state[cp1]["Box"] >= 1:
            pass
        else:
            # print(f"No box")
            return False

        ### 2. Check if the full demand for PADS items can be fulfilled ###
        required_pads_items = -pads_demand
        # print(f"Required PADS: {required_pads_items}")
        # print(f"PADS availability: {quantity_state[cp0]}")
        if required_pads_items <= quantity_state[cp0]:
            pass
        else:
            # print(f"Not full PADS demand.")
            return False

        ### 3. Check if at least one item can be removed ###
        if quantity_state_cp0.total() + quantity_state_cp1.total() > 0:
            pass
        else:
            return False


        ### 4. Check if rco covers the entire demand of the co ###
        if rco.quantities == co.quantities:
            # print(f"First order - all go!")
            return True
        else:
            pass

        ### 5. Check if entire remaining demand can be settled by physical inventory ###
        required_other_items = -other_demand
        # print("Required other items: ", required_other_items)
        # print("Available other items: ", quantity_state[cp1])
        if required_other_items <= quantity_state[cp1]:
            return True
        else:
            return False


# Quantity Calculator
class RemoveItemsAccordingToCustomerOrder(Qalculator):
    """Removed items from the two warehouses according to remaining demand of customer order and according to business
    rules:
    1) Every parcel needs a box, which has to be picked from cp1.
    2) If the remaining demand is the full demand, remove as many demanded items as possible but at least all items to
     settle demand for PADS items. This means that all PADS items are removed from the VMI, the reservations for the
     items are removed, and the removal of items is booked in the planning duplicate of the VMI. As many available other
     items as possible are removed from the company's warehouse.
    3) If the remaining demand is a partial quantity of the full demand, remove the entire remaining demand from the
    company's warehouse"""

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """
        Quantity state refers to four decoupling points: cp0 (VMI), cp1 (Warehouse), cp3 (PADS inventory - planning
        duplicate), and cp4 (PADS item reservations). All quantity connections are removing.
        The involved objects are: 1 CO, 1 RemainingCO, 1 Parcel, 1 Employee.

        Every execution removes one Box from cp1, other quantity operations differ according to the remaining demand of
        the CO that has to be settled. No more than two parcels may be sent to filfill the full demand of a customer
        order, therefore, the next step is to identify whether this is the first of the second time items are picked
        with regard to the same CO. This is done by comparing the remaining demand with the full demand of the CO.
        If it is the first parcel: The transition is only enabled, if all ordered PADS items are available in the VMI =>
        the quantity operation to cp0 removes all PADS items of the customer order. Furthermore, the reservations for
        these items are removed from cp4 and the removal of the PADS-items from the VMI is booked in the planning
        duplicate cp3. Additionally, the demand for all available non-PADS items is settled in by a removing quantity
        operation to cp1. If it is the second parcel: The transition is only enabled, if the entire remaining demand can
        be settled by the physical inventory. As all PADS items have been removed in the first iteration, there is only
        one non-zero quantity operation => the quantity operation to cp1 removes the entire remaining demand.

        Thus, the quantity operations are determined as follows:
        1) The quantity operation of cp1 always removes one box.
        2) Determine iteration of removal for CO => compare remaining demand to co demand.
            a) First iteration:
                - remove all demanded PADS items from VMI (cp0)
                - remove all reservations for PADS items from cp4
                - remove demand for PADS items from planning duplicate of VMI (cp3)
                - remove available demand for non-PADS items from company's warehouse (cp1)
            b) Second iteration:
                - remove entire remaining demand from company's warehouse (cp1)
        """
        quantity_operations = CollectionCounter()


        # identify involved objects
        co = list(binding_function[CustomerOrder])[0]
        rco = list(binding_function[RemainingCO])[0]

        # identify involved collection points
        cp0 = [cp for cp in quantity_state.keys() if cp.name == "cp0"][0]  # VMI
        cp1 = [cp for cp in quantity_state.keys() if cp.name == "cp1"][0]  # Warehouse
        cp3 = [cp for cp in quantity_state.keys() if cp.name == "cp3"][0]  # PADS planning duplicate
        cp4 = [cp for cp in quantity_state.keys() if cp.name == "cp4"][0]  # PADS reservations
        cp2 = [cp for cp in quantity_state.keys() if cp.name == "cp2"][0]  # planning system

        # quick check for validity: 1) if remaining demand is larger than full demand raise error, 2) if remaining demand is
        # empty raise error, 3) if remaining demand contains PADS items, raise error.
        if -rco.quantities > -co.quantities:
            print(f"Remaining Demand: {rco.quantities}, Full Demand: {co.quantities}")
            raise ValueError("Remaining demand is larger than full demand so there must be an Error somewhere.")
        elif rco.quantities == Counter():
            print(f"Remaining Demand: {rco.quantities}")
            raise ValueError("Somehow completely fulfilled demand has been cycled back (remaining demand is empty). "
                             "There must be an error.")
        elif counter_projection(rco.quantities, items_PADS) > Counter():
            print(f"Remaining Demand: {rco.quantities}")
            raise ValueError("Remaining demand contains PADS items, which should not be possible.")
        else:
            pass

        # print(f"Picking and packing was enabled with a remaining demand of {rco.quantities} for CO {co}.")

        ### 1. Remove PADS items ###
        # demand for PADS items
        demand_pads_items = counter_projection(rco.quantities, items_PADS)

        # execute removal of PADS items in all PADS-item inventories
        quantity_update_pads = self.quantity_update_removing_available_items(demand_pads_items, quantity_state[cp0])
        # relevant_item_levels_VMI = counter_projection(quantity_state[cp0], set(demand_pads_items.keys()))
        # print(f"The item level for the involved item types of the VMI is {relevant_item_levels_VMI}")

        # double check whether all demanded PADS items can be removed from VMI
        if quantity_update_pads == demand_pads_items:
            pass
        else:
            raise ValueError("Not all PADS items could be removed from VMI, so transitions was incorrectly enabled.")

        # print(f"Quantity update PADS for {co}: {quantity_update_pads}")
        # remove all required pads items from VMI and from reservations
        quantity_operations[cp0] = quantity_update_pads
        quantity_operations[cp4] = quantity_update_pads
        quantity_operations[cp3] = quantity_update_pads

        ### 2. Remove other items ###
        # demand non-PADS items
        demand_non_pads_items = counter_projection(rco.quantities, items_other_brands)
        # relevant_item_levels_other = counter_projection(quantity_state[cp1], set(demand_non_pads_items.keys()))
        # print(f"The item level for the involved item types of the warehouse is {relevant_item_levels_other}")

        # quantity update removing all available items
        quantity_update_other_items = self.quantity_update_removing_available_items(demand=demand_non_pads_items,
                                                                                    available_items=quantity_state[cp1])

        # always remove a box
        quantity_update_cp1 = Counter({"Box": -1})
        quantity_update_cp1.update(quantity_update_other_items)
        # print(f"Quantity update other items for {co}: {quantity_update_cp1}")
        quantity_operations[cp1] = quantity_update_cp1

        # book additional removal of a box for a second delivery in planning system
        if demand_non_pads_items == quantity_update_other_items:
            quantity_operations[cp2] = Counter()
        else:
            quantity_operations[cp2] = Counter({"Box": -1})

        return quantity_operations

# Event
class PickAndPackItemsForCustomerOrder(Event):
    activity_name = "Pick and pack items for Customer Order"
    log_activity = True

    def __init__(self, timestamp: datetime.datetime, label: str = None, properties: dict = None,
                 duration: datetime.timedelta = None):

        super().__init__(timestamp=timestamp, label=label, properties=properties, duration=duration)

    def _execute_event_start(self, binding_function: BindingFunction, quantity_state: CollectionCounter = None) -> list[
        Instruction]:
        """1) Determine duration of event in accordance with binding function (duration dependent on # picked items).
        2) Add o2o relationship to picking employee to support next event is executed by the same employee."""

        # set duration according to the number of items that could theoretically be picked
        rco = list(binding_function[RemainingCO])[0]
        event_total_item_movement = get_abs_counter(rco.quantities).total() + 1 # include the box
        minutes_per_item = rng.uniform(low=speed_of_picking_items["min"], high=speed_of_picking_items["max"])
        duration = event_total_item_movement * minutes_per_item

        if duration <= 0:
            raise ValueError("Duration of picking and packing event is not positive.")
        else:
            self.add_duration(datetime.timedelta(seconds=duration))

        # add o2o relation to picking employee
        parcel_ot = [ot for ot in binding_function.keys() if ot.object_type_name == "Parcel"][0]
        parcel = list(binding_function[parcel_ot])[0]
        emp = list(binding_function[WarehouseEmployees])[0]
        parcel.add_o2o_relationship(obj=emp, relationship="Packing Employee")

        return []

    def _execute_event_end(self, execution: Execution) -> list[Instruction]:
        """Set object quantity for parcel, to add information of items associated with this parcel.
        If not the entire demand is fulfilled, create new RemainingCO object so the rest can be picked.
        Set o2o relationship between parcel and customer order."""

        # identify collection_points
        cp0 = [cp for cp in self.quantity_operations.keys() if cp.name == "cp0"][0]
        cp1 = [cp for cp in self.quantity_operations.keys() if cp.name == "cp1"][0]

        # identify removed items
        items_removed_cp1 = -self.quantity_operations[cp1]  #positive
        pads_items_removed = -self.quantity_operations[cp0]  #positive

        # identify involved objects
        co = [obj for obj in self.objects if isinstance(obj, CustomerOrder)][0]
        parcel = [obj for obj in self.objects if obj.object_type.object_type_name == "Parcel"][0]
        rco = [obj for obj in self.objects if isinstance(obj, RemainingCO)][0]

        ### 1. Associate Parcel with customer order ###
        # set o2o relationship of parcel's association to customer order
        parcel.add_o2o_relationship(obj=co, relationship="Customer Order")

        ### 2. set object quantity of parcel ###
        # determine ordered items within the parcel
        non_box_items = counter_projection(items_removed_cp1, set(items_removed_cp1.keys()) - {"Box"})
        non_box_items.update(pads_items_removed)
        # print(f"  Items removed from Warehouse (cp1): {items_removed_cp1}")
        # print(f"  Items removed from VMI (cp0): {pads_items_removed}")
        # print(f"  Items in Parcel: {non_box_items}")

        # logging of parcel object quantity removed.
        parcel.quantities = non_box_items

        ### 3. Associate Customer Order with Parcel ###
        # determine remaining open demand
        fulfilled_demand = Counter()
        fulfilled_demand.subtract(non_box_items)
        # print(f"  Fulfilled demand: {fulfilled_demand}")
        # print(f"  Customer order demand ({co}): {co.quantities}")
        # print(f"  Remaining demand considered in this operations ({rco}): {rco.quantities}")

        # full demand of customer order fulfilled, first and final iteration
        if fulfilled_demand == co.quantities == rco.quantities:  # full demand fulfilled
            # add o2o relationship to CO to indicate that the parcel contains the full order
            # print(f"### Full Demand of {co} fulfilled")
            co.add_o2o_relationship(obj=parcel, relationship="Full Order")
            return []

        # not the full demand fulfilled but full remaining demand fulfilled => remaining open demand fulfilled
        elif fulfilled_demand == rco.quantities:
            # print(f"### Remaining demand of {co} fulfilled")
            co.add_o2o_relationship(obj=parcel, relationship="Remaining Order")
            return []

        # neither full demand nor full remaining demand fulfilled => partial demand fulfilled
        else:
            co.add_o2o_relationship(obj=parcel, relationship="Partial Order")

        ### 4. Create remaining customer order and parcel objects for second iteration ###
        # calculate remaining demand
        remaining_demand = determine_remaining_demand(possible_demand=fulfilled_demand, full_demand=co.quantities)
        remaining_demand = counter_projection(remaining_demand, items_other_brands - {"Box"})
        # print(f"### Partial Demand of {co} fulfilled: {fulfilled_demand}, Remaining open demand: {remaining_demand}")
        # print(f"  Fulfilled demand: {fulfilled_demand}")
        # print(f"  Customer order demand ({co}): {co.quantities}")
        # print(f"  Remaining demand considered in this operations ({rco}): {rco.quantities}")

        time_until_rco = self.draw_from_uniform_distribution(min=0.01, max=5) * datetime.timedelta(minutes=1)
        time_until_parcel = self.draw_from_uniform_distribution(min=5, max=15) * datetime.timedelta(minutes=1)

        # create new remaining CO object for next iteration
        instruction_remaining_co = InstructionObjectCreation(timedelta=time_until_rco,
                                                             object_type=RemainingCO,
                                                             quantities=remaining_demand,
                                                             o2o={co: "Partial Demand"})

        # create parcel object for next iteration
        instruction_new_parcel = InstructionObjectCreation(timedelta=time_until_parcel,
                                                           object_type="Parcel",
                                                           quantities=Counter(),
                                                           o2o={co: "Corresponding Order"})

        return [instruction_remaining_co, instruction_new_parcel]

    def create_objects_for_binding(self, input_binding: BindingFunction) \
            -> list[InstructionObjectCreation]:
        return []


### t6: Send Parcel to Customer ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
def object_guard_t6(binding_function: BindingFunction) -> bool:
    """Transition is only enabled if binding refers to the same employee who picked items."""
    # identify parcel and employee
    parcel_ot = [ot for ot in binding_function.keys() if ot.object_type_name == "Parcel"][0]
    parcel = list(binding_function[parcel_ot])[0]
    emp = list(binding_function[WarehouseEmployees])[0]

    if emp in parcel.o2o.keys():
        return True
    else:
        return False


## Quantity Calculator
# none

## Event
# nothing special

### t8: Completed Customer Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
def object_guard_t8(binding_function: BindingFunction) -> bool:
    """Transition is only enabled if involved customer order has fully settled demand."""

    # identify customer order
    co = list(binding_function[CustomerOrder])[0]

    if "Full Order" in co.o2o.values() or "Remaining Order" in co.o2o.values():
        return True
    else:
        return False


## Quantity Calculator
# none

## Event
# nothing special

### t9: Remaining Items for Customer Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
#none

## Guards
def object_guard_t9(binding_function: BindingFunction) -> bool:
    """Transition is only enabled if involved customer order only has partially settled demand which has not yet been
    completed."""

    # identify customer order
    co = list(binding_function[CustomerOrder])[0]
    # print(co.o2o.values())

    if ("Full Order" not in co.o2o.values()) and ("Remaining Order" not in co.o2o.values()):
        return True
    else:
        return False


## Quantity Calculator
# none

## Event
# none

### t10: Cancel Customer Order ###
## Quantified Objects (binding_function_quantities) dict[Type[Object]: int]
# none

## Guards
def object_guard_t10(binding_function: BindingFunction) -> bool:
    """Transition is only enabled if involved customer order has been cancelled."""
    co = list(binding_function[CustomerOrder])[0]
    return not co.customer_order_accepted


## Quantity Calculator
# none

## Event

############## CONFIGURATION Q-NET ###################

## labels
transition_labels = {"t0": "Place Replenishment Order",
                     "t1": "Identify incoming Delivery",
                     "t2": "Unpack Incoming Delivery",
                     "t3": "Place delivered Items into Inventory",
                     "t4": "Register incoming Customer Order",
                     "t5": "Pick and pack items for Customer Order",
                     "t6": "Send Parcel to Customer",
                     "t8": "Completed Customer Order",
                     "t9": "Remaining Items for Customer Order",
                     "t10": "Cancel Customer Order",
                     "t11": "Initiate Replenishment Order (SmallStock)",
                     "t12": "Initiate PADS Delivery (TimeBased)",
                     "t13": "Initiate Replenishment Order (TimeBased)",
                     "t14": "Initiate PADS Delivery (SmallStock)"
                     }

silent_transitions = {"t11", "t12", "t13", "t14", "t9", "t8"}

quantity_guards = {"t3": quantity_guard_t3,
                   "t5": QuardT5()}

object_guards = {"t1": object_guard_t1,
                 "t5": object_guard_t5, # typical example for object guard
                 "t6": object_guard_t6,
                 "t8": object_guard_t8,
                 "t9": object_guard_t9,
                 "t10": object_guard_t10}

qualculators = {"t11": InitialisedReplenishments(),
                "t0": ReplenishmentOrderQualculator(),
                "t12": TimeBasedPADSDelivery(),
                "t14": SmallStockPADSDelivery(),
                "t3": DistributePaletteToInventory(),
                "t4": RegisterQuantitiesOfAcceptedOrders(),
                "t5": RemoveItemsAccordingToCustomerOrder()}

activities = [
    InitiateReplenishmentOrderSmallStock,
    InitiateReplenishmentOrderTimeBased,
    InitiatePADSDeliveryTimeBased,
    InitiatePADSDeliverySmallStock,
    PlaceReplenishmentOrder,
    UnloadDelivery,
    RegisterIncomingCustomerOrder,
    PickAndPackItemsForCustomerOrder]

### object places ###
place_mapping = {"p0": ReplenishmentOrder,
                 "p1": ReplenishmentOrder,
                 "p2": ReplenishmentOrder,
                 "p3": Delivery,
                 "p4": Delivery,
                 "p5": Delivery,
                 "p7": Palette,
                 "p8": Palette,
                 "p9": CustomerOrder,
                 "p10": CustomerOrder,
                 "p11": CustomerOrder,
                 "p13": CustomerOrder,
                 "p14": CustomerOrder,
                 "p15": RemainingCO,
                 "p16": RemainingCO,
                 "p18": "Parcel",
                 "p19": "Parcel",
                 "p20": "Parcel",
                 "p22": WarehouseEmployees,
                 "p24": WarehouseEmployees,
                 "p25": AdministrativeEmployees,
                 "p26": LoadingBay,
                 "p27": LoadingBay,
                 "p28": TimingReplenishmentOrder,
                 "p29": TimingReplenishmentOrder,
                 "p30": TimingPADSDelivery,
                 "p31": TimingPADSDelivery}

# initial and final
additional_initial_places = {"p22", "p25", "p26", "p3", "p0", "p7"}

### collection points ###
collection_point_labels = {"cp0": "PADS Inventory (VMI)",
                           "cp1": "Company Warehouse",
                           "cp2": "Planning System",
                           # "cp3": "PADS Inventory - planning duplicate",
                           # "cp4": "Reserved PADS items",
                           # "cp5": "Initiated Replenishment Orders",
                           }


### arcs ###
arcs = {
    ("t11", "p0"), ("cp2", "t11"), ("t11", "cp5"),
    ("p0", "t0"), ("t0", "p1"), ("p25", "t0"), ("t0", "p25"), ("t0", "cp2"), ("cp5", "t0"),
    ("p1", "t1"), ("t1", "p2"), ("p3", "t1"), ("t1", "p4"), ("p26", "t1"), ("t1", "p27"),
    ("p4", "t2"), ("t2", "p5"), ("t2", "p7"), ("p22", "t2"), ("t2", "p22"), ("p27", "t2"), ("t2", "p26"),
    ("p7", "t3"), ("t3", "p8"), ("p22", "t3"), ("t3", "p22"), ("t3", "cp0"), ("t3", "cp1"),
    ("p9", "t4"), ("t4", "p10"), ("p25", "t4"), ("t4", "p25"), ("t4", "cp2"), ("t4", "cp4"), ("cp0", "t4"),
    ("p10", "t10"), ("t10", "p11"),
    ("t5", "p13"), ("p10", "t5"), ("p15", "t5"), ("t5", "p16"), ("p18", "t5"), ("t5", "p19"), ("p22", "t5"),
    ("t5", "p24"), ("cp0", "t5"), ("cp1", "t5"), ("t5", "cp4"), ("t5", "cp3"), ("t5", "cp2"),
    ("p13", "t8"), ("t8", "p14"),
    ("p13", "t9"), ("t9", "p10"),
    ("p19", "t6"), ("t6", "p20"), ("p24", "t6"), ("t6", "p22"),
    ("t12", "p3"), ("p30", "t12"), ("t12", "p31"), ("t12", "cp3"),
    ("p28", "t13"), ("t13", "p29"), ("t13", "p0"),
    ("cp3", "t14"), ("t14", "p3")
}

# variable
variable_arcs = {("p1", "t1"), ("t1", "p2"), ("p6", "t2"), ("t2", "p7"), ("p22", "t2"), ("t2", "p22")}

########### Markings ###########
# object places

# collection points


qnet_conf = QnetConfig(name="example_material_flow")
qnet_conf.quantity_net_name = "qnet_config_example_material_flow"
qnet_conf.net_structure = arcs
qnet_conf.place_types = place_mapping
qnet_conf.initial_places = additional_initial_places
qnet_conf.collection_point_labels = collection_point_labels
qnet_conf.transition_labels = transition_labels
qnet_conf.object_types_classes = [CustomerOrder, ReplenishmentOrder, Delivery, Palette, WarehouseEmployees,
                                  AdministrativeEmployees, RemainingCO, LoadingBay, TimingReplenishmentOrder,
                                  TimingPADSDelivery]
qnet_conf.object_types_attributes = {"Parcel": {}}
qnet_conf.transition_object_guard = object_guards
qnet_conf.transition_quantity_guard = quantity_guards
qnet_conf.small_stock_guards = {"t11": quantity_guard_t11_config,
                                "t14": quantity_guard_t14_config}
qnet_conf.quantity_calculators = qualculators
qnet_conf.silent_transitions = silent_transitions
qnet_conf.manually_initiated_transitions = {"t10"}

qnet_conf.transition_binding_selection = {"t3": prioritise_boxes}

qnet_conf.initial_marking_object_types = {LoadingBay: loading_bays,
                                          CustomerOrder: 2,
                                          AdministrativeEmployees: len(AdministrativeEmployees.remaining_objects_to_create),
                                          WarehouseEmployees: len(WarehouseEmployees.remaining_objects_to_create)}
qnet_conf.initial_marking_collection_points = {"cp0": initial_item_level_PADS,
                                               "cp1": initial_item_level_other,
                                               "cp2": initial_item_level_other,
                                               "cp3": initial_item_level_PADS,
                                               "cp4": Counter(),
                                               "cp5": Counter()}


qnet_conf.activity_classes = activities
qnet_conf.silent_activities = {"Remaining Items for Customer Order", "Cancel Customer Order"}
qnet_conf.binding_function_quantities = {"t1": {ReplenishmentOrder: 0, Delivery: 1, LoadingBay: 1},
                                         "t2": {WarehouseEmployees: 0, Delivery: 1, Palette: 0, LoadingBay: 1}}
qnet_conf.maximum_binding_function_quantities = {"t1": {ReplenishmentOrder: 1, Delivery: 1, LoadingBay: 1},
                                                 "t2": {WarehouseEmployees: 2, Delivery: 1, Palette: 0, LoadingBay: 1}}
qnet_conf.minimum_binding_function_quantities = {"t2": {WarehouseEmployees: 1, Delivery: 1, Palette: 1, LoadingBay: 1}}
