import argparse
from datetime import date
from src.data.master_data import generate_master_data
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter
from src.engine.simulation import SimulationEngine

def main():
    parser = argparse.ArgumentParser(description="Supply Chain Simulation Engine")
    parser.add_argument("--config", type=str, help="Path to config.yaml (not fully implemented, using synthetic data)", default="config.yaml")
    parser.add_argument("--demand_file", type=str, help="Path to demand.csv", required=True)
    parser.add_argument("--output_dir", type=str, help="Directory to save output CSVs", default="outputs")
    parser.add_argument("--days", type=int, help="Number of days to simulate", default=364)
    parser.add_argument("--start_date", type=str, help="Start date (YYYY-MM-DD)", default="2024-01-01")
    
    args = parser.parse_args()
    
    # 1. Load State / Master Data
    print("Loading Master Data...")
    state = generate_master_data(config_path=args.config, seed=42)
    
    # 2. Demand Loader
    demand_loader = DemandLoader(state)
    demand_loader.load(args.demand_file)
    
    # 3. Setup Exporter
    exporter = Exporter(args.output_dir)
    
    # 4. Initialize and run Engine
    engine = SimulationEngine(state, demand_loader, exporter)
    
    start_dt = date.fromisoformat(args.start_date)
    
    # Run
    engine.run(start_date=start_dt, days=args.days)
    
    # Close resources
    exporter.close()
    
    print(f"Simulation outputs written to '{args.output_dir}' directory.")

if __name__ == "__main__":
    main()
