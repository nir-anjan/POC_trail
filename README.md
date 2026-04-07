# Retail Supply Chain Simulation Engine

A daily-level, deterministic Python simulation engine designed to model inventory flows logically matching real-world supply chain mechanisms. Built to consume an externally generated, immutable demand signal (`demand.csv`), rather than generating demand endogenously.

## Goal

- Model daily inventory flows across 3 tiers (Suppliers -> Distribution Centers -> Stores).
- Support explicit tracking of True Demand vs Observed Sales (Deliveries).
- Naturally derive real-world phenomena like stockouts, overstocks, and delayed shipments.

## System Architecture

The project has the following directories and components:

*   **`demand_generator.py`**: A quick utility script explicitly designed for local/POC usage to spin up a mock `demand.csv`.
*   **`generate.py`**: The main entry point and CLI runner.
*   **`src/data/master_data.py`**: Handles configuring the network topology (25 Stores, 200 Items, 15 Suppliers, 2 DCs).
*   **`src/demand/demand_loader.py`**: Validates the schema and precomputes the `requested_qty` demand matrix used strictly as *True* Demand. 
*   **`src/models/state.py`**: Dataclasses for in-memory inventory structures.
*   **`src/engine/`**: Features the core simulation loops organized by step:
    *   `receipts.py`: Processes supplier deliveries to the DCs.
    *   `ordering.py`: Computes store targets (Coverage logic) and commits Supplier Orders.
    *   `fulfillment.py`: Implements proportion-based DC allocation logic and Store Fulfillment.
    *   `simulation.py`: The timeline orchestrator loop executing the process step-by-step.
*   **`src/utils/exporter.py`**: Generates and writes the output analytical CSVs simulating real-world data logs.

## Setup & Running

**Prerequisites**: Python 3.9+ 

1. **Generate Mock Demand Matrix:**
    We must provide the standard True Demand input matrix first.
    ```bash
    python3 demand_generator.py
    ```

2. **Run the Simulation Engine:**
    Run the simulation by providing the config and our demand signal. This runs for a simulated 52 weeks (364 days).
    ```bash
    python3 generate.py --demand_file demand.csv
    ```

## Outputs
By default, the simulation will write weekly extracts and log outputs into `outputs/` folder.
*   **`InventoryInformation.csv`**: Sunday inventory snapshots (Qty On Hand, Qty On Order).
*   **`CustomerOrderHeader.csv` & `CustomerOrderLine.csv`**: Aggregation of unconstrained demand representing True requirement.
*   **`SupplierOrderHeader.csv` & `SupplierOrderLine.csv`**: Rounded DC-to-Supplier Case Pack sized orders logic.
*   **`SupplierReceipts.csv`**: Ledger of actual receipts.
*   **`CustomerOrderDelivery.csv` & `SalesHistoryInformation.csv`**: Captured fulfilled deliveries modeling real-world stockouts correctly (Deliveries < OrderQuantity).

## Modeling Notes

The engine separates true demand and fulfillment across an orchestrated loop running Mon-Sun:
- **Daily Loop Constraints**: The engine fulfills store need from DC constrained by stock availability (proportional logic applied when constrained). Store Fulfills customer demand similarly bounded by its on-hand stock.
- **Lost Sales**: A stockout condition isn't defined explicitly by a flag, but inherently represented whenever `DeliveredQuantity` is fundamentally less than the recorded `OrderQuantity`. 
