# QEL Simulation

This is a tool for the simulation of a Quantity Event Log (QEL). A QEL is an object-centric event log considering item 
quantities and the basis for quantity-related process mining (QRPM). The output format is an SQLite database according 
to the OCEL 2.0 standard[1] with an additional table for the quantity operations.

[1] https://www.ocel-standard.org/

## Getting Started
### Installation
The repository uses poetry for dependency management. If you do not have poetry installed, you can install it by running:
```pip install poetry```
Installation of the full tool has to occur in four steps:
1. Manually install PyGraphviz (needed for the visualisation of the underlying Q-net): https://gitlab.com/graphviz/graphviz/-/package_files/6164164/download
2. To install PyGraphviz in the poetry environment, you must follow the instructions on https://pygraphviz.github.io/documentation/stable/install.html
For Windows this means you must run:
```poetry run pip install --config-settings="--global-option=build_ext" `
              --config-settings="--global-option=-IC:\Program Files\Graphviz\include" `
              --config-settings="--global-option=-LC:\Program Files\Graphviz\lib" `
              pygraphviz```
3. Run ```poetry install``` again to synchronise the dependencies

### Overview of the Tool
A simulation is specified using two files: The q-net configuration file and the simulation configuration file. The 
options for the configuration parameters are specified in the respective config classes that can be found in the 
"simulation" folder.
The simulation is set up in the initialisation of the simulation object using the simulation config (which includes the 
q-net config as an attribute).
The simulation is executed by calling the "run_simulation" method of the simulation object.
The resulting event log can be exported using the method "export_simulated_log()" and is saved to a folder "event_log" 
in the same folder.

The simulation is based on the following components:
- The q-net: The q-net specifies the control flow of the simulation. 
It is an extended object-centric process model where activities can be assigned to transitions and object types to places.
- Activities (class Event): Activities can be assigned to transitions in the q-net. 
Whenever a non-silent transition is fired, a corresponding event is created and logged.
- Object types (class Object): Object types can be assigned to places in the q-net. 
Whenever an object is created, or attributes change this is logged.
- Simulation: The simulation object is the main object that orchestrates the simulation. 
It is initialised with the simulation config and runs the simulation. 
The simulation controls when objects are created and when transitions are fired (i.e, when tokens are consumed and when tokens are produced).

In the following, we go into more detail on the individual elements and how they are specified in the configuration files.
We will first explain the basic possibilities for specification and merely mention the more advanced options.
An example using the advanced options is provided in the "examples" folder.
The more detailed basic explanation accompanies the modular building-block style example. *TODO: To be completed*


## Quantity Net Configuration
The quantity net configuration specifies all necessary elements of an executable quantity net.
In includes the following elements:
- Quantity Net
- Object Types
- Activities

In the following, we will explain the options for configuring each of these elements.

### Quantity Net
The basis of the quantity net is the structure of the net which is specified by a set of arcs.
- **Structure**: Every arc must connect a transition (name starting with "t") with either an object place (name starting with "p") or a collection point (name starting with "c").
While the object arcs are directed and a tuple ("p1", "t1") specifies an arc from p1 to t1, arcs including collection points are not directed, so the order of the elements in the tuple is irrelevant.
The q-net structure is specified using the attribute *net_structure* in a q-net configuration.
- **Sources and Sinks**: The initial and final object places are automatically determined by the q-net structure -- object places without an incoming arc are initial places, object places without an outgoing arc are final places.
If you want to deviate from this, you can set individual places as initial or final places using the attributes *initial_places* and *final_places* attributes in the q-net configuration.
Setting the initial places is relevant if you generate objects for an object type automatically, as the default is to place an object into all initial places of the object type.
If you specify the location to place objects into the net manually, this setting would be irrelevant.
The specification of the final places is only relevant for performance reasons. 
The default assumption is, that the final marking of the net is reached once an object token reaches a sink place, leading to objects being set to inactive, and, therefore, no longer considered in the simulation once this is the case. 
- **Object Places**: The default is that all places are assigned to a default object type.
However, you can assign your individual object type names to places using the *place_types* attribute in the q-net configuration.
Here you can pass a dictionary with the place names as keys and the object type names as values.
- **Variable Arcs / Transition binding function quantities**: Two ways of specifying, one per arc, the other per transition. 
**Warning: Specifications per arc overwrite specifications per transition.**
  - Per transition: You can specify the number of tokens that are consumed and produced per object type using a dict. 
    While this ensures that it is well-formed, you have to make sure all object types the transition refers to are included in the dict. 
    The arcs are set to variable automatically.
      - static numbers: *binding_function_quantities* and 0 means completely variable, you must set 1 for all non-variable object types.
      - maximum number of tokens: *maximum_binding_function_quantities* set to 1 for all non-variable object types, 0 for completely variable object types with no upper bound and the value you want for the rest.
      - minimum number of tokens: *minimum_binding_function_quantities* set to 1 for all non-variable object types and the value you want as minimum for the rest.
    - Per arc: You can specify the number of tokens that are consumed and produced by an arc using the attributes that include the expression *variable_arc* in the q-net configuration.
    But this includes the risk of not specifying it in a well-formed manner. 
    So far, no check for this. 
    Changes here overwrite the values set in the transition specification, and they are set for the entire object type.
        - static number of object tokens that is not 1
        - range of object tokens
        - unspecified number of object tokens: any number is allowed by default. 
        Number can be restricted in more detail using object guards.
- **Transition labels**: By setting the "transition_labels" attribute to a dictionary with transition names as keys and the 
labels as values, you can specify the names of the transitions in the q-net. 
These names will also be logged in the event log.
- **Silent Transitions**: All silent transitions are always executed instantly, if not specified otherwise (see manually initiated transitions below). 
The default is that all unlabelled transitions are silent.
If you want to specify your own silent transitions, i.e., labelled transitions that are executed instantly, you can do so by passing a set of transition names to the attribute *silent_transitions* in the q-net configuration.
- **Initial Markings Object Places**: There are multiple ways of specifying the initial marking of the q-net.
  1. Pass a set of objects (computer-science objects of the class Object) to the attribute *initial_objects* in the q-net configuration.
  These will be placed in the initial places of the object type they belong to.
  2. A dictionary with the object type name or object type class as keys and an integer as values passed to the attribute *initial_marking_object_types* leads to the generation of this number of objects per type which are subsequently added to each of the object type's initial places.
  3. You can specify the initial marking by passing a dictionary with the place names as keys and the number of tokens as values to the attribute *initial_marking_object_places* in the q-net configuration.
  4. The last attribute to specify an initial marking for object places is called _initial_objects_in_places_. Here, you pass a dictionary with the place names as keys and a multiset of objects as values. 
- **Initial Marking Collection Points**: You can specify the initial marking of collection points by passing a dictionary with the collection point names as keys and a Counter (library: Collections) as value to the attribute *initial_marking_collection_points* in the q-net configuration.
- **Final Marking**: If the lifecycle of an object does not come to an end by reaching a single sink place, you can specify all possible final markings (aka markings in which the object can/should finish) of the q-net by setting a dictionary as *final_markings*. 
The dict should specify all possible sets of final markings per object type, so the key is the object type and the value is a list of sets.
- **Object Guards** (advanced): To further restrict the firing of a transition w.r.t. the objects in the input object places, you can specify object guards, i.e., set a dictionary with the transition names as keys and a callable function as _transition_object_guard_ in the q-net configuration.
The function you pass must take an object of the type "BindingFunction" (a dictionary with Object Type Classes of the input places as keys and multisets of objects as values) as input and return a boolean value.
If the function returns True, the transition is considered enabled under the passed binding.
Common examples for the usage of such guards are specific object attribute values or certain combinations of objects in the input places (e.g., only fire with object combinations that have an o2o-relationship).
- **Quantity Guards** (partially advanced): You can also restrict the firing of a transition in consideration of the input objects (the object binding function) in light of the current item levels of all connected collection points.
This is done by setting _transition_quantity_guard_ to a dictionary with the transition names as keys and either (1) a class that inherits from "QuantityGuard", or (2) a callable function returning a boolean that takes two inputs: the object binding function and a collection counter the current item levels of all connected collection points. <br>
The typical scenario in which a transition should only be enabled if the quantity of a certain item is below a certain threshold for either a single item type or all item types is readily available as a building block.
To use it you pass a dictionary with "QuantityGuardSmallstockConfig"-objects for the transitions (keys) to the attribute _small_stock_guards_. <br>
  This config has three attributes specifying how you want your smallstockguard to work:
     - _counter_threshold_: a collection counter with the thresholds for a set of item types for connected collection points,
     - _counter_all_item_types_: a dictionary with a boolean as value for each of the collection points included in the collection counter (key).
  The boolean value specifies for each of the collection points whether the threshold should be applied to all item types or only to a specific set of item types, i.e., must all item types be below the threshold or only one of them.
  Default is False for all collection points.
     - _all_counter_condition_: a boolean value specifying whether the transition is enabled if the conditions are met for all collection points or if the condition is met for one of the collection points.
  Default is True, meaning all collection points must meet the condition.

Examples for all possible ways of defining object and quantity guards can be found in the Inventory Management example.


### Quantity Net Execution

(in progress)

#### Object Types
**Warning: Changes to objects are global and affect the object anywhere in the q-net, i.e., all tokens referring to the same identifier are affected by the change in object attributes, object quantities and object status.**
If you want to specify your own object types for the executable q-net, you can do so by specifying the object types in the q-net configuration.
There are two possibilities:
  - The simple building-block style: *object_types_attributes* dict with object type name and then you can specify attributes and default values or just put None.
  - Advanced option: Creating your own object type class that inherits from the Object class and specifying the class in the *object_types_classes* attribute.


#### Activities
- Silent Activities: If you want a transition to be labelled but not included in the event log, you can specify the "silent_activities" attribute in the q-net configuration.
The set of activity names you pass here will not be logged in the event log.

### Transition Executions
- **Object Guard**: You can specify the conditions under which a transition can be fired by passing a dictionary with the transition names as keys and a list of object guards as values to the attribute *object_guards* in the q-net configuration.
- **Manually Initiated Transitions**: By default, all silent transitions are executed automatically. 

### Simulation configuration



#### Advanced Options

[//]: # (## Functionality)

[//]: # (The tool is built in a modular way. The main components are Events, Objects, the QEL, the Q-net, and the Queue. The Q-net is the )

[//]: # (basis for the simulation which is executed by an overall "quantity net execution" &#40;QNE&#41; object. The QNE)

[//]: # (object fires binding executions &#40;transitions with a corresponding binding&#41; and initiates the )

[//]: # (execution of connected events as well as the creation of and changes made to objects based on the instructions it is passed from the )

[//]: # (simulation object. The QEL is gradually built up according to the OCEL 2.0 standard during the executions.)

[//]: # (The simulation object passes standardised instructions to the QNE which then executes them. The QNE can execute the following instructions:)

[//]: # (- Event Execution: This triggers the creation of an event object as well as calling the pre-event and the start event methods. Additionally, the corresponding transition consumes the tokens specified by the passed binding function.)

[//]: # (- Event Termination: This triggers the termination of an event by calling its the event_end method and finishing the binding execution by producing the tokens in the q-net.)

[//]: # (- Object Creation: This triggers the creation of a PM-object of a specified type by initiating the object creation of the object type's class and setting the initial attributes and o2o relations as specified.)

[//]: # (- Object Status Update: The changes the status of a PM-object &#40;possibilities: created, active, terminated, inactive&#41;)

[//]: # (- Object Activity Update)

[//]: # (- Object Quantity Update)

[//]: # ()
[//]: # (Please note: In the default settings, silent transitions are executed automatically. If you only want specific silent )

[//]: # (transitions to be fired with a corresponding instruction, you can specify this by passing the set of transition names )

[//]: # (for the "manually_initiated_transitions" parameter in the q-net config.)

[//]: # (We will use the example process mentioned above to explain the functionality in more detail.)

[//]: # ()
[//]: # (### Events)

[//]: # (An event in the process mining sense is represented by a &#40;programming-related&#41; object of a class inheriting from the )

[//]: # (class "Event" -- in other words: By creating a class that inherits from the Event class, you can define your own )

[//]: # (activities.)

[//]: # (You can specify activities in the q-net configuration file using two different options: 1&#41; by specifying the activity name and )

[//]: # (default attribute values. passing a dict of activity names, or 2&#41; by passing along your own )

[//]: # (custom classes inheriting from the Event class as list &#40;"activity_classes"&#41;)

[//]: # ()
[//]: # (#### Activity parameters)

[//]: # (You can specify &#40;some of&#41; your activities by just passing a dict with the activity names as keys.)

[//]: # (The value for each activity can be either "None" or another dict with the activity attributes as keys and the default value as value.)

[//]: # ()
[//]: # (#### Custom activity classes)

[//]: # (You can also define your own activity classes by inheriting from the Event class. This allows you to define your own activities with custom attributes and methods.)

[//]: # (You activity must have the following three methods:)

[//]: # (- "_execute_event_start" &#40;to be executed when the event is started&#41;. This is a good place to specify the duration of )

[//]: # (the event.)

[//]: # ()
[//]: # ()
[//]: # (### Q-net)

[//]: # (The quantity net specifies the control flow of the simulation. It is an extended object-centric process model where )

[//]: # (activities can be assigned to transitions and object types to places [2].)



[2] van der Aalst, W. M. P., & Berti, A. (2020). Discovering Object-centric Petri Nets. Fundamenta Informaticae, 175(1–4), 1–40. https://doi.org/10.3233/FI-2020-1946



