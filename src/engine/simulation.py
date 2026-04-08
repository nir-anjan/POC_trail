"""
simulation.py  –  Main orchestrator (DC → Store flow only)
Daily loop:
  Every day  : process_dc_store_receipts → fulfill_daily_demand → check_and_trigger_replenishment
  Every Monday: create_customer_orders (True Demand log)
  Every Sunday: process_weekly_aggregates (CSV flush + inventory snapshot)
"""
import random
from datetime import date, timedelta

from src.models.state import SimulationState
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter
from src.engine.receipts import process_dc_store_receipts
from src.engine.fulfillment import fulfill_daily_demand
from src.engine.ordering import (
    create_customer_orders,
    check_and_trigger_replenishment,
)


class SimulationEngine:
    def __init__(
        self,
        state: SimulationState,
        demand_loader: DemandLoader,
        exporter: Exporter,
        config: dict,
    ):
        self.state         = state
        self.demand_loader = demand_loader
        self.exporter      = exporter
        self.config        = config
        self.rng           = random.Random(config.get("seed", 42))

    # ------------------------------------------------------------------ #
    # Inventory seeding from config
    # ------------------------------------------------------------------ #
    def _initialize_inventory(self, start_date: date):
        store_stock = self.config.get("store_initial_stock", 100)
        dc_stock    = self.config.get("dc_initial_stock",   4000)

        print(f"  Seeding stores: {store_stock} units each …")
        for store in self.state.stores.values():
            for item in self.state.items.values():
                self.state.on_hand_store[(store.store_code, item.item_code)] = store_stock

        print(f"  Seeding DCs: {dc_stock} units each …")
        for dc in self.state.dcs.values():
            for item in self.state.items.values():
                self.state.on_hand_dc[(dc.dc_code, item.item_code)] = dc_stock

    # ------------------------------------------------------------------ #
    # Main run loop
    # ------------------------------------------------------------------ #
    def run(self, start_date: date, days: int):
        print(f"\nStarting simulation: {start_date}  →  {days} days ({days // 7} weeks)")
        self._initialize_inventory(start_date)

        replenishment_cfg = {
            **self.config.get("replenishment", {}),
            **self.config.get("replenishment_defaults", {}),
        }

        order_counter = [0]   # mutable counter for unique order IDs
        current_date  = start_date

        for day_idx in range(days):
            weekday  = current_date.weekday()           # 0=Mon … 6=Sun
            iso      = current_date.isocalendar()
            week_id  = f"{iso.year}-W{iso.week:02d}"

            print(f"  Day {day_idx + 1:>2}/{days}  {current_date}  ({week_id})", end="")

            # ── Step 1: Deliver in-transit DC→Store orders ───────────
            process_dc_store_receipts(self.state, current_date, self.exporter)

            # ── Step 2: Fulfill daily customer demand ────────────────
            fulfill_daily_demand(
                self.state, current_date, self.demand_loader, self.exporter
            )

            # ── Step 3: Threshold-based replenishment check ──────────
            check_and_trigger_replenishment(
                self.state, current_date, self.demand_loader, self.exporter,
                replenishment_cfg, self.rng, order_counter,
            )

            # ── Step 4 (Monday): Log True Demand as Customer Orders ──
            if weekday == 0:
                create_customer_orders(
                    self.state, current_date, self.demand_loader,
                    self.exporter, week_id,
                )

            # ── Step 5 (Sunday): Weekly CSV flush ───────────────────
            if weekday == 6:
                self.exporter.process_weekly_aggregates(
                    self.state, current_date, week_id
                )
                in_transit = len(self.state.in_transit_orders)
                print(f"  ← weekly flush | in-transit orders: {in_transit}", end="")

            print()
            current_date += timedelta(days=1)

        # If simulation doesn't end on Sunday, flush remaining aggregates
        if (current_date - timedelta(days=1)).weekday() != 6:
            iso     = (current_date - timedelta(days=1)).isocalendar()
            week_id = f"{iso.year}-W{iso.week:02d}"
            self.exporter.process_weekly_aggregates(
                self.state, current_date - timedelta(days=1), week_id
            )

        print(f"\nSimulation complete. Total replenishment orders: {order_counter[0]}\n")
