"""
Build supplier classification database for Rule B.
Analyze Unknown items, identify top suppliers, create classification mapping.
"""

import pandas as pd
from pathlib import Path
import json

# Find latest classified v3 file
labeled_dir = Path("C:/Data/Crawler/labeled")
v3_files = sorted(labeled_dir.glob("*_classified_v3.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True)

if not v3_files:
    print("No v3 classified files found")
    exit(1)

latest_file = v3_files[0]
print(f"Loading: {latest_file.name}")

df = pd.read_excel(latest_file)

# Filter for Unknown items
unknown_df = df[df['Type'] == 'Unknown'].copy()
print(f"\nTotal Unknown items: {len(unknown_df)}")

# Count by Supplier Name
supplier_unknown = unknown_df['Supplier Name'].value_counts()
print(f"\nTop suppliers with Unknown items (first 30):")
for i, (supplier, count) in enumerate(supplier_unknown.head(30).items(), 1):
    print(f"  {i:2}. {count:3} items - {supplier}")

# Classify top 50 suppliers by domain (high confidence mapping)
# Based on company names - research equipment, medical device, lab equipment
SUPPLIER_CLASSIFICATION = {
    "APPLIED SCIENTIFIC INSTRUMENTATION INC": "research_equipment",
    "FISHER SCIENTIFIC COMPANY LLC": "lab_equipment",
    "GE HEALTHCARE": "medical_equipment",
    "GLOBAL LIFE SCIENCES SOLUTIONS USA LLC": "lab_equipment",
    "PHILIPS HEALTHCARE": "medical_equipment",
    "LAERDAL MEDICAL CORPORATION": "medical_equipment",
    "PRESIDIO NETWORKED SOLUTIONS GROUP LLC": "IT",
    "SCIENTIFICA LLC": "research_equipment",
    "CARL ZEISS MICROSCOPY": "research_equipment",
    "PHC CORPORATION OF NORTH AMERICA": "research_equipment",
    "EVIDENT SCIENTIFIC": "research_equipment",
    "GE MEDICAL SYSTEMS INFORMATION": "medical_equipment",
    "NEUROLOGICA CORPORATION": "medical_equipment",
    "CARL ZEISS MEDITEC USA INC": "medical_equipment",
    "SIEMENS MEDICAL SOLUTIONS USA INC": "medical_equipment",
    "INTEG SYSTEMS CORPORATION": "IT",
    "ALPHA MEDICAL EQUIPMENT OF NY INC": "medical_equipment",
    "HEIDELBERG ENGINEERING INC": "medical_equipment",
    "KARL STORZ ENDOSCOPY-AMERICA INC": "medical_equipment",
    "OLYMPUS AMERICA INC": "medical_equipment",
    "FUJIFILM SONOSITE INC": "medical_equipment",
    "DAVID KOPF INSTRUMENTS": "research_equipment",
    "AGILENT TECHNOLOGIES INC": "lab_equipment",
    "CARESTREAM AMERICA": "medical_equipment",
    "E3 DIAGNOSTICS": "medical_equipment",
    "AQUATIC ENTERPRISES INC": "unknown",
    "MAGVENTURE INC": "medical_equipment",
    "MINDRAY DS USA INC": "medical_equipment",
    "BRUKER CELLULAR ANALYSIS INC": "research_equipment",
    "QIAGEN": "lab_equipment",
}

# Build full supplier DB: top classified + rest as "unknown"
supplier_db = {}
for supplier_name in unknown_df['Supplier Name'].unique():
    supplier_type = SUPPLIER_CLASSIFICATION.get(supplier_name, "unknown")
    supplier_db[supplier_name] = supplier_type

output_file = Path("docs/references/supplier_classification.json")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(supplier_db, f, indent=2, ensure_ascii=False)

print(f"\nSupplier DB created: {output_file}")
print(f"Mapped {len(supplier_db)} unique suppliers")

# Count by type
from collections import Counter
type_counts = Counter(supplier_db.values())
print(f"Classification distribution:")
for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {count}")

# Show which Unknown items will be reclassified
reclassified = 0
for _, row in unknown_df.iterrows():
    supplier_type = supplier_db.get(row['Supplier Name'], 'unknown')
    if supplier_type in ['lab_equipment', 'medical_equipment', 'research_equipment']:
        reclassified += 1

print(f"\nEstimated reclassified by Rule B: {reclassified} items (~{reclassified/len(unknown_df)*100:.1f}%)")
