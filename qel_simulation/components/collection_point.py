from collections import Counter

from qel_simulation.qnet_elements.place import Place


class CollectionPoint(Place):
    def __init__(self, name, label: str = None, properties: dict = None):
        super().__init__(name=name, label=label, properties=properties)
        self._marking = Counter()
        self._item_types = set()

    @property
    def item_types(self):
        return self._item_types

    @item_types.setter
    def item_types(self, item_types):
        if isinstance(item_types, str):
            self._item_types = {item_types}
        elif isinstance(item_types, set):
            self._item_types = item_types
        elif isinstance(item_types, (list, tuple)):
            self._item_types = set(item_types)
        else:
            raise ValueError(f"Item types must be a set not {type(item_types)}")

    @property
    def silent(self):
        if self.label:
            return False
        else:
            return True

    @silent.setter
    def silent(self, silent: bool):
        if silent:
            self.label = None
        else:
            self.label = self.name

    def add_token(self, tokens):
        raise ValueError("Collection points only update marking according to quantity operation. "
                         "They don't add/remove tokens. "
                         "Pass 'Counter' object for each item type to 'update_marking' instead.")

    def remove_token(self, tokens):
        raise ValueError("Collection points only update marking according to quantity operation. "
                         "They don't add/remove tokens. "
                         "Pass 'Counter' object for each item type to 'update_marking' instead.")

    def update_marking(self, quantity_update: Counter):
        if isinstance(quantity_update, Counter):
            self._marking.update(quantity_update)
            if set(dict(quantity_update).keys()).issubset(self.item_types):
                pass
            else:
                self.item_types = self.item_types | set(dict(quantity_update).keys())
        else:
            raise ValueError("Quantity update must be a Counter object.")
