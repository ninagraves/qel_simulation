import uuid

from qel_simulation.qnet_elements import Transition
from qel_simulation.qnet_elements.transition import TransitionExecution


class Execution:
    def __init__(self, transition_execution: TransitionExecution, transition: Transition):
        self.execution_item_id = uuid.uuid4()
        self.transition_execution = transition_execution
        self.transition = transition
