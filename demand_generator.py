"""
demand_generator.py
Generates synthetic demand.csv for the specified number of days.
Usage: python3 demand_generator.py
"""
import csv
import random
from datetime import date, timedelta

from src.data.master_data import generate_master_data


def generate_demand_csv(
    filename: str,
    start_date: date,
    days: int = 70,
    seed: int = 42,
):
    random.seed(seed)
    state  = generate_master_data(seed=seed)
    stores = list(state.stores.keys())
    items  = list(state.items.keys())

    # ONLY the first item as specified earlier
    single_item = items[0]

    # Base demand per store: between 10–50 units/day
    base_rates = {s: random.randint(10, 50) for s in stores}

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "StoreCode", "ItemCode", "DemandQty"])

        for d in range(days):
            current_date = start_date + timedelta(days=d)
            date_str     = current_date.strftime("%Y-%m-%d")

            # Saturday/Sunday bump
            is_weekend = current_date.weekday() >= 5
            weekend_mult = 1.5 if is_weekend else 1.0

            for s in stores:
                base = base_rates[s] * weekend_mult
                
                # High base noise (e.g. ±50%)
                noise = random.randint(int(-base * 0.5), int(base * 0.7))
                
                # Random "Promo" Spike (10% chance)
                spike_mult = 1.0
                if random.random() < 0.10:
                    spike_mult = random.uniform(2.5, 5.0)
                
                # Random "Lull" (5% chance)
                if random.random() < 0.05:
                    qty = 0
                else:
                    qty = int(max(0, (base + noise) * spike_mult))

                if qty >= 0:
                    writer.writerow([date_str, s, single_item, qty])

    total_rows = sum(1 for _ in open(filename)) - 1
    print(f"Generated {filename}: {total_rows:,} rows | {days} days | {len(stores)} stores")


if __name__ == "__main__":
    start = date(2024, 1, 1)
    generate_demand_csv("demand.csv", start, days=70)
