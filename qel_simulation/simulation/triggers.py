from abc import ABC, abstractmethod
from collections import Counter
from typing import Any

from qel_simulation.qnet_elements.collection_point import CollectionPoint
from qel_simulation.qnet_elements.object_place import ObjectPlace
from qel_simulation.qnet_elements.transition import Transition


# assumption: small stock is always positive

class Trigger(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class MultiTrigger(Trigger, ABC):

    def __init__(self, triggers: list[Trigger]):
        super().__init__()
        self._triggers = triggers

    @property
    def triggers(self):
        return self._triggers

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class AnyTrigger(MultiTrigger, ABC):

    def __init__(self, triggers: list[Trigger]):
        super().__init__(triggers=triggers)

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        return any([trigger.check_triggering(**kwargs) for trigger in self.triggers])


class AllTrigger(MultiTrigger, ABC):

    def __init__(self, triggers: list[Trigger]):
        super().__init__(triggers=triggers)

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""

        return all([trigger.check_triggering(**kwargs) for trigger in self.triggers])


class NetElementTrigger(Trigger, ABC):

    def __init__(self, net_element: Any):
        super().__init__()
        self._net_element = None
        self.net_element = net_element

    @property
    def net_element(self):
        return self._net_element

    @net_element.setter
    def net_element(self, net_element):
        self._net_element = net_element

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class PlaceMarkingTrigger(NetElementTrigger, ABC):

    def __init__(self, place: ObjectPlace):
        super().__init__(net_element=place)

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class PlaceMarkingLength(PlaceMarkingTrigger, ABC):

    def __init__(self, place: ObjectPlace, threshold: int):
        super().__init__(place=place)
        self._threshold = threshold

    @property
    def threshold(self):
        return self._threshold

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        return self.net_element.marking >= self.threshold


class PlaceMarkingMax(PlaceMarkingLength):

    def __init__(self, place: ObjectPlace, threshold: int):
        super().__init__(place=place, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Check if number of objects in the place is lower than threshold."""
        return len(self.net_element.marking) <= self.threshold


class PlaceMarkingMin(PlaceMarkingLength):

    def __init__(self, place: ObjectPlace, threshold: int):
        super().__init__(place=place, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Check if the number of objects in the place is as least as many as the threshold."""
        return len(self.net_element.marking) >= self.threshold


class TransitionTrigger(NetElementTrigger, ABC):

    def __init__(self, transition: Transition):
        super().__init__(net_element=transition)

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class TransitionExecutions(TransitionTrigger, ABC):

    def __init__(self, transition: Transition, threshold: int):
        super().__init__(transition=transition)
        self._threshold = threshold

    @property
    def threshold(self):
        return self._threshold

    @abstractmethod
    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class TransitionExecutionsMax(TransitionExecutions):

    def __init__(self, transition: Transition, threshold: int):
        super().__init__(transition=transition, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Check if number of executions of the transition is lower than threshold."""
        return len(self.net_element.executions) <= self.threshold


class TransitionExecutionsMin(TransitionExecutions):

    def __init__(self, transition: Transition, threshold: int):
        super().__init__(transition=transition, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Check if number of executions of the transition is as least as many as the threshold."""
        return len(self.net_element.executions) >= self.threshold


class QuantityTrigger(NetElementTrigger, ABC):

    def __init__(self, collection_point: CollectionPoint):
        super().__init__(net_element=collection_point)

    @property
    def item_types(self) -> set[str]:
        return self._get_item_types()

    @abstractmethod
    def check_triggering(self) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...

    @abstractmethod
    def _get_item_types(self) -> set[str]:
        """Define method to determine all the item types involved in the triggering of the policy."""
        ...


class QuantityTriggerItemTypes(QuantityTrigger):

    def __init__(self, collection_point: CollectionPoint, threshold: Counter):
        super().__init__(collection_point=collection_point)
        self._threshold = threshold

    @property
    def threshold(self):
        return self._threshold

    def _get_item_types(self) -> set[str]:
        return set(self.threshold.keys())

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled."""
        ...


class QuantityTriggerMin(QuantityTriggerItemTypes, ABC):
    """Trigger is initiated when marking of the collection point is lower or equal the small stock for all item types."""

    def __init__(self, collection_point: CollectionPoint, threshold: Counter):
        super().__init__(collection_point=collection_point, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled.
        Policy is enabled if the passed marking of the collection point is lower or equal to the small stock for all
        item types in the counter.
        Functionality: Limit item quantity to only relevant item types. Check if for each item type the value is lower
        than the small stock."""

        # only consider relevant item types
        item_quantity = dict(self.net_element.marking)
        considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})

        # check if the value for all item types is smaller or equal than the small stock
        # (item quantity is included in small stock)
        if considered_item_quantity <= self.threshold:
            return True
        else:
            return False

    def get_item_types_below_threshold(self, item_quantity: Counter) -> set[str]:
        """Pass item quantity and get all item types where the passed item quantity is lower than the small stock."""

        # only consider relevant item types
        item_quantity = dict(item_quantity)
        considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})

        # union of small stock and current marking => min of both per item type
        lowest_value_per_item_type = considered_item_quantity | self.threshold

        # subtract small stock from union => all positive values are larger than the small stock
        non_relevant_quantities = lowest_value_per_item_type - self.threshold  # bc assumption: small stock is always positive

        # relevant item quantities are the ones that were dropped at subtraction
        relevant_item_types = self.item_types - set(non_relevant_quantities.keys())

        return relevant_item_types


class AnyItemTypeSmallStock(QuantityTriggerMin):
    """Policy is triggered when marking of the collection point is lower or equal the small stock
        for at least one item type."""

    def __init__(self, collection_point: CollectionPoint, threshold: Counter):
        super().__init__(collection_point=collection_point, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled.
        Policy is enabled if the passed marking of the collection point is lower or equal to the small stock.
        Functionality: Limit item quantity to only relevant item types.
        Get the union of the item quantity and the small stock (max(item_quantity[x], small_stock[x])).
        Subtract small stock from union. If the result contains less item types than the small stock, it is enabled."""

        # get item types where the value is smaller or equal than the small stock
        relevant_item_types = self.get_item_types_below_threshold(item_quantity=self.net_element.marking)
        if len(relevant_item_types) <= len(self.item_types):
            return True
        else:
            return False


class AllItemTypesSmallStock(QuantityTriggerMin):
    """Policy is triggered when marking of the collection point is lower or equal the small stock
        for all item types."""

    def __init__(self, collection_point: CollectionPoint, threshold: Counter):
        super().__init__(collection_point=collection_point, threshold=threshold)

    def check_triggering(self, **kwargs) -> bool:
        """Pass a marking and check if the policy is enabled.
        Policy is enabled if the passed marking of the collection point is lower or equal to the small stock.
        Functionality: Limit item quantity to only relevant item types.
        Get the union of the item quantity and the small stock (max(item_quantity[x], small_stock[x])).
        Subtract small stock from union. If the result contains less item types than the small stock, it is enabled."""

        # only consider relevant item types
        item_quantity = dict(self.net_element.marking)
        considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})

        # check if the value for all item types is smaller or equal than the small stock
        # (item quantity is included in small stock)
        if considered_item_quantity <= self.threshold:
            return True
        else:
            return False

#
#
# class AllSmallStockAllFixedLots(ItemTypePolicy):
#     """Policy is triggered when marking of the collection point is lower or equal the small stock for all item types.
#     When triggered, the lot size for all item types are returned."""
#
#     def __init__(self, small_stock: Counter, lot_size: Counter = None):
#         super().__init__()
#         self._small_stock = small_stock
#         self._lot_size = lot_size if lot_size else Counter()
#
#     @property
#     def small_stock(self):
#         return self._small_stock
#
#     @property
#     def lot_size(self):
#         return self._lot_size
#
#     def check_triggering(self, item_quantity: Counter) -> bool:
#         """Pass a marking and check if the policy is enabled.
#         Policy is enabled if the passed marking of the collection point is lower or equal to the small stock for all
#         item types in the counter.
#         Functionality: Limit item quantity to only relevant item types. Check if for each item type the value is lower
#         than the small stock."""
#
#         # only consider relevant item types
#         item_quantity = dict(item_quantity)
#         considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})
#
#         # check if the value for all item types is smaller or equal than the small stock
#         # (item quantity is included in small stock)
#         if considered_item_quantity <= self.small_stock:
#             return True
#         else:
#             return False
#
#     def get_quantity(self, item_quantity: Counter) -> Counter:
#         """Pass a marking and get the fixed lot sizes for all item types."""
#
#         # check if policy is enabled
#         if self.check_triggering(item_quantity):
#             pass
#         else:
#             raise ValueError("Policy is not enabled.")
#
#         # as lot sizes are fixed for this policy, the returned lot size is always the same: self.lot_size
#         return self.lot_size
#
#     def _get_item_types(self) -> set[str]:
#         return set(self.small_stock.keys())
#
#
# class AnySmallStockAnyFixedLots(ItemTypePolicy):
#     """Policy is triggered when marking of the collection point is lower or equal the small stock
#     for at least one item type. When triggered, the lot size for only the triggering item types are returned."""
#
#     def __init__(self, small_stock: Counter, lot_size: Counter = None):
#         super().__init__()
#         self._small_stock = small_stock
#         self._lot_size = lot_size if lot_size else Counter()
#
#     @property
#     def small_stock(self):
#         return self._small_stock
#
#     @property
#     def lot_size(self):
#         return self._lot_size
#
#
#
#     def get_quantity(self, item_quantity: Counter) -> Counter:
#         """Pass a marking and get the item quantities of only the triggering item types.
#         Functionality: Limit item quantity to only relevant item types.
#         Get minimum of passed item quantity and small stock per item type (=> Union).
#         Basic subtraction of small stock from union => for all positive values item quantity is larger than the small stock.
#         Relevant item types are the ones that were dropped at subtraction, so only the respective lot sizes are returned."""
#
#         # check if policy is enabled
#         if self.check_triggering(item_quantity):
#             pass
#         else:
#             raise ValueError("Policy is not enabled.")
#
#         relevant_item_types = self.get_item_types_below_small_stock(item_quantity=item_quantity)
#
#         # limit lot size counter to enabled item types
#         all_lot_sizes = dict(self.lot_size)
#         relevant_lot_sizes = Counter({item_type: all_lot_sizes[item_type] for item_type in relevant_item_types})
#
#         return relevant_lot_sizes
#
#     def _get_item_types(self) -> set[str]:
#         return set(self.small_stock.keys())
#
# class AnySmallStockAllFixedLots(ItemTypePolicy):
#     """Policy is triggered when marking of the collection point is lower or equal the small stock
#     for at least one item type. When triggered, the lot size for only the triggering item types are returned."""
#
#     def __init__(self, small_stock: Counter, lot_size: Counter):
#         super().__init__()
#         self._small_stock = small_stock
#         self._lot_size = lot_size
#
#     @property
#     def small_stock(self):
#         return self._small_stock
#
#     @property
#     def lot_size(self):
#         return self._lot_size
#
#     def check_triggering(self, item_quantity: Counter) -> bool:
#         """Pass a marking and check if the policy is enabled.
#         Policy is enabled if the passed marking of the collection point is lower or equal to the small stock.
#         Functionality: Limit item quantity to only relevant item types.
#         Get the union of the item quantity and the small stock (max(item_quantity[x], small_stock[x])).
#         Subtract small stock from union. If the result contains less item types than the small stock, it is enabled."""
#
#         # only consider relevant item types
#         item_quantity = dict(item_quantity)
#         considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})
#
#         # subtract lot size from max of current marking / small stock for each item type
#         largest_value_per_item_type = considered_item_quantity | self.small_stock
#         if len(largest_value_per_item_type - self.small_stock) <= len(
#                 self.small_stock):  # bc assumption: small stock is always positive
#             return True
#         else:
#             return False
#
#     def get_quantity(self, item_quantity: Counter) -> Counter:
#         """Pass a marking and get all item quantities of the policy."""
#
#         # check if policy is enabled
#         if self.check_triggering(item_quantity):
#             pass
#         else:
#             raise ValueError("Policy is not enabled.")
#
#         return self.lot_size
#
#     def _get_item_types(self) -> set[str]:
#         return set(self.small_stock.keys())
#
#
# class AllSmallStockAllLargeStock(ItemTypePolicy):
#     """Policy is triggered when marking of the collection point is lower or equal the small stock for all item types.
#     When triggered, the lot size for each item type is calculated based on the large stock of the item type."""
#
#     def __init__(self, small_stock: Counter, large_stock: Counter):
#         super().__init__()
#         self._small_stock = small_stock
#         self._large_stock = large_stock
#
#     @property
#     def small_stock(self):
#         return self._small_stock
#
#     @property
#     def large_stock(self):
#         return self._large_stock
#
#     def check_triggering(self, item_quantity: Counter) -> bool:
#         """Pass a marking and check if the policy is enabled.
#                 Policy is enabled if the passed marking of the collection point is lower or equal to the small stock for all
#                 item types in the counter.
#                 Functionality: Limit item quantity to only relevant item types. Check if for each item type the value is lower
#                 than the small stock."""
#
#         # only consider relevant item types
#         item_quantity = dict(item_quantity)
#         considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})
#
#         # check if the value for all item types is smaller or equal than the small stock
#         # (item quantity is included in small stock)
#         if considered_item_quantity <= self.small_stock:
#             return True
#         else:
#             return False
#
#     def get_item_types_below_small_stock(self, item_quantity: Counter) -> set[str]:
#         """Pass item quantity and get all item types where the passed item quantity is lower than the small stock."""
#
#         # only consider relevant item types
#         item_quantity = dict(item_quantity)
#         considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})
#
#         # union of small stock and current marking => min of both per item type
#         lowest_value_per_item_type = considered_item_quantity | self.small_stock
#
#         # subtract small stock from union => all positive values are larger than the small stock
#         non_relevant_quantities = lowest_value_per_item_type - self.small_stock  # bc assumption: small stock is always positive
#
#         # relevant item quantities are the ones that were dropped at subtraction
#         relevant_item_types = self.item_types - set(non_relevant_quantities.keys())
#
#         return relevant_item_types
#
#     def get_quantity(self, item_quantity: Counter) -> Counter:
#         """Pass a marking and get the lot sizes for all item types."""
#
#         # check if policy is enabled
#         if self.check_triggering(item_quantity):
#             pass
#         else:
#             raise ValueError("Policy is not enabled.")
#
#         # only consider relevant item types
#         item_quantity = dict(item_quantity)
#         considered_item_quantity = Counter({item_type: item_quantity[item_type] for item_type in self.item_types})
#
#         # required quantities are the difference between the large stock and the current marking.
#         # So we subtract the current marking from the large stock.
#         # if current marking is negative: subtraction of negative value => more than large stock is passed.
#         required_quantities = self.large_stock - considered_item_quantity # bc assumption: large stock is always positive
#
#         return required_quantities
#
#     def _get_item_types(self) -> set[str]:
#         return set(self.large_stock.keys())
