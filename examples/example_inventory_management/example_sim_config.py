import datetime

from qel_simulation.simulation.simulation_config import SimulationConfig
from examples.example_inventory_management.example_qnet_config import expected_customer_orders_per_day, qnet_conf

####### EVENTS #######

## Schedules
creation_time_based = {"Timing Replenishment Order": datetime.timedelta(days=9),
                       "Timing PADS Delivery": datetime.timedelta(days=5)}
creation_frequency = {"Customer Order": expected_customer_orders_per_day}

## Durations
durations_normal_min = {"Identify incoming Delivery": (20, 3),
                        "Place delivered Items into Inventory": (12, 1),
                        "Send Parcel to Customer": (5, 0.2)}
durations_uniform = {"Cancel Customer Order": (1, 8)}

config = SimulationConfig(name="example_material_flow")
config.qnet_config = qnet_conf
config.object_creation_fixed_time_interval = creation_time_based
config.object_creation_frequencies_arrival_rates = creation_frequency
config.initial_scheduled_executions = {"Timing Replenishment Order": datetime.datetime(month=10, year=2019, day=15, hour=14, minute=21, second=21),
                                        "Timing PADS Delivery": datetime.datetime(month=10, year=2019, day=16, hour=17, minute=21, second=21)}
config.durations_min_normal = durations_normal_min
config.durations_min_uniform = durations_uniform
config.activity_priority = [
                            "Initiate Replenishment Order (SmallStock)",
                            "Initiate PADS Delivery (SmallStock)",
                            "Place Replenishment Order",
                            "Place delivered Items into Inventory",
                            "Pick and pack items for Customer Order",
                            ]
config.priority_probability = 0.5
config.max_execution_steps = 500 #7000
# config.max_events = 10021
