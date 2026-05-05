"""
Debug script for the adaptive processor to identify issues.
"""

import logging
import traceback
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_adaptive_processor():
    """Debug the adaptive processor step by step."""
    
    print("=== ADAPTIVE PROCESSOR DEBUG ===")
    
    # Step 1: Check if module can be imported
    try:
        print("1. Testing module import...")
        from adaptive_excel_processor import AdaptiveExcelProcessor
        print("   ✓ AdaptiveExcelProcessor imported successfully")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        traceback.print_exc()
        return False
    
    # Step 2: Check keyword files
    try:
        print("2. Checking keyword files...")
        hw_file = Path("hardware_keywords.txt")
        sw_file = Path("software_keywords.txt")
        
        if hw_file.exists():
            print(f"   ✓ Hardware keywords file found: {hw_file}")
            hw_content = hw_file.read_text()
            hw_lines = [l.strip() for l in hw_content.splitlines() if l.strip() and not l.strip().startswith('#')]
            print(f"   ✓ Hardware keywords loaded: {len(hw_lines)} keywords")
        else:
            print(f"   ✗ Hardware keywords file not found: {hw_file}")
            return False
            
        if sw_file.exists():
            print(f"   ✓ Software keywords file found: {sw_file}")
            sw_content = sw_file.read_text()
            sw_lines = [l.strip() for l in sw_content.splitlines() if l.strip() and not l.strip().startswith('#')]
            print(f"   ✓ Software keywords loaded: {len(sw_lines)} keywords")
        else:
            print(f"   ✗ Software keywords file not found: {sw_file}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error checking keyword files: {e}")
        traceback.print_exc()
        return False
    
    # Step 3: Try to create processor
    try:
        print("3. Creating adaptive processor...")
        processor = AdaptiveExcelProcessor(
            hw_keywords_file="hardware_keywords.txt",
            sw_keywords_file="software_keywords.txt",
            output_dir=r"D:\SOM_in_labeled",
            learning_mode=True,
            min_occurrences=5,
            confidence_threshold=0.7
        )
        print("   ✓ Adaptive processor created successfully")
        print(f"   ✓ Loaded {len(processor.hw_keywords)} HW keywords")
        print(f"   ✓ Loaded {len(processor.sw_keywords)} SW keywords")
        
    except Exception as e:
        print(f"   ✗ Error creating processor: {e}")
        traceback.print_exc()
        return False
    
    # Step 4: Check for test files
    try:
        print("4. Looking for test files...")
        test_files = []
        
        # Look in current directory
        test_files.extend(list(Path('.').glob('*.xlsx')))
        test_files.extend(list(Path('.').glob('*.xls')))
        
        # Look in common directories
        common_dirs = [r"D:\SOM_in_labeled", "output", "test"]
        for dir_path in common_dirs:
            if Path(dir_path).exists():
                test_files.extend(list(Path(dir_path).glob('*.xlsx')))
                test_files.extend(list(Path(dir_path).glob('*.xls')))
        
        # Filter out already processed files
        test_files = [f for f in test_files if not f.stem.endswith('_labeled')]
        
        if test_files:
            test_file = test_files[0]
            print(f"   ✓ Found test file: {test_file}")
        else:
            print("   ✗ No test files found")
            print("   Create a test Excel file to continue debugging")
            return False
            
    except Exception as e:
        print(f"   ✗ Error finding test files: {e}")
        traceback.print_exc()
        return False
    
    # Step 5: Test file processing
    try:
        print("5. Testing file processing...")
        print(f"   Testing with: {test_file}")
        
        # Check if file should be processed
        should_process = processor.should_process(test_file)
        print(f"   Should process: {should_process}")
        
        if not should_process:
            print("   ✗ File should not be processed (already labeled or temp file)")
            return False
        
        # Try to read the file
        print("   Attempting to read Excel file...")
        df = processor.read_excel_file(test_file)
        print(f"   ✓ Excel file read successfully: {len(df)} rows, {len(df.columns)} columns")
        print(f"   Columns: {list(df.columns)}")
        
        # Find description column
        print("   Finding description column...")
        desc_col = processor.find_description_column(df)
        print(f"   ✓ Description column found: '{desc_col}'")
        
        # Test classification on first few rows
        print("   Testing classification...")
        for i in range(min(3, len(df))):
            description = df.iloc[i][desc_col]
            classification = processor.classify_item(description)
            print(f"   Row {i}: '{description[:50]}...' -> {classification}")
        
        # Test full processing in safe mode
        print("   Testing full processing (test mode)...")
        success = processor.process_file(test_file, test_mode=True, auto_promote=False)
        
        if success:
            print("   ✓ File processing successful!")
            
            # Show learning analytics
            analytics = processor.generate_learning_analytics()
            print(f"   Learning Analytics:")
            print(f"     - HW candidates: {analytics['hw_learning_rate']}")
            print(f"     - SW candidates: {analytics['sw_learning_rate']}")
            print(f"     - Ready for promotion (HW): {len(analytics['promotion_candidates']['hw'])}")
            print(f"     - Ready for promotion (SW): {len(analytics['promotion_candidates']['sw'])}")
            
            return True
        else:
            print("   ✗ File processing failed")
            return False
            
    except Exception as e:
        print(f"   ✗ Error during file processing: {e}")
        traceback.print_exc()
        return False

def test_specific_file(file_path):
    """Test processing a specific file."""
    print(f"\n=== TESTING SPECIFIC FILE: {file_path} ===")
    
    try:
        from adaptive_excel_processor import AdaptiveExcelProcessor
        
        processor = AdaptiveExcelProcessor(
            hw_keywords_file="hardware_keywords.txt",
            sw_keywords_file="software_keywords.txt",
            output_dir=r"D:\SOM_in_labeled",
            learning_mode=True,
            min_occurrences=5,
            confidence_threshold=0.7
        )
        
        print(f"Testing file: {file_path}")
        success = processor.process_file(file_path, test_mode=True)
        
        if success:
            print("✓ SUCCESS: File processed successfully")
            return True
        else:
            print("✗ FAILED: File processing failed")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Adaptive Processor Debug Tool")
    print("=" * 50)
    
    # Run general debug
    success = debug_adaptive_processor()
    
    if success:
        print("\n🎉 DEBUG COMPLETED SUCCESSFULLY!")
        print("The adaptive processor is working correctly.")
    else:
        print("\n❌ DEBUG FAILED!")
        print("There are issues with the adaptive processor.")
        print("Check the error messages above for details.")
    
    # If you want to test a specific file, uncomment and modify this:
    # test_specific_file("NQ_DG_RESEARCH_CAPITAL_V2-39579943_labeled.xlsx")
