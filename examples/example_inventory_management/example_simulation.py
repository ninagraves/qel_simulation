from qel_simulation.simulation.simulation import Simulation
from examples.example_inventory_management.example_sim_config import config

qsim = Simulation(name=f"Example_Inventory_Management", config=config)
qsim.start_simulation()
qsim.export_simulated_log()

