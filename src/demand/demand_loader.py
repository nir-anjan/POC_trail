import csv
from collections import defaultdict
from datetime import datetime, date

class DemandLoader:
    def __init__(self, state):
        self.state = state
        self.requested_qty = defaultdict(int) # (store, item, date) -> int
        
    def load(self, filepath: str):
        print(f"Loading demand from {filepath}...")
        valid_stores = set(self.state.stores.keys())
        valid_items = set(self.state.items.keys())
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                store = row['StoreCode']
                item = row['ItemCode']
                date_str = row['Date']
                qty = int(row['DemandQty'])
                
                if store not in valid_stores:
                    raise ValueError(f"Invalid StoreCode in demand: {store}")
                if item not in valid_items:
                    raise ValueError(f"Invalid ItemCode in demand: {item}")
                
                # Parse date
                dt = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                self.requested_qty[(store, item, dt)] += qty
                
        print("Demand loaded and validated successfully.")
        return self.requested_qty

    def get_demand(self, store: str, item: str, date_obj: date) -> int:
        return self.requested_qty.get((store, item, date_obj), 0)
