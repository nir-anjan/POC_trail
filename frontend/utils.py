"""
utils.py — Data loading and transformation for the Streamlit dashboard.
"""
import os
import pandas as pd


def get_outputs_dir() -> str:
    """Returns the absolute path to the outputs/ folder relative to this file."""
    return os.path.join(os.path.dirname(__file__), "..", "outputs")


def load_sales(outputs_dir: str) -> pd.DataFrame:
    path = os.path.join(outputs_dir, "SalesHistoryInformation.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def load_inventory(outputs_dir: str) -> pd.DataFrame:
    path = os.path.join(outputs_dir, "InventoryInformation.csv")
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Keep only store rows (not DCs)
    return df[df["SiteCode"].str.startswith("Store_")].copy()


def get_stores(sales_df: pd.DataFrame) -> list:
    return sorted(sales_df["StoreCode"].unique().tolist())


def get_items(sales_df: pd.DataFrame, store_code: str) -> list:
    return sorted(
        sales_df[sales_df["StoreCode"] == store_code]["ItemCode"].unique().tolist()
    )


def get_chart_data(
    sales_df: pd.DataFrame,
    inv_df: pd.DataFrame,
    store_code: str,
    item_code: str,
) -> pd.DataFrame:
    """
    Returns a merged DataFrame with columns:
      WeekId | SalesQuantity | QuantityOnHand
    sorted by week for plotting.
    """
    # Filter sales
    s = sales_df[
        (sales_df["StoreCode"] == store_code) &
        (sales_df["ItemCode"]  == item_code)
    ][["WeekId", "SalesQuantity"]].copy()

    # Filter inventory snapshot (one row per store/item/week-end)
    # Map InventoryDate → WeekId using pandas isocalendar
    inv = inv_df[
        (inv_df["SiteCode"]  == store_code) &
        (inv_df["ItemCode"]  == item_code)
    ][["InventoryDate", "QuantityOnHand"]].copy()

    inv["InventoryDate"] = pd.to_datetime(inv["InventoryDate"])
    inv["WeekId"] = inv["InventoryDate"].apply(
        lambda d: f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
    )
    inv = inv[["WeekId", "QuantityOnHand"]]

    if s.empty and inv.empty:
        return pd.DataFrame(columns=["WeekId", "SalesQuantity", "QuantityOnHand"])

    merged = pd.merge(s, inv, on="WeekId", how="outer").fillna(0)
    merged["SalesQuantity"]  = merged["SalesQuantity"].astype(int)
    merged["QuantityOnHand"] = merged["QuantityOnHand"].astype(int)

    # Sort by week string (ISO format sorts correctly lexicographically)
    merged = merged.sort_values("WeekId").reset_index(drop=True)
    return merged
