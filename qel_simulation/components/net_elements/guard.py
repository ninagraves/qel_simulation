from collections import Counter
from typing import Callable

from qel_simulation.components.log_elements.object import BindingFunction
from qel_simulation.components.net_elements.collection_point import CollectionCounter, CollectionPoint


class QuantityGuardSmallstockConfig:

    def __init__(self, counter_threshold: dict[str | CollectionPoint: Counter],
                 counter_all_item_types: dict[str | CollectionPoint: bool] = None,
                 all_counter_condition: bool = True):
        self.counter_threshold: dict[str | CollectionPoint: Counter] = counter_threshold
        self.counter_all_item_types: dict[str | CollectionPoint: bool] = counter_all_item_types
        self.all_counter_condition = all_counter_condition

class QuantityGuard():

    def __init__(self):
        pass

    def __call__(self, binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
        """Determines whether transition is enabled with regard to the specifications."""
        return self.check_quantity_enablement(binding_function=binding_function, quantity_state=quantity_state)

    def check_quantity_enablement(self, binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
        return True

    def determine_available_items(self, demand: Counter, available_items: Counter) -> Counter:
        """Determine how many items can be removed and return quantity update for the removing all demanded and available items."""

        # identify required items and item types
        required_item_types = set(demand.keys())
        required_items = -demand  # positive

        # item level of required items that are available
        available_required_items = self.quantity_projection(available_items, required_item_types)  # positive

        # if all required items are available, remove them all
        if required_items <= available_required_items:
            return demand
        else:
            available_required_items.update(demand)  # item level if all items were removed
            required_available_items = +available_required_items  # positive, only positive counterpart
            quantity_update = Counter()
            quantity_update.subtract(required_available_items)  # quantity operation has to remove available items
            return quantity_update

    def quantity_projection(self, item_quantity: Counter, item_subset: set) -> Counter:
        """Projects the item_quantity on the passed item subset."""
        return Counter(
            {item: item_quantity[item] for item in item_subset.intersection(set(dict(item_quantity).keys()))})

    def determine_remaining_demand(self, possible_demand: Counter, full_demand: Counter) -> Counter:
        """Provide possible demand and full demand and return the remaining demand."""
        remaining_demand = full_demand.copy()
        remaining_demand.subtract(possible_demand)
        return remaining_demand


class QuantityGuardSmallStock(QuantityGuard):
    def __init__(self, counter_threshold: CollectionCounter,
                 counter_all_item_types: dict[CollectionPoint: bool] = None,
                 all_counter_condition: bool = True):

        super().__init__()

        self.counter_threshold = counter_threshold
        self.counter_all_item_types = counter_all_item_types if counter_all_item_types else \
            dict(zip(list(counter_threshold.keys()), [False] * len(counter_threshold.keys())))
        self.all_counter_condition = all_counter_condition

    def __call__(self, binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
        """Determines whether transition is enabled with regard to the specifications."""
        if self.all_counter_condition:
            return self.check_small_stock_counters_all(quantity_state=quantity_state)
        else:
            return self.check_small_stock_counters_any(quantity_state=quantity_state)

    def check_small_stock_counters_all(self, quantity_state: CollectionCounter) -> bool:

        for cp, threshold in self.counter_threshold.items():
            # check whether the condition has to be fulfilled for a single item type or for all item types
            if self.counter_all_item_types[cp]:  # check for all item types
                result_counter = self.check_item_types_all(item_level=quantity_state[cp], threshold=threshold)
            else:  # check for any item type
                result_counter = self.check_item_types_any(item_level=quantity_state[cp], threshold=threshold)

            if result_counter:
                pass
            else:
                return False

        return True

    def check_small_stock_counters_any(self, quantity_state: CollectionCounter) -> bool:

        for counter, threshold in self.counter_threshold.items():

            # check whether the condition has to be fulfilled for a single item type or for all item types
            if self.counter_all_item_types[counter]:  # check for all item types
                result_counter = self.check_item_types_all(item_level=quantity_state[counter], threshold=threshold)
            else:  # check for any item type
                result_counter = self.check_item_types_any(item_level=quantity_state[counter], threshold=threshold)

            if result_counter:
                return True
            else:
                pass

        return False

    def check_item_types_any(self, item_level: Counter, threshold: Counter) -> bool:
        """pass an item quantity and a threshold. Returns whether any item type quantity is below the threshold."""

        # only consider item level of relevant item types
        threshold_types = set(threshold.keys())
        relevant_item_level = self.quantity_projection(item_quantity=item_level, item_subset=threshold_types)

        # determine difference between item level and threshold
        delta = relevant_item_level
        delta.subtract(threshold)
        above_threshold = +delta

        # if all item types have a positive item level after subtracting the threshold, condition is not met
        if len(above_threshold.keys()) == len(threshold.keys()):
            return False
        else:
            return True

    def check_item_types_all(self, item_level: Counter, threshold: Counter) -> bool:
        """pass an item quantity and a threshold. Returns whether any item type quantity is below the threshold."""

        # only consider item level of relevant item types
        threshold_types = set(threshold.keys())
        relevant_item_level = self.quantity_projection(item_quantity=item_level, item_subset=threshold_types)

        # determine difference between item level and threshold
        delta = relevant_item_level
        delta.subtract(threshold)
        above_threshold = +delta

        # only if no item type has a positive item level after subtracting the threshold, condition is met
        if len(above_threshold.keys()) == 0:
            return True
        else:
            return False

class Guard():
    """Guard to put additional requirements to the execution of transitions depending on the current state of the net.
    Guard must only refer to binding of input object types (there is an input place of this object type),
    as object creation is called later in the process."""
    def __init__(self):
        self._object_guard = None
        self._quantity_guard = None
        pass

    @property
    def object_guard(self):
        if self._object_guard:
            return True
        else:
            return False

    @object_guard.setter
    def object_guard(self, object_guard: Callable[[BindingFunction], bool]):
        self._object_guard = object_guard

    @property
    def quantity_guard(self):
        if self._quantity_guard:
            return True
        else:
            return False

    def get_quantity_guard(self):
        return self._quantity_guard

    @quantity_guard.setter
    def quantity_guard(self, quantity_guard: Callable[[BindingFunction, CollectionCounter], bool] | QuantityGuardSmallStock):
        self._quantity_guard = quantity_guard

    def check_objects(self, binding_function: BindingFunction) -> bool:
        if self.object_guard:
            return self._object_guard(binding_function)
        else:
            return True

    def check_quantities(self, binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
        """" Therefore, quantity guard specifies what the quantity state must look like for the transition to be enabled."""
        if self.quantity_guard:
            return self._quantity_guard(binding_function, quantity_state)
        else:
            return True

    def __call__(self, binding_function: BindingFunction, quantity_state: CollectionCounter) -> bool:
        """Guard specifies if transition should fire given the current state of the net."""
        if self.check_objects(binding_function=binding_function):
            if self.check_quantities(binding_function=binding_function, quantity_state=quantity_state):
                return True
        else:
            return False

