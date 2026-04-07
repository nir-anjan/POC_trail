import csv
from datetime import date
import os
from collections import defaultdict
from src.models.state import SimulationState

class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # File handles and writers
        self.files = {}
        self.writers = {}
        
        # In-memory accumulators for weekly stats
        # (store_code, item_code) -> [total_requested, total_delivered]
        self.weekly_fulfillment = defaultdict(lambda: [0, 0]) 
        
        self._init_files()
        
    def _init_files(self):
        # Customer Orders
        self.add_file('CustomerOrderHeader.csv', ['OrderID', 'OrderDate', 'StoreCode'])
        self.add_file('CustomerOrderLine.csv', ['OrderID', 'ItemCode', 'OrderQty'])
        
        # Supplier Orders
        self.add_file('SupplierOrderHeader.csv', ['OrderID', 'OrderDate', 'SupplierCode', 'DCCode'])
        self.add_file('SupplierOrderLine.csv', ['OrderID', 'ItemCode', 'NeedQty', 'OrderQty'])
        
        # Supplier Receipts
        self.add_file('SupplierReceipts.csv', ['Date', 'SupplierCode', 'DCCode', 'ItemCode', 'QtyReceived'])
        
        # Weekly Outputs
        self.add_file('InventoryInformation.csv', ['Date', 'LocationType', 'LocationCode', 'ItemCode', 'QuantityOnHand', 'OnOrderQty'])
        self.add_file('CustomerOrderDelivery.csv', ['WeekEndingDate', 'StoreCode', 'ItemCode', 'OrderQuantity', 'DeliveredQuantity', 'DeliveryStatus'])
        self.add_file('SalesHistoryInformation.csv', ['WeekEndingDate', 'StoreCode', 'ItemCode', 'SalesQuantity'])

    def add_file(self, filename: str, headers: list):
        path = os.path.join(self.output_dir, filename)
        f = open(path, 'w', newline='')
        writer = csv.writer(f)
        writer.writerow(headers)
        self.files[filename] = f
        self.writers[filename] = writer

    def record_customer_order_header(self, order_id: str, date: date, store_code: str):
        self.writers['CustomerOrderHeader.csv'].writerow([order_id, date.strftime('%Y-%m-%d'), store_code])

    def record_customer_order_line(self, order_id: str, item_code: str, order_qty: int):
        self.writers['CustomerOrderLine.csv'].writerow([order_id, item_code, order_qty])

    def record_supplier_order_header(self, order_id: str, date: date, supplier_code: str, dc_code: str):
        self.writers['SupplierOrderHeader.csv'].writerow([order_id, date.strftime('%Y-%m-%d'), supplier_code, dc_code])

    def record_supplier_order_line(self, order_id: str, item_code: str, need_qty: int, order_qty: int):
        self.writers['SupplierOrderLine.csv'].writerow([order_id, item_code, need_qty, order_qty])

    def record_supplier_receipt(self, date: date, supplier_code: str, dc_code: str, item_code: str, qty: int):
        self.writers['SupplierReceipts.csv'].writerow([date.strftime('%Y-%m-%d'), supplier_code, dc_code, item_code, qty])

    def accumulate_daily_fulfillment(self, current_date: date, store_code: str, item_code: str, req_qty: int, delivered: int):
        self.weekly_fulfillment[(store_code, item_code)][0] += req_qty
        self.weekly_fulfillment[(store_code, item_code)][1] += delivered

    def process_weekly_aggregates(self, state: SimulationState, current_date: date):
        """
        Runs on SUNDAY.
        Writes Inventory snapshot, Deliveries, and Sales.
        """
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 1. Inventory Snapshot
        for store in state.stores.values():
            for item in state.items.values():
                on_hand = state.on_hand_store.get((store.store_code, item.item_code), 0)
                # Store doesn't technically have "on order" in the same way DC does for external suppliers in this spec
                # It arrives same day from DC. So on_order = 0
                self.writers['InventoryInformation.csv'].writerow([
                    date_str, 'STORE', store.store_code, item.item_code, on_hand, 0
                ])
                
        for dc in state.dcs.values():
            for item in state.items.values():
                on_hand = state.on_hand_dc.get((dc.dc_code, item.item_code), 0)
                on_order = state.on_order_dc_qty.get((dc.dc_code, item.item_code), 0)
                self.writers['InventoryInformation.csv'].writerow([
                    date_str, 'DC', dc.dc_code, item.item_code, on_hand, on_order
                ])
                
        # 2. Deliveries and Sales
        for (store_code, item_code), (req, delivered) in self.weekly_fulfillment.items():
            if req > 0:
                status = "FULL" if delivered >= req else "PARTIAL"
                
                # CustomerOrderDelivery
                self.writers['CustomerOrderDelivery.csv'].writerow([
                    date_str, store_code, item_code, req, delivered, status
                ])
                
                # SalesHistory
                self.writers['SalesHistoryInformation.csv'].writerow([
                    date_str, store_code, item_code, delivered
                ])
                
        # Reset accumulations for the next week
        self.weekly_fulfillment.clear()

    def close(self):
        for f in self.files.values():
            f.close()
