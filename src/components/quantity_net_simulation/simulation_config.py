import datetime
from typing import Type

from src.components.base_element import BaseElement
from src.components.log_elements.event import Event
from src.components.log_elements.object import Object
from src.components.quantity_net_simulation.qnet_config import QnetConfig
from src.components.quantity_net_simulation.queue_config import QueueConfig
from src.components.quantity_net_simulation.triggers import Trigger


class SimulationConfig(BaseElement):
    def __init__(self, name: str, label: str = None, properties: dict = None, qnet_config: QnetConfig = None,
                 queue_config: QueueConfig = None):
        super().__init__(name=name, label=label, properties=properties)

        # other configs
        self.qnet_config: QnetConfig = qnet_config
        self.queue_config: QueueConfig = queue_config if queue_config else QueueConfig(name="Queue Config")

        # operators
        self.random_seed: int = 42

        # durations
        self.durations_fixed: dict[
            str | Type[Event], datetime.timedelta | int | float] = {}  # {activity_name: duration}
        self.durations_min_uniform: dict[
            str | Type[Event], tuple[int | float, int | float]] = {}  # {activity_name: (min, max)}
        self.durations_min_normal: dict[
            str | Type[Event], tuple[float | int, float | int]] = {}  # {activity_name: (mean, std)}
        self.durations_beta: dict[str | Type[Event], tuple[
            float | int, float | int]] = {}  # {activity_name: (alpha, beta)} => mode: alpha-1/(alpha+beta-2), mean = alpha/(alpha+beta)
        self.durations_gamma: dict[str | Type[Event], tuple[
            float | int, float | int]] = {}  # {activity_name: (alpha, beta)} => mode: (alpha-1)*beta, mean = alpha*beta
        self.durations_default_normal_min_params: tuple[float | int, float | int] = (12, 3)

        # object creation
        self.object_creation_triggered: dict[Trigger: Type[Object]] = {}  # {trigger: object_type}
        self.object_creation_frequencies_arrival_rates: dict[
            str | Type[Object], int | float] = {}  # {object_type: expected arrival rate per business day (lambda)}
        self.object_creation_fixed_time_interval: dict[
            str | Type[Object], datetime.timedelta | int | float] = {}  # {object_type: duration (if int or float: unit it is multiplied by is hours)}
        self.initial_scheduled_executions: dict[
            str | Type[Object], datetime.datetime] = {}  # {object type: first execution time}

        # prioritised activities
        self.activity_priority: list[str | Type[Event]] = [] # list of activities in appropriate order
        self.priority_probability: float = 0.5 # probability of choosing the activity with the highest priority

        # end conditions -> runs until the first one triggers
        # maximum number of execution steps
        self.max_execution_steps: int = 50000
        # while simulation time is before than start time + passed timedelta, execution continues
        self.max_simulation_time: datetime.timedelta = datetime.timedelta(days=365)
        # simulation runs while fewer than passed number of objects have terminated the process
        self.max_objects: int = 50000
        # simulation runs while fewer than passed number of events have been executed
        self.max_events: int = 10000
