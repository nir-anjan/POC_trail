"""
ordering.py  –  Threshold-based DC → Store replenishment
Triggered DAILY for each (store, item):
  If on_hand_store < min_inventory AND no pending order:
    order_qty = forecast_horizon_days × avg_daily_demand + safety_stock_days × avg_daily
    Create InTransitOrder with lead_time_min–lead_time_max days arrival
    Mark (store, item) as pending

Also creates CustomerOrderHeader/Line (True Demand) weekly on Mondays.
"""
import random
from datetime import date, timedelta
from src.models.state import SimulationState, InTransitOrder
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter


# ────────────────────────────────────────────────────────────────────────────
# Customer Order Creation (True Demand log — Monday only)
# ────────────────────────────────────────────────────────────────────────────
def create_customer_orders(
    state: SimulationState,
    week_start: date,
    demand_loader: DemandLoader,
    exporter: Exporter,
    week_id: str,
):
    for store in state.stores.values():
        order_number = f"CO_{week_id}_{store.store_code}"
        exporter.record_customer_order_header(
            order_number=order_number,
            store_code=store.store_code,
            week_id=week_id,
            order_date=week_start,
        )
        line_num = 1
        for item in state.items.values():
            weekly_demand = sum(
                demand_loader.get_demand(
                    store.store_code, item.item_code, week_start + timedelta(days=d)
                )
                for d in range(7)
            )
            if weekly_demand > 0:
                exporter.record_customer_order_line(
                    order_number=order_number,
                    line_number=line_num,
                    store_code=store.store_code,
                    item_code=item.item_code,
                    week_id=week_id,
                    order_qty=weekly_demand,
                )
                line_num += 1


# ────────────────────────────────────────────────────────────────────────────
# Threshold-based replenishment check (runs EVERY DAY per store/item)
# ────────────────────────────────────────────────────────────────────────────
def check_and_trigger_replenishment(
    state: SimulationState,
    current_date: date,
    demand_loader: DemandLoader,
    exporter: Exporter,
    replenishment_cfg: dict,
    rng: random.Random,
    order_counter: list,      # mutable counter [n] passed from engine
):
    """
    For each (store, item):
      1. Compute avg_daily demand from last 7 days
      2. Compute min_inventory = min_inventory_days × avg_daily
      3. If on_hand < min_inventory AND NOT pending → place order
         order_qty = (forecast_horizon_days + safety_stock_days) × avg_daily
         lead_time = random.randint(lead_time_min, lead_time_max)
         Schedule InTransitOrder(arrival = today + lead_time)
    """
    lt_min        = replenishment_cfg.get("lead_time_min_days",    1)
    lt_max        = replenishment_cfg.get("lead_time_max_days",    2)
    fh_days       = replenishment_cfg.get("forecast_horizon_days", 4)
    ss_days       = replenishment_cfg.get("safety_stock_days",     1)
    min_inv_days  = replenishment_cfg.get("min_inventory_days",    2)
    prevent_dup   = replenishment_cfg.get("prevent_duplicate_orders", True)

    for store in state.stores.values():
        dc_code = store.assigned_dc
        for item in state.items.values():
            key     = (store.store_code, item.item_code)
            on_hand = state.on_hand_store.get(key, 0)

            # ── Compute 7-day rolling avg demand ────────────────────
            past_demand = sum(
                demand_loader.get_demand(
                    store.store_code, item.item_code,
                    current_date - timedelta(days=d)
                )
                for d in range(1, 8)
            )
            avg_daily = past_demand / 7.0

            min_inventory = avg_daily * min_inv_days

            # ── Threshold check ──────────────────────────────────────
            if on_hand >= min_inventory:
                continue
            if prevent_dup and key in state.pending_replenishment:
                continue
            if state.on_hand_dc.get((dc_code, item.item_code), 0) <= 0:
                continue  # DC is dry, nothing to order

            # ── Place order ──────────────────────────────────────────
            order_qty = int((fh_days + ss_days) * avg_daily)
            order_qty = max(order_qty, item.case_pack_size)  # at least 1 case pack

            lead_time    = rng.randint(lt_min, lt_max)
            arrival      = current_date + timedelta(days=lead_time)
            order_counter[0] += 1
            order_id     = f"REPR_{current_date.strftime('%Y%m%d')}_{store.store_code}_{item.item_code}_{order_counter[0]}"

            state.in_transit_orders.append(InTransitOrder(
                order_id    = order_id,
                store_code  = store.store_code,
                dc_code     = dc_code,
                item_code   = item.item_code,
                qty         = order_qty,
                arrival_date= arrival,
            ))
            if prevent_dup:
                state.pending_replenishment.add(key)

            exporter.record_replenishment_order(
                order_id     = order_id,
                store_code   = store.store_code,
                dc_code      = dc_code,
                item_code    = item.item_code,
                order_date   = current_date,
                arrival_date = arrival,
                order_qty    = order_qty,
            )
