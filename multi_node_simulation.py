# Multi-Node Supply Chain Simulation
# Author: GitHub Copilot
# This file implements a parameterized, modular supply chain with N nodes.


from collections import deque
import random
from metrics_logger import MetricsLogger

class TrackedUnit:
    def __init__(self, unit_id, t_demand_actual_customer=None):
        self.id = unit_id
        self.timeline = {
            't_demand_actual_customer': t_demand_actual_customer,
            't_order_to_supplier': None,
            't_order_arrived_at_supplier': None,
            't_order_to_manufacturer': None,
            't_order_arrived_at_manufacturer': None,
            't_manufacturing_completed': None,
            't_shipped_to_distributor': None,
            't_arrived_at_distributor': None,
            't_shipped_to_shop': None,
            't_arrived_at_shop': None,
            't_given_to_actual_customer': None
        }

class Node:
    def __init__(self, node_id, initial_inventory, order_comm_lag, lag_time, is_manufacturer=False, manufacturing_time=None):
        self.node_id = node_id
        self.inventory = initial_inventory
        self.order_comm_lag = order_comm_lag
        self.lag_time = lag_time
        self.inventory_units = []  # List of TrackedUnit objects in inventory
        self.customer_queue = deque()  # (arrival_time, qty, TrackedUnit)
        self.order_queue = deque()     # (order_time, qty, TrackedUnit)
        self.incoming_shipments = deque()  # (arrival_time, TrackedUnit, sent_time)
        self.incoming_orders = deque()     # (arrival_time, TrackedUnit, sent_time)
        self.outgoing_shipments = deque()  # (arrival_time, TrackedUnit, sent_time)
        self.is_manufacturer = is_manufacturer
        self.manufacturing_time = manufacturing_time
        self.production_queue = deque()  # (order_time, qty)
        self.current_production_end = None
        self.current_production_qty = 0
        self.current_production_unit = None
        self.current_production_order = None

    def receive_shipments(self, current_time):
        received_units = []
        while self.incoming_shipments and self.incoming_shipments[0][0] <= current_time:
            shipment = self.incoming_shipments.popleft()
            if len(shipment) == 4:
                _, unit, shipping_time, requested_time = shipment
            else:
                raise ValueError(f"Unexpected incoming_shipments tuple length: {len(shipment)}")
            self.inventory_units.append(unit)
            received_units.append((unit, requested_time))
        return received_units

    def receive_orders(self, current_time):
        orders = []
        while self.incoming_orders and self.incoming_orders[0][0] <= current_time:
            _, order, sent_time = self.incoming_orders.popleft()
            orders.append((sent_time, order))
        return orders

    def add_to_customer_queue(self, t, unit, requested_time):
        self.customer_queue.append((t, 1, unit, requested_time))

    def propagate_order_upstream(self, t, unit, upstream_node, order_comm_lag):
        arrival_time = t + order_comm_lag
        upstream_node.incoming_orders.append((arrival_time, unit, t))
        unit.timeline['t_order_to_supplier'] = t
        unit.timeline['t_order_arrived_at_supplier'] = arrival_time

    def fulfill_customer_queue(self, t, downstream_node=None):
        # Fulfill as much demand as possible (FIFO)
        shipped_units = []
        while self.customer_queue and self.inventory_units:
            arrival_time, qty, unit, requested_time = self.customer_queue[0]
            self.customer_queue.popleft()
            inv_unit = self.inventory_units.pop(0)
            if downstream_node is not None:
                # Ship to downstream node with lag
                downstream_node.incoming_shipments.append((t + self.lag_time, inv_unit, t, requested_time))
                shipped_units.append((t + self.lag_time, inv_unit, t, requested_time))
            else:
                # Node 1: hand to customer
                inv_unit.timeline['t_given_to_actual_customer'] = t
                shipped_units.append((t, inv_unit, t, requested_time))
        return shipped_units

    def process_manufacturing(self, t, downstream_node):
        # Parallel batch production: start a new batch as soon as a request is received, even if others are in progress
        if not hasattr(self, 'active_batches'):
            self.active_batches = []  # Each batch: dict with keys 'end', 'units', 'requested_times', 'start'

        completed_units = []

        # 1. Check for completed batches and ship them
        batches_to_ship = [batch for batch in self.active_batches if t >= batch['end']]
        for batch in batches_to_ship:
            for unit, requested_time in zip(batch['units'], batch['requested_times']):
                unit.timeline['t_manufacturing_completed'] = batch['end']
                downstream_node.incoming_shipments.append((batch['end'] + self.lag_time, unit, batch['end'], requested_time))
                completed_units.append(unit)
            self.active_batches.remove(batch)

        # 2. Start new batches for all new arrivals (grouped by arrival time)
        while self.customer_queue:
            first_arrival_time, _, _, _ = self.customer_queue[0]
            batch_units = []
            batch_requested_times = []
            while self.customer_queue and self.customer_queue[0][0] == first_arrival_time:
                _, qty, unit, requested_time = self.customer_queue.popleft()
                batch_units.append(unit)
                batch_requested_times.append(requested_time)
            if batch_units:
                batch = {
                    'start': t,
                    'end': t + self.manufacturing_time,
                    'units': batch_units,
                    'requested_times': batch_requested_times
                }
                self.active_batches.append(batch)

        return completed_units

class MultiNodeSimulation:
    def __init__(self, num_nodes, initial_inventories, order_comm_lags, lag_times, max_time=100, manufacturing_time=3, max_demand=50, seed=None):
        self.num_nodes = num_nodes
        self.initial_inventories = initial_inventories[:]
        assert num_nodes == len(initial_inventories) == len(order_comm_lags) == len(lag_times)
        self.manufacturing_time = manufacturing_time
        self.max_demand = max_demand
        if seed is not None:
            random.seed(seed)
        self.seed = seed
        self.nodes = [
            Node(i+1, initial_inventories[i], order_comm_lags[i], lag_times[i],
                 is_manufacturer=(i == num_nodes-1), manufacturing_time=manufacturing_time if i == num_nodes-1 else None)
            for i in range(num_nodes)
        ]
        self.time = 0
        self.max_time = max_time
        self.stats = []
        self.customer_demand_history = []
        self.tracked_units = []  # All TrackedUnit objects for analysis

        # Initialize metrics logger
        self.metrics_logger = MetricsLogger(num_nodes)

        # Initialize inventory units for initial inventory
        for i, node in enumerate(self.nodes):
            for j in range(self.initial_inventories[i]):
                unit_id = (f'init_{i+1}', j)
                unit = TrackedUnit(unit_id)
                node.inventory_units.append(unit)
                self.tracked_units.append(unit)
                # Add to metrics logger with None as customer_request_time for initial inventory
                self.metrics_logger.add_unit(unit_id, customer_request_time=None)

    def step(self, customer_demand=None):
        t = self.time
        # 0. Handle new customer demand: create TrackedUnit for each unit demanded
        new_units = []
        if customer_demand is None:
            customer_demand = random.randint(0, self.max_demand)
        self.customer_demand_history.append(customer_demand)
        for i in range(customer_demand):
            unit_id = (t, i)
            unit = TrackedUnit(unit_id, t_demand_actual_customer=t)
            new_units.append(unit)
            self.tracked_units.append(unit)
            # Add to metrics logger for each new demand unit
            self.metrics_logger.add_unit(unit_id, customer_request_time=t)
            self.metrics_logger.update(unit.id, 'order_to_node1', t)
        for unit in new_units:
            self.nodes[0].add_to_customer_queue(t, unit, t)
            # Node 1 propagates customer demand upstream to Node 2
            if self.num_nodes > 1:
                arrival_time = t + self.nodes[0].order_comm_lag
                self.nodes[1].incoming_orders.append((arrival_time, unit, t))
                unit.timeline['t_order_to_supplier'] = t
                unit.timeline['t_order_arrived_at_supplier'] = arrival_time

        # 1. All nodes receive shipments
        for node in self.nodes:
            received_units = node.receive_shipments(t)
            for unit,requested_time in received_units:
                self.metrics_logger.update(unit.id, f'arrive_at_node{node.node_id}', (t,requested_time))

        # 2. All nodes process incoming orders and propagate upstream
        for i in range(1, self.num_nodes):
            node = self.nodes[i]
            upstream_node = self.nodes[i+1] if i < self.num_nodes - 1 else None
            orders = node.receive_orders(t)
            for sent_time, unit in orders:
                node.add_to_customer_queue(t, unit, sent_time)
                # Update metrics for order placed to this node
                self.metrics_logger.update(unit.id, f'order_to_node{node.node_id}', t)
                if upstream_node is not None:
                    node.propagate_order_upstream(t, unit, upstream_node, node.order_comm_lag)
                # For manufacturer, do not append again; already added via add_to_customer_queue

        # 3. All nodes fulfill customer queue
        for i in range(self.num_nodes-1, -1, -1):
            node = self.nodes[i]
            if node.is_manufacturer:
                # Process manufacturing and update metrics for completed units
                completed_units = node.process_manufacturing(t, self.nodes[i-1])
                for unit in completed_units:
                    self.metrics_logger.update(unit.id, 'manufacturing_completed', t)
            else:
                # Fulfill customer queue and get shipped units
                shipped_units = node.fulfill_customer_queue(t, downstream_node=None if i == 0 else self.nodes[i-1])
                for arrival_time, unit, shipped_time, requested_time in shipped_units:
                    if i == 0:
                        # Delivered to customer
                        self.metrics_logger.update(unit.id, 'customer_delivered', (t,requested_time))
                    else:
                        # Shipped to next node (arrives will be logged on receipt)
                        pass

        # 4. Collect stats
        self.stats.append({
            'time': t,
            'inventories': [len(node.inventory_units) for node in self.nodes],
            'customer_queues': [len(node.customer_queue) for node in self.nodes],
            'incoming_shipments': [len(node.incoming_shipments) for node in self.nodes],
            'incoming_orders': [len(node.incoming_orders) for node in self.nodes],
        })
        self.time += 1

    def is_finished(self):
        return self.time >= self.max_time

    def reset(self):
        for i, node in enumerate(self.nodes):
            node.inventory = self.initial_inventories[i]
            node.customer_queue.clear()
            node.order_queue.clear()
            node.incoming_shipments.clear()
            node.incoming_orders.clear()
            if getattr(node, 'is_manufacturer', False):
                node.production_queue.clear()
                node.current_production_end = None
                node.current_production_qty = 0
        self.time = 0
        self.stats = []
        self.customer_demand_history = []

    def get_results(self):
        # Returns a list of dicts with inventory values for each node at each timestep
        results = []
        for stat in self.stats:
            row = {}
            for i, inv in enumerate(stat['inventories']):
                row[f"Node {i+1} Inv"] = inv
            results.append(row)
        return results

    def get_tracked_units(self):
        return self.tracked_units
