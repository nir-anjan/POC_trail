"""
receipts.py  –  Daily in-transit order delivery (DC → Store)
Processes InTransitOrders that are due today:
  - Updates on_hand_store
  - Decrements on_hand_dc
  - Clears the pending_replenishment flag so new orders can be triggered
"""
from datetime import date
from src.models.state import SimulationState
from src.utils.exporter import Exporter


def process_dc_store_receipts(
    state: SimulationState,
    current_date: date,
    exporter: Exporter,
):
    """
    Deliver any in-transit DC→Store orders due today.
    Inventory update: on_hand_store += qty; on_hand_dc -= qty
    """
    remaining = []

    for order in state.in_transit_orders:
        if order.arrival_date > current_date:
            remaining.append(order)
            continue

        # Deliver to store
        qty_available = state.on_hand_dc.get((order.dc_code, order.item_code), 0)
        actual_qty    = min(order.qty, qty_available)   # DC might have less now

        if actual_qty > 0:
            state.on_hand_store[(order.store_code, order.item_code)] = (
                state.on_hand_store.get((order.store_code, order.item_code), 0)
                + actual_qty
            )
            state.on_hand_dc[(order.dc_code, order.item_code)] = (
                qty_available - actual_qty
            )

        # Clear pending flag so next threshold check can re-order
        state.pending_replenishment.discard((order.store_code, order.item_code))

        # Write receipt to exporter
        exporter.record_dc_store_receipt(
            order_id    = order.order_id,
            store_code  = order.store_code,
            dc_code     = order.dc_code,
            item_code   = order.item_code,
            receipt_date= current_date,
            qty         = actual_qty,
        )

    state.in_transit_orders = remaining
