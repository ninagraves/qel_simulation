from src.components.base_element import ConnectedElement


class Place(ConnectedElement):

    def __init__(self, name, label: str = None, properties: dict = None):

        super().__init__(name=name, label=label, properties=properties)

        self._initial = None
        self._final = None
        self._marking = None

    def __str__(self):
        return self.name

    @property
    def initial(self):
        if self._initial:
            return self._initial
        else:
            pass

        if len(self.input_arcs) == 0:
            return True
        else:
            return False

    @initial.setter
    def initial(self, initial: bool):
        self._initial = initial

    @property
    def final(self):
        if self._final:
            return self._final
        else:
            pass

        if len(self.output_arcs) == 0:
            return True
        else:
            return False

    @final.setter
    def final(self, final: bool):
        self._final = final

    @property
    def marking(self):
        return self._marking

    def add_token(self, tokens: int):
        if isinstance(tokens, int):
            self._marking += tokens
        else:
            raise ValueError(f"Variable passed to mark decoupling point is not an integer.")

    def remove_token(self, tokens: int):
        if isinstance(tokens, int) and self.marking >= tokens:
            self._marking -= tokens
        else:
            raise ValueError(f"Trying to remove more lazy tokens from decoupling point than available.")
