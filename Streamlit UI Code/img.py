import liionpack as lp
import numpy as np
import pybamm
import matplotlib.pyplot as plt

# Generate the netlist for a battery pack (16 parallel, 2 series)
# Adjusted initial voltage to a more typical value for LG M50 cells (Chen2020 chemistry)
netlist = lp.setup_circuit(Np=16, Ns=2, Rb=1e-4, Rc=1e-2, Ri=5e-2, V=3.7, I=0.0)

# Define output variables to track during simulation
output_variables = [
    "X-averaged total heating [W.m-3]",
    "Volume-averaged cell temperature [K]",
    "X-averaged negative particle surface concentration [mol.m-3]",
    "X-averaged positive particle surface concentration [mol.m-3]",
]

# Define the experiment: simplified charge/discharge cycle
experiment = pybamm.Experiment([
    "Rest for 10 seconds",  # Short initial rest to stabilize initial conditions
    "Charge at 20 A for 30 minutes or until 4.2 V",
    "Rest for 15 minutes",
    "Discharge at 20 A for 30 minutes or until 2.8 V",
    "Rest for 30 minutes"
], period="10 seconds")

# Load parameter values for the battery chemistry (LG M50 cell)
parameter_values = pybamm.ParameterValues("Chen2020")

# Adjust initial SOC to a reasonable value (0.5 = 50% SOC)
initial_soc = 0.5

# Solve the pack simulation
output = lp.solve(
    netlist=netlist,
    parameter_values=parameter_values,
    experiment=experiment,
    output_variables=output_variables,
    initial_soc=initial_soc
)

# Plot pack-level results (terminal voltage and current)
lp.plot_pack(output)

# Plot individual cell current for the first cell
plt.figure()
plt.plot(output["Time [s]"], output["Cell current [A]"][:, 0])
plt.xlabel("Time [s]")
plt.ylabel("Cell Current [A]")
plt.title("Cell Current Under Load")
plt.show()