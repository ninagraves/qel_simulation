# QEL Simulation

This is a tool for the simulation of a Quantity Event Log (QEL). A QEL is an object-centric event log considering item 
quantities and the basis for quantity-related process mining (QRPM). The output format is an SQLite database according 
to the OCEL 2.0 standard[1] with an additional table for the quantity operations.

[1] https://www.ocel-standard.org/

## Installation
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

## Usage
A simulation is specified using two files: The q-net configuration file and the simulation configuration file. The 
options for the configuration parameters are specified in the respective config classes that can be found in the 
"components/quantity_net_simulation" folder.
The simulation is set up in the initialisation of the simulation object using the simulation config (which includes the 
q-net config as an attribute).
The simulation is executed by calling the "run_simulation" method of the simulation object.
The resulting event log can be exported using the method "export_simulated_log()" and is saved to a folder "event_log" 
in the same folder.

Find an extensive example for the simulation of an inventory management process in the examples folder.
There you find 1) the files specifying the control flow for the q-net and the simulation parameters, 2) the example 
simulation script that can be executed to run the simulation, and 3) a jupyter notebook with some calls to visualise 
the model.

## Functionality
The tool is built in a modular way. The main components are Events, Objects, the QEL, the Q-net, and the Queue. The Q-net is the 
basis for the simulation which is executed by an overall "quantity net execution" (QNE) object. The QNE
object fires binding executions (transitions with a corresponding binding) and initiates the 
execution of connected events as well as the creation of and changes made to objects based on the instructions it is passed from the 
simulation object. The QEL is gradually built up according to the OCEL 2.0 standard during the executions.
The simulation object passes standardised instructions to the QNE which then executes them. The QNE can execute the following instructions:
- Event Execution: This triggers the creation of an event object as well as calling the pre-event and the start event methods. Additionally, the corresponding transition consumes the tokens specified by the passed binding function.
- Event Termination: This triggers the termination of an event by calling its the event_end method and finishing the binding execution by producing the tokens in the q-net.
- Object Creation: This triggers the creation of a PM-object of a specified type by initiating the object creation of the object type's class and setting the initial attributes and o2o relations as specified.
- Object Status Update: The changes the status of a PM-object (possibilities: created, active, terminated, inactive)
- Object Activity Update
- Object Quantity Update

Please note: In the default settings, silent transitions are executed automatically. If you only want specific silent 
transitions to be fired with a corresponding instruction, you can specify this by passing the set of transition names 
for the "manually_initiated_transitions" parameter in the q-net config.
We will use the example process mentioned above to explain the functionality in more detail.

### Events
An event in the process mining sense is represented by a (programming-related) object of a class inheriting from the 
class "Event" -- in other words: By creating a class that inherits from the Event class, you can define your own 
activities.
You can specify activities in the q-net configuration file using two different options: 1) by specifying the activity name and 
default attribute values. passing a dict of activity names, or 2) by passing along your own 
custom classes inheriting from the Event class as list ("activity_classes")

#### Activity parameters
You can specify (some of) your activities by just passing a dict with the activity names as keys.
The value for each activity can be either "None" or another dict with the activity attributes as keys and the default value as value.

#### Custom activity classes
You can also define your own activity classes by inheriting from the Event class. This allows you to define your own activities with custom attributes and methods.
You activity must have the following three methods:
- "_execute_event_start" (to be executed when the event is started). This is a good place to specify the duration of 
the event.


### Q-net
The quantity net specifies the control flow of the simulation. It is an extended object-centric process model where 
activities can be assigned to transitions and object types to places [2].



[2] van der Aalst, W. M. P., & Berti, A. (2020). Discovering Object-centric Petri Nets. Fundamenta Informaticae, 175(1–4), 1–40. https://doi.org/10.3233/FI-2020-1946



