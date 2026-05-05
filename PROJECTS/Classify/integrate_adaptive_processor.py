"""
Integration script to help transition from the original ExcelProcessor to AdaptiveExcelProcessor.
Provides backward compatibility and migration utilities.
"""

import logging
from pathlib import Path
from adaptive_excel_processor import AdaptiveExcelProcessor
from excel_processor import ExcelProcessor  # Original processor

def migrate_to_adaptive():
    """Migrate from original processor to adaptive processor."""
    print("=== MIGRATING TO ADAPTIVE PROCESSOR ===")
    
    # Check if keyword files exist
    hw_file = Path("hardware_keywords.txt")
    sw_file = Path("software_keywords.txt")
    
    if not hw_file.exists() or not sw_file.exists():
        print("❌ Keyword files not found. Please ensure hardware_keywords.txt and software_keywords.txt exist.")
        return False
    
    # Create adaptive processor with conservative settings
    adaptive_processor = AdaptiveExcelProcessor(
        hw_keywords_file=str(hw_file),
        sw_keywords_file=str(sw_file),
        output_dir=r"D:\SOM_in_labeled",
        learning_mode=True,
        min_occurrences=7,  # Conservative threshold
        confidence_threshold=0.7
    )
    
    print("✅ Adaptive processor initialized with conservative settings:")
    print(f"   - Learning mode: {adaptive_processor.learning_mode}")
    print(f"   - Min occurrences for promotion: {adaptive_processor.min_occurrences}")
    print(f"   - Confidence threshold: {adaptive_processor.confidence_threshold}")
    
    return adaptive_processor

def compare_processors(test_file):
    """Compare results between original and adaptive processors."""
    print(f"\n=== COMPARING PROCESSORS ON {test_file} ===")
    
    # Test original processor
    original = ExcelProcessor("hardware_keywords.txt", "software_keywords.txt")
    
    # Test adaptive processor
    adaptive = AdaptiveExcelProcessor(
        "hardware_keywords.txt", 
        "software_keywords.txt",
        learning_mode=True,
        min_occurrences=10,  # High threshold for comparison
        test_mode=True
    )
    
    try:
        # Read file with both processors
        df_orig = original.read_excel_file(test_file)
        df_adapt = adaptive.read_excel_file(test_file)
        
        desc_col_orig = original.find_description_column(df_orig)
        desc_col_adapt = adaptive.find_description_column(df_adapt)
        
        # Classify with both
        df_orig.insert(0, 'TYPE_ORIG', df_orig[desc_col_orig].apply(original.classify_item))
        df_adapt.insert(0, 'TYPE_ADAPT', df_adapt[desc_col_adapt].apply(adaptive.classify_item))
        
        # Compare results
        if len(df_orig) == len(df_adapt):
            differences = 0
            for i in range(len(df_orig)):
                orig_type = df_orig.iloc[i]['TYPE_ORIG']
                adapt_type = df_adapt.iloc[i]['TYPE_ADAPT']
                if orig_type != adapt_type:
                    differences += 1
                    print(f"Difference at row {i}: '{df_orig.iloc[i][desc_col_orig][:50]}...'")
                    print(f"  Original: {orig_type}, Adaptive: {adapt_type}")
            
            print(f"\n📊 Comparison Results:")
            print(f"   - Total items: {len(df_orig)}")
            print(f"   - Differences: {differences}")
            print(f"   - Agreement: {((len(df_orig) - differences) / len(df_orig) * 100):.1f}%")
            
            if differences == 0:
                print("✅ Perfect agreement between processors!")
            elif differences < len(df_orig) * 0.1:  # Less than 10% difference
                print("✅ Good agreement - safe to migrate")
            else:
                print("⚠️  Significant differences - review before migrating")
        
    except Exception as e:
        print(f"❌ Error during comparison: {e}")

def safe_test_adaptive(test_file, min_occurrences=5):
    """Safely test the adaptive processor."""
    print(f"\n=== SAFE TESTING ADAPTIVE PROCESSOR ===")
    
    adaptive = AdaptiveExcelProcessor(
        "hardware_keywords.txt",
        "software_keywords.txt",
        learning_mode=True,
        min_occurrences=min_occurrences
    )
    
    # Test in safe mode (no auto-promotion)
    print(f"Testing with min_occurrences={min_occurrences}")
    success = adaptive.process_file(test_file, auto_promote=False, test_mode=True)
    
    if success:
        print("✅ Test processing successful")
        
        # Show learning analytics
        analytics = adaptive.generate_learning_analytics()
        print(f"\n📈 Learning Analytics:")
        print(f"   - HW candidates discovered: {analytics['hw_learning_rate']}")
        print(f"   - SW candidates discovered: {analytics['sw_learning_rate']}")
        print(f"   - Ready for promotion (HW): {len(analytics['promotion_candidates']['hw'])}")
        print(f"   - Ready for promotion (SW): {len(analytics['promotion_candidates']['sw'])}")
        
        # Show what would be promoted
        if analytics['promotion_candidates']['hw']:
            print(f"\n🔧 HW Keywords ready for promotion:")
            for keyword, count in analytics['promotion_candidates']['hw'][:5]:
                print(f"   - {keyword} (seen {count:.1f} times)")
        
        if analytics['promotion_candidates']['sw']:
            print(f"\n💻 SW Keywords ready for promotion:")
            for keyword, count in analytics['promotion_candidates']['sw'][:5]:
                print(f"   - {keyword} (seen {count:.1f} times)")
        
        return True
    else:
        print("❌ Test processing failed")
        return False

def update_monitor_script():
    """Provide instructions for updating monitor scripts."""
    print("\n=== UPDATING MONITOR SCRIPTS ===")
    
    instructions = """
To update your monitor scripts to use the adaptive processor:

1. Replace the import:
   OLD: from excel_processor import ExcelProcessor
   NEW: from adaptive_excel_processor import AdaptiveExcelProcessor

2. Update processor initialization:
   OLD: processor = ExcelProcessor(hw_file, sw_file, output_dir)
   NEW: processor = AdaptiveExcelProcessor(hw_file, sw_file, output_dir, learning_mode=True, min_occurrences=5)

3. Processing calls remain the same:
   processor.process_file(file_path)
   processor.process_directory(directory_path)

4. Optional: Add learning reports:
   print(processor.get_learning_report())

5. For testing, use test_mode=True:
   processor.process_file(file_path, test_mode=True)

The adaptive processor is backward compatible with your existing code!
"""
    
    print(instructions)

def main():
    """Main integration function."""
    logging.basicConfig(level=logging.INFO)
    
    print("=== ADAPTIVE PROCESSOR INTEGRATION HELPER ===")
    
    # Check for test files
    test_files = list(Path('.').glob('test*.xlsx')) + list(Path('.').glob('*.xlsx'))
    test_files = [f for f in test_files if not f.stem.endswith('_labeled')]
    
    if test_files:
        test_file = test_files[0]
        print(f"Found test file: {test_file}")
        
        # Migrate to adaptive
        processor = migrate_to_adaptive()
        if processor:
            # Compare processors
            compare_processors(test_file)
            
            # Safe test
            safe_test_adaptive(test_file)
            
            # Show learning report
            print("\n" + "="*50)
            print("LEARNING REPORT")
            print("="*50)
            print(processor.get_learning_report())
    
    # Show update instructions
    update_monitor_script()
    
    print("\n=== INTEGRATION COMPLETE ===")

if __name__ == "__main__":
    main()
