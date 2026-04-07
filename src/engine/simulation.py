from datetime import date, timedelta
from src.models.state import SimulationState
from src.demand.demand_loader import DemandLoader
from src.utils.exporter import Exporter

from src.engine.receipts import process_receipts
from src.engine.ordering import create_customer_orders, compute_store_needs, create_supplier_orders
from src.engine.fulfillment import allocate_and_fulfill

class SimulationEngine:
    def __init__(self, state: SimulationState, demand_loader: DemandLoader, exporter: Exporter):
        self.state = state
        self.demand_loader = demand_loader
        self.exporter = exporter
        
    def initialize_inventory(self, start_date: date):
        """
        Seeds initial inventory to 4 weeks of max historical demand to avoid instant stockouts.
        """
        # Look ahead 28 days to create a reasonable starting inventory
        for store in self.state.stores.values():
            for item in self.state.items.values():
                total = sum(
                    self.demand_loader.get_demand(store.store_code, item.item_code, start_date + timedelta(days=d))
                    for d in range(28)
                )
                self.state.on_hand_store[(store.store_code, item.item_code)] = int(total * 1.5)
                
        for dc in self.state.dcs.values():
            for item in self.state.items.values():
                # DC supports ~12 stores on average.
                total = 0
                for store in [s for s in self.state.stores.values() if s.assigned_dc == dc.dc_code]:
                    total += sum(
                        self.demand_loader.get_demand(store.store_code, item.item_code, start_date + timedelta(days=d))
                        for d in range(28)
                    )
                self.state.on_hand_dc[(dc.dc_code, item.item_code)] = int(total * 2.0)

    def run(self, start_date: date, days: int):
        print(f"Starting simulation from {start_date} for {days} days...")
        
        self.initialize_inventory(start_date)
        
        current_date = start_date
        
        for day in range(days):
            weekday = current_date.weekday() # 0 = Mon, 6 = Sun
            
            if day % 30 == 0:
                print(f" Simulating day {day}/{days}: {current_date}")
            
            # Step 1: Supplier -> DC receipts
            process_receipts(self.state, current_date, self.exporter)
            
            if weekday == 0: # MONDAY
                # Step 2: Customer Order Creation
                create_customer_orders(self.state, current_date, self.demand_loader, self.exporter)
                
            # Step 3: Compute Store Replenishment Need
            needs = compute_store_needs(self.state, current_date, self.demand_loader)
            
            # Step 4 & 5: DC -> Store Allocation and Fulfillment
            allocate_and_fulfill(self.state, current_date, needs, self.demand_loader, self.exporter)
            
            if weekday == 6: # SUNDAY
                # Step 6, 7 & 9: Record Deliveries, Sales, Inventory
                self.exporter.process_weekly_aggregates(self.state, current_date)
                
            if weekday == 0: # MONDAY
                # Step 8: DC Supplier Ordering
                create_supplier_orders(self.state, current_date, self.demand_loader, self.exporter)
                
            current_date += timedelta(days=1)
            
        print("Simulation complete.")
