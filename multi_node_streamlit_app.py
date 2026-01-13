# Multi-Node Supply Chain Streamlit App
# Author: GitHub Copilot
# Visualizes the multi-node supply chain simulation with node inventories and queue details

import streamlit as st
import matplotlib.pyplot as plt
from multi_node_simulation import MultiNodeSimulation
import pandas as pd
import json
import os

st.set_page_config(layout="wide")
st.title("Multi-Node Supply Chain Simulation")

# Load config file for defaults
config_path = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
else:
    config = {}



# ...existing code...



# Ensure simulation is initialized in session state
if 'sim' not in st.session_state:
    st.session_state.sim = MultiNodeSimulation(
        config.get("num_nodes", 4),
        config.get("initial_inventories", [50]*config.get("num_nodes", 4)),
        config.get("order_comm_lags", [1]*config.get("num_nodes", 4)),
        config.get("lag_times", [3]*config.get("num_nodes", 4)),
        max_time=config.get("max_time", 30),
        manufacturing_time=config.get("manufacturing_time", 3),
        max_demand=config.get("max_demand", 50),
        seed=config.get("seed", None)
    )
    st.session_state.sim.reset()

sim = st.session_state.sim


# Controls

col1, col2, col3 = st.columns(3)
with col1:
    customer_demand = st.number_input(
        "Customer Demand (this step, leave blank for random)",
        min_value=0, max_value=1000, value=None, step=1,
        key="customer_demand_input_main"
    )
    if st.button("Next Step", key="next_step_btn_main"):
        # If no value entered, use None for random demand
        if customer_demand is not None:
            st.session_state.last_customer_demand = customer_demand
        else:
            st.session_state.last_customer_demand = None
        if not sim.is_finished():
            sim.step(st.session_state.last_customer_demand)
with col2:
    if st.button("Reset Simulation", key="reset_sim_btn_main"):
        sim.reset()
        # Reset cycle time history for a clean run
        if hasattr(sim, 'metrics_logger'):
            sim.metrics_logger.cycle_time_history = []
        st.session_state.last_customer_demand = None
with col3:
    if st.button("Run Full Simulation", key="run_full_sim_btn_main"):
        # Reset cycle time history before running full simulation
        if hasattr(sim, 'metrics_logger'):
            sim.metrics_logger.cycle_time_history = []
        while not sim.is_finished():
            sim.step()
            # Save cycle times at each step
            if hasattr(sim, 'metrics_logger'):
                sim.metrics_logger.compute_cycle_times(save_history=True)

# Show average demand immediately after controls
if sim.customer_demand_history:
    avg_demand = sum(sim.customer_demand_history) / len(sim.customer_demand_history)
    st.subheader(f"Average Demand: {avg_demand:.2f}")
    print(f"Average Demand: {avg_demand:.2f}")
    print(f"Customer Demand History: {sim.customer_demand_history}")

    
# Options to show/hide each section
show_node_stats = config.get("show_node_stats", True)
show_simulation_results = config.get("show_simulation_results", True)
show_supply_chain_figure = config.get("show_supply_chain_figure", True)

# Sidebar for parameters, using config defaults if available
st.sidebar.header("Simulation Parameters")
num_nodes = st.sidebar.slider("Number of Nodes", min_value=2, max_value=6, value=config.get("num_nodes", 4), key="num_nodes_slider")
max_time = st.sidebar.number_input("Simulation Steps", min_value=10, max_value=10000, value=config.get("max_time", 30), key="max_time_input")
max_demand = st.sidebar.number_input("Max Customer Demand", min_value=1, max_value=1000, value=config.get("max_demand", 50), key="max_demand_input")

init_inv = st.sidebar.text_input("Initial Inventories (comma-separated)", value=','.join(str(x) for x in config.get("initial_inventories", [50]*num_nodes)), key="init_inv_input")
order_comm_lags = st.sidebar.text_input("Order Communication Lags (comma-separated)", value=','.join(str(x) for x in config.get("order_comm_lags", [1]*num_nodes)), key="order_comm_lags_input")
lag_times = st.sidebar.text_input("Lag Times (comma-separated)", value=','.join(str(x) for x in config.get("lag_times", [3]*num_nodes)), key="lag_times_input")
manufacturing_time = st.sidebar.number_input("Manufacturing Time (last node)", min_value=1, max_value=20, value=config.get("manufacturing_time", 3), key="manufacturing_time_input")
seed = st.sidebar.text_input("Random Seed (leave blank for random)", value=str(config.get("seed", "")), key="seed_input")

init_inv = [int(x) for x in init_inv.split(',')]
order_comm_lags = [int(x) for x in order_comm_lags.split(',')]
lag_times = [int(x) for x in lag_times.split(',')]
# Fix seed parsing to handle None and non-integer values gracefully
try:
    seed_val = int(seed) if seed.strip() and seed.strip().lower() != 'none' else None
except ValueError:
    seed_val = None

# Session state for simulation
if (
    'sim' not in st.session_state or
    st.session_state.sim.num_nodes != num_nodes or
    st.session_state.sim.initial_inventories != init_inv or
    [n.order_comm_lag for n in st.session_state.sim.nodes] != order_comm_lags or
    [n.lag_time for n in st.session_state.sim.nodes] != lag_times or
    st.session_state.sim.max_time != max_time or
    st.session_state.sim.manufacturing_time != manufacturing_time or
    st.session_state.sim.max_demand != max_demand or
    st.session_state.sim.seed != seed_val
):
    st.session_state.sim = MultiNodeSimulation(num_nodes, init_inv, order_comm_lags, lag_times, max_time=max_time, manufacturing_time=manufacturing_time, max_demand=max_demand, seed=seed_val)
    st.session_state.sim.reset()
    st.session_state.last_customer_demand = None

sim = st.session_state.sim

# Controls

col1, col2, col3 = st.columns(3)
with col1:
    customer_demand = st.number_input("Customer Demand (this step, leave blank for random)", min_value=0, max_value=1000, value=None, step=1)
    if st.button("Next Step"):
        # If no value entered, use None for random demand
        if customer_demand is not None:
            st.session_state.last_customer_demand = customer_demand
        else:
            st.session_state.last_customer_demand = None
        if not sim.is_finished():
            sim.step(st.session_state.last_customer_demand)
with col2:
    if st.button("Reset Simulation"):
        sim.reset()
        # Reset cycle time history for a clean run
        if hasattr(sim, 'metrics_logger'):
            sim.metrics_logger.cycle_time_history = []
        st.session_state.last_customer_demand = None
with col3:
    if st.button("Run Full Simulation"):
        # Reset cycle time history before running full simulation
        if hasattr(sim, 'metrics_logger'):
            sim.metrics_logger.cycle_time_history = []
        while not sim.is_finished():
            sim.step()
            # Save cycle times at each step
            if hasattr(sim, 'metrics_logger'):
                sim.metrics_logger.compute_cycle_times(save_history=True)

st.header(f"Time Step: {sim.time}")

# Show stats table
st.subheader("Node Stats Table")
def get_manufacturer_batches(node):
    batches = getattr(node, 'active_batches', [])
    batch_list = []
    for batch in batches:
        batch_list.append(
            f"(start:{batch['start']}, end:{batch['end']}, qty:{len(batch['units'])}, units:{[u.id for u in batch['units']]})"
        )
    return batch_list

st.table({
    f"Node {i+1}": {
        "Inventory": len(sim.nodes[i].inventory_units),
        "Customer Queue": [(arrival_time, qty, requested_time) for (arrival_time, qty, unit, requested_time) in list(sim.nodes[i].customer_queue)],
        "Supplier Queue": [(order_time, qty) for (order_time, qty, unit) in list(sim.nodes[i].order_queue)],
        "Shipments in Transit": [
            f"(arrives:{arr}, unit:{getattr(unit, 'id', unit)}, sent:{sent}" + (f", requested:{req})" if len(shipment) == 4 else ")")
            for shipment in sim.nodes[i].incoming_shipments
            for (arr, unit, sent, *rest) in [shipment]
            for req in (rest[0] if rest else None,)
        ],
        **({
            "Active Batches": get_manufacturer_batches(sim.nodes[i])
        } if getattr(sim.nodes[i], 'is_manufacturer', False) else {})
    } for i in range(num_nodes)
})

# Add demand display to the main table
st.subheader("Simulation Results")
results = st.session_state.sim.get_results()
demand_row = [d for d in st.session_state.sim.customer_demand_history]

# Build table headers
headers = [f"Node {i+1} Inv" for i in range(st.session_state.sim.num_nodes)] + ["Demand"]

# Build table rows
rows = []
for t in range(len(results)):
    inv_row = [results[t][f"Node {i+1} Inv"] for i in range(st.session_state.sim.num_nodes)]
    demand_val = st.session_state.sim.customer_demand_history[t] if t < len(st.session_state.sim.customer_demand_history) else ""
    rows.append(inv_row + [demand_val])

st.table([headers] + rows)

# Draw supply chain diagram
fig, ax = plt.subplots(figsize=(2*num_nodes, 5))
ax.axis('off')

node_x = [2*i for i in range(num_nodes)]
node_y = [3]*num_nodes

# Draw nodes
for i in range(num_nodes):
    ax.add_patch(plt.Circle((node_x[i], node_y[i]), 0.4, color='violet', zorder=2))  # Restore original node size
    ax.text(node_x[i], node_y[i]+0.7, f"Node {i+1}", ha='center', fontsize=12, fontweight='bold')
    # Show real-time inventory from inventory_units
    ax.text(node_x[i], node_y[i]+0.4, f"Inventory: {len(sim.nodes[i].inventory_units)}", ha='center', fontsize=10, color='purple')

# Draw arrows and queue details
for i in range(num_nodes-1):
    # Arrow for product flow (downstream)
    ax.arrow(node_x[i+1]-0.5, node_y[i], -1, 0, head_width=0.2, head_length=0.2, fc='blue', ec='blue', length_includes_head=True, zorder=1)
    # Arrow for order flow (upstream)
    ax.arrow(node_x[i]+0.5, node_y[i]+0.2, 1, 0, head_width=0.15, head_length=0.15, fc='magenta', ec='magenta', length_includes_head=True, zorder=1)
    # Shipments in transit (downstream)
    shipments = list(sim.nodes[i].incoming_shipments)
    shipment_str = ', '.join([
        f"(arrives:{arr}, unit:{getattr(unit, 'id', unit)}, sent:{sent}, requested:{req})"
        for shipment in shipments
        for (arr, unit, sent, *rest) in [shipment]
        for req in (rest[0] if rest else None,)
    ])
    ax.text(node_x[i], node_y[i]-0.7, f"Shipments in Transit: {shipment_str}", ha='center', fontsize=9, color='blue')

# Last node shipments
shipments_last = list(sim.nodes[-1].incoming_shipments)
shipment_str_last = ', '.join([
    f"(arrives:{arr}, unit:{getattr(unit, 'id', unit)}, sent:{sent}, requested:{req})"
    for shipment in shipments_last
    for (arr, unit, sent, *rest) in [shipment]
    for req in (rest[0] if rest else None,)
])
ax.text(node_x[-1], node_y[-1]-0.7, f"Shipments in Transit: {shipment_str_last}", ha='center', fontsize=9, color='blue')

st.pyplot(fig)

# After simulation run, show tracked units table

# Show modular metrics table from MetricsLogger
if hasattr(st.session_state.sim, 'metrics_logger'):
    # Show a table with the average value for each cycle time metric at each timestep
    st.subheader("Average Cycle Times (History)")
    # Only add to history if not already done this step (avoid duplicate rows)
    if not sim.is_finished() or not sim.metrics_logger.cycle_time_history:
        sim.metrics_logger.compute_cycle_times(save_history=True)
    cycle_time_history = sim.metrics_logger.get_cycle_time_history()
    if not cycle_time_history.empty:
        st.dataframe(cycle_time_history, height=400, use_container_width=True)
    else:
        st.write("No cycle time history yet.")
    df_metrics = st.session_state.sim.metrics_logger.to_dataframe()
    st.subheader("Per-Unit Metrics Table")
    st.dataframe(df_metrics, height=600, use_container_width=True)
    st.markdown("""
        <style>
        .stDataFrame td { white-space: normal !important; word-break: break-word !important; }
        </style>
        """, unsafe_allow_html=True)

if sim.is_finished():
    st.warning("Simulation finished. Press Reset to start again.")
