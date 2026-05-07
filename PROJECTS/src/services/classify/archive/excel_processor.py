# ARCHIVED 2026-05-07
# Original processor, superseded by AdaptiveExcelProcessor in adaptive_excel_processor.py.
# Kept for reference only. Do not import or run this file.

"""
Unified Excel file processing module for the folder monitor application.
Handles both .xls and .xlsx files with appropriate engines.
"""

import pandas as pd
from pathlib import Path
import warnings
import logging

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class ExcelProcessor:
    def __init__(self, hw_keywords_file=None, sw_keywords_file=None, output_dir=None):
        self.hw_keywords = []
        self.sw_keywords = []
        self.output_dir = Path(output_dir) if output_dir else Path(r"D:\SOM_in_labeled")
        
        if hw_keywords_file and sw_keywords_file:
            self.load_keywords(hw_keywords_file, sw_keywords_file)

    def load_keywords(self, hw_file, sw_file):
        """Load hardware and software keywords from files."""
        try:
            self.hw_keywords = [l.strip().lower() for l in Path(hw_file).read_text().splitlines() if l.strip()]
            self.sw_keywords = [l.strip().lower() for l in Path(sw_file).read_text().splitlines() if l.strip()]
            logging.info(f"Loaded {len(self.hw_keywords)} hardware and {len(self.sw_keywords)} software keywords")
        except Exception as e:
            logging.error(f"Error loading keywords: {e}")
            raise

    @staticmethod
    def should_process(file_path):
        """Check if file should be processed based on name and extension."""
        path = Path(file_path)
        
        # Skip temporary files and already processed files
        if path.name.startswith('~$') or path.stem.endswith('_labeled'):
            return False
            
        # Only process Excel files
        return path.suffix.lower() in ['.xls', '.xlsx']

    def read_excel_file(self, file_path):
        """Read Excel file with appropriate engine based on extension."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        # Choose engine based on file extension
        if file_ext == '.xls':
            engine = 'xlrd'
        elif file_ext == '.xlsx':
            engine = 'openpyxl'
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        try:
            # Read with header at row 2 (index 1)
            df = pd.read_excel(file_path, header=1, engine=engine)
            logging.info(f"Successfully read {file_path.name} using {engine} engine")
            return df
        except Exception as e:
            logging.error(f"Error reading {file_path.name}: {e}")
            raise

    def find_description_column(self, df):
        """Find the description column dynamically."""
        # First try exact match
        desc_cols = [c for c in df.columns if 'description' in c.lower()]
        
        # If not found, try other common patterns
        if not desc_cols:
            patterns = ['desc', 'item', 'name', 'title', 'product', 'material']
            desc_cols = [c for c in df.columns if any(word in c.lower() for word in patterns)]
        
        if not desc_cols:
            available_cols = ', '.join(df.columns[:10])  # Show first 10 columns
            raise ValueError(f"No description column found. Available columns: {available_cols}...")
        
        desc_col = desc_cols[0]
        logging.info(f"Using '{desc_col}' as description column")
        return desc_col

    def classify_item(self, description):
        """Classify item based on description and keywords."""
        if not description:
            return "Non-Instrument"
            
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in self.hw_keywords):
            return "Instrument"
        elif any(keyword in desc_lower for keyword in self.sw_keywords):
            return "Software"
        else:
            return "Non-Instrument"

    def clean_dataframe(self, df):
        """Remove unwanted columns from dataframe."""
        # Drop columns by position: A-F (0-5), H (7), J-M (9-12), P-AF (15-31)
        cols = df.columns.tolist()
        drop_indices = list(range(0, 6)) + [7] + list(range(9, 13)) + list(range(15, 32))
        to_drop = [cols[i] for i in drop_indices if i < len(cols)]
        
        df.drop(columns=to_drop, inplace=True, errors='ignore')
        return df

    def process_file(self, file_path):
        """Process a single Excel file: read, classify, clean, and save."""
        try:
            file_path = Path(file_path)
            
            if not self.should_process(file_path):
                logging.info(f"Skipping {file_path.name} - should not be processed")
                return False

            # Read the Excel file
            df = self.read_excel_file(file_path)
            
            # Find description column
            desc_col = self.find_description_column(df)
            
            # Clean unwanted columns
            df = self.clean_dataframe(df)
            
            # Classify items
            df.insert(0, 'TYPE', df[desc_col].apply(self.classify_item))
            
            # Save to output directory
            self.output_dir.mkdir(exist_ok=True)
            output_file = self.output_dir / (file_path.stem + '_labeled.xlsx')
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            logging.info(f"Successfully processed and saved: {output_file.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            return False

    def process_directory(self, directory_path):
        """Process all Excel files in a directory."""
        directory = Path(directory_path)
        processed_count = 0
        
        # Process both .xls and .xlsx files
        for pattern in ['*.xls', '*.xlsx']:
            for file_path in directory.glob(pattern):
                if self.process_file(file_path):
                    processed_count += 1
        
        logging.info(f"Processed {processed_count} files in {directory}")
        return processed_count

# Convenience functions for backward compatibility
def process_single_file(file_path, hw_keywords_file, sw_keywords_file, output_dir=None):
    """Process a single file - maintains backward compatibility."""
    processor = ExcelProcessor(hw_keywords_file, sw_keywords_file, output_dir)
    return processor.process_file(file_path)

def process_directory(directory_path, hw_keywords_file, sw_keywords_file, output_dir=None):
    """Process all files in directory - maintains backward compatibility."""
    processor = ExcelProcessor(hw_keywords_file, sw_keywords_file, output_dir)
    return processor.process_directory(directory_path)