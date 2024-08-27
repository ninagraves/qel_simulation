import datetime

from src.components.base_element import BaseElement


class QueueConfig(BaseElement):
    def __init__(self, name: str, label: str = None, properties: dict = None):
        super().__init__(name=name, label=label, properties=properties)

        # initial time
        self.initial_time: datetime.datetime = datetime.datetime(month=10, year=2019, day=12, hour=12, minute=21)

        # working time
