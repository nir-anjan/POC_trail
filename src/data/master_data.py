"""
master_data.py
Generates deterministic master data from config.yaml counts.
Also writes 6 static reference CSVs to outputs/master/ using pandas.
"""
import random
import os
from datetime import date, timedelta

import pandas as pd
import yaml

from src.models.state import SimulationState, Store, DC, Item, Supplier

# ── Category / lifecycle pools ─────────────────────────────────────────────
CATEGORIES       = ["Snacks", "Beverages", "Dairy", "Frozen", "Household", "Personal Care"]
VELOCITY_CLASSES = ["fast", "medium", "slow", "lumpy"]
LIFECYCLES       = ["steady", "growth", "decay", "new_item"]
SIZE_GROUPS      = ["Small", "Medium", "Large", None]


def generate_master_data(config_path: str = "config.yaml", seed: int = 42) -> SimulationState:
    random.seed(seed)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    n_stores    = cfg["site_count_store"]
    n_dcs       = cfg["site_count_dc"]
    n_items     = cfg["item_count"]
    n_suppliers = cfg["supplier_count"]

    state = SimulationState()

    # 1. DCs
    dc_codes = [f"DC_{str(i).zfill(2)}" for i in range(1, n_dcs + 1)]
    for code in dc_codes:
        state.dcs[code] = DC(dc_code=code)

    # 2. Stores
    for i in range(1, n_stores + 1):
        code = f"Store_{str(i).zfill(3)}"
        dc   = dc_codes[i % n_dcs]
        state.stores[code] = Store(store_code=code, assigned_dc=dc)

    # 3. Suppliers
    for i in range(1, n_suppliers + 1):
        code = f"SUP_{str(i).zfill(3)}"
        cat  = random.choice(CATEGORIES)
        state.suppliers[code] = Supplier(
            supplier_code=code,
            supplier_name=f"Supplier {i}",
            category=cat,
        )
        state.supplier_lead_time_days[code] = random.randint(14, 49)  # 2–7 weeks
        state.supplier_items[code] = []

    # 4. Items — load from demand_snacks.yaml if available, else generic
    snacks_path = "demand_snacks.yaml"
    if os.path.exists(snacks_path):
        with open(snacks_path) as f:
            snacks_cfg = yaml.safe_load(f)
        product_list = list(snacks_cfg.get("products", {}).keys())
        print(f"  Found {len(product_list)} items in snacks config.")
    else:
        product_list = [f"ITEM_{str(i).zfill(4)}" for i in range(1, n_items + 1)]

    sup_list = list(state.suppliers.keys())
    for i, code in enumerate(product_list):
        case_pack  = random.choice([6, 12, 24, 48, 100])
        category   = random.choice(CATEGORIES)
        velocity   = random.choice(VELOCITY_CLASSES)
        lifecycle  = random.choice(LIFECYCLES)
        sg         = random.choice(SIZE_GROUPS)
        unit_cost  = round(random.uniform(0.5, 50.0), 2)

        state.items[code] = Item(
            item_code       = code,
            case_pack_size  = case_pack,
            category        = category,
            velocity_class  = velocity,
            lifecycle_profile= lifecycle,
            size_group      = sg,
            size_rank       = str(random.randint(1, 5)) if sg else None,
            unit_cost       = unit_cost,
        )
        sup = sup_list[i % len(sup_list)]
        state.item_supplier[code] = sup
        state.supplier_items[sup].append(code)

    # Align item_count with what we actually loaded
    state_item_count = len(state.items)

    # 5. Initialise all inventory to 0 (seeded later by SimulationEngine)
    for s in state.stores:
        for it in state.items:
            state.on_hand_store[(s, it)]   = 0
    for dc in state.dcs:
        for it in state.items:
            state.on_hand_dc[(dc, it)]     = 0
            state.on_order_dc_qty[(dc, it)]= 0

    # 6. Validation
    assert len(state.stores)    == n_stores,    f"Expected {n_stores} stores, got {len(state.stores)}"
    assert len(state.items)     == state_item_count, f"Expected {state_item_count} items, got {len(state.items)}"
    assert len(state.dcs)       == n_dcs,       f"Expected {n_dcs} DCs, got {len(state.dcs)}"

    return state


def write_master_csvs(state: SimulationState, output_dir: str, config: dict):
    """Write 6 static reference tables to outputs/master/ using pandas."""
    master_dir = os.path.join(output_dir, "master")
    os.makedirs(master_dir, exist_ok=True)

    # ── SiteInformation ──────────────────────────────────────────────
    site_rows = []
    for s in state.stores.values():
        site_rows.append({"SiteCode": s.store_code, "SiteType": "STORE", "ParentDC": s.assigned_dc})
    for dc in state.dcs.values():
        site_rows.append({"SiteCode": dc.dc_code, "SiteType": "DC", "ParentDC": None})
    pd.DataFrame(site_rows).to_csv(os.path.join(master_dir, "SiteInformation.csv"), index=False)

    # ── ItemInformation ───────────────────────────────────────────────
    item_rows = [
        {
            "ItemCode":        it.item_code,
            "Category":        it.category,
            "VelocityClass":   it.velocity_class,
            "LifecycleProfile":it.lifecycle_profile,
            "CasePackSize":    it.case_pack_size,
            "SizeGroup":       it.size_group,
            "SizeRank":        it.size_rank,
            "UnitCost":        it.unit_cost,
        }
        for it in state.items.values()
    ]
    pd.DataFrame(item_rows).to_csv(os.path.join(master_dir, "ItemInformation.csv"), index=False)

    # ── SupplierInformation ───────────────────────────────────────────
    sup_rows = [
        {"SupplierCode": s.supplier_code, "SupplierName": s.supplier_name, "Category": s.category}
        for s in state.suppliers.values()
    ]
    pd.DataFrame(sup_rows).to_csv(os.path.join(master_dir, "SupplierInformation.csv"), index=False)

    # ── CalendarPeriod ────────────────────────────────────────────────
    sim_days  = config.get("simulation_days", 364)
    start_str = config.get("start_date", "2024-01-01")
    start_dt  = date.fromisoformat(start_str)
    cal_rows  = []
    for d in range(sim_days):
        cd = start_dt + timedelta(days=d)
        iso = cd.isocalendar()
        cal_rows.append({
            "CalendarDate":  cd.strftime("%Y-%m-%d"),
            "WeekId":        f"{iso.year}-W{iso.week:02d}",
            "WeekStartDate": (cd - timedelta(days=cd.weekday())).strftime("%Y-%m-%d"),
            "MonthId":       cd.strftime("%Y-%m"),
            "QuarterId":     f"{cd.year}-Q{(cd.month - 1) // 3 + 1}",
            "YearId":        cd.year,
            "DayOfWeek":     cd.strftime("%A"),
            "IsWeekend":     cd.weekday() >= 5,
        })
    pd.DataFrame(cal_rows).to_csv(os.path.join(master_dir, "CalendarPeriod.csv"), index=False)

    # ── Currency ─────────────────────────────────────────────────────
    pd.DataFrame([
        {"CurrencyCode": "USD", "CurrencyName": "US Dollar", "ExchangeRate": 1.0},
        {"CurrencyCode": "INR", "CurrencyName": "Indian Rupee", "ExchangeRate": 83.5},
    ]).to_csv(os.path.join(master_dir, "Currency.csv"), index=False)

    # ── PromoEvents (empty scaffold) ─────────────────────────────────
    pd.DataFrame(columns=[
        "PromoEventId", "ItemCode", "SiteCode", "EventType",
        "PromoStartDate", "PromoEndDate", "DemandMultiplier",
        "PostPromoDecayDays", "PostPromoDecayShape", "Category",
    ]).to_csv(os.path.join(master_dir, "PromoEvents.csv"), index=False)

    print(f"  Master CSVs written to {master_dir}/")
