#!/usr/bin/env python3
"""
Process results.json:
1. Remove items with status "error"
2. Deduplicate by popup_content_html
3. Overwrite results.json with cleaned data
4. Extract CRM fields (Company, Contact, Phone, Email) into crm_export.csv
"""

import json
import csv
import re
import sys
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Simple HTML to text converter."""
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, data):
        self.result.append(data)

    def get_text(self):
        return ''.join(self.result)


def html_to_text(html_str):
    """Convert HTML string to plain text."""
    if not html_str:
        return ""
    extractor = HTMLTextExtractor()
    try:
        extractor.feed(html_str)
    except Exception:
        return html_str
    return extractor.get_text()


def extract_email(text):
    """Extract email addresses from text."""
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    # Filter out common non-email matches and deduplicate
    filtered = []
    seen = set()
    for e in emails:
        e_lower = e.lower()
        if e_lower not in seen and not e_lower.endswith('.png') and not e_lower.endswith('.jpg'):
            seen.add(e_lower)
            filtered.append(e)
    return '; '.join(filtered) if filtered else ''


def extract_phone(text):
    """Extract phone numbers from text."""
    # Look for phone patterns after Tel/Telefon/Fon/Phone markers
    phone_patterns = [
        r'(?:Tel(?:efon|\.)?|Fon|Phone|Mobil)\s*[:/.]?\s*([+\d][\d\s/\-–().]+\d)',
        r'(?:Fax)\s*[:/.]?\s*([+\d][\d\s/\-–().]+\d)',
    ]
    phones = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip().rstrip('.')
            if len(re.sub(r'\D', '', cleaned)) >= 6:  # At least 6 digits
                phones.append(cleaned)

    # Deduplicate
    seen = set()
    unique_phones = []
    for p in phones:
        normalized = re.sub(r'\s+', '', p)
        if normalized not in seen:
            seen.add(normalized)
            unique_phones.append(p)

    return '; '.join(unique_phones) if unique_phones else ''


def extract_company_name(text):
    """Extract company name - typically the first substantive line."""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return ''

    # Skip common prefixes like "(Angaben gemäß § 5 TMG)"
    skip_patterns = [
        r'^\(Angaben',
        r'^Impressum',
        r'^Anbieterkennzeichnung',
        r'^Angaben gemäß',
    ]

    for line in lines:
        skip = False
        for pat in skip_patterns:
            if re.match(pat, line, re.IGNORECASE):
                skip = True
                break
        if not skip and len(line) > 2:
            return line

    return lines[0] if lines else ''


def extract_contact_person(text):
    """Extract contact person name."""
    patterns = [
        r'Vertretungsberechtigte/?r?\s*[:/]?\s*(.+?)(?:\n|Handelsregister|Berufsaufsicht|Berufskammer|$)',
        r'Geschäftsführ(?:er|ung)\s*[:/]?\s*(.+?)(?:\n|Handelsregister|Berufsaufsicht|$)',
        r'Inhaber(?:in)?\s*[:/]?\s*(.+?)(?:\n|Handelsregister|$)',
        r'Geschäftsleitung\s*[:/]?\s*(.+?)(?:\n|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up: remove trailing labels
            name = re.split(r'\b(?:Handelsregister|Berufsaufsicht|Berufskammer|Aufsichtsbehörde|USt)', name)[0]
            name = name.strip().rstrip(',').rstrip(':').strip()
            if len(name) > 2 and len(name) < 200:
                return name

    return ''


def main():
    input_file = 'results.json'
    output_json = 'results.json'
    output_csv = 'crm_export.csv'

    print(f'Loading {input_file}...')
    sys.stdout.flush()

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f'Total items loaded: {total}')
    sys.stdout.flush()

    # Step 1 & 2: Remove errors and deduplicate by popup_content_html
    seen_html = set()
    unique = []
    errors_removed = 0
    duplicates_removed = 0

    for item in data:
        if item.get('status') == 'error':
            errors_removed += 1
            continue

        html = item.get('popup_content_html')
        if html is None:
            unique.append(item)
        elif html not in seen_html:
            seen_html.add(html)
            unique.append(item)
        else:
            duplicates_removed += 1

    print(f'Errors removed: {errors_removed}')
    print(f'Duplicates removed: {duplicates_removed}')
    print(f'Unique items remaining: {len(unique)}')
    sys.stdout.flush()

    # Step 3: Save cleaned JSON
    print(f'Writing cleaned {output_json}...')
    sys.stdout.flush()
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f'Saved {output_json}')
    sys.stdout.flush()

    # Step 4: Extract CRM data and write CSV
    print(f'Extracting CRM data to {output_csv}...')
    sys.stdout.flush()

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['Company Name', 'Contact Person', 'Telephone', 'Email', 'Source URL'])

        for item in unique:
            text = item.get('popup_content_text', '')
            if not text:
                html = item.get('popup_content_html', '')
                text = html_to_text(html)

            if not text.strip():
                continue

            company = extract_company_name(text)
            contact = extract_contact_person(text)
            phone = extract_phone(text)
            email = extract_email(text)
            url = item.get('url', '')

            writer.writerow([company, contact, phone, email, url])

    print(f'Saved {output_csv}')
    print('Done!')


if __name__ == '__main__':
    main()
