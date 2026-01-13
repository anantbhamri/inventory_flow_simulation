# Supply Chain Simulation: Shop, Inventory, Product Queue, Customer Queue
# Modular, well-commented code for easy understanding and extension
# Author: GitHub Copilot

import random
from collections import deque

# -----------------------------
# Customer class
# -----------------------------
class Customer:
	def __init__(self, arrival_time, demand):
		"""
		Represents a customer with arrival time and demand quantity.
		"""
		self.arrival_time = arrival_time
		self.demand = demand
		self.wait_time = 0  # Time spent waiting in the queue

# -----------------------------
# Inventory class
# -----------------------------
class Inventory:
	def __init__(self, max_capacity):
		"""
		Manages the shop's inventory.
		"""
		self.max_capacity = max_capacity
		self.current = max_capacity  # Start full

	def remove(self, quantity):
		"""
		Remove up to 'quantity' units from inventory. Returns actual removed.
		"""
		removed = min(self.current, quantity)
		self.current -= removed
		return removed

	def add(self, quantity):
		"""
		Add up to 'quantity' units to inventory, not exceeding max_capacity.
		"""
		space = self.max_capacity - self.current
		added = min(space, quantity)
		self.current += added
		return added

# -----------------------------
# ProductQueue class
# -----------------------------
class ProductQueue:
	def __init__(self):
		"""
		FIFO queue for incoming shipments from manufacturer.
		Each entry: (arrival_time, quantity)
		"""
		self.queue = deque()

	def add_shipment(self, arrival_time, quantity):
		self.queue.append((arrival_time, quantity))

	def pop_ready_shipments(self, current_time):
		"""
		Pop and return all shipments that have arrived by current_time.
		Returns a list of (arrival_time, quantity).
		"""
		ready = []
		while self.queue and self.queue[0][0] <= current_time:
			ready.append(self.queue.popleft())
		return ready

	def queue_size(self):
		return sum(q for _, q in self.queue)

	def quantity_in_front_of_last(self):
		"""
		Returns the sum of quantities in front of the last item in the queue.
		If queue is empty or has one item, returns 0.
		"""
		if len(self.queue) <= 1:
			return 0
		return sum(q for _, q in list(self.queue)[:-1])

# -----------------------------
# CustomerQueue class
# -----------------------------
class CustomerQueue:
	def __init__(self):
		"""
		FIFO queue for waiting customers.
		"""
		self.queue = deque()

	def add_customer(self, customer):
		self.queue.append(customer)

	def pop_customer(self):
		if self.queue:
			return self.queue.popleft()
		return None

	def is_empty(self):
		return len(self.queue) == 0

	def queue_size(self):
		return len(self.queue)

	def quantity_in_front_of_last(self):
		"""
		Returns the sum of demands in front of the last customer in the queue.
		If queue is empty or has one item, returns 0.
		"""
		if len(self.queue) <= 1:
			return 0
		return sum(c.demand for c in list(self.queue)[:-1])

# -----------------------------
# Shop class
# -----------------------------
class Shop:
	def __init__(self, max_inventory, lead_time):
		"""
		Shop manages inventory, product queue, and customer queue.
		"""
		self.inventory = Inventory(max_inventory)
		self.product_queue = ProductQueue()
		self.customer_queue = CustomerQueue()
		self.lead_time = lead_time  # Time for manufacturer to deliver
		self.pending_order = None  # (customer, remaining_demand)

	def process_incoming_shipments(self, current_time):
		"""
		Add arrived shipments to inventory.
		"""
		shipments = self.product_queue.pop_ready_shipments(current_time)
		for arrival_time, quantity in shipments:
			self.inventory.add(quantity)

	def handle_customer(self, customer, current_time):
		"""
		Try to fulfill customer demand. If not possible, add to queue (do not partially serve).
		"""
		if self.customer_queue.is_empty() and self.pending_order is None:
			# No waiting customers, try to serve immediately
			if self.inventory.current >= customer.demand:
				# Fully served, place refill order
				self.inventory.remove(customer.demand)
				self.product_queue.add_shipment(current_time + self.lead_time, customer.demand)
				return 'served'
			else:
				# Not enough inventory, add to queue and place order for full demand
				self.customer_queue.add_customer(customer)
				self.product_queue.add_shipment(current_time + self.lead_time, customer.demand)
				return 'queued'
		else:
			# There are waiting customers, add to queue
			self.customer_queue.add_customer(customer)
			return 'queued'

	def process_waiting_customers(self, current_time):
		"""
		Serve as many waiting customers as possible in one timestep, but only if their full demand can be met from current inventory.
		No partial fulfillment from inventory; customers wait until their full demand can be met.
		"""
		# First, handle any pending order (should not occur with new logic, but keep for safety)
		if self.pending_order:
			# Do not process any new customers until pending order is resolved
			return 'waiting'

		# Now, process as many customers as possible from the queue
		while not self.customer_queue.is_empty():
			next_customer = self.customer_queue.queue[0]
			if self.inventory.current >= next_customer.demand:
				# Serve and remove from queue
				self.inventory.remove(next_customer.demand)
				self.customer_queue.pop_customer()
				self.product_queue.add_shipment(current_time + self.lead_time, next_customer.demand)
				# Continue to next customer
			else:
				# Not enough inventory to serve this customer; stop processing
				break
		return 'idle'

# -----------------------------
# Simulation class
# -----------------------------

# Refactored Simulation class for step-by-step execution
class Simulation:
	def __init__(self, max_inventory=10, lead_time=3, max_time=100, max_customer_interval=5, min_demand=1, max_demand=5, seed=None):
		"""
		Step-by-step supply chain simulation for interactive visualization.
		"""
		self.max_inventory = max_inventory
		self.lead_time = lead_time
		self.max_time = max_time
		self.max_customer_interval = max_customer_interval
		self.min_demand = min_demand
		self.max_demand = max_demand
		self.shop = Shop(max_inventory, lead_time)
		self.time = 0
		self.next_customer_time = 0
		self.stats = []  # Collect stats for analysis
		self.last_customer = None  # Track last customer arrival and demand
		self.last_customer_arrived = False
		self.orders_with_manufacturer = []  # List of (sent_time, quantity)
		if seed is not None:
			random.seed(seed)

	def step(self):
		"""
		Advance the simulation by one time step.
		Returns a dict with the current state for visualization, including inventory calculation details.
		"""
		t = self.time
		prev_inventory = self.shop.inventory.current

		# 1. Process incoming shipments
		shipments = self.shop.product_queue.pop_ready_shipments(t)
		incoming = sum(q for _, q in shipments)
		self.shop.inventory.add(incoming)

		# Remove arrived shipments from orders_with_manufacturer
		def order_arrival_time(order):
			if isinstance(order, dict):
				return order['arrival_time']
			else:
				return order[0]
		self.orders_with_manufacturer = [order for order in self.orders_with_manufacturer if order_arrival_time(order) > t]

		# 2. Process waiting customers (if any)
		consumed = 0
		# Track inventory before serving customers
		before_customers = self.shop.inventory.current
		# Serve as many as possible, tracking what is consumed
		if self.shop.pending_order:
			# Should not happen with new logic, but for safety
			pass
		else:
			# Serve as many as possible (do NOT place new manufacturer order here)
			while not self.shop.customer_queue.is_empty():
				next_customer = self.shop.customer_queue.queue[0]
				if self.shop.inventory.current >= next_customer.demand:
					self.shop.inventory.remove(next_customer.demand)
					consumed += next_customer.demand
					self.shop.customer_queue.pop_customer()
					# Do NOT place another manufacturer order here
				else:
					break

		# 3. Customer arrival
		customer_arrived = False
		customer_demand = None
		if t >= self.next_customer_time:
			demand = random.randint(self.min_demand, self.max_demand)
			customer = Customer(arrival_time=t, demand=demand)
			# Always place manufacturer order at demand time
			self.shop.product_queue.add_shipment(t + self.lead_time, customer.demand)
			# Store both order time and arrival time
			self.orders_with_manufacturer.append({'order_time': t, 'arrival_time': t + self.lead_time, 'quantity': demand})
			if self.shop.customer_queue.is_empty() and self.shop.pending_order is None:
				if self.shop.inventory.current >= customer.demand:
					self.shop.inventory.remove(customer.demand)
					consumed += customer.demand
					customer_arrived = True
					customer_demand = demand
				else:
					self.shop.customer_queue.add_customer(customer)
					customer_arrived = True
					customer_demand = demand
			else:
				self.shop.customer_queue.add_customer(customer)
				customer_arrived = True
				customer_demand = demand
			# Schedule next customer
			interval = random.randint(1, self.max_customer_interval)
			self.next_customer_time = t + interval
			self.last_customer = customer
		else:
			customer_arrived = False
			customer_demand = None

		# 4. Collect stats
		product_queue_in_front_of_last = self.shop.product_queue.quantity_in_front_of_last()
		customer_queue_in_front_of_last = self.shop.customer_queue.quantity_in_front_of_last()
		state = {
			'time': t,
			'inventory': self.shop.inventory.current,
			'product_queue': list(self.shop.product_queue.queue),  # [(arrival_time, quantity), ...]
			'product_queue_size': self.shop.product_queue.queue_size(),
			'product_queue_in_front_of_last': product_queue_in_front_of_last,
			'customer_queue': list((c.arrival_time, c.demand) for c in self.shop.customer_queue.queue),
			'customer_queue_size': self.shop.customer_queue.queue_size(),
			'customer_queue_in_front_of_last': customer_queue_in_front_of_last,
			'customer_arrived': customer_arrived,
			'customer_demand': customer_demand,
			'orders_with_manufacturer': list(self.orders_with_manufacturer),
			'inventory_prev': prev_inventory,
			'inventory_incoming': incoming,
			'inventory_consumed': consumed,
			'inventory_calc': f"{prev_inventory} + {incoming} - {consumed} = {self.shop.inventory.current}",
		}
		# Store history for histogram
		if not hasattr(self, 'product_queue_in_front_of_last_hist'):
			self.product_queue_in_front_of_last_hist = []
		if not hasattr(self, 'customer_queue_in_front_of_last_hist'):
			self.customer_queue_in_front_of_last_hist = []
		self.product_queue_in_front_of_last_hist.append(product_queue_in_front_of_last)
		self.customer_queue_in_front_of_last_hist.append(customer_queue_in_front_of_last)
		self.stats.append(state)
		self.time += 1
		return state

	def reset(self):
		"""
		Reset the simulation to the initial state.
		"""
		self.shop = Shop(self.max_inventory, self.lead_time)
		self.time = 0
		self.next_customer_time = 0
		self.stats = []
		self.last_customer = None
		self.last_customer_arrived = False
		self.orders_with_manufacturer = []

	def is_finished(self):
		return self.time >= self.max_time

	def print_stats(self, every=10):
		for stat in self.stats[::every]:
			print(f"Time {stat['time']}: Inventory={stat['inventory']}, ProductQueue={stat['product_queue_size']} (front of last: {stat['product_queue_in_front_of_last']}), CustomerQueue={stat['customer_queue_size']} (front of last: {stat['customer_queue_in_front_of_last']})")

# -----------------------------
# Main entry point
# -----------------------------
# For testing step-by-step mode
if __name__ == "__main__":
	sim = Simulation(
		max_inventory=250,
		lead_time=5,
		max_time=20,
		max_customer_interval=1,
		min_demand=0,
		max_demand=100,
		seed=42
	)
	while not sim.is_finished():
		state = sim.step()
		print(f"Time {state['time']}: Inventory={state['inventory']}, ProductQueue={state['product_queue_size']} (front of last: {state['product_queue_in_front_of_last']}), CustomerQueue={state['customer_queue_size']} (front of last: {state['customer_queue_in_front_of_last']}), CustomerArrived={state['customer_arrived']}, CustomerDemand={state['customer_demand']}, OrdersWithManufacturer={state['orders_with_manufacturer']}")
