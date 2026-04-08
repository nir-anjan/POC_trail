"""
exporter.py
Writes all simulation output CSVs with spec-aligned schemas.
Adds ReplenishmentOrders.csv and DCStoreReceipts.csv for the DC→Store flow.
"""
import csv
import os
import pandas as pd
from collections import defaultdict
from datetime import date

from src.models.state import SimulationState


class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self._files:   dict = {}
        self._writers: dict = {}

        # Weekly accumulator: (store_code, item_code) → [req, delivered, sales_amount]
        self._weekly: dict = defaultdict(lambda: [0, 0, 0.0])

        self._init_files()

    # ------------------------------------------------------------------ #
    def _init_files(self):
        self._open("CustomerOrderHeader.csv",
                   ["CustomerOrderNumber", "StoreCode", "WeekId", "OrderDate"])
        self._open("CustomerOrderLine.csv",
                   ["CustomerOrderNumber", "LineNumber", "StoreCode",
                    "ItemCode", "WeekId", "OrderQuantity"])
        self._open("CustomerOrderDelivery.csv",
                   ["CustomerOrderNumber", "LineNumber", "StoreCode", "ItemCode",
                    "WeekId", "DeliveredQuantity", "UnfilledQuantity", "DeliveryStatus"])
        self._open("SalesHistoryInformation.csv",
                   ["StoreCode", "ItemCode", "WeekId",
                    "SalesQuantity", "SalesAmount"])
        self._open("InventoryInformation.csv",
                   ["SiteCode", "ItemCode", "InventoryDate",
                    "QuantityOnHand", "OnOrderQty", "InventoryStatus"])
        # DC → Store specific outputs
        self._open("ReplenishmentOrders.csv",
                   ["OrderId", "StoreCode", "DCCode", "ItemCode",
                    "OrderDate", "ExpectedArrivalDate", "OrderQuantity"])
        self._open("DCStoreReceipts.csv",
                   ["OrderId", "StoreCode", "DCCode", "ItemCode",
                    "ReceiptDate", "ReceivedQuantity"])

    def _open(self, filename: str, headers: list):
        path   = os.path.join(self.output_dir, filename)
        f      = open(path, "w", newline="")
        writer = csv.writer(f)
        writer.writerow(headers)
        self._files[filename]   = f
        self._writers[filename] = writer

    # ── Customer Orders ──────────────────────────────────────────────
    def record_customer_order_header(
        self, order_number: str, store_code: str, week_id: str, order_date: date
    ):
        self._writers["CustomerOrderHeader.csv"].writerow(
            [order_number, store_code, week_id, order_date.strftime("%Y-%m-%d")]
        )

    def record_customer_order_line(
        self, order_number: str, line_number: int, store_code: str,
        item_code: str, week_id: str, order_qty: int
    ):
        self._writers["CustomerOrderLine.csv"].writerow(
            [order_number, line_number, store_code, item_code, week_id, order_qty]
        )

    # ── Replenishment Orders (DC → Store) ────────────────────────────
    def record_replenishment_order(
        self, order_id: str, store_code: str, dc_code: str, item_code: str,
        order_date: date, arrival_date: date, order_qty: int
    ):
        self._writers["ReplenishmentOrders.csv"].writerow([
            order_id, store_code, dc_code, item_code,
            order_date.strftime("%Y-%m-%d"),
            arrival_date.strftime("%Y-%m-%d"),
            order_qty,
        ])

    def record_dc_store_receipt(
        self, order_id: str, store_code: str, dc_code: str, item_code: str,
        receipt_date: date, qty: int
    ):
        self._writers["DCStoreReceipts.csv"].writerow([
            order_id, store_code, dc_code, item_code,
            receipt_date.strftime("%Y-%m-%d"), qty,
        ])

    # ── Daily accumulation ─────────────────────────────────────────
    def accumulate_daily_fulfillment(
        self, store_code: str, item_code: str,
        req_qty: int, delivered: int, unit_cost: float
    ):
        b = self._weekly[(store_code, item_code)]
        b[0] += req_qty
        b[1] += delivered
        b[2] += delivered * unit_cost

    # ── Weekly flush (Sunday) ────────────────────────────────────────
    def process_weekly_aggregates(
        self, state: SimulationState, week_end_date: date, week_id: str
    ):
        date_str = week_end_date.strftime("%Y-%m-%d")

        # Deliveries + Sales
        for (store_code, item_code), (req, delivered, sales_amt) in self._weekly.items():
            if req <= 0:
                continue
            unfilled = req - delivered
            if delivered == 0:
                status = "ZERO"
            elif delivered < req:
                status = "PARTIAL"
            else:
                status = "FULL"

            order_num = f"CO_{week_id}_{store_code}"
            self._writers["CustomerOrderDelivery.csv"].writerow([
                order_num, 1, store_code, item_code,
                week_id, delivered, unfilled, status,
            ])
            self._writers["SalesHistoryInformation.csv"].writerow([
                store_code, item_code, week_id,
                delivered, round(sales_amt, 2),
            ])

        # Inventory snapshot
        for store in state.stores.values():
            for item in state.items.values():
                qty        = state.on_hand_store.get((store.store_code, item.item_code), 0)
                in_transit = sum(
                    o.qty for o in state.in_transit_orders
                    if o.store_code == store.store_code and o.item_code == item.item_code
                )
                inv_status = "Zero" if qty == 0 else "Low" if qty < 10 else "Available"
                self._writers["InventoryInformation.csv"].writerow([
                    store.store_code, item.item_code, date_str,
                    qty, in_transit, inv_status,
                ])

        for dc in state.dcs.values():
            for item in state.items.values():
                qty = state.on_hand_dc.get((dc.dc_code, item.item_code), 0)
                self._writers["InventoryInformation.csv"].writerow([
                    dc.dc_code, item.item_code, date_str, qty, 0, "Available",
                ])

        self._weekly.clear()

    def close(self):
        for f in self._files.values():
            f.close()
