"""
fulfillment.py  –  Daily sales computation (DC → Store flow only)
  sales[t]     = min(demand[t], on_hand_store[t])
  unmet[t]     = demand[t] - sales[t]
  inventory[t] = on_hand_store[t] - sales[t]   (never negative)
"""
from datetime import date
from src.models.state import SimulationState
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter


def fulfill_daily_demand(
    state: SimulationState,
    current_date: date,
    demand_loader: DemandLoader,
    exporter: Exporter,
):
    """
    For every (store, item) with positive demand today:
      - Compute constrained sales
      - Update store inventory
      - Accumulate for weekly CSV flush
    """
    for store in state.stores.values():
        for item in state.items.values():
            demand = demand_loader.get_demand(
                store.store_code, item.item_code, current_date
            )
            if demand <= 0:
                continue

            on_hand = state.on_hand_store.get((store.store_code, item.item_code), 0)

            # CRITICAL: sales constrained by physical inventory
            sales = min(demand, on_hand)
            unmet = demand - sales          # stockout signal

            # Update inventory — never goes negative
            state.on_hand_store[(store.store_code, item.item_code)] = on_hand - sales

            # Accumulate for Sunday weekly flush
            exporter.accumulate_daily_fulfillment(
                store_code=store.store_code,
                item_code=item.item_code,
                req_qty=demand,
                delivered=sales,
                unit_cost=item.unit_cost,
            )
