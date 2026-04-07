from datetime import date, timedelta
from src.models.state import SimulationState
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter
from collections import defaultdict
import math
import uuid

def create_customer_orders(state: SimulationState, current_date: date, demand_loader: DemandLoader, exporter: Exporter):
    """
    Step 2: Customer Order Creation (MONDAY ONLY).
    Aggregate weekly demand (Mon-Sun).
    Write CustomerOrderHeader and CustomerOrderLine.
    """
    # Assuming current_date is Monday
    start_date = current_date
    
    order_id_prefix = f"CUST_ORD_{start_date.strftime('%Y%m%d')}"
    
    for store in state.stores.values():
        order_id = f"{order_id_prefix}_{store.store_code}"
        
        # Write header
        exporter.record_customer_order_header(order_id, start_date, store.store_code)
        
        has_lines = False
        for item in state.items.values():
            weekly_demand = sum(
                demand_loader.get_demand(store.store_code, item.item_code, start_date + timedelta(days=d))
                for d in range(7)
            )
            
            if weekly_demand > 0:
                has_lines = True
                exporter.record_customer_order_line(order_id, item.item_code, weekly_demand)

def compute_store_needs(state: SimulationState, current_date: date, demand_loader: DemandLoader, coverage_days: int = 14) -> dict:
    """
    Step 3: Compute Store Replenishment Need (DAILY).
    avg_daily = moving average of last 28 days demand
    target = avg_daily * coverage_days
    need = max(0, target - on_hand[store, item])
    Returns: dict[(store_code, item_code)] -> int
    """
    needs = {}
    
    for store in state.stores.values():
        for item in state.items.values():
            # Calculate 28-day moving average
            total_past_demand = sum(
                demand_loader.get_demand(store.store_code, item.item_code, current_date - timedelta(days=d))
                for d in range(1, 29)
            )
            avg_daily = total_past_demand / 28.0
            
            target = avg_daily * coverage_days
            on_hand = state.on_hand_store.get((store.store_code, item.item_code), 0)
            
            # Need is rounded to int
            need = int(max(0, target - on_hand))
            needs[(store.store_code, item.item_code)] = need
            
    return needs

def create_supplier_orders(state: SimulationState, current_date: date, demand_loader: DemandLoader, exporter: Exporter, dc_coverage_days: int = 21):
    """
    Step 8: DC Supplier Ordering (MONDAY ONLY).
    target - (on_hand + on_order)
    raw_order_qty rounded up to CasePackSize
    """
    from src.models.state import ReceiptEvent
    
    order_id_prefix = f"SUP_ORD_{current_date.strftime('%Y%m%d')}"
    
    for dc in state.dcs.values():
        for sup in state.suppliers.values():
            # Check if this supplier has items
            sup_items = [i for i in state.items.values() if state.item_supplier[i.item_code] == sup.supplier_code]
            if not sup_items:
                continue
                
            order_id = f"{order_id_prefix}_{dc.dc_code}_{sup.supplier_code}"
            header_written = False
            
            for item in sup_items:
                # DC Target: Calculate avg daily demand for all stores assigned to this DC
                dc_stores = [s for s in state.stores.values() if s.assigned_dc == dc.dc_code]
                
                total_past_demand = 0
                for store in dc_stores:
                    total_past_demand += sum(
                        demand_loader.get_demand(store.store_code, item.item_code, current_date - timedelta(days=d))
                        for d in range(1, 29)
                    )
                
                dc_avg_daily = total_past_demand / 28.0
                dc_target = dc_avg_daily * dc_coverage_days
                
                # Check current state
                on_hand = state.on_hand_dc.get((dc.dc_code, item.item_code), 0)
                on_order = state.on_order_dc_qty.get((dc.dc_code, item.item_code), 0)
                
                raw_order_qty = max(0, dc_target - (on_hand + on_order))
                
                if raw_order_qty > 0:
                    cp = item.case_pack_size
                    # Round up to multiple of case pack
                    order_qty = math.ceil(raw_order_qty / cp) * cp
                    
                    if not header_written:
                        exporter.record_supplier_order_header(order_id, current_date, sup.supplier_code, dc.dc_code)
                        header_written = True
                        
                    # Write line
                    exporter.record_supplier_order_line(order_id, item.item_code, raw_order_qty, order_qty)
                    
                    # Create expected receipt event
                    lead_time = state.supplier_lead_time_days.get(sup.supplier_code, 5)
                    arrival = current_date + timedelta(days=lead_time)
                    
                    state.expected_receipts.append(ReceiptEvent(
                        arrival_date=arrival,
                        item_code=item.item_code,
                        qty=order_qty,
                        supplier_code=sup.supplier_code,
                        dc_code=dc.dc_code
                    ))
                    
                    state.on_order_dc_qty[(dc.dc_code, item.item_code)] += order_qty
