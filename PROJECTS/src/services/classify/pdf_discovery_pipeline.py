"""
PDF Discovery Pipeline
======================
Integrates classified items with PDF discovery and document extraction.

Pipeline:
1. Load classified items (with supplier names)
2. Match suppliers to masterlist (get vendor websites)
3. Run ScraperEngine to download relevant PDFs
4. Convert PDFs to .txt/.md format
5. Organize output for Power Automate
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class PDFDiscoveryPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, classified_file: str, masterlist_file: str, output_dir: str, scraper_engine_path: str):
        """
        Args:
            classified_file: Path to classified Excel file with TYPE and Supplier Name columns
            masterlist_file: Path to masterlist Excel file mapping Supplier Name -> Website
            output_dir: Where to save PDFs and converted documents
            scraper_engine_path: Path to ScraperEngine module
        """
        self.classified_file = Path(classified_file)
        self.masterlist_file = Path(masterlist_file)
        self.output_dir = Path(output_dir)
        self.scraper_engine_path = Path(scraper_engine_path)

        self.df_classified = None
        self.df_masterlist = None
        self.supplier_matches = {}

    def load_data(self):
        """Load classified items and masterlist."""
        logger.info(f"Loading classified data: {self.classified_file.name}")
        self.df_classified = pd.read_excel(self.classified_file)

        logger.info(f"Loading masterlist: {self.masterlist_file.name}")
        self.df_masterlist = pd.read_excel(self.masterlist_file)

        logger.info(f"Classified: {len(self.df_classified)} items")
        logger.info(f"Masterlist: {len(self.df_masterlist)} suppliers")

    def match_suppliers(self) -> Dict[str, str]:
        """
        Match classified suppliers to masterlist websites.
        Returns: {supplier_name: website_url}
        """
        logger.info("Matching suppliers to masterlist...")

        matches = {}
        unmatched = []

        for supplier in self.df_classified['Supplier Name'].unique():
            row = self.df_masterlist[self.df_masterlist['Supplier Name'] == supplier]
            if len(row) > 0:
                website = row.iloc[0]['Website']
                matches[supplier] = website
            else:
                unmatched.append(supplier)

        logger.info(f"Matched: {len(matches)} suppliers")
        logger.info(f"Unmatched: {len(unmatched)} suppliers (will be skipped)")

        if unmatched:
            logger.warning(f"Unmatched suppliers: {unmatched[:5]}...")

        self.supplier_matches = matches
        return matches

    def create_supplier_excel(self) -> Path:
        """
        Create supplier Excel file for ScraperEngine.
        Format: [Supplier Name, Website]
        """
        logger.info("Creating supplier list for ScraperEngine...")

        supplier_list = [
            {'Supplier Name': name, 'Website': website}
            for name, website in self.supplier_matches.items()
        ]

        df = pd.DataFrame(supplier_list)

        supplier_file = self.output_dir / "suppliers_for_scraping.xlsx"
        df.to_excel(supplier_file, index=False)

        logger.info(f"Created supplier list: {supplier_file.name} ({len(df)} suppliers)")
        return supplier_file

    def run_scraper(self, supplier_file: Path) -> Path:
        """
        Run ScraperEngine to download PDFs.
        Returns: Path to PDFs directory
        """
        logger.info("Running ScraperEngine to download PDFs...")

        pdfs_dir = self.output_dir / "raw_pdfs"
        pdfs_dir.mkdir(exist_ok=True)

        # Import and run ScraperEngine
        try:
            import sys
            sys.path.insert(0, str(self.scraper_engine_path.parent))
            from scraper_engine import ScraperEngine

            engine = ScraperEngine(
                use_relevance_filter=True,
                allowlist_only=False,  # Accept all relevant docs
                skip_recent_sites=False,
            )

            result = engine.run(str(supplier_file), str(pdfs_dir))

            logger.info(f"ScraperEngine complete:")
            logger.info(f"  Pages crawled: {result.get('pages', 0)}")
            logger.info(f"  PDFs downloaded: {result.get('pdfs', 0)}")

            return pdfs_dir

        except Exception as e:
            logger.error(f"ScraperEngine failed: {e}")
            raise

    def convert_pdfs_to_text(self, pdfs_dir: Path) -> Path:
        """
        Convert all PDFs in directory to .txt and .md format.
        Uses pdfplumber for extraction.
        """
        logger.info("Converting PDFs to text format...")

        text_dir = self.output_dir / "documents_text"
        text_dir.mkdir(exist_ok=True)

        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed. Install: pip install pdfplumber")
            raise

        pdf_files = list(pdfs_dir.glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to convert")

        converted_count = 0
        failed_count = 0

        for pdf_file in pdf_files:
            try:
                # Extract text from PDF
                with pdfplumber.open(pdf_file) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

                if not text.strip():
                    logger.warning(f"No text extracted from {pdf_file.name}")
                    continue

                # Save as .txt
                txt_file = text_dir / (pdf_file.stem + ".txt")
                txt_file.write_text(text, encoding='utf-8')

                # Also save as .md (same content, different extension for Power Automate)
                md_file = text_dir / (pdf_file.stem + ".md")
                md_file.write_text(text, encoding='utf-8')

                converted_count += 1

                if converted_count % 10 == 0:
                    logger.info(f"Converted {converted_count} PDFs...")

            except Exception as e:
                logger.error(f"Failed to convert {pdf_file.name}: {e}")
                failed_count += 1

        logger.info(f"Conversion complete: {converted_count} successful, {failed_count} failed")
        return text_dir

    def create_index(self, text_dir: Path) -> Path:
        """
        Create index mapping classified items to their documentation.
        Maps item -> supplier -> documents found
        """
        logger.info("Creating document index...")

        # Get list of text files by supplier
        text_files_by_supplier = {}
        for txt_file in text_dir.glob("*.txt"):
            # Filename format: supplier_name_or_doc.txt
            # Extract supplier name (first part before numbers/special chars)
            supplier_hint = txt_file.stem.split('_')[0]
            text_files_by_supplier.setdefault(supplier_hint, []).append(txt_file)

        # Create mapping of items to documents
        index = []
        for _, row in self.df_classified.iterrows():
            item_desc = row.get('Item Description', '')
            supplier = row.get('Supplier Name', '')
            item_type = row.get('TYPE', '')

            # Find documents for this supplier
            docs = []
            for supplier_name in self.supplier_matches.keys():
                if supplier_name.lower() in supplier.lower() or supplier.lower() in supplier_name.lower():
                    # Find matching text files
                    for txt_file in text_dir.glob("*.txt"):
                        if supplier_name.lower() in txt_file.stem.lower():
                            docs.append(str(txt_file.relative_to(self.output_dir)))

            index.append({
                'Item Description': item_desc,
                'Supplier Name': supplier,
                'TYPE': item_type,
                'Documentation Files': '; '.join(docs) if docs else 'NOT FOUND',
                'Document Count': len(docs)
            })

        # Save index as Excel
        index_df = pd.DataFrame(index)
        index_file = self.output_dir / "item_documentation_index.xlsx"
        index_df.to_excel(index_file, index=False)

        logger.info(f"Index created: {index_file.name}")
        logger.info(f"Items with documentation: {len([i for i in index if i['Document Count'] > 0])}")
        logger.info(f"Items without documentation: {len([i for i in index if i['Document Count'] == 0])}")

        return index_file

    def run(self):
        """Execute full pipeline."""
        logger.info("=" * 70)
        logger.info("PDF Discovery Pipeline Started")
        logger.info("=" * 70)

        try:
            # Step 1: Load data
            self.load_data()

            # Step 2: Match suppliers
            self.match_suppliers()

            # Step 3: Create supplier list
            supplier_file = self.create_supplier_excel()

            # Step 4: Run scraper
            pdfs_dir = self.run_scraper(supplier_file)

            # Step 5: Convert PDFs to text
            text_dir = self.convert_pdfs_to_text(pdfs_dir)

            # Step 6: Create index
            index_file = self.create_index(text_dir)

            logger.info("=" * 70)
            logger.info("PDF Discovery Pipeline Complete!")
            logger.info(f"Output directory: {self.output_dir}")
            logger.info(f"Documents: {text_dir}")
            logger.info(f"Index: {index_file}")
            logger.info("=" * 70)

            return {
                'success': True,
                'output_dir': str(self.output_dir),
                'documents_dir': str(text_dir),
                'index_file': str(index_file),
                'message': 'Pipeline completed successfully'
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Pipeline failed'
            }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configuration
    classified_file = r"C:\Data\Crawler\output\NQ_DG_RESEARCH_CAPITAL_V2-43839654(sheet1)_labeled.xlsx"
    masterlist_file = r"C:\Projects\Crawler\PROJECTS\data\masterlist\updated_master_list.xlsx"
    output_dir = r"C:\Data\Crawler\pdf_discovery"
    scraper_engine_path = r"C:\Projects\Crawler\PROJECTS\src\services\scraper-full\scraper_engine.py"

    # Run pipeline
    pipeline = PDFDiscoveryPipeline(classified_file, masterlist_file, output_dir, scraper_engine_path)
    result = pipeline.run()

    print(json.dumps(result, indent=2))
