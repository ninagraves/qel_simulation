from src.components.net_elements.arc import Arc
from src.components.net_elements.object_place import ObjectPlace
class ObjectArc(Arc):

    def __init__(self, source, target, name=None, label: str = None, properties: dict = None):

        super().__init__(source=source, target=target, name=name, label=label, properties=properties)

        if isinstance(self.place, ObjectPlace):
            pass
        else:
            raise ValueError("Only arcs connected to ObjectPlaces can be ObjectArcs.")

        self._variable = False

    @property
    def variable(self):

        if self._variable == False:
            pass
        else:
            return True

        # get transition's specification for number of objects of arc's type required to fire
        transition_binding_specification = self.transition.binding_function_quantities[self.object_type]

        if transition_binding_specification == 1:
            return False
        else:
            return True

    @variable.setter
    def variable(self, value: bool):
        self._variable = value

    @property
    def object_type(self):
        return self.place.object_type
