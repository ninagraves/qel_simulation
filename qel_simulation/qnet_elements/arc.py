from qel_simulation.components.base_element import ConnectingElement
from qel_simulation.qnet_elements.place import Place


class Arc(ConnectingElement):

    def __init__(self, source, target, name=None, label: str = None, properties: dict = None):

        # source is place, target isn't
        c1 = isinstance(source, Place) and not isinstance(target, Place)
        # target is place, source isn't
        c2 = isinstance(target, Place) and not isinstance(source, Place)

        if c1 or c2:
            pass
        else:
            raise ValueError("Arcs may only connect a place to a transition or a transition to a place.")

        if name:
            pass
        else:
            name = f"({source.name}, {target.name})"
        super().__init__(source=source, target=target, name=name, label=label, properties=properties)

    @property
    def place(self):
        if isinstance(self.source, Place):
            return self.source
        else:
            return self.target

    @property
    def transition(self):
        if isinstance(self.source, Place):
            return self.target
        else:
            return self.source
