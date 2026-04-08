import yaml
import csv
import random
from datetime import datetime, timedelta
import os

def load_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def get_weekly_seasonality_factor(date, config, rng):
    # Day name in lowercase to match yaml keys (monday, tuesday, etc.)
    day_name = date.strftime('%A').lower()
    weekly_cfg = config.get('weekly_seasonality', {})
    return weekly_cfg.get(day_name, 1.0)

def get_annual_seasonality_factor(date, config):
    # ISO week number (1-52/53)
    _, week_num, _ = date.isocalendar()
    annual_cfg = config.get('annual_seasonality', {})
    weeks_map = annual_cfg.get('weeks', {})
    # Return the factor for the week, default to 1.0
    return weeks_map.get(week_num, 1.0)

def get_noise(config, rng):
    noise_cfg = config.get('noise', {})
    min_val = noise_cfg.get('min', 1.0)
    max_val = noise_cfg.get('max', 1.0)
    return rng.uniform(min_val, max_val)

def generate_demand(config, start_date, end_date, num_stores, output_file):
    products = config.get('products', {})
    promotions = config.get('promotions', {})
    promo_multiplier = promotions.get('default_multiplier', 1.0)
    
    stores = [f"Store_{i:03d}" for i in range(1, num_stores + 1)]
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['Date', 'StoreCode', 'ItemCode', 'DemandQty']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Pre-calculate factors that are the same for all products on this day
            annual_fact = get_annual_seasonality_factor(current_date, config)
            
            for store in stores:
                for product_id, product_data in products.items():
                    avg_daily_velocity = product_data.get('avg_daily_velocity', 0)
                    
                    # Deterministic Seeding: Seed per row for reproducibility
                    seed_str = f"{date_str}_{store}_{product_id}"
                    rng = random.Random(seed_str)
                    
                    weekly_fact = get_weekly_seasonality_factor(current_date, config, rng)
                    noise_val = get_noise(config, rng)
                    
                    # Final Formula as requested:
                    # final_demand = avg_daily_velocity * annual_seasonality[week] * weekly_seasonality[day] * noise * promotions
                    final_demand = round(
                        avg_daily_velocity * 
                        annual_fact * 
                        weekly_fact * 
                        noise_val * 
                        promo_multiplier
                    )
                    
                    writer.writerow({
                        'Date': date_str,
                        'StoreCode': store,
                        'ItemCode': product_id,
                        'DemandQty': final_demand
                    })
            
            current_date += timedelta(days=1)

if __name__ == "__main__":
    # ── Projects Paths
    CONFIG_PATH = 'demand_snacks.yaml'
    OUTPUT_PATH = 'demand.csv'
    
    # ── Load Project Master Config
    with open('config.yaml') as f:
        master_cfg = yaml.safe_load(f)
    
    config = load_config(CONFIG_PATH)
    
    # ── Simulation range derived from config.yaml
    start_str = master_cfg.get("start_date", "2024-01-01")
    sim_days  = master_cfg.get("simulation_days", 70)
    
    START_DATE = datetime.strptime(start_str, "%Y-%m-%d")
    END_DATE   = START_DATE + timedelta(days=sim_days - 1)
    
    NUM_STORES = master_cfg.get("site_count_store", 10) 
    
    print(f"Generating demand for {START_DATE.date()} to {END_DATE.date()}...")
    generate_demand(config, START_DATE, END_DATE, NUM_STORES, OUTPUT_PATH)
    print(f"Demand generated and saved to {OUTPUT_PATH}")