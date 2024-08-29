from abc import ABC
from typing import Any

import pygraphviz as pgv

from qel_simulation.components.quantity_net import QuantityNet, Transition, Qarc, ObjectArc, ObjectPlace, CollectionPoint
from qel_simulation.GLOBAL import CHART_COLOURS


class GraphElement:
    def __init__(self, id: Any, name: str = None, obj_label: str = None):
        self.id = id
        self.name = name if name else ""
        self.obj_label = obj_label if obj_label else ""

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({type(self).__name__})"


class NodeTemplate(GraphElement, ABC):

    def __init__(self, id: Any, name: str = None, obj_label: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.style = "filled"
        self.height = 0.5
        self.shape = ...
        self.class_name = ...
        self.penwidth = ...
        self.color = ...
        self.fillcolor = ...
        self.display_label = ...
        self.width = 0.5
        self.fixedsize = ...
        self.fontname = "Arial"
        self.fontsize = 12
        self.fontcolor = "black"


class ObjectPlaceNode(NodeTemplate):

    def __init__(self, color: str, id: Any, class_name: str, initial_object_type: str = None, name: str = None, obj_label: str | int = None,
                 display_label: bool = False):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.shape = "circle"
        self.class_name = class_name
        self.fillcolor = f"{color}70"
        self.penwidth = 1.0
        self.color = color
        self.xlabel = f"<<FONT COLOR='{color}'><b>{initial_object_type}</b></FONT>>" if initial_object_type else ""
        self.ylabel = f""
        self.display_label = display_label
        self.fixedsize = True


class CollectionPointNode(NodeTemplate):

    def __init__(self, id: Any, name: str, obj_label: str | int = None, display_label: bool = True):
        super().__init__(id=id, name=name, obj_label=obj_label if obj_label and obj_label > 0 else f"{obj_label}")
        self.shape = "triangle"
        self.class_name = "CollectionPoint"
        self.fillcolor = "white"
        self.penwidth = 2
        self.color = "black"
        self.display_label = True
        self.label = obj_label if obj_label and obj_label > 0 else f"{obj_label}"
        self.fixedsize = True
        self.height = 0.75  # Increase the height
        self.width = 0.75  # Increase the width
        self.xlabel = f"{name}"

class SilentCollectionPointNode(CollectionPointNode):

    def __init__(self, id: Any, name: str, item_types: int, obj_label: str = None, display_label: bool = False):
        super().__init__(id=id, name=name, obj_label=obj_label, display_label=display_label)
        self.fillcolor = "#00000040"
        self.xlabel = ""
        self.display_label = True


class TransitionNode(NodeTemplate):

    def __init__(self, id: Any, obj_label: str, name: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.shape = "rectangle"
        self.class_name = "Transition"
        self.fillcolor = "white"
        self.penwidth = 1.0
        self.color = "black"
        self.display_label = True
        self.fixedsize = False



class SilentTransitionNode(TransitionNode):
    def __init__(self, id: Any, obj_label: str, name: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.display_label = False
        self.fillcolor = "#00000040"
        self.width = 0.1

# class TransitionNode(NodeTemplate):
#
#     def __init__(self, id: Any, obj_label: str, name: str = None, has_qualculator=False, has_quantity_guard=False):
#         super().__init__(id=id, name=name, obj_label=obj_label)
#         self.shape = "none"
#         self.class_name = "Transition"
#         self.fillcolor = "white"
#         self.penwidth = 1.0
#         self.color = "black"
#         self.display_label = True
#         self.fixedsize = False
#         self.has_qualculator = has_qualculator
#         self.has_quantity_guard = has_quantity_guard
#
#
#         self.label = f'''<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10">
#                          <TR>
#                             <TD WIDTH="10" HEIGHT="20%" FIXEDSIZE="TRUE" CELLPADDING="0" BGCOLOR="{'#0098A1' if self.has_qualculator else 'white'}">
#                             </TD>
#                             <TD WIDTH="30" HEIGHT="30%" ALIGN='LEFT' FIXEDSIZE="FALSE" ROWSPAN="2"><FONT POINT-SIZE="12">{self.obj_label}</FONT></TD>
#                          </TR>
#                          <TR>
#                             <TD WIDTH="10" HEIGHT="20%"  FIXEDSIZE="TRUE" CELLPADDING="0" BGCOLOR="{'#CE108A' if self.has_quantity_guard else 'white'}">
#                             </TD>
#                          </TR>
#                          </TABLE>>'''
#
#
# class SilentTransitionNode(TransitionNode):
#     def __init__(self, id: Any, obj_label: str, name: str = None, has_qualculator=False, has_quantity_guard=False):
#         super().__init__(id=id, name=name, obj_label=obj_label, has_qualculator=has_qualculator, has_quantity_guard=has_quantity_guard)
#         self.label = f'''<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10">
#                                  <TR>
#                                     <TD WIDTH="10" HEIGHT="20%" FIXEDSIZE="TRUE" CELLPADDING="0" BGCOLOR="{'#0098A1' if self.has_qualculator else '#00000040'}">
#                                     </TD>
#                                     <TD WIDTH="20" HEIGHT="30%" ALIGN='LEFT' FIXEDSIZE="FALSE" ROWSPAN="2" BGCOLOR="#00000040"></TD>
#                                  </TR>
#                                  <TR>
#                                     <TD WIDTH="10" HEIGHT="20%"  FIXEDSIZE="TRUE" CELLPADDING="0" BGCOLOR="{'#CE108A' if self.has_quantity_guard else '#00000040'}">
#                                     </TD>
#                                  </TR>
#                                  </TABLE>>'''

class EdgeTemplate(GraphElement, ABC):

    def __init__(self, id: Any, source_id: str, target_id: str, name: str = None, obj_label: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.style = ...
        self.fontname = "Arial"
        self.fontsize = 10
        self.fontcolor = "black"
        self.class_name = ...
        self.penwidth = ...
        self.color = ...
        self.display_label = ...
        self.source_id = source_id
        self.target_id = target_id


class ObjectArcEdge(EdgeTemplate):

    def __init__(self, id: Any, color: str, source_id: str, target_id: str, name: str = None, obj_label: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label, source_id=source_id, target_id=target_id)
        self.fontname = "Arial"
        self.fontsize = 10
        self.fontcolor = "black"
        self.class_name = "ObjectArc"
        self.penwidth = 1.0
        self.color = color
        self.display_label = False
        self.style = "solid"


class VariableObjectArcEdge(EdgeTemplate):

    def __init__(self, id: Any, color: str, source_id: str, target_id: str, name: str = None, obj_label: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label, source_id=source_id, target_id=target_id)
        self.fontname = "Arial"
        self.fontsize = 10
        self.fontcolor = "black"
        self.class_name = "ObjectArc"
        self.penwidth = 3
        self.color = color
        self.display_label = False
        self.style = "bold"


class QuantityArcEdge(EdgeTemplate):

    def __init__(self, id: Any, obj_label: str, source_id: str, target_id: str, name: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label, source_id=source_id, target_id=target_id)
        self.fontname = "Arial"
        self.fontsize = 10
        self.fontcolor = "black"
        self.class_name = "QuantityArc"
        self.penwidth = 1
        self.color = "black"
        self.display_label = True
        self.style = "dashed"


class GraphTemplate(GraphElement):

    def __init__(self, id: Any, obj_label: str = None, name: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        # self.ordering = "in"
        self.orientation = "H"
        self.direction = "LR"
        self.directed = True


class QuantityGraph(GraphTemplate):
    none_graphviz_attribute_names = ["obj_label", "display_label", "source_id", "target_id", "id"]

    def __init__(self, qnet: QuantityNet, name: str = None, id: Any = None, marked: bool = False, obj_label: str = None):
        super().__init__(id=id, name=name, obj_label=obj_label)
        self.transitions = set()
        self.object_places = set()
        self.collection_points = set()
        self.object_arcs = set()
        self.quantity_arcs = set()
        self.graph = None

        # set color scheme
        relevant_colors = CHART_COLOURS[:len(qnet.object_types)]
        self.color_scheme = dict(zip(list(qnet.object_types), relevant_colors))

        # create node and arc elements
        self.create_transition_nodes(qnet.transitions)
        self.create_object_place_nodes(qnet.object_places, marked=marked)
        self.create_collection_point_nodes(qnet.collection_points)
        self.create_object_arc_edges(qnet.object_arcs | qnet.variable_arcs)
        self.create_quantity_arc_edges(qnet.quantity_arcs)

    def create_transition_nodes(self, transition_objects: set[Transition]):

        for transition in transition_objects:
            if transition.silent:
                transition_node = SilentTransitionNode(id=transition.name, name=transition.name,
                                                       obj_label=transition.label)
            else:
                transition_node = TransitionNode(id=transition.name, name=transition.name, obj_label=transition.label)

            self.transitions.add(transition_node)

    def create_object_place_nodes(self, object_places: set[ObjectPlace], marked: bool = False):

        for place in object_places:

            if isinstance(place, ObjectPlace):
                if place.object_type.log_object_type:
                    pass
                else:
                    continue
            else:
                pass


            if place.initial:
                initial = place.object_type.object_type_name
            else:
                initial = None

            obj_label = ""
            display = False

            if marked:
                if len(place.marking) > 0:
                    obj_label = len(place.marking)
                    display = True
                else:
                    pass
            else:
                pass

            place_node = ObjectPlaceNode(id=place.name, name=place.name, obj_label=obj_label, display_label=display,
                                         color=self.color_scheme[place.object_type], initial_object_type=initial,
                                         class_name = place.object_type.object_type_name)
            self.object_places.add(place_node)

    def create_collection_point_nodes(self, collection_points: set[CollectionPoint], marked: bool = False):

        for collection_point in collection_points:

            if collection_point.silent:
                collection_point_node = SilentCollectionPointNode(id=collection_point.name, name=collection_point.label,
                                                                  item_types=len(collection_point.item_types),
                                                                  obj_label="", display_label=False)
            else:
                collection_point_node = CollectionPointNode(id=collection_point.name, name=collection_point.label,
                                                            obj_label=len(collection_point.item_types), display_label=True)
            self.collection_points.add(collection_point_node)

    def create_object_arc_edges(self, object_arcs: set[ObjectArc]):

        for arc in object_arcs:

            if isinstance(arc, ObjectArc):
                if arc.object_type.log_object_type:
                    pass
                else:
                    continue
            else:
                pass

            if arc.variable:
                object_arc_edge = VariableObjectArcEdge(id=arc.name, name=arc.name, obj_label=arc.label,
                                                        color=self.color_scheme[arc.object_type],
                                                        source_id=arc.source.name, target_id=arc.target.name)
            else:
                object_arc_edge = ObjectArcEdge(id=arc.name, name=arc.name, obj_label=arc.label,
                                                color=self.color_scheme[arc.object_type], source_id=arc.source.name,
                                                target_id=arc.target.name)

            self.object_arcs.add(object_arc_edge)

    def create_quantity_arc_edges(self, quantity_arcs: set[Qarc]):

        for qa in quantity_arcs:

            quantity_arc_edge = QuantityArcEdge(id=qa.name, name=qa.name, obj_label="", source_id=qa.source.name,
                                                target_id=qa.target.name)
            quantity_arc_edge.dir = "none"
            self.quantity_arcs.add(quantity_arc_edge)

    def add_nodes_to_graph(self):

        for node in self.transitions | self.object_places | self.collection_points:

            attributes = vars(node).copy()
            # attributes['class'] = attributes["class_name"]

            if attributes['display_label']:
                attributes['label'] = attributes["obj_label"]
            else:
                attributes['label'] = ""
                attributes['name'] = ""

            for none_attribute in QuantityGraph.none_graphviz_attribute_names:
                if none_attribute in attributes.keys():
                    attributes.pop(none_attribute)
                else:
                    pass

            self.graph.add_node(node.id, **attributes)

    def add_edges_to_graph(self):

        for edge in self.quantity_arcs | self.object_arcs:
            attributes = vars(edge).copy()
            # attributes['class'] = attributes["class_name"]

            if attributes['display_label']:
                attributes['label'] = attributes["obj_label"]
            else:
                attributes['label'] = ""
                attributes['name'] = ""

            for none_attribute in QuantityGraph.none_graphviz_attribute_names:
                if none_attribute in attributes.keys():
                    attributes.pop(none_attribute)
                else:
                    pass

            self.graph.add_edge(edge.source_id, edge.target_id, **attributes)

    def clear_graph(self):
        self.graph = None

    def create_graph(self):
        self.clear_graph()
        # self.graph = pgv.AGraph(directed=self.directed, orientation=self.orientation, direction=self.direction)
        self.graph = pgv.AGraph(directed=True, rankdir="LR", strict=False, seed=42, ratio=0.35)
        # ranksep="0.3", nodesep="0.4"
        self.add_nodes_to_graph()
        self.add_edges_to_graph()

    def export_graph(self, file_name: str = None, file_format: str = "svg"):

        if not self.graph:
            self.create_graph()
        else:
            pass

        if file_name:
            if file_format.lower() == 'svg':
                # correct path
                if ".svg" in file_name:
                    pass
                else:
                    file_name = file_name + ".svg"

            # create file
            if self.graph:
                self.graph.draw(f"{file_name}", prog="dot", format="svg")
            else:
                raise ValueError("no graph configured.")

        elif file_format.lower() == 'png':
            # correct path
            if ".png" in file_name:
                pass
            else:
                file_name = f"{file_name}.png"

            # create file
            if self.graph:
                self.graph.draw(file_name, prog="dot", format="png")
            else:
                raise ValueError("no graph configured.")

        elif file_format.lower() == 'dot':
            # potentially .dot would have to be removed
            if ".dot" in file_name:
                pass
            else:
                file_name = f"{file_name}.dot"

            # create file
            if self.graph:
                self.graph.draw(file_name, prog="dot", format="dot")
            else:
                raise ValueError("no graph configured.")

        else:
            file_name = f"{self.name}.svg"
            if self.graph:
                self.graph.draw(f"{file_name}", prog="dot", format="svg")
            else:
                raise ValueError("no graph configured.")

    def get_string_representation(self):
        if self.graph:
            return self.graph.string_nop()
        else:
            raise ValueError("no graph configured.")
