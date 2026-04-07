import pandas as pd
import os

def load_all_data(outputs_dir: str):
    """Loads and transforms both sales and inventory data from the simulation outputs."""
    sales_path = os.path.join(outputs_dir, "SalesHistoryInformation.csv")
    inv_path = os.path.join(outputs_dir, "InventoryInformation.csv")
    
    # Load Sales
    if not os.path.exists(sales_path):
        sales_df = pd.DataFrame(columns=["WeekEndingDate", "StoreCode", "ItemCode", "SalesQuantity"])
    else:
        sales_df = pd.read_csv(sales_path)
        if "WeekEndingDate" in sales_df.columns:
             sales_df["WeekEndingDate"] = pd.to_datetime(sales_df["WeekEndingDate"])
             
    # Load Inventory
    if not os.path.exists(inv_path):
        inv_df = pd.DataFrame(columns=["Date", "LocationType", "LocationCode", "ItemCode", "QuantityOnHand"])
    else:
        inv_df = pd.read_csv(inv_path)
        if "Date" in inv_df.columns:
            # The simulator records inventory on Sunday, same as WeekEndingDate
            inv_df["Date"] = pd.to_datetime(inv_df["Date"])
            
    return sales_df, inv_df
    
def aggregate_dashboard_metrics(sales_df: pd.DataFrame, inv_df: pd.DataFrame, stores: list = None, items: list = None) -> pd.DataFrame:
    """Filters data based on UI and merges sales with inventory snapshots."""
    
    # 1. Process Sales Data
    s_df = sales_df.copy()
    if stores:
        s_df = s_df[s_df["StoreCode"].isin(stores)]
    if items:
        s_df = s_df[s_df["ItemCode"].isin(items)]
        
    if not s_df.empty:
        weekly_sales = s_df.groupby("WeekEndingDate")["SalesQuantity"].sum().reset_index()
        weekly_sales.rename(columns={"WeekEndingDate": "Week", "SalesQuantity": "Total Sales"}, inplace=True)
    else:
        weekly_sales = pd.DataFrame(columns=["Week", "Total Sales"])
        
    # 2. Process Inventory Data
    i_df = inv_df.copy()
    if stores:
        # Inventory maps StoreCode to LocationCode
        i_df = i_df[(i_df["LocationCode"].isin(stores)) & (i_df["LocationType"] == "STORE")]
    if items:
        i_df = i_df[i_df["ItemCode"].isin(items)]
        
    if not i_df.empty:
        weekly_inv = i_df.groupby("Date")["QuantityOnHand"].sum().reset_index()
        weekly_inv.rename(columns={"Date": "Week", "QuantityOnHand": "Total Inventory"}, inplace=True)
    else:
        weekly_inv = pd.DataFrame(columns=["Week", "Total Inventory"])
        
    # 3. Merge together on Week
    if weekly_sales.empty and weekly_inv.empty:
        return pd.DataFrame(columns=["Week", "Total Sales", "Total Inventory"])
        
    if weekly_sales.empty:
        merged = weekly_inv
        merged["Total Sales"] = 0
        return merged
        
    if weekly_inv.empty:
        merged = weekly_sales
        merged["Total Inventory"] = 0
        return merged
        
    merged = pd.merge(weekly_sales, weekly_inv, on="Week", how="outer").fillna(0)
    merged.sort_values("Week", inplace=True)
    
    return merged
