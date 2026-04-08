"""
demand_loader.py
Loads and validates the externally generated demand CSV.
Provides a daily lookup API: get_demand(store, item, date) -> int
Uses pandas for all data handling.
"""
import pandas as pd
from datetime import date
from collections import defaultdict


class DemandLoader:
    def __init__(self, state):
        self.state = state
        # Internal index: (store_code, item_code, date) -> qty
        self._demand: dict = defaultdict(int)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def load(self, filepath: str):
        print(f"  Loading demand from: {filepath}")
        valid_stores = set(self.state.stores.keys())
        valid_items  = set(self.state.items.keys())

        df = pd.read_csv(filepath, parse_dates=["Date"])

        # ── Schema validation ──────────────────────────────────────────
        required = {"Date", "StoreCode", "ItemCode", "DemandQty"}
        missing  = required - set(df.columns)
        if missing:
            raise ValueError(f"demand.csv is missing columns: {missing}")

        # Drop rows with nulls in key columns
        df = df.dropna(subset=list(required))
        df["DemandQty"] = df["DemandQty"].astype(int)

        # ── Cross-reference validation ─────────────────────────────────
        bad_stores = set(df["StoreCode"].unique()) - valid_stores
        if bad_stores:
            raise ValueError(f"Unknown StoreCode(s) in demand: {bad_stores}")

        bad_items = set(df["ItemCode"].unique()) - valid_items
        if bad_items:
            raise ValueError(f"Unknown ItemCode(s) in demand: {bad_items}")

        # ── Build in-memory index ──────────────────────────────────────
        for row in df.itertuples(index=False):
            key = (row.StoreCode, row.ItemCode, row.Date.date())
            self._demand[key] += int(row.DemandQty)

        print(f"  Demand loaded: {len(df):,} rows | "
              f"{df['StoreCode'].nunique()} stores | "
              f"{df['ItemCode'].nunique()} items")
        return self._demand

    def get_demand(self, store: str, item: str, date_obj: date) -> int:
        return self._demand.get((store, item, date_obj), 0)
