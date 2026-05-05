import pandas as pd
import os

# Write output to file since terminal isn't showing output
with open('progress_check.txt', 'w') as f:
    f.write("=== PROGRESS CHECK ===\n")
    
    try:
        # Read the results file
        df = pd.read_excel('crossref_results_20250808_235653.xlsx')
        f.write(f"Total rows: {len(df)}\n")
        f.write(f"Columns: {list(df.columns)}\n")
        f.write(f"Unique Item Codes: {df['Item Code'].nunique()}\n")
        f.write(f"Last few Item Codes:\n")
        for item in df['Item Code'].tail(10):
            f.write(f"  {item}\n")
        
        # Check input file
        if os.path.exists('NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx'):
            input_df = pd.read_excel('NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx')
            total_items = len(input_df)
            processed_items = df['Item Code'].nunique()
            remaining = total_items - processed_items
            
            f.write(f"\nInput file total items: {total_items}\n")
            f.write(f"Processed items: {processed_items}\n")
            f.write(f"Remaining items: {remaining}\n")
            f.write(f"Progress: {processed_items/total_items*100:.1f}%\n")
            
            if remaining > 0:
                f.write("Analysis is incomplete - need to resume\n")
            else:
                f.write("Analysis appears complete!\n")
        
        f.write("\n=== CHECK COMPLETE ===\n")
        
    except Exception as e:
        f.write(f"Error: {e}\n")
        import traceback
        f.write(traceback.format_exc())

