"""
Test script for the enhanced adaptive Excel processor.
Provides safe testing capabilities with detailed reporting.
"""

import logging
from pathlib import Path
from adaptive_excel_processor import AdaptiveExcelProcessor
import json

def setup_logging():
    """Setup logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('test_adaptive_processor.log'),
            logging.StreamHandler()
        ]
    )

def test_keyword_extraction():
    """Test the enhanced keyword extraction."""
    print("\n=== TESTING KEYWORD EXTRACTION ===")
    
    processor = AdaptiveExcelProcessor(learning_mode=True)
    
    test_descriptions = [
        "VIP ECO ULT FREEZER UPRIGHT 26 CU.FT. 115V - HC REFRIGERANT",
        "Nanosonic Printer Cart Mount 2",
        "LAB FREEZER UPRIGHT -30C, 17.8 CU.FT.",
        "MDF-C2156VANC-PA CRYOGENIC FREEZER CHEST 8 CU.FT",
        "Keating Lab : VIP ECO ULT FREEZER UPRIGHT 26 CU.FT. 115V - HC REFRIGERANT",
        "Agilent 7890B Gas Chromatograph with Mass Spectrometer",
        "Thermo Fisher Scientific Multimeter Model 12345",
        "Laboratory Balance Analytical Scale 0.1mg Precision",
        "Microplate Reader BioTek ELx800 Absorbance",
        "Software License Microsoft Office 365 Enterprise"
    ]
    
    for desc in test_descriptions:
        keywords = processor.extract_keywords_from_description(desc)
        print(f"\nDescription: {desc}")
        print(f"Extracted keywords: {keywords}")

def test_keyword_validation():
    """Test keyword validation logic."""
    print("\n=== TESTING KEYWORD VALIDATION ===")
    
    processor = AdaptiveExcelProcessor(learning_mode=True)
    
    test_keywords = [
        "spectrometer",  # Should be valid
        "freezer",       # Should be invalid (storage equipment)
        "cart",          # Should be invalid (accessory)
        "cu",           # Should be invalid (unit)
        "MDF-C2156VANC", # Should be invalid (model number)
        "analyzer",     # Should be valid
        "system",       # Should be invalid (too common)
        "microscope",   # Should be valid
        "123",          # Should be invalid (number)
        "precision",    # Should be valid
    ]
    
    for keyword in test_keywords:
        is_valid, reason = processor.validate_keyword(keyword, 'hw')
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{status}: '{keyword}' - {reason}")

def test_confidence_scoring():
    """Test confidence scoring system."""
    print("\n=== TESTING CONFIDENCE SCORING ===")
    
    processor = AdaptiveExcelProcessor(learning_mode=True)
    
    test_cases = [
        ("spectrometer", "Agilent 7890B Gas Chromatograph with Mass Spectrometer"),
        ("freezer", "VIP ECO ULT FREEZER UPRIGHT 26 CU.FT."),
        ("analyzer", "Laboratory Balance Analytical Scale 0.1mg Precision"),
        ("system", "Software License Microsoft Office 365 Enterprise System"),
        ("precision", "High Precision Laboratory Balance 0.1mg Accuracy"),
    ]
    
    for keyword, description in test_cases:
        confidence = processor.calculate_keyword_confidence(keyword, description)
        print(f"'{keyword}' in '{description[:50]}...' -> Confidence: {confidence:.2f}")

def test_with_sample_data(test_file=None):
    """Test the processor with actual Excel data."""
    print("\n=== TESTING WITH SAMPLE DATA ===")
    
    if not test_file:
        print("No test file provided. Create a test Excel file first.")
        return
    
    # Test in safe mode first
    processor = AdaptiveExcelProcessor(
        hw_keywords_file="hardware_keywords.txt",
        sw_keywords_file="software_keywords.txt",
        output_dir=r"D:\SOM_in_labeled",
        learning_mode=True,
        min_occurrences=3  # Lower threshold for testing
    )
    
    print("Testing in TEST MODE (no auto-promotion)...")
    success = processor.process_file(test_file, auto_promote=False, test_mode=True)
    
    if success:
        print("✓ File processed successfully in test mode")
        
        # Show what would be learned
        analytics = processor.generate_learning_analytics()
        print(f"\nLearning Analytics:")
        print(f"- HW candidates: {analytics['hw_learning_rate']}")
        print(f"- SW candidates: {analytics['sw_learning_rate']}")
        print(f"- Ready for promotion (HW): {len(analytics['promotion_candidates']['hw'])}")
        print(f"- Ready for promotion (SW): {len(analytics['promotion_candidates']['sw'])}")
        
        # Show top candidates
        print(f"\nTop HW Candidates:")
        for keyword, count in analytics['top_candidates']['hw'][:5]:
            print(f"  - {keyword}: {count:.1f}")
        
        print(f"\nTop SW Candidates:")
        for keyword, count in analytics['top_candidates']['sw'][:5]:
            print(f"  - {keyword}: {count:.1f}")
        
        return True
    else:
        print("✗ File processing failed")
        return False

def test_full_processing(test_file=None):
    """Test full processing with learning enabled."""
    print("\n=== TESTING FULL PROCESSING ===")
    
    if not test_file:
        print("No test file provided.")
        return
    
    processor = AdaptiveExcelProcessor(
        hw_keywords_file="hardware_keywords.txt",
        sw_keywords_file="software_keywords.txt",
        output_dir=r"D:\SOM_in_labeled",
        learning_mode=True,
        min_occurrences=2  # Very low for testing
    )
    
    print("Processing with learning enabled...")
    success = processor.process_file(test_file, auto_promote=True, test_mode=False)
    
    if success:
        print("✓ File processed with learning enabled")
        print(processor.get_learning_report())
        return True
    else:
        print("✗ File processing failed")
        return False

def main():
    """Main test function."""
    setup_logging()
    
    print("=== ENHANCED ADAPTIVE EXCEL PROCESSOR TEST SUITE ===")
    
    # Test individual components
    test_keyword_extraction()
    test_keyword_validation()
    test_confidence_scoring()
    
    # Test with sample data if available
    test_files = list(Path('.').glob('test*.xlsx')) + list(Path('.').glob('test*.xls'))
    
    if test_files:
        test_file = test_files[0]
        print(f"\nFound test file: {test_file}")
        
        # Test in safe mode first
        print("\n" + "="*50)
        print("SAFE MODE TESTING (Recommended first)")
        print("="*50)
        test_with_sample_data(test_file)
        
        # Ask user if they want to test full processing
        print("\n" + "="*50)
        response = input("Test full processing with learning enabled? (y/N): ").lower().strip()
        if response == 'y':
            print("FULL PROCESSING TEST")
            print("="*50)
            test_full_processing(test_file)
        else:
            print("Skipping full processing test.")
    else:
        print("\nNo test Excel files found. Create a test file to test with real data.")
    
    print("\n=== TEST SUITE COMPLETE ===")

if __name__ == "__main__":
    main()
