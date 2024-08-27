import uuid


class BaseElement:

    def __init__(self, name: any = None, label: str = None, properties: dict = None):
        self._id = uuid.uuid4()
        self._name = name if name else self.id
        self._label = label if label else None
        self._properties = properties if properties else None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({type(self).__name__})"

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def properties(self):
        return self._properties

    @id.setter
    def id(self, id):
        self._id = id

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label

    @properties.setter
    def properties(self, properties):
        self._properties = properties


class ConnectingElement(BaseElement):
    def __init__(self, source, target, name=None, label: str = None, properties: dict = None):
        super().__init__(name=name, label=label, properties=properties)
        self._source = source
        self._target = target

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @source.setter
    def source(self, source):
        self._source = source

    @target.setter
    def target(self, target):
        self._target = target


class ConnectedElement(BaseElement):

    def __init__(self, name, label: str = None, properties: dict = None):

        super().__init__(name=name, label=label, properties=properties)
        self._input_arcs = set()
        self._output_arcs = set()

    @property
    def arcs(self):
        return self.input_arcs | self.output_arcs

    @property
    def input_arcs(self) -> set:
        return self._input_arcs

    @property
    def output_arcs(self):
        return self._output_arcs

    @input_arcs.setter
    def input_arcs(self, input_arcs: set[ConnectingElement]):
        self._input_arcs = input_arcs

    @output_arcs.setter
    def output_arcs(self, output_arcs: set[ConnectingElement]):
        self._output_arcs = output_arcs

    @property
    def inputs(self):
        """
        set of all input elements
        """
        return set([arc.source for arc in self.input_arcs if isinstance(arc.source, ConnectedElement)])

    @property
    def outputs(self):
        """
        set of all output elements
        """
        return set([arc.target for arc in self.output_arcs if isinstance(arc.target, ConnectedElement)])

    def add_input_arc(self, arc: ConnectingElement):
        if isinstance(arc, ConnectingElement) and not isinstance(arc.source, type(arc.target)):
            if self == arc.target:
                self._input_arcs.add(arc)
            else:
                raise ValueError("Only arcs connected to the elements itsself can be added as input arcs.")
        else:
            raise ValueError(
                "Input arcs must be connecting elements and the source and target must be of different types.")

    def add_output_arc(self, arc: ConnectingElement):
        if isinstance(arc, ConnectingElement) and type(arc.source) is not type(arc.target):
            if self == arc.source:
                self._output_arcs.add(arc)
            else:
                raise ValueError("Only arcs connected to the elements itsself can be added as output arcs.")
        else:
            raise ValueError(
                "Output arcs must be connecting elements and the source and target must be of different types.")
