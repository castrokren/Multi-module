"""
Enhanced Adaptive Excel file processing module with self-learning capabilities.
Automatically discovers and adds new keywords based on classification patterns.
Includes improved keyword extraction, validation, confidence scoring, and safety features.
"""

import pandas as pd
from pathlib import Path
import warnings
import logging
from collections import Counter
import json
from datetime import datetime
import re

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class AdaptiveExcelProcessor:
    def __init__(self, hw_keywords_file=None, sw_keywords_file=None, ni_keywords_file=None, output_dir=None, 
                 learning_mode=True, min_occurrences=5, confidence_threshold=0.7):
        self.hw_keywords = []
        self.sw_keywords = []
        self.ni_keywords = []  # Non-Instrument keywords
        self.output_dir = Path(output_dir) if output_dir else Path(r"D:\SOM_in_labeled")
        self.learning_mode = learning_mode
        self.min_occurrences = min_occurrences
        self.confidence_threshold = confidence_threshold
        
        # Learning data structures
        self.hw_keywords_file = Path(hw_keywords_file) if hw_keywords_file else None
        self.sw_keywords_file = Path(sw_keywords_file) if sw_keywords_file else None
        self.ni_keywords_file = Path(ni_keywords_file) if ni_keywords_file else None
        self.learning_log = self.output_dir / "learning_log.json"
        self.candidate_keywords = {'hw': Counter(), 'sw': Counter(), 'ni': Counter()}
        
        # Enhanced stopwords and technical indicators
        self.stopwords = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was', 'were',
            'model', 'part', 'number', 'serial', 'item', 'description', 'specification',
            'unit', 'each', 'piece', 'set', 'kit', 'assembly', 'component', 'accessory',
            'mount', 'cart', 'stand', 'holder', 'bracket', 'frame', 'base', 'support',
            'cabinet', 'storage', 'container', 'box', 'case', 'enclosure', 'housing'
        }
        
        # Vendor-based classification keywords - SIMPLIFIED to avoid conflicts
        # Only use very specific, unambiguous vendor names
        self.vendor_keywords = {
            'ni': {  # Non-Instrument vendors - VERY SPECIFIC
                'empire office inc', 'office depot', 'staples', 'amazon business',
                'steelcase', 'herman miller', 'knoll', 'haworth', 'humanscale',
                'ups', 'fedex', 'dhl'
            },
            'hw': {  # Research Instrument vendors - VERY SPECIFIC
                'thermo fisher scientific', 'agilent technologies', 'waters corporation',
                'beckman coulter', 'bio-rad laboratories', 'qiagen', 'promega',
                'zeiss', 'leica microsystems', 'olympus', 'eppendorf', 'sartorius',
                'applied biosystems', 'illumina', 'roche', 'abbott'
            },
            'sw': {  # Software vendors - VERY SPECIFIC
                'microsoft', 'adobe', 'autodesk', 'mathworks', 'graphpad',
                'spss', 'oracle', 'salesforce', 'tableau'
            }
        }
        
        self.technical_indicators = {
            'meter', 'analyzer', 'spectrometer', 'chromatograph', 'microscope', 
            'detector', 'sensor', 'instrument', 'measurement', 'analysis', 'testing',
            'calibration', 'precision', 'accuracy', 'resolution', 'sensitivity',
            'monitor', 'controller', 'regulator', 'transducer', 'transmitter'
        }
        
        self.units = {
            'cu', 'ft', 'volts', 'watts', 'amps', 'hertz', 'pounds', 'inches', 
            'mm', 'cm', 'kg', 'g', 'mg', 'ml', 'l', 'gal', 'psi', 'bar', 'pa',
            'celsius', 'fahrenheit', 'kelvin', 'rpm', 'hz', 'db', 'lux'
        }
        
        if hw_keywords_file and sw_keywords_file:
            self.load_keywords(hw_keywords_file, sw_keywords_file, ni_keywords_file)
            self.load_learning_log()

    def load_keywords(self, hw_file, sw_file, ni_file=None):
        """Load hardware, software, and non-instrument keywords from files."""
        try:
            hw_content = Path(hw_file).read_text()
            sw_content = Path(sw_file).read_text()
            
            # Filter out commented lines and empty lines
            self.hw_keywords = [
                l.strip().lower() for l in hw_content.splitlines() 
                if l.strip() and not l.strip().startswith('#')
            ]
            self.sw_keywords = [
                l.strip().lower() for l in sw_content.splitlines() 
                if l.strip() and not l.strip().startswith('#')
            ]
            
            # Load non-instrument keywords if file provided
            if ni_file:
                ni_content = Path(ni_file).read_text()
                self.ni_keywords = [
                    l.strip().lower() for l in ni_content.splitlines() 
                    if l.strip() and not l.strip().startswith('#')
                ]
            
            logging.info(f"Loaded {len(self.hw_keywords)} hardware, {len(self.sw_keywords)} software, and {len(self.ni_keywords)} non-instrument keywords")
        except Exception as e:
            logging.error(f"Error loading keywords: {e}")
            raise

    def load_learning_log(self):
        """Load previous learning data."""
        if self.learning_log.exists():
            try:
                with open(self.learning_log, 'r') as f:
                    data = json.load(f)
                    self.candidate_keywords['hw'] = Counter(data.get('hw_candidates', {}))
                    self.candidate_keywords['sw'] = Counter(data.get('sw_candidates', {}))
                    self.candidate_keywords['ni'] = Counter(data.get('ni_candidates', {}))
                logging.info(f"Loaded learning log with {len(self.candidate_keywords['hw'])} HW, {len(self.candidate_keywords['sw'])} SW, and {len(self.candidate_keywords['ni'])} NI candidates")
            except Exception as e:
                logging.warning(f"Could not load learning log: {e}")

    def save_learning_log(self):
        """Save learning data to file."""
        try:
            self.output_dir.mkdir(exist_ok=True)
            data = {
                'hw_candidates': dict(self.candidate_keywords['hw']),
                'sw_candidates': dict(self.candidate_keywords['sw']),
                'ni_candidates': dict(self.candidate_keywords['ni']),
                'last_updated': datetime.now().isoformat(),
                'settings': {
                    'min_occurrences': self.min_occurrences,
                    'confidence_threshold': self.confidence_threshold,
                    'learning_mode': self.learning_mode
                }
            }
            with open(self.learning_log, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info("Saved learning log")
        except Exception as e:
            logging.error(f"Error saving learning log: {e}")

    def extract_keywords_from_description(self, description):
        """Enhanced keyword extraction with better filtering."""
        if not description:
            return []
        
        # Clean the description
        desc_clean = description.lower()
        
        # Remove model numbers, serial numbers, and measurements
        desc_clean = re.sub(r'\b[A-Z0-9\-]{6,}\b', '', desc_clean)  # Model numbers like MDF-C2156VANC-PA
        desc_clean = re.sub(r'\b\d+\s*(cu\.ft\.|volts?|v|w|a|hz|rpm|db|lux|psi|bar)\b', '', desc_clean)  # Measurements
        desc_clean = re.sub(r'\b\d+\.\d+\s*(cu\.ft\.|volts?|v|w|a|hz|rpm|db|lux|psi|bar)\b', '', desc_clean)  # Decimal measurements
        
        # Extract words
        words = desc_clean.split()
        keywords = []
        
        for word in words:
            # Clean word
            clean_word = word.strip('.,;:()[]{}"\'-')
            
            # Filter criteria
            if (len(clean_word) >= 3 and 
                clean_word not in self.stopwords and 
                not clean_word.isdigit() and
                clean_word not in self.units and
                not re.match(r'^\d+[a-z]*$', clean_word)):  # Numbers with letters
                keywords.append(clean_word)
        
        return keywords

    def calculate_keyword_confidence(self, keyword, description):
        """Calculate confidence score for a potential keyword."""
        desc_lower = description.lower()
        confidence = 1.0
        
        # Higher confidence for keywords in technical contexts
        if any(indicator in desc_lower for indicator in self.technical_indicators):
            confidence *= 1.5
        
        # Reduce confidence for common words that might be false positives
        common_words = {'system', 'device', 'equipment', 'machine', 'tool', 'unit'}
        if keyword in common_words:
            confidence *= 0.5
        
        # Boost confidence for compound technical terms
        if len(keyword) > 8 and any(tech in keyword for tech in ['meter', 'scope', 'graph', 'analyzer']):
            confidence *= 1.3
        
        # Reduce confidence for very short or very long words
        if len(keyword) < 4:
            confidence *= 0.7
        elif len(keyword) > 20:
            confidence *= 0.8
        
        return min(confidence, 3.0)  # Cap at 3.0

    def validate_keyword(self, keyword, category):
        """Validate if a keyword should be promoted."""
        # Reject if too short
        if len(keyword) < 3:
            return False, "Too short"
        
        # Reject if it's a measurement unit
        if keyword in self.units:
            return False, "Measurement unit"
        
        # Reject if it's a model number pattern
        if re.match(r'^[a-z0-9\-]{2,}$', keyword) and len(keyword) > 6:
            return False, "Model number pattern"
        
        # Reject if it's mostly numbers
        if re.match(r'^\d+[a-z]*$', keyword):
            return False, "Number pattern"
        
        # Reject if it's a common non-technical word
        if keyword in self.stopwords:
            return False, "Common stopword"
        
        # Accept if it contains technical indicators
        if any(tech in keyword for tech in ['meter', 'scope', 'graph', 'analyzer', 'detector', 'sensor']):
            return True, "Technical term"
        
        # Accept if it's a reasonable length and not obviously wrong
        if 4 <= len(keyword) <= 15:
            return True, "Valid keyword"
        
        return False, "Failed validation"

    @staticmethod
    def should_process(file_path):
        """Check if file should be processed based on name and extension."""
        path = Path(file_path)
        
        if path.name.startswith('~$') or path.stem.endswith('_labeled'):
            return False
            
        return path.suffix.lower() in ['.xls', '.xlsx']

    def read_excel_file(self, file_path):
        """Read Excel file with appropriate engine based on extension."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.xls':
            engine = 'xlrd'
        elif file_ext == '.xlsx':
            engine = 'openpyxl'
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        try:
            df = pd.read_excel(file_path, header=1, engine=engine)
            logging.info(f"Successfully read {file_path.name} using {engine} engine")
            return df
        except Exception as e:
            logging.error(f"Error reading {file_path.name}: {e}")
            raise

    def find_description_column(self, df):
        """Find the description column dynamically."""
        desc_cols = [c for c in df.columns if 'description' in c.lower()]
        
        if not desc_cols:
            patterns = ['desc', 'item', 'name', 'title', 'product', 'material']
            desc_cols = [c for c in df.columns if any(word in c.lower() for word in patterns)]
        
        if not desc_cols:
            available_cols = ', '.join(df.columns[:10])
            raise ValueError(f"No description column found. Available columns: {available_cols}...")
        
        desc_col = desc_cols[0]
        logging.info(f"Using '{desc_col}' as description column")
        return desc_col
    
    def find_supplier_column(self, df):
        """Find the supplier/vendor column dynamically."""
        supplier_cols = [c for c in df.columns if 'supplier' in c.lower()]
        
        if not supplier_cols:
            patterns = ['vendor', 'company', 'manufacturer', 'distributor', 'source']
            supplier_cols = [c for c in df.columns if any(word in c.lower() for word in patterns)]
        
        if supplier_cols:
            supplier_col = supplier_cols[0]
            logging.info(f"Using '{supplier_col}' as supplier column")
            return supplier_col
        else:
            logging.info("No supplier column found - vendor-based classification disabled")
            return None
    
    def classify_by_vendor(self, vendor_name):
        """Classify item based on vendor name."""
        if not vendor_name:
            return None
            
        vendor_lower = vendor_name.lower()
        
        # Check each category's vendor keywords
        for category, keywords in self.vendor_keywords.items():
            if any(keyword in vendor_lower for keyword in keywords):
                if category == 'hw':
                    return "Research Instrument"
                elif category == 'sw':
                    return "Software"
                elif category == 'ni':
                    return "Non-Instrument"
        
        return None

    def classify_item(self, description, vendor=None):
        """Classify item based on description and vendor with three-category system."""
        if not description:
            return "Unknown"
            
        desc_lower = description.lower()
        
        # STRONG vendor-based classification (highest priority)
        vendor_classification = self.classify_by_vendor(vendor)
        if vendor_classification:
            logging.debug(f"Vendor-based classification: '{vendor}' → {vendor_classification}")
            # Learn from vendor classification
            if self.learning_mode:
                category = 'hw' if vendor_classification == "Research Instrument" else \
                          'sw' if vendor_classification == "Software" else 'ni'
                self._learn_from_classification(description, category)
            return vendor_classification
        
        # Fall back to description-based classification with CLEAR rules
        # Rule 1: If it's furniture/office equipment, it's Non-Instrument
        furniture_signals = [
            'cabinet', 'desk', 'table', 'chair', 'shelf', 'shelving', 'storage',
            'steelcase', 'worksurface', 'tackboard', 'end panel', 'desk legs', 
            'ufb bracket', 'light shelf', 'led', 'locks', 'furniture', 'bench'
        ]
        
        if any(signal in desc_lower for signal in furniture_signals):
            classification = "Non-Instrument"
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return classification
        
        # Rule 2: If it's consumables/supplies, it's Non-Instrument
        consumable_signals = [
            'kit', 'reagent', 'consumable', 'tube', 'tip', 'plate', 'vial',
            'filter', 'cable', 'adapter', 'power supply', 'battery', 'rack',
            'stand', 'mount', 'holder', 'box', 'bottle', 'accessory', 'part'
        ]
        
        if any(signal in desc_lower for signal in consumable_signals):
            classification = "Non-Instrument"
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return classification
        
        # Rule 3: If it's a service, it's Non-Instrument
        service_signals = [
            'service', 'installation', 'calibration', 'shipping', 'delivery',
            'training', 'support', 'maintenance', 'repair', 'consulting'
        ]
        
        if any(signal in desc_lower for signal in service_signals):
            classification = "Non-Instrument"
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return classification
        
        # Check for strong software signals
        strong_sw_signals = [
            'software', 'license', 'licence', 'subscription', 'activation', 'key',
            'matlab', 'labview', 'flowjo', 'graphpad', 'prism', 'imagej', 'zen',
            'microsoft', 'adobe', 'autodesk', 'solidworks'
        ]
        
        if any(signal in desc_lower for signal in strong_sw_signals):
            classification = "Software"
            if self.learning_mode:
                self._learn_from_classification(description, 'sw')
            return classification
        
        # Check for strong research instrument signals
        strong_hw_signals = [
            'microscope', 'spectrometer', 'chromatograph', 'centrifuge', 'incubator',
            'autoclave', 'pcr', 'thermocycler', 'flowcytometer', 'plate reader',
            'imager', 'imaging', 'luminometer', 'sonicator', 'electrophoresis',
            'transilluminator', 'bioreactor', 'analyzer', 'balance', 'tem', 'sem', 'nmr'
        ]
        
        if any(signal in desc_lower for signal in strong_hw_signals):
            classification = "Research Instrument"
            if self.learning_mode:
                self._learn_from_classification(description, 'hw')
            return classification
        
        # No strong signals - unknown
        return "Unknown"

    def _learn_from_classification(self, description, category):
        """Learn new potential keywords from classified items with confidence scoring."""
        keywords = self.extract_keywords_from_description(description)
        
        # Get the appropriate existing keyword list based on category
        if category == 'hw':
            existing = self.hw_keywords
        elif category == 'sw':
            existing = self.sw_keywords
        elif category == 'ni':
            existing = self.ni_keywords
        else:
            return  # Invalid category
        
        for keyword in keywords:
            if keyword not in existing:
                confidence = self.calculate_keyword_confidence(keyword, description)
                self.candidate_keywords[category][keyword] += confidence

    def backup_keywords_before_update(self):
        """Create backup of keyword files before updating."""
        backup_dir = self.output_dir / "#backup_logs"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.hw_keywords_file and self.hw_keywords_file.exists():
            backup_hw = backup_dir / f"hardware_keywords_backup_{timestamp}.txt"
            backup_hw.write_text(self.hw_keywords_file.read_text())
            logging.info(f"Backed up hardware keywords to {backup_hw}")
        
        if self.sw_keywords_file and self.sw_keywords_file.exists():
            backup_sw = backup_dir / f"software_keywords_backup_{timestamp}.txt"
            backup_sw.write_text(self.sw_keywords_file.read_text())
            logging.info(f"Backed up software keywords to {backup_sw}")
        
        if self.ni_keywords_file and self.ni_keywords_file.exists():
            backup_ni = backup_dir / f"non_instrument_keywords_backup_{timestamp}.txt"
            backup_ni.write_text(self.ni_keywords_file.read_text())
            logging.info(f"Backed up non-instrument keywords to {backup_ni}")

    def promote_candidate_keywords(self, min_occurrences=None):
        """Promote frequently occurring candidate keywords with validation."""
        if min_occurrences is None:
            min_occurrences = self.min_occurrences
            
        promoted = {'hw': [], 'sw': [], 'ni': []}
        rejected = {'hw': [], 'sw': [], 'ni': []}
        
        for category in ['hw', 'sw', 'ni']:
            # Get the appropriate keyword list
            if category == 'hw':
                keywords_list = self.hw_keywords
            elif category == 'sw':
                keywords_list = self.sw_keywords
            else:  # 'ni'
                keywords_list = self.ni_keywords
            
            for keyword, count in self.candidate_keywords[category].items():
                if count >= min_occurrences and keyword not in keywords_list:
                    is_valid, reason = self.validate_keyword(keyword, category)
                    
                    if is_valid:
                        keywords_list.append(keyword)
                        promoted[category].append((keyword, count, reason))
                        logging.info(f"Promoted '{keyword}' to {category} keywords (seen {count:.1f} times) - {reason}")
                    else:
                        rejected[category].append((keyword, count, reason))
                        logging.warning(f"Rejected '{keyword}' - {reason}")
        
        # Save updated keyword files with backup
        needs_backup = False
        if promoted['hw'] and self.hw_keywords_file:
            needs_backup = True
        if promoted['sw'] and self.sw_keywords_file:
            needs_backup = True
        if promoted['ni'] and self.ni_keywords_file:
            needs_backup = True
        
        if needs_backup:
            self.backup_keywords_before_update()
        
        if promoted['hw'] and self.hw_keywords_file:
            self._save_keywords(self.hw_keywords_file, self.hw_keywords)
        if promoted['sw'] and self.sw_keywords_file:
            self._save_keywords(self.sw_keywords_file, self.sw_keywords)
        if promoted['ni'] and self.ni_keywords_file:
            self._save_keywords(self.ni_keywords_file, self.ni_keywords)
        
        return promoted, rejected

    def _save_keywords(self, file_path, keywords):
        """Save keywords to file."""
        try:
            with open(file_path, 'w') as f:
                f.write('\n'.join(sorted(keywords)))
            logging.info(f"Updated {file_path}")
        except Exception as e:
            logging.error(f"Error saving keywords to {file_path}: {e}")

    def generate_learning_analytics(self):
        """Generate detailed analytics about learning progress."""
        total_hw_candidates = sum(self.candidate_keywords['hw'].values())
        total_sw_candidates = sum(self.candidate_keywords['sw'].values())
        total_ni_candidates = sum(self.candidate_keywords['ni'].values())
        
        analytics = {
            'total_classifications': total_hw_candidates + total_sw_candidates + total_ni_candidates,
            'hw_learning_rate': len(self.candidate_keywords['hw']),
            'sw_learning_rate': len(self.candidate_keywords['sw']),
            'ni_learning_rate': len(self.candidate_keywords['ni']),
            'promotion_candidates': {
                'hw': [(k, v) for k, v in self.candidate_keywords['hw'].items() if v >= self.min_occurrences],
                'sw': [(k, v) for k, v in self.candidate_keywords['sw'].items() if v >= self.min_occurrences],
                'ni': [(k, v) for k, v in self.candidate_keywords['ni'].items() if v >= self.min_occurrences]
            },
            'top_candidates': {
                'hw': self.candidate_keywords['hw'].most_common(10),
                'sw': self.candidate_keywords['sw'].most_common(10),
                'ni': self.candidate_keywords['ni'].most_common(10)
            },
            'learning_health': {
                'hw_avg_confidence': total_hw_candidates / max(len(self.candidate_keywords['hw']), 1),
                'sw_avg_confidence': total_sw_candidates / max(len(self.candidate_keywords['sw']), 1),
                'ni_avg_confidence': total_ni_candidates / max(len(self.candidate_keywords['ni']), 1)
            }
        }
        return analytics

    def get_learning_report(self):
        """Generate a comprehensive learning report."""
        analytics = self.generate_learning_analytics()
        
        report = f"""
=== ADAPTIVE LEARNING REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Current Keywords:
- Research Instruments: {len(self.hw_keywords)} keywords
- Software: {len(self.sw_keywords)} keywords
- Non-Instruments: {len(self.ni_keywords)} keywords

Learning Progress:
- Total classifications learned from: {analytics['total_classifications']}
- Instrument candidates: {analytics['hw_learning_rate']}
- Software candidates: {analytics['sw_learning_rate']}
- Non-Instrument candidates: {analytics['ni_learning_rate']}

Ready for Promotion (≥{self.min_occurrences} occurrences):
- Instruments: {len(analytics['promotion_candidates']['hw'])} candidates
- Software: {len(analytics['promotion_candidates']['sw'])} candidates
- Non-Instruments: {len(analytics['promotion_candidates']['ni'])} candidates

Top Instrument Candidates:
"""
        for keyword, count in analytics['top_candidates']['hw'][:5]:
            report += f"  - {keyword}: {count:.1f}\n"
        
        report += "\nTop Software Candidates:\n"
        for keyword, count in analytics['top_candidates']['sw'][:5]:
            report += f"  - {keyword}: {count:.1f}\n"
        
        report += "\nTop Non-Instrument Candidates:\n"
        for keyword, count in analytics['top_candidates']['ni'][:5]:
            report += f"  - {keyword}: {count:.1f}\n"
        
        return report

    def clean_dataframe(self, df):
        """Remove unwanted columns from dataframe."""
        cols = df.columns.tolist()
        drop_indices = list(range(0, 6)) + [7] + list(range(9, 13)) + list(range(15, 32))
        to_drop = [cols[i] for i in drop_indices if i < len(cols)]
        
        df.drop(columns=to_drop, inplace=True, errors='ignore')
        return df

    def process_file(self, file_path, auto_promote=True, min_occurrences=None, test_mode=False):
        """Process a single Excel file: read, classify, clean, and save."""
        try:
            file_path = Path(file_path)
            
            if not self.should_process(file_path):
                logging.info(f"Skipping {file_path.name} - should not be processed")
                return False

            df = self.read_excel_file(file_path)
            desc_col = self.find_description_column(df)
            supplier_col = self.find_supplier_column(df)
            df = self.clean_dataframe(df)
            
            # Classify items using both description and supplier (learning happens here)
            if supplier_col and supplier_col in df.columns:
                # Use both description and supplier for classification
                df.insert(0, 'TYPE', df.apply(lambda row: self.classify_item(
                    row[desc_col], 
                    row[supplier_col] if pd.notna(row[supplier_col]) else None
                ), axis=1))
                logging.info(f"Using description column '{desc_col}' and supplier column '{supplier_col}' for classification")
            else:
                # Fall back to description-only classification
                df.insert(0, 'TYPE', df[desc_col].apply(self.classify_item))
                logging.info(f"Using description column '{desc_col}' only for classification")
            
            # Auto-promote candidate keywords if enabled and not in test mode
            if auto_promote and self.learning_mode and not test_mode:
                promoted, rejected = self.promote_candidate_keywords(min_occurrences)
                if promoted['hw'] or promoted['sw'] or promoted['ni']:
                    logging.info(f"Auto-promoted {len(promoted['hw'])} Instrument, {len(promoted['sw'])} Software, and {len(promoted['ni'])} Non-Instrument keywords")
                if rejected['hw'] or rejected['sw'] or rejected['ni']:
                    logging.info(f"Rejected {len(rejected['hw'])} Instrument, {len(rejected['sw'])} Software, and {len(rejected['ni'])} Non-Instrument candidates")
            
            # Save learning log
            if self.learning_mode:
                self.save_learning_log()
            
            # Save processed file
            self.output_dir.mkdir(exist_ok=True)
            output_file = self.output_dir / (file_path.stem + '_labeled.xlsx')
            df.to_excel(output_file, index=False, engine='openpyxl')
            
            logging.info(f"Successfully processed and saved: {output_file.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            return False

    def process_directory(self, directory_path, auto_promote=True, min_occurrences=None, test_mode=False):
        """Process all Excel files in a directory."""
        directory = Path(directory_path)
        processed_count = 0
        
        for pattern in ['*.xls', '*.xlsx']:
            for file_path in directory.glob(pattern):
                if self.process_file(file_path, auto_promote=False, min_occurrences=min_occurrences, test_mode=test_mode):
                    processed_count += 1
        
        # Promote keywords once after processing all files
        if auto_promote and self.learning_mode and not test_mode:
            promoted, rejected = self.promote_candidate_keywords(min_occurrences)
            logging.info(f"Batch promoted {len(promoted['hw'])} Instrument, {len(promoted['sw'])} Software, and {len(promoted['ni'])} Non-Instrument keywords")
            logging.info(f"Batch rejected {len(rejected['hw'])} Instrument, {len(rejected['sw'])} Software, and {len(rejected['ni'])} Non-Instrument candidates")
        
        # Save learning log
        if self.learning_mode:
            self.save_learning_log()
        
        # Print learning report
        if self.learning_mode:
            print(self.get_learning_report())
        
        logging.info(f"Processed {processed_count} files in {directory}")
        return processed_count


# Convenience functions
def process_single_file(file_path, hw_keywords_file, sw_keywords_file, ni_keywords_file=None, output_dir=None, 
                       learning_mode=True, min_occurrences=5, test_mode=False):
    """Process a single file with adaptive learning."""
    processor = AdaptiveExcelProcessor(
        hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir, 
        learning_mode=learning_mode, min_occurrences=min_occurrences
    )
    return processor.process_file(file_path, test_mode=test_mode)

def process_directory(directory_path, hw_keywords_file, sw_keywords_file, ni_keywords_file=None, output_dir=None, 
                     learning_mode=True, min_occurrences=5, test_mode=False):
    """Process all files in directory with adaptive learning."""
    processor = AdaptiveExcelProcessor(
        hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir, 
        learning_mode=learning_mode, min_occurrences=min_occurrences
    )
    return processor.process_directory(directory_path, test_mode=test_mode)

def generate_learning_report(hw_keywords_file, sw_keywords_file, ni_keywords_file=None, output_dir=None):
    """Generate a learning report without processing files."""
    processor = AdaptiveExcelProcessor(hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir, learning_mode=True)
    processor.load_learning_log()
    return processor.get_learning_report()

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test with conservative settings and three-category system
    processor = AdaptiveExcelProcessor(
        hw_keywords_file="research_instrument_keywords.txt",
        sw_keywords_file="software_keywords.txt",
        ni_keywords_file="non_instrument_keywords.txt",
        output_dir=r"D:\SOM_in_labeled",
        learning_mode=True,
        min_occurrences=5
    )
    
    # Print initial learning report
    print(processor.get_learning_report())
