from datetime import date
from src.models.state import SimulationState
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter
from collections import defaultdict

def allocate_and_fulfill(state: SimulationState, current_date: date, needs: dict, demand_loader: DemandLoader, exporter: Exporter):
    """
    Step 4: DC -> Store Allocation
    Step 5: Fulfillment
    """
    
    # --- STEP 4: Allocation ---
    # Need to group needs by (DC, Item)
    dc_item_requests = defaultdict(list)
    for (store_code, item_code), need in needs.items():
        if need > 0:
            store = state.stores[store_code]
            dc_code = store.assigned_dc
            dc_item_requests[(dc_code, item_code)].append((store_code, need))
            
    # Process allocations
    for (dc_code, item_code), requests in dc_item_requests.items():
        total_need = sum(req[1] for req in requests)
        available = state.on_hand_dc.get((dc_code, item_code), 0)
        
        if total_need <= available:
            # Full allocation
            for store_code, need in requests:
                state.on_hand_dc[(dc_code, item_code)] -= need
                state.on_hand_store[(store_code, item_code)] += need
        else:
            # Proportional allocation
            # Calculate proportion and round down, allocate remainder fairly if needed (or just leave unallocated)
            remaining_available = available
            allocated = {}
            for store_code, need in requests:
                proportion = need / total_need
                alloc_qty = int(available * proportion)
                allocated[store_code] = alloc_qty
                remaining_available -= alloc_qty
                
            # Distribute any remaining due to rounding
            # Sort by highest need to break ties
            requests_sorted = sorted(requests, key=lambda x: x[1], reverse=True)
            idx = 0
            while remaining_available > 0 and idx < len(requests_sorted):
                store_code = requests_sorted[idx][0]
                allocated[store_code] += 1
                remaining_available -= 1
                idx += 1
                
            # Actually apply allocations
            for store_code, alloc_qty in allocated.items():
                if alloc_qty > 0:
                    state.on_hand_dc[(dc_code, item_code)] -= alloc_qty
                    state.on_hand_store[(store_code, item_code)] += alloc_qty
                    
    # --- STEP 5: Fulfillment ---
    for store in state.stores.values():
        for item in state.items.values():
            req_qty = demand_loader.get_demand(store.store_code, item.item_code, current_date)
            
            if req_qty > 0:
                on_hand = state.on_hand_store.get((store.store_code, item.item_code), 0)
                delivered = min(req_qty, on_hand)
                
                # Deduct from store inventory
                state.on_hand_store[(store.store_code, item.item_code)] -= delivered
                
                # Record to exporter for Sunday aggregation
                exporter.accumulate_daily_fulfillment(current_date, store.store_code, item.item_code, req_qty, delivered)
