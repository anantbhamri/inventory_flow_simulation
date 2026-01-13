# Streamlit app for step-by-step supply chain simulation visualization
# Run with: streamlit run streamlit_app.py

import streamlit as st
from main import Simulation

# --- Streamlit App State Management ---
if 'sim' not in st.session_state:
    st.session_state.sim = Simulation(
        max_inventory=250,
		lead_time=5,
		max_time=20,
		max_customer_interval=1,
		min_demand=0,
		max_demand=100,
		seed=42
    )
    st.session_state.sim.reset()
    st.session_state.last_state = None

sim = st.session_state.sim

st.title('Supply Chain Simulation (Step-by-Step)')

# Controls
col1, col2 = st.columns(2)
with col1:
    if st.button('Next Step'):
        if not sim.is_finished():
            st.session_state.last_state = sim.step()
with col2:
    if st.button('Reset Simulation'):
        sim.reset()
        st.session_state.last_state = None

# Show current state
time = sim.time if not sim.is_finished() else sim.time - 1
st.header(f'Time Step: {time}')

if st.session_state.last_state:
    state = st.session_state.last_state
else:
    # Show initial state
    state = {
        'time': 0,
        'inventory': sim.shop.inventory.current,
        'product_queue': list(sim.shop.product_queue.queue),
        'product_queue_size': sim.shop.product_queue.queue_size(),
        'product_queue_in_front_of_last': sim.shop.product_queue.quantity_in_front_of_last(),
        'customer_queue': list((c.arrival_time, c.demand) for c in sim.shop.customer_queue.queue),
        'customer_queue_size': sim.shop.customer_queue.queue_size(),
        'customer_queue_in_front_of_last': sim.shop.customer_queue.quantity_in_front_of_last(),
        'customer_arrived': False,
        'customer_demand': None,
        'orders_with_manufacturer': [],
    }


# Inventory
st.subheader('Inventory')
st.progress(state['inventory'] / sim.max_inventory)
st.write(f"Current Inventory: {state['inventory']} / {sim.max_inventory}")
if 'inventory_calc' in state:
    st.write(f"Inventory Calculation: {state['inventory_calc']}")
    st.caption(f"Previous: {state.get('inventory_prev', 0)}, Incoming: {state.get('inventory_incoming', 0)}, Consumed: {state.get('inventory_consumed', 0)}")

# Product Queue
st.subheader('Product Queue (Shipments from Manufacturer)')
if state['product_queue']:
    st.table([
        {'Arrival Time': at, 'Quantity': q} for (at, q) in state['product_queue']
    ])
else:
    st.write('No shipments in queue.')
st.write(f"Total in Product Queue: {state['product_queue_size']}")
st.write(f"Quantity in front of last: {state['product_queue_in_front_of_last']}")

# Orders with Manufacturer

st.subheader('Orders with Manufacturer (in transit)')
if state['orders_with_manufacturer']:
    # Support both old (tuple) and new (dict) formats for backward compatibility
    orders = state['orders_with_manufacturer']
    if isinstance(orders[0], dict):
        st.table([
            {'Order Time': o['order_time'], 'Arrival Time': o['arrival_time'], 'Quantity': o['quantity']} for o in orders
        ])
    else:
        st.table([
            {'Arrival Time': at, 'Quantity': q} for (at, q) in orders
        ])
else:
    st.write('No orders in transit.')

# Customer Queue
st.subheader('Customer Queue (Waiting Customers)')
if state['customer_queue']:
    st.table([
        {'Arrival Time': at, 'Demand': d} for (at, d) in state['customer_queue']
    ])
else:
    st.write('No customers waiting.')
st.write(f"Total in Customer Queue: {state['customer_queue_size']}")
st.write(f"Quantity in front of last: {state['customer_queue_in_front_of_last']}")



# Customer Arrival
st.subheader('Customer Arrival at This Step')
if state['customer_arrived']:
    st.success(f"Customer arrived and requested {state['customer_demand']} units.")
else:
    st.info("No customer arrived this step.")

# Table of demand from consumer at each timestep
st.subheader('Demand from Consumer at Each Timestep')
if hasattr(sim, 'stats') and sim.stats:
    demand_data = [
        {'Time': s['time'], 'Demand': s['customer_demand'] if s['customer_arrived'] else 0}
        for s in sim.stats
    ]
    st.table(demand_data)
else:
    st.write('No demand data yet.')

# Histograms of 'in front of last' values
import matplotlib.pyplot as plt
import numpy as np

st.subheader("Histogram: Product Queue In Front of Last")
if hasattr(sim, 'product_queue_in_front_of_last_hist') and sim.product_queue_in_front_of_last_hist:
    fig1, ax1 = plt.subplots()
    ax1.hist(sim.product_queue_in_front_of_last_hist, bins=20, color='skyblue', edgecolor='black')
    ax1.set_xlabel('Quantity in Front of Last (Product Queue)')
    ax1.set_ylabel('Frequency')
    st.pyplot(fig1)
else:
    st.write("No data yet.")

st.subheader("Histogram: Customer Queue In Front of Last")
if hasattr(sim, 'customer_queue_in_front_of_last_hist') and sim.customer_queue_in_front_of_last_hist:
    fig2, ax2 = plt.subplots()
    ax2.hist(sim.customer_queue_in_front_of_last_hist, bins=20, color='salmon', edgecolor='black')
    ax2.set_xlabel('Quantity in Front of Last (Customer Queue)')
    ax2.set_ylabel('Frequency')
    st.pyplot(fig2)
else:
    st.write("No data yet.")

# --- Queue Size Over Time ---
st.subheader("Queue Size Over Time")
if hasattr(sim, 'stats') and sim.stats:
    times = [s['time'] for s in sim.stats]
    product_queue_sizes = [s['product_queue_size'] for s in sim.stats]
    customer_queue_sizes = [s['customer_queue_size'] for s in sim.stats]
    fig_q, ax_q = plt.subplots()
    ax_q.plot(times, product_queue_sizes, label='Product Queue Size', color='blue')
    ax_q.plot(times, customer_queue_sizes, label='Customer Queue Size', color='red')
    ax_q.set_xlabel('Time')
    ax_q.set_ylabel('Queue Size')
    ax_q.legend()
    st.pyplot(fig_q)
else:
    st.write('No queue size data yet.')

# Simulation End
if sim.is_finished():
    st.warning('Simulation finished. Press Reset to start again.')
