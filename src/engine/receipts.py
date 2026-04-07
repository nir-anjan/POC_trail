from datetime import date
from src.models.state import SimulationState
from src.utils.exporter import Exporter

def process_receipts(state: SimulationState, current_date: date, exporter: Exporter):
    """
    Step 1: Supplier -> DC receipts.
    Update on_hand_dc and on_order_dc_qty.
    """
    remaining_receipts = []
    
    for receipt in state.expected_receipts:
        if receipt.arrival_date <= current_date:
            # Receive order
            # TODO: Can apply partial/late delivery variance here for specific scenarios
            state.on_hand_dc[(receipt.dc_code, receipt.item_code)] += receipt.qty
            state.on_order_dc_qty[(receipt.dc_code, receipt.item_code)] -= receipt.qty
            
            # Record receipt
            # SupplierReceipts.csv: Date, Supplier, DC, Item, QtyReceived
            exporter.record_supplier_receipt(
                current_date, 
                receipt.supplier_code, 
                receipt.dc_code, 
                receipt.item_code, 
                receipt.qty
            )
        else:
            remaining_receipts.append(receipt)
            
    state.expected_receipts = remaining_receipts
