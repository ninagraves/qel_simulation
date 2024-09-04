from collections import Counter

from qel_simulation.components.collection_point import CollectionPoint


class CollectionCounter(dict):
    def __init__(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            if not isinstance(key, CollectionPoint):
                raise ValueError("All keys must be a collection points.")
            if not isinstance(value, Counter):
                raise ValueError("All values must be Counter objects.")
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if not isinstance(key, CollectionPoint):
            raise ValueError("All keys must be a collection points.")
        if not isinstance(value, Counter):
            raise ValueError("All values must be Counter objects.")
        super().__setitem__(key, value)
