"""
Adaptive Excel processor with self-learning capabilities.
Classifies items as Research Instrument, Software, or Non-Instrument.
Learns new keywords from classification patterns and promotes them automatically.
"""

import pandas as pd
from pathlib import Path
import logging
from collections import Counter
import json
from datetime import datetime

from utils import (
    should_process, read_excel_file,
    find_description_column, find_supplier_column, clean_dataframe,
    _RE_MODEL_NUMBERS, _RE_MEASUREMENTS, _RE_NUMBER_SUFFIX, _RE_MODEL_PATTERN,
)

# Maximum candidates tracked per category before pruning oldest/lowest-scored entries
_MAX_CANDIDATES = 1000


class AdaptiveExcelProcessor:
    def __init__(self, hw_keywords_file=None, sw_keywords_file=None, ni_keywords_file=None,
                 output_dir=None, learning_mode=True, min_occurrences=5,
                 confidence_threshold=0.7):

        # Resolve output directory from config if not supplied
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            try:
                from config import config as _cfg
                self.output_dir = _cfg.output_directory
            except Exception:
                self.output_dir = Path(r"D:\SOM_in_labeled")

        self.hw_keywords = []
        self.sw_keywords = []
        self.ni_keywords = []
        self.learning_mode = learning_mode
        self.min_occurrences = min_occurrences
        self.confidence_threshold = confidence_threshold

        self.hw_keywords_file = Path(hw_keywords_file) if hw_keywords_file else None
        self.sw_keywords_file = Path(sw_keywords_file) if sw_keywords_file else None
        self.ni_keywords_file = Path(ni_keywords_file) if ni_keywords_file else None
        self.learning_log = self.output_dir / "learning_log.json"

        self.candidate_keywords = {'hw': Counter(), 'sw': Counter(), 'ni': Counter()}
        self._learning_dirty = False  # Only write log when candidates actually changed

        self.stopwords = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was', 'were',
            'model', 'part', 'number', 'serial', 'item', 'description', 'specification',
            'unit', 'each', 'piece', 'set', 'kit', 'assembly', 'component', 'accessory',
            'mount', 'cart', 'stand', 'holder', 'bracket', 'frame', 'base', 'support',
            'cabinet', 'storage', 'container', 'box', 'case', 'enclosure', 'housing',
        }

        self.vendor_keywords = {
            'ni': {
                'empire office inc', 'office depot', 'staples', 'amazon business',
                'steelcase', 'herman miller', 'knoll', 'haworth', 'humanscale',
                'ups', 'fedex', 'dhl',
            },
            'hw': {
                'thermo fisher scientific', 'agilent technologies', 'waters corporation',
                'beckman coulter', 'bio-rad laboratories', 'qiagen', 'promega',
                'zeiss', 'leica microsystems', 'olympus', 'eppendorf', 'sartorius',
                'applied biosystems', 'illumina', 'roche', 'abbott',
            },
            'sw': {
                'microsoft', 'adobe', 'autodesk', 'mathworks', 'graphpad',
                'spss', 'oracle', 'salesforce', 'tableau',
            },
        }

        self.technical_indicators = {
            'meter', 'analyzer', 'spectrometer', 'chromatograph', 'microscope',
            'detector', 'sensor', 'instrument', 'measurement', 'analysis', 'testing',
            'calibration', 'precision', 'accuracy', 'resolution', 'sensitivity',
            'monitor', 'controller', 'regulator', 'transducer', 'transmitter',
        }

        self.units = {
            'cu', 'ft', 'volts', 'watts', 'amps', 'hertz', 'pounds', 'inches',
            'mm', 'cm', 'kg', 'g', 'mg', 'ml', 'l', 'gal', 'psi', 'bar', 'pa',
            'celsius', 'fahrenheit', 'kelvin', 'rpm', 'hz', 'db', 'lux',
        }

        if hw_keywords_file and sw_keywords_file:
            self.load_keywords(hw_keywords_file, sw_keywords_file, ni_keywords_file)
            self.load_learning_log()

    # ------------------------------------------------------------------ #
    # Keyword loading / saving                                             #
    # ------------------------------------------------------------------ #

    def load_keywords(self, hw_file, sw_file, ni_file=None):
        """Load keyword lists from text files, ignoring comment lines."""
        def _load(path):
            return [
                l.strip().lower() for l in Path(path).read_text().splitlines()
                if l.strip() and not l.strip().startswith('#')
            ]

        try:
            self.hw_keywords = _load(hw_file)
            self.sw_keywords = _load(sw_file)
            if ni_file:
                self.ni_keywords = _load(ni_file)
            logging.info(
                f"Keywords loaded — HW: {len(self.hw_keywords)}, "
                f"SW: {len(self.sw_keywords)}, NI: {len(self.ni_keywords)}"
            )
        except Exception as e:
            logging.error(f"Error loading keywords: {e}")
            raise

    def load_learning_log(self):
        """Restore candidate keyword counts from the previous session."""
        if not self.learning_log.exists():
            return
        try:
            with open(self.learning_log) as f:
                data = json.load(f)
            self.candidate_keywords['hw'] = Counter(data.get('hw_candidates', {}))
            self.candidate_keywords['sw'] = Counter(data.get('sw_candidates', {}))
            self.candidate_keywords['ni'] = Counter(data.get('ni_candidates', {}))
            logging.info(
                f"Learning log loaded — HW: {len(self.candidate_keywords['hw'])}, "
                f"SW: {len(self.candidate_keywords['sw'])}, "
                f"NI: {len(self.candidate_keywords['ni'])} candidates"
            )
        except Exception as e:
            logging.warning(f"Could not load learning log: {e}")

    def save_learning_log(self):
        """Persist candidate keyword counts to disk (only when changed)."""
        if not self._learning_dirty:
            return
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
                    'learning_mode': self.learning_mode,
                },
            }
            with open(self.learning_log, 'w') as f:
                json.dump(data, f, indent=2)
            self._learning_dirty = False
            logging.info("Learning log saved")
        except Exception as e:
            logging.error(f"Error saving learning log: {e}")

    def _save_keywords(self, file_path, keywords):
        """Write a sorted keyword list to file."""
        try:
            Path(file_path).write_text('\n'.join(sorted(keywords)))
            logging.info(f"Updated {file_path}")
        except Exception as e:
            logging.error(f"Error saving keywords to {file_path}: {e}")

    # ------------------------------------------------------------------ #
    # Learning internals                                                   #
    # ------------------------------------------------------------------ #

    def extract_keywords_from_description(self, description):
        """Extract candidate keywords from a description string."""
        if not description:
            return []

        desc_clean = description.lower()
        desc_clean = _RE_MODEL_NUMBERS.sub('', desc_clean)
        desc_clean = _RE_MEASUREMENTS.sub('', desc_clean)

        keywords = []
        for word in desc_clean.split():
            clean = word.strip('.,;:()[]{}"\'-')
            if (
                len(clean) >= 3
                and clean not in self.stopwords
                and not clean.isdigit()
                and clean not in self.units
                and not _RE_NUMBER_SUFFIX.match(clean)
            ):
                keywords.append(clean)
        return keywords

    def calculate_keyword_confidence(self, keyword, description):
        """Score how likely a candidate keyword is genuinely meaningful."""
        desc_lower = description.lower()
        confidence = 1.0

        if any(ind in desc_lower for ind in self.technical_indicators):
            confidence *= 1.5

        if keyword in {'system', 'device', 'equipment', 'machine', 'tool', 'unit'}:
            confidence *= 0.5

        if len(keyword) > 8 and any(t in keyword for t in ('meter', 'scope', 'graph', 'analyzer')):
            confidence *= 1.3

        if len(keyword) < 4:
            confidence *= 0.7
        elif len(keyword) > 20:
            confidence *= 0.8

        return min(confidence, 3.0)

    def validate_keyword(self, keyword, category):
        """Check whether a candidate keyword meets promotion criteria."""
        if len(keyword) < 3:
            return False, "Too short"
        if keyword in self.units:
            return False, "Measurement unit"
        if _RE_MODEL_PATTERN.match(keyword) and len(keyword) > 6:
            return False, "Model number pattern"
        if _RE_NUMBER_SUFFIX.match(keyword):
            return False, "Number pattern"
        if keyword in self.stopwords:
            return False, "Common stopword"
        if any(t in keyword for t in ('meter', 'scope', 'graph', 'analyzer', 'detector', 'sensor')):
            return True, "Technical term"
        if 4 <= len(keyword) <= 15:
            return True, "Valid keyword"
        return False, "Failed validation"

    def _learn_from_classification(self, description, category):
        """Update candidate counters from a newly classified item."""
        keywords = self.extract_keywords_from_description(description)
        existing = {'hw': self.hw_keywords, 'sw': self.sw_keywords, 'ni': self.ni_keywords}.get(category, [])

        for kw in keywords:
            if kw not in existing:
                self.candidate_keywords[category][kw] += self.calculate_keyword_confidence(kw, description)
                self._learning_dirty = True

        # Prune if we exceed the cap — keep the highest-scored entries
        for cat in ('hw', 'sw', 'ni'):
            if len(self.candidate_keywords[cat]) > _MAX_CANDIDATES:
                top = self.candidate_keywords[cat].most_common(_MAX_CANDIDATES)
                self.candidate_keywords[cat] = Counter(dict(top))

    # ------------------------------------------------------------------ #
    # Classification                                                       #
    # ------------------------------------------------------------------ #

    def classify_by_vendor(self, vendor_name):
        """Return a category string based on vendor name, or None."""
        if not vendor_name:
            return None
        vendor_lower = vendor_name.lower()
        category_map = {'hw': "Research Instrument", 'sw': "Software", 'ni': "Non-Instrument"}
        for cat, keywords in self.vendor_keywords.items():
            if any(kw in vendor_lower for kw in keywords):
                return category_map[cat]
        return None

    def classify_item(self, description, vendor=None):
        """Classify one item using vendor then description rules."""
        if not description:
            return "Unknown"

        desc_lower = description.lower()

        vendor_result = self.classify_by_vendor(vendor)
        if vendor_result:
            if self.learning_mode:
                cat = 'hw' if vendor_result == "Research Instrument" else \
                      'sw' if vendor_result == "Software" else 'ni'
                self._learn_from_classification(description, cat)
            return vendor_result

        furniture_signals = (
            'cabinet', 'desk', 'table', 'chair', 'shelf', 'shelving', 'storage',
            'steelcase', 'worksurface', 'tackboard', 'end panel', 'desk legs',
            'ufb bracket', 'light shelf', 'led', 'locks', 'furniture', 'bench',
        )
        if any(s in desc_lower for s in furniture_signals):
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return "Non-Instrument"

        consumable_signals = (
            'kit', 'reagent', 'consumable', 'tube', 'tip', 'plate', 'vial',
            'filter', 'cable', 'adapter', 'power supply', 'battery', 'rack',
            'stand', 'mount', 'holder', 'box', 'bottle', 'accessory', 'part',
        )
        if any(s in desc_lower for s in consumable_signals):
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return "Non-Instrument"

        service_signals = (
            'service', 'installation', 'calibration', 'shipping', 'delivery',
            'training', 'support', 'maintenance', 'repair', 'consulting',
        )
        if any(s in desc_lower for s in service_signals):
            if self.learning_mode:
                self._learn_from_classification(description, 'ni')
            return "Non-Instrument"

        strong_sw_signals = (
            'software', 'license', 'licence', 'subscription', 'activation', 'key',
            'matlab', 'labview', 'flowjo', 'graphpad', 'prism', 'imagej', 'zen',
            'microsoft', 'adobe', 'autodesk', 'solidworks',
        )
        if any(s in desc_lower for s in strong_sw_signals):
            if self.learning_mode:
                self._learn_from_classification(description, 'sw')
            return "Software"

        strong_hw_signals = (
            'microscope', 'spectrometer', 'chromatograph', 'centrifuge', 'incubator',
            'autoclave', 'pcr', 'thermocycler', 'flowcytometer', 'plate reader',
            'imager', 'imaging', 'luminometer', 'sonicator', 'electrophoresis',
            'transilluminator', 'bioreactor', 'analyzer', 'balance', 'tem', 'sem', 'nmr',
        )
        if any(s in desc_lower for s in strong_hw_signals):
            if self.learning_mode:
                self._learn_from_classification(description, 'hw')
            return "Research Instrument"

        return "Unknown"

    # ------------------------------------------------------------------ #
    # Keyword promotion                                                    #
    # ------------------------------------------------------------------ #

    def backup_keywords_before_update(self):
        """Back up keyword files before modifying them."""
        backup_dir = self.output_dir / "#backup_logs"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        for attr, label in (
            ('hw_keywords_file', 'hardware'),
            ('sw_keywords_file', 'software'),
            ('ni_keywords_file', 'non_instrument'),
        ):
            src = getattr(self, attr)
            if src and src.exists():
                dest = backup_dir / f"{label}_keywords_backup_{ts}.txt"
                dest.write_text(src.read_text())
                logging.info(f"Backed up {label} keywords → {dest.name}")

    def promote_candidate_keywords(self, min_occurrences=None):
        """Promote candidates that exceed the occurrence threshold."""
        if min_occurrences is None:
            min_occurrences = self.min_occurrences

        promoted = {'hw': [], 'sw': [], 'ni': []}
        rejected = {'hw': [], 'sw': [], 'ni': []}

        kw_lists = {'hw': self.hw_keywords, 'sw': self.sw_keywords, 'ni': self.ni_keywords}

        for cat, kw_list in kw_lists.items():
            for keyword, count in self.candidate_keywords[cat].items():
                if count >= min_occurrences and keyword not in kw_list:
                    valid, reason = self.validate_keyword(keyword, cat)
                    if valid:
                        kw_list.append(keyword)
                        promoted[cat].append((keyword, count, reason))
                        logging.info(f"Promoted '{keyword}' → {cat} ({count:.1f} occurrences)")
                    else:
                        rejected[cat].append((keyword, count, reason))

        needs_backup = any(promoted[c] for c in ('hw', 'sw', 'ni'))
        if needs_backup:
            self.backup_keywords_before_update()

        file_map = {
            'hw': self.hw_keywords_file,
            'sw': self.sw_keywords_file,
            'ni': self.ni_keywords_file,
        }
        for cat, kw_list in kw_lists.items():
            if promoted[cat] and file_map[cat]:
                self._save_keywords(file_map[cat], kw_list)

        return promoted, rejected

    # ------------------------------------------------------------------ #
    # Reporting                                                            #
    # ------------------------------------------------------------------ #

    def generate_learning_analytics(self):
        totals = {c: sum(self.candidate_keywords[c].values()) for c in ('hw', 'sw', 'ni')}
        return {
            'total_classifications': sum(totals.values()),
            'hw_learning_rate': len(self.candidate_keywords['hw']),
            'sw_learning_rate': len(self.candidate_keywords['sw']),
            'ni_learning_rate': len(self.candidate_keywords['ni']),
            'promotion_candidates': {
                c: [(k, v) for k, v in self.candidate_keywords[c].items()
                    if v >= self.min_occurrences]
                for c in ('hw', 'sw', 'ni')
            },
            'top_candidates': {
                c: self.candidate_keywords[c].most_common(10)
                for c in ('hw', 'sw', 'ni')
            },
            'learning_health': {
                f'{c}_avg_confidence': totals[c] / max(len(self.candidate_keywords[c]), 1)
                for c in ('hw', 'sw', 'ni')
            },
        }

    def get_learning_report(self):
        a = self.generate_learning_analytics()
        lines = [
            f"\n=== ADAPTIVE LEARNING REPORT ===",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nCurrent Keywords:",
            f"  Research Instruments : {len(self.hw_keywords)}",
            f"  Software             : {len(self.sw_keywords)}",
            f"  Non-Instruments      : {len(self.ni_keywords)}",
            f"\nLearning Progress:",
            f"  Total classifications: {a['total_classifications']}",
            f"  Instrument candidates: {a['hw_learning_rate']}",
            f"  Software candidates  : {a['sw_learning_rate']}",
            f"  Non-Instr candidates : {a['ni_learning_rate']}",
            f"\nReady for Promotion (≥{self.min_occurrences} occurrences):",
            f"  Instruments  : {len(a['promotion_candidates']['hw'])}",
            f"  Software     : {len(a['promotion_candidates']['sw'])}",
            f"  Non-Instr    : {len(a['promotion_candidates']['ni'])}",
        ]
        for label, cat in (("Instrument", "hw"), ("Software", "sw"), ("Non-Instrument", "ni")):
            lines.append(f"\nTop {label} Candidates:")
            for kw, count in a['top_candidates'][cat][:5]:
                lines.append(f"  {kw}: {count:.1f}")
        return '\n'.join(lines)

    # ------------------------------------------------------------------ #
    # File processing                                                      #
    # ------------------------------------------------------------------ #

    def process_file(self, file_path, auto_promote=True, min_occurrences=None, test_mode=False):
        """Classify all items in one Excel file and write a labeled output file."""
        try:
            file_path = Path(file_path)
            if not should_process(file_path):
                logging.info(f"Skipping {file_path.name}")
                return False

            df = read_excel_file(file_path)
            desc_col = find_description_column(df)
            supplier_col = find_supplier_column(df)
            df = clean_dataframe(df)

            if supplier_col and supplier_col in df.columns:
                df.insert(0, 'TYPE', df.apply(
                    lambda row: self.classify_item(
                        row[desc_col],
                        row[supplier_col] if pd.notna(row[supplier_col]) else None,
                    ), axis=1
                ))
            else:
                df.insert(0, 'TYPE', df[desc_col].apply(self.classify_item))

            if auto_promote and self.learning_mode and not test_mode:
                promoted, rejected = self.promote_candidate_keywords(min_occurrences)
                hw_p, sw_p, ni_p = len(promoted['hw']), len(promoted['sw']), len(promoted['ni'])
                if any((hw_p, sw_p, ni_p)):
                    logging.info(f"Promoted — HW: {hw_p}, SW: {sw_p}, NI: {ni_p}")

            if self.learning_mode:
                self.save_learning_log()

            self.output_dir.mkdir(exist_ok=True)
            output_file = self.output_dir / (file_path.stem + '_labeled.xlsx')
            df.to_excel(output_file, index=False, engine='openpyxl')
            logging.info(f"Saved: {output_file.name}")
            return True

        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            return False

    def process_directory(self, directory_path, auto_promote=True, min_occurrences=None,
                          test_mode=False):
        """Classify all Excel files in a directory, promoting keywords once at the end."""
        directory = Path(directory_path)
        processed = 0

        for pattern in ('*.xls', '*.xlsx'):
            for fp in directory.glob(pattern):
                if self.process_file(fp, auto_promote=False,
                                     min_occurrences=min_occurrences,
                                     test_mode=test_mode):
                    processed += 1

        if auto_promote and self.learning_mode and not test_mode:
            promoted, rejected = self.promote_candidate_keywords(min_occurrences)
            logging.info(
                f"Batch promotion — HW: {len(promoted['hw'])}, "
                f"SW: {len(promoted['sw'])}, NI: {len(promoted['ni'])}"
            )

        if self.learning_mode:
            self.save_learning_log()
            print(self.get_learning_report())

        logging.info(f"Processed {processed} files in {directory}")
        return processed


# ------------------------------------------------------------------ #
# Module-level convenience functions                                   #
# ------------------------------------------------------------------ #

def process_single_file(file_path, hw_keywords_file, sw_keywords_file,
                        ni_keywords_file=None, output_dir=None,
                        learning_mode=True, min_occurrences=5, test_mode=False):
    processor = AdaptiveExcelProcessor(
        hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir,
        learning_mode=learning_mode, min_occurrences=min_occurrences,
    )
    return processor.process_file(file_path, test_mode=test_mode)


def process_directory(directory_path, hw_keywords_file, sw_keywords_file,
                      ni_keywords_file=None, output_dir=None,
                      learning_mode=True, min_occurrences=5, test_mode=False):
    processor = AdaptiveExcelProcessor(
        hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir,
        learning_mode=learning_mode, min_occurrences=min_occurrences,
    )
    return processor.process_directory(directory_path, test_mode=test_mode)


def generate_learning_report(hw_keywords_file, sw_keywords_file,
                              ni_keywords_file=None, output_dir=None):
    processor = AdaptiveExcelProcessor(
        hw_keywords_file, sw_keywords_file, ni_keywords_file, output_dir,
        learning_mode=True,
    )
    processor.load_learning_log()
    return processor.get_learning_report()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    from config import config as _cfg
    processor = AdaptiveExcelProcessor(
        hw_keywords_file=str(_cfg.hardware_keywords_file),
        sw_keywords_file=str(_cfg.software_keywords_file),
        ni_keywords_file=str(_cfg.non_instrument_keywords_file),
        output_dir=str(_cfg.output_directory),
        learning_mode=True,
        min_occurrences=5,
    )
    print(processor.get_learning_report())
