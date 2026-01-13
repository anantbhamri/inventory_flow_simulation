import pandas as pd
import json
import os

# Load config file for defaults
config_path = os.path.join(os.path.dirname(__file__), "config.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
else:
    config = {}

class MetricsLogger:
    
    def __init__(self, num_nodes):
        self.num_nodes = num_nodes
        self.metrics = []  # List of dicts, one per unit
        self.unit_id_to_idx = {}  # Map unit.id to row index in metrics
        # Build modular column names
        self.columns = ['unit_id', 'customer_request']
        for i in range(1, num_nodes+1):
            self.columns.append(f'order_to_node{i}')
            self.columns.append(f'arrive_at_node{i}')
        self.columns.append('manufacturing_completed')
        self.columns.append('customer_delivered')
        # Store average cycle times at each timestep
        self.cycle_time_history = []

    def add_unit(self, unit_id, customer_request_time):
        unit_id_str = str(unit_id)
        row = {col: None for col in self.columns}
        row['unit_id'] = unit_id_str
        row['customer_request'] = customer_request_time
        self.unit_id_to_idx[unit_id_str] = len(self.metrics)
        self.metrics.append(row)

    def update(self, unit_id, column, value):
        unit_id_str = str(unit_id)
        idx = self.unit_id_to_idx.get(unit_id_str)
        if idx is not None and column in self.columns:
            self.metrics[idx][column] = value

    def to_dataframe(self):
        return pd.DataFrame(self.metrics, columns=self.columns)

    def to_csv(self, path):
        df = self.to_dataframe()
        df.to_csv(path, index=False)

    def compute_cycle_times(self, save_history=True):
        """
        Returns a dictionary with cycle time lists for:
        - 'customer_node1_cycle': time from customer request to delivery (customer_delivered - customer_request)
        - 'full_cycle': time from customer request to final delivery (customer_delivered - customer_request)
        - 'node_pair_cycles': list of cycle times for each node_i to node_{i+1} (arrive_at_node_{i+1} - arrive_at_node_{i})
        If save_history is True, appends the current average cycle times to the history.
        """
        df = self.to_dataframe().copy()
        # Customer to node1 cycle times: difference between consecutive customer_delivered times
        # If customer_delivered is a tuple, extract both values and compute their difference
        delivered_tuples = [t for t in df['customer_delivered'].dropna().tolist() if isinstance(t, tuple)]
        customer_node1_cycle = [t[0] - t[1] for t in delivered_tuples if isinstance(t, tuple) and len(t) == 2]
        # Full cycle times: difference between customer_request and first value in customer_delivered tuple
        full_cycle = [
            delivered[0] - request
            for request, delivered in zip(df['customer_request'], df['customer_delivered'])
            if pd.notna(request) and pd.notna(delivered) and isinstance(delivered, tuple)
        ]
        # Node pair cycles (original implementation)
        # node_pair_cycles = {}
        # for i in range(1, self.num_nodes):
        #     col = f'arrive_at_node{i}'
        #     cycles = []
        #     for val in df[col]:
        #         if pd.notna(val) and isinstance(val, tuple) and len(val) == 2:
        #             cycles.append(val[0] - val[1])
        #     node_pair_cycles[f'node_{i}_to_node_{i+1}_cycle'] = cycles

        # New node pair cycles calculation as requested
        
        node_pair_cycles = {}
        for i in range(1, self.num_nodes):
            col = f'arrive_at_node{i}'
            cycles = []
            if i == 1:
                # node_1_to_node2: use arrive_at_node1 and customer_delivered tuple
                for arrive_val, delivered_val in zip(df[col], df['customer_delivered']):
                    if pd.notna(arrive_val) and pd.notna(delivered_val) and isinstance(delivered_val, tuple) and len(delivered_val) == 2 and isinstance(arrive_val, tuple) and len(arrive_val) == 2:
                        cycles.append(delivered_val[0] - arrive_val[1])
                
            else:
                # node_i_to_node_{i+1}: use arrive_at_node{i} and arrive_at_node{i-1}
                col_downstream = f'arrive_at_node{i-1}'
                for arrive_i, arrive_downstream in zip(df[col], df[col_downstream]):
                    if pd.notna(arrive_i) and pd.notna(arrive_downstream) and isinstance(arrive_downstream, tuple) and len(arrive_downstream) == 2 and isinstance(arrive_i, tuple) and len(arrive_i) == 2:
                        arrive_downstream_time = arrive_downstream[0]
                        # lag time between node i and i-1 is in config file lag_time[i-1]
                        lag_time_interest = config.get("lag_times", [0]*self.num_nodes)[i-1]
                        left_current_time = arrive_downstream_time - lag_time_interest
                        request_time = arrive_i[1]
                        cycles.append(left_current_time - request_time)
            node_pair_cycles[f'node_{i}_to_node_{i+1}_cycle'] = cycles
            # print(f"Node {i} to Node {i+1} cycles: {cycles}")

        # Compute averages
        avg_customer_node1 = sum(customer_node1_cycle)/len(customer_node1_cycle) if customer_node1_cycle else None
        avg_full_cycle = sum(full_cycle)/len(full_cycle) if full_cycle else None
        avg_node_pair_cycles = {}
        for k, v in node_pair_cycles.items():
            avg_node_pair_cycles[k] = sum(v)/len(v) if v else None
        # Save to history if requested
        if save_history:
            row = {'customer_node1_cycle': avg_customer_node1, 'full_cycle': avg_full_cycle}
            row.update(avg_node_pair_cycles)
            self.cycle_time_history.append(row)
        return {
            'customer_node1_cycle': customer_node1_cycle,
            'full_cycle': full_cycle,
            'node_pair_cycles': node_pair_cycles
        }

    def get_cycle_time_history(self):
        """
        Returns a DataFrame of the average cycle times at each timestep, with columns ordered as:
        full_cycle, customer_node1_cycle, node_1_to_node_2_cycle, node_2_to_node_3_cycle, ...
        """
        if not self.cycle_time_history:
            return pd.DataFrame()
        # Ensure all keys are present in all rows
        all_keys = set()
        for row in self.cycle_time_history:
            all_keys.update(row.keys())
        # Fill missing keys with None
        filled_history = []
        for row in self.cycle_time_history:
            filled_row = {k: row.get(k, None) for k in all_keys}
            filled_history.append(filled_row)
        
        # Determine column order
        col_order = ['full_cycle', 'customer_node1_cycle']
        for i in range(1, self.num_nodes):
            col_order.append(f'node_{i}_to_node_{i+1}_cycle')
        # Add any other columns at the end
        for k in all_keys:
            if k not in col_order:
                col_order.append(k)
        df = pd.DataFrame(filled_history)
        # Only keep columns that exist in the DataFrame
        col_order = [c for c in col_order if c in df.columns]
        return df[col_order]