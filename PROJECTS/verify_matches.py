import pandas as pd

excel_file = "src/services/cross-reference/results/crossref_results_20260617_152525.xlsx"
try:
    df = pd.read_excel(excel_file)
    print(f"Total matches in file: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 5 matches:")
    print("="*120)

    for idx, row in df.head(5).iterrows():
        print(f"\nMatch #{idx+1}:")
        print(f"  Item Code: {row.iloc[1] if len(row) > 1 else 'N/A'}")
        print(f"  Description: {str(row.iloc[2])[:60] if len(row) > 2 else 'N/A'}...")
        print(f"  PDF File: {row.iloc[4] if len(row) > 4 else 'N/A'}")
        print(f"  Score: {row.iloc[5] if len(row) > 5 else 'N/A'}")
        print(f"  Supplier: {row.iloc[6] if len(row) > 6 else 'N/A'}")
except Exception as e:
    print(f"Error reading file: {e}")
