from abc import ABC, abstractmethod
from collections import Counter

from qel_simulation.simulation.object import BindingFunction
from qel_simulation.components.collection_counter import CollectionCounter


class Qalculator (ABC):

    def __init__(self):
        self._connected_counters = set()

    @property
    def connected_counters(self):
        return self._connected_counters

    @connected_counters.setter
    def connected_counters(self, connected_counters):
        if isinstance(connected_counters, set):
            self._connected_counters = connected_counters
        else:
            raise ValueError("Connected counters must be a set.")

    # @abstractmethod
    # def intended_quantity_changes(self, binding_function: BindingFunction = BindingFunction()) -> Counter:
    #     """Determine the intended quantity changes for a given binding function independent of the current state of
    #     collection points."""
    #     ...
    #
    # @abstractmethod
    # def intended_relocations(self, quantity_state: CollectionCounter, binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
    #     """Determine the intended relocations for a given binding function independent of the current state of collection points."""
    #     ...
    #
    # @abstractmethod
    # def check_possibility_quantity_changes(self, intended_quantity_changes: Counter, quantity_state: CollectionCounter) -> bool:
    #     """Check if intended quantity changes are possible under consideration of the current state of adjacent
    #     collection points."""
    #     ...
    #
    # @abstractmethod
    # def check_possibility_relocations(self, intended_relocations: CollectionCounter, quantity_state: CollectionCounter) -> bool:
    #     """Check if intended relocations are possible under consideration of the current state of adjacent
    #     collection points."""
    #     ...
    #
    # @abstractmethod
    # def adjusted_quantity_changes(self, intended_quantity_changes: Counter, quantity_state: CollectionCounter) -> Counter:
    #     """Only called if quantity changes have to be adjusted according to provided conditions.
    #     Given the state of adjacent collection points, quantity changes are adjusted as defined in this method.
    #     """
    #     ...
    #
    # @abstractmethod
    # def adjusted_quantity_relocations(self, intended_relocations: CollectionCounter, quantity_state: CollectionCounter) -> CollectionCounter:
    #     """Only called if quantity changes have to be adjusted according to provided conditions.
    #     Given the state of adjacent collection points, quantity changes are adjusted as defined in this method.
    #     """
    #     ...
    #
    # @abstractmethod
    # def distribution_changes(self, quantity_changes: Counter, quantity_state: CollectionCounter) -> CollectionCounter:
    #     """Distributes the quantity changes to the connected collection points as specified in this method.
    #     Returns a collection counter describing the quantity change operations."""
    #     ...
    #
    # def valid_collection_counter(self, collection_counter: CollectionCounter, quantity_state: CollectionCounter):
    #     """Check if collection counter has an entry for every collection counter. Removes all entries that do not refer
    #     to collection points from the quantity state and adds empty Counters to all missing collection points."""
    #
    #     # check if collection counter has an entry for every collection counter
    #     for cp in collection_counter.keys():
    #         if not cp in quantity_state.keys():
    #             quantity_state[cp] = Counter()
    #
    #     # remove all entries that do not refer to collection points from the quantity state
    #     for cp in quantity_state.keys():
    #         if not cp in collection_counter.keys():
    #             del quantity_state[cp]
    #
    #
    # def material_movement(self, change_operations: CollectionCounter, final_relocations: CollectionCounter):
    #     """This method is called after all checks and adjustments have been made. It is used to determine the collected quantity
    #     operations that are to be executed. Describes the final change operations as well as the final relocations.
    #     This method is not abstract and does not have to be implemented."""
    #
    #     collection_points = set(change_operations.keys()) | set(final_relocations.keys())
    #     material_movement = CollectionCounter()
    #     for cp in collection_points:
    #         movement = Counter()
    #         movement.update(change_operations[cp])
    #         movement.update(final_relocations[cp])
    #         material_movement[cp] = movement
    #
    #     return material_movement
    #
    # def check_validity_relocations(self, intended_relocations: CollectionCounter):
    #     """Check if intended relocations describe a movement of items."""
    #     relocations = Counter()
    #     for movement in intended_relocations.values():
    #         relocations.update(movement)
    #     if not relocations.total() == 0:
    #         raise ValueError("Intended relocations do not describe a movement of items.")
    #     else:
    #         pass

    @abstractmethod
    def determine_quantity_operations(self, quantity_state: CollectionCounter, binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        """Determine quantity operations based on provided quantity state and binding function."""
        ...

    def determine_remaining_demand(self, possible_demand: Counter, full_demand: Counter) -> Counter:
        """Provide possible demand and full demand and get the remaining open demand."""
        remaining_demand = full_demand.copy()
        remaining_demand.subtract(possible_demand)
        return remaining_demand

    def quantity_update_removing_available_items(self, demand: Counter, available_items: Counter) -> Counter:
        """Determine how many items can be removed and return quantity update for the removing all demanded and available items."""

        # identify required items and item types
        required_item_types = set(demand.keys())
        required_items = -demand  # positive

        # item level of required items that are available
        item_level_required_item_types = self.counter_projection(available_items, required_item_types)  # positive
        available_required_items = item_level_required_item_types.copy()

        # if all required items are available, remove them all
        if required_items <= item_level_required_item_types:
            return demand
        else:
            # item level after removal of all available items
            available_required_items.update(demand)  # item level if all items were removed
            item_level_after_removal = +available_required_items  # positive, only positive counterpart

            # difference in item level is the quantity update
            removed_items = item_level_required_item_types - item_level_after_removal
            quantity_update = Counter()
            quantity_update.subtract(removed_items)  # quantity operation has to remove available items, so negative

            return quantity_update

    def counter_projection(self, counter: Counter, item_subset: set) -> Counter:
        """Projects the counter on the passed item subset."""
        return Counter({item: counter[item] for item in item_subset.intersection(set(dict(counter).keys()))})

class DefaulQalculator(Qalculator):
    def __init__(self):
        super().__init__()

    def determine_quantity_operations(self, quantity_state: CollectionCounter,
                                      binding_function: BindingFunction = BindingFunction()) -> CollectionCounter:
        return CollectionCounter()
