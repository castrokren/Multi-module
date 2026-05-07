import pandas as pd
import os

print("Starting check...")
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

try:
    print("Attempting to read Excel file...")
    df = pd.read_excel('crossref_results_20250808_235653.xlsx')
    print(f'Total rows: {len(df)}')
    print(f'Columns: {list(df.columns)}')
    print(f'Unique Item Codes: {df["Item Code"].nunique()}')
    print(f'Last few Item Codes:')
    print(df['Item Code'].tail(10).tolist())
    print(f'First few Item Codes:')
    print(df['Item Code'].head(10).tolist())
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
