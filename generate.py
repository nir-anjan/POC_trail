"""
generate.py  –  CLI entry point
Usage:
  python3 generate.py --demand_file demand.csv
  python3 generate.py --demand_file demand.csv --config config.yaml --output_dir outputs
"""
import argparse
from datetime import date

import yaml

from src.data.master_data import generate_master_data, write_master_csvs
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter
from src.engine.simulation import SimulationEngine


def main():
    parser = argparse.ArgumentParser(description="Supply Chain Simulation Engine")
    parser.add_argument("--config",      default="config.yaml",  help="Path to config.yaml")
    parser.add_argument("--demand_file", required=True,          help="Path to demand.csv")
    parser.add_argument("--output_dir",  default="outputs",      help="Output directory")
    parser.add_argument("--start_date",  default="2024-01-01",   help="Simulation start (YYYY-MM-DD)")
    args = parser.parse_args()

    # 1. Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)
    config["start_date"] = args.start_date

    seed       = config.get("seed", 42)
    sim_days   = config.get("simulation_days", 70)
    start_date = date.fromisoformat(args.start_date)

    print("=" * 60)
    print("  Supply Chain Simulation Engine  (DC → Store)")
    print(f"  Config  : {args.config}")
    print(f"  Demand  : {args.demand_file}")
    print(f"  Period  : {start_date}  +{sim_days} days ({sim_days // 7} weeks)")
    print("=" * 60)

    # 2. Master data
    print("\n[1/5] Generating master data …")
    state = generate_master_data(config_path=args.config, seed=seed)

    # 3. Demand
    print("\n[2/5] Loading demand …")
    demand_loader = DemandLoader(state)
    demand_loader.load(args.demand_file)

    # 4. Exporter + master CSVs
    print("\n[3/5] Initialising outputs …")
    exporter = Exporter(args.output_dir)
    write_master_csvs(state, args.output_dir, config)

    # 5. Run engine
    print("\n[4/5] Running simulation …")
    engine = SimulationEngine(state, demand_loader, exporter, config)
    engine.run(start_date=start_date, days=sim_days)

    # 6. Close
    print("[5/5] Flushing outputs …")
    exporter.close()

    print(f"\n✅  Done. CSVs written to '{args.output_dir}/'")
    print("=" * 60)


if __name__ == "__main__":
    main()
