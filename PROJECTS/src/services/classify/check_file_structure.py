import openpyxl
import pandas as pd

excel_file = r"C:\Data\Crawler\input\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1).xlsx"

# Check with openpyxl
wb = openpyxl.load_workbook(excel_file)
ws = wb.active
print("First 3 rows of file:")
for idx in range(1, 4):
    row = [cell.value for cell in ws[idx]]
    print(f"  Row {idx}: {row[:5]}...")

# Check with pandas default
df_default = pd.read_excel(excel_file)
print(f"\npandas default read - shape: {df_default.shape}")
print(f"  Columns type: {type(df_default.columns[0])}")
print(f"  First column: {df_default.columns[0]}")

# Check with pandas header=0
df_h0 = pd.read_excel(excel_file, header=0)
print(f"\npandas header=0 - shape: {df_h0.shape}")
print(f"  Columns: {list(df_h0.columns[:5])}")

# Check with pandas header=1
df_h1 = pd.read_excel(excel_file, header=1)
print(f"\npandas header=1 - shape: {df_h1.shape}")
print(f"  Columns type: {type(df_h1.columns[0])}")
print(f"  First column: {df_h1.columns[0]}")
