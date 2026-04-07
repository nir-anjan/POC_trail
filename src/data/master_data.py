import random
import yaml
from typing import Tuple
from src.models.state import SimulationState, Store, DC, Item, Supplier

def generate_master_data(config_path: str = "config.yaml", seed: int = 42) -> SimulationState:
    random.seed(seed)
    
    # Load constraints from config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    site_count_store = config["site_count_store"]
    site_count_dc = config["site_count_dc"]
    item_count = config["item_count"]
    supplier_count = config["supplier_count"]

    state = SimulationState()
    
    # 1. Create DCs
    dc_codes = [f"DC_{str(i).zfill(2)}" for i in range(1, site_count_dc + 1)]
    for code in dc_codes:
        state.dcs[code] = DC(dc_code=code)
        
    # 2. Create Stores and assign rough equally mapping
    for i in range(1, site_count_store + 1):
        store_code = f"Store_{str(i).zfill(3)}"
        assigned_dc = dc_codes[i % site_count_dc]
        state.stores[store_code] = Store(store_code=store_code, assigned_dc=assigned_dc)
        
    # 3. Create Suppliers
    for i in range(1, supplier_count + 1):
        sup_code = f"SUP_{str(i).zfill(3)}"
        state.suppliers[sup_code] = Supplier(supplier_code=sup_code)
        state.supplier_lead_time_days[sup_code] = random.randint(2, 7)
        state.supplier_items[sup_code] = []
        
    # 4. Create Items
    supplier_list = list(state.suppliers.keys())
    for i in range(1, item_count + 1):
        item_code = f"ITEM_{str(i).zfill(4)}"
        case_pack = random.choice([6, 12, 24, 48, 100])
        state.items[item_code] = Item(item_code=item_code, case_pack_size=case_pack)
        
        # Distribute items uniformly across suppliers
        sup = supplier_list[i % len(supplier_list)]
        state.item_supplier[item_code] = sup
        state.supplier_items[sup].append(item_code)
        
    # Initialize all inventory limits
    for s_code in state.stores:
        for i_code in state.items:
            state.on_hand_store[(s_code, i_code)] = 0
            
    for d_code in state.dcs:
        for i_code in state.items:
            state.on_hand_dc[(d_code, i_code)] = 0
            state.on_order_dc_qty[(d_code, i_code)] = 0
            
    # VALIDATION CHECKS
    if len(state.stores) != 25:
        raise ValueError(f"Expected 25 stores, but generated {len(state.stores)}")
    if len(state.items) != 200:
        raise ValueError(f"Expected 200 items, but generated {len(state.items)}")
    if len(state.suppliers) != 15:
        raise ValueError(f"Expected 15 suppliers, but generated {len(state.suppliers)}")
    if len(state.dcs) != 2:
        raise ValueError(f"Expected 2 DCs, but generated {len(state.dcs)}")
            
    return state
