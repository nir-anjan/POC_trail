"""
state.py  –  Data models for the simulation
Now includes in_transit_orders tracking for threshold-based DC→Store replenishment.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import datetime


@dataclass
class Item:
    item_code: str
    case_pack_size: int
    category: str = "Uncategorized"
    velocity_class: str = "medium"
    lifecycle_profile: str = "steady"
    size_group: Optional[str] = None
    size_rank: Optional[str] = None
    unit_cost: float = 10.0


@dataclass
class Store:
    store_code: str
    assigned_dc: str
    site_type: str = "STORE"


@dataclass
class DC:
    dc_code: str
    site_type: str = "DC"


@dataclass
class Supplier:
    supplier_code: str
    supplier_name: str = ""
    category: str = "Uncategorized"


@dataclass
class InTransitOrder:
    """Tracks a DC→Store replenishment order in flight."""
    order_id: str
    store_code: str
    dc_code: str
    item_code: str
    qty: int
    arrival_date: datetime.date


# ReceiptEvent kept for any supplier-level future use
@dataclass
class ReceiptEvent:
    arrival_date: datetime.date
    item_code: str
    qty: int
    supplier_code: str
    dc_code: str
    purchase_order_number: str
    line_number: int


@dataclass
class SimulationState:
    stores: Dict[str, Store]           = field(default_factory=dict)
    dcs: Dict[str, DC]                 = field(default_factory=dict)
    items: Dict[str, Item]             = field(default_factory=dict)
    suppliers: Dict[str, Supplier]     = field(default_factory=dict)

    supplier_items: Dict[str, List[str]]   = field(default_factory=dict)
    item_supplier: Dict[str, str]          = field(default_factory=dict)
    supplier_lead_time_days: Dict[str, int]= field(default_factory=dict)

    # Daily inventory state
    on_hand_store: Dict[Tuple[str, str], int] = field(default_factory=dict)
    on_hand_dc:    Dict[Tuple[str, str], int] = field(default_factory=dict)

    # In-transit DC → Store orders (threshold-based replenishment)
    in_transit_orders: List[InTransitOrder]   = field(default_factory=list)

    # Pending order flag: set[(store_code, item_code)] → prevents duplicate orders
    pending_replenishment: set = field(default_factory=set)

    # Kept for future supplier upstream use
    on_order_dc_qty: Dict[Tuple[str, str], int] = field(default_factory=dict)
    expected_receipts: List[ReceiptEvent]        = field(default_factory=list)
