import csv
import random
from datetime import date, timedelta
from src.data.master_data import generate_master_data

def generate_demand_csv(filename: str, start_date: date, days: int = 364, seed: int = 42):
    random.seed(seed)
    
    # Get the master data
    state = generate_master_data(seed=seed)
    stores = list(state.stores.keys())
    items = list(state.items.keys())
    
    # ONLY grab the first item as requested
    single_item = items[0]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'StoreCode', 'ItemCode', 'DemandQty'])
        
        base_rates = {}
        for s in stores:
            # Random base rate between 10 and 50 for the single item
            base_rates[(s, single_item)] = random.randint(10, 50)

        for d in range(days):
            current_date = start_date + timedelta(days=d)
            date_str = current_date.strftime('%Y-%m-%d')
            
            for s in stores:
                base = base_rates[(s, single_item)]
                # Add some daily noise
                noise = random.randint(int(-base * 0.2), int(base * 0.5))
                qty = max(0, base + noise)
                
                if qty > 0:
                    writer.writerow([date_str, s, single_item, qty])

if __name__ == "__main__":
    print("Generating synthetic demand.csv...")
    start = date(2024, 1, 1)
    generate_demand_csv("demand.csv", start, days=364)
    print("Done generating demand.csv")
