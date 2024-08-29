from qel_simulation.qnet_elements.arc import Arc
from qel_simulation.qnet_elements.collection_point import CollectionPoint

class Qarc(Arc):

    def __init__(self, source, target, name=None, label: str = None, properties: dict = None):

        if isinstance(source, CollectionPoint) or isinstance(target, CollectionPoint):
            pass
        else:
            raise ValueError("Only arcs connected to a collection point can be QuantityArc.")

        super().__init__(source=source, target=target, name=name, label=label, properties=properties)

    @property
    def item_types(self):
        return self.place.item_types

