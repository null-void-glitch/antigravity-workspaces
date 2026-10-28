#!/usr/bin/env python3
"""
export_csv.py

Reads results2_copy.json and exports it to a CSV file, including only the selected columns:
- company_name
- contact_person
- phone
- email
"""

import json
import csv
import re

INPUT_FILE = '/home/null/work/antigravity-workspaces/RI24/results2_copy.json'
OUTPUT_FILE = '/home/null/work/antigravity-workspaces/RI24/results2_copy.csv'
FIELDNAMES = ['company_name', 'contact_person', 'phone', 'email']

def main():
    print(f"Reading from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # Clean up contact_person if needed
    for item in items:
        cp = item.get('contact_person') or ''
        # Strip the "Ansprechpartner/in" string and any following newlines
        cleaned = re.sub(r'^Ansprechpartner/in\s*\n?\s*', '', cp).strip()
        item['contact_person'] = cleaned

    print(f"Writing to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(items)
        print(f"Exported {len(items)} rows successfully.")
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    main()
