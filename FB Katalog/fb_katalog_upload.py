# Combined script: fb_katalog_upload.py

import os
import sys
import csv
import xml.etree.ElementTree as ET
import requests
from dotenv import load_dotenv

# Google API imports with fallback error handling
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("Error: Required Google API libraries are not installed.")
    print("Please install them by running:")
    print("pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# ------------------------------------------------------------
# Configuration for Google Drive API
# ------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ------------------------------------------------------------
# Functions for XML download and conversion to CSV
# ------------------------------------------------------------

def download_xml(url, username, password, output_file):
    """Download XML file from the given URL using basic auth."""
    print(f"Downloading {url}...")
    with requests.get(url, auth=(username, password), stream=True, timeout=30) as response:
        response.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download complete.")


def parse_and_convert(xml_file):
    """Parse the downloaded XML and generate CSV files for different property types."""
    target_zip_codes = {
        '09355', '09353', '09350', '09243', '08060', '08451', '09356', '09337',
        '08132', '08459', '08141', '08412', '08134', '08107', '08427', '08396',
        '08118', '09212', '08373', '08144', '08428', '08112', '08371', '08147',
        '08393'
    }

    # Prepare CSV files
    files = {
        'haeuser': open('ri24_haeuser_zwickau.csv', 'w', newline='', encoding='utf-8'),
        'etw': open('ri24_etw_zwickau.csv', 'w', newline='', encoding='utf-8'),
        'grundstueck': open('ri24_grundstueck_zwickau.csv', 'w', newline='', encoding='utf-8'),
        'mietwhg': open('ri24_mietwhg_zwickau.csv', 'w', newline='', encoding='utf-8')
    }
    writers = {k: csv.writer(f) for k, f in files.items()}

    header = ['id', 'title', 'description', 'availability', 'condition', 'price', 'link', 'image_link', 'brand']
    for w in writers.values():
        w.writerow(header)

    context = ET.iterparse(xml_file, events=('end',))
    for event, elem in context:
        if elem.tag == 'immo':
            zip_code = elem.findtext('zip_code')
            if zip_code in target_zip_codes:
                obj_type = elem.findtext('object_type')
                payment_type = elem.findtext('payment_type')
                target_writer = None
                if payment_type == 'buy' and obj_type == 'Haus':
                    target_writer = writers['haeuser']
                elif payment_type == 'buy' and obj_type == 'Wohnung':
                    target_writer = writers['etw']
                elif payment_type == 'buy' and (obj_type == 'Grundstueck' or obj_type == 'Grundstück'):
                    target_writer = writers['grundstueck']
                elif payment_type == 'rent' and obj_type == 'Wohnung':
                    target_writer = writers['mietwhg']
                if target_writer:
                    ad_id = elem.findtext('ad_id') or ''
                    title = elem.findtext('title') or ''
                    description = (elem.findtext('description') or '').strip()
                    availability = 'in stock'
                    condition = 'new'
                    price_val = elem.findtext('price')
                    price = f"{price_val} EUR" if price_val else ''
                    link = elem.findtext('ad_url') or ''
                    image_link = elem.findtext('photo_url') or ''
                    brand = 'Regionalimmobilien24'
                    target_writer.writerow([ad_id, title, description, availability, condition, price, link, image_link, brand])
            # Free memory
            elem.clear()

    for f in files.values():
        f.close()

# ------------------------------------------------------------
# Functions for Google Drive authentication and CSV upload
# ------------------------------------------------------------

def get_credentials():
    """Authenticate using embedded OAuth credentials (no external JSON files needed)."""

    # ── Embedded OAuth client credentials (from credentials.json) ──
    EMBEDDED_CLIENT_ID = "602625620145-61qhcm63r47sdp7b1equga5b9cva9tj1.apps.googleusercontent.com"
    EMBEDDED_CLIENT_SECRET = "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"

    # ── Embedded refresh token (from token.json) ──
    EMBEDDED_REFRESH_TOKEN = "1//030yTr7M5PCC6CgYIARAAGAMSNwF-L9IrOuHw_yXQZ83lty_2faQElpaAudVB6_VMPoxhmkrNHDS7q_uzMIjah8fzhJlMilmgP6g"

    creds = Credentials(
        token=None,  # Will be refreshed automatically
        refresh_token=EMBEDDED_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=EMBEDDED_CLIENT_ID,
        client_secret=EMBEDDED_CLIENT_SECRET,
        scopes=SCOPES
    )

    # Refresh to get a valid access token
    print("Refreshing access token...")
    creds.refresh(Request())

    return creds


def find_existing_file(service, name):
    """Search Google Drive for an existing file (Google Sheet) by name. Returns file ID if found."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    results = service.files().list(q=query, fields='files(id, webViewLink)', pageSize=1).execute()
    files = results.get('files', [])
    if files:
        return files[0]
    return None


def upload_csv_as_sheets(service, filepath):
    """Upload or update a CSV file on Google Drive as a Google Sheet. Returns the file ID.

    If a Sheet with the same name already exists, its content is updated in place
    so the file ID and share link remain stable.
    """
    filename = os.path.basename(filepath)
    sheet_name = filename.replace('.csv', '')
    media = MediaFileUpload(filepath, mimetype='text/csv', resumable=True)

    existing = find_existing_file(service, sheet_name)

    if existing:
        # Update existing file content (preserves ID and share link)
        file_id = existing['id']
        print(f"Updating existing '{sheet_name}' (id: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"Successfully updated {filename}")
        print(f"View link: {existing.get('webViewLink')}")
        return file_id
    else:
        # First run: create new file
        print(f"Uploading {filename} to Google Drive (new file)...")
        file_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

        # Make file publicly readable
        service.permissions().create(
            fileId=file.get('id'),
            body={
                'type': 'anyone',
                'role': 'reader'
            }
        ).execute()

        print(f"Successfully uploaded {filename}")
        print(f"View link: {file.get('webViewLink')}")
        return file.get('id')

# ------------------------------------------------------------
# Main execution flow
# ------------------------------------------------------------
if __name__ == '__main__':
    # Load environment variables for XML download
    load_dotenv()
    username = os.getenv("XML_USERNAME")
    password = os.getenv("XML_PASSWORD")
    if not username or not password:
        print("Error: XML_USERNAME and XML_PASSWORD must be set in the .env file.")
        sys.exit(1)

    # Step 1: Download XML
    url = "https://zbv.regionalimmobilien24.de/webapi/xml/export.xml"
    xml_file = "export_downloaded.xml"
    download_xml(url, username, password, xml_file)

    # Step 2: Parse XML and generate CSVs
    print("Parsing and converting...")
    parse_and_convert(xml_file)
    print("CSV generation complete.")

    # Step 3: Authenticate with Google Drive
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    # Step 4: Upload generated CSV files as Google Sheets
    csv_files = [
        'ri24_haeuser_zwickau.csv',
        'ri24_etw_zwickau.csv',
        'ri24_grundstueck_zwickau.csv',
        'ri24_mietwhg_zwickau.csv'
    ]
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            upload_csv_as_sheets(service, csv_file)
        else:
            print(f"Warning: {csv_file} does not exist. Skipping.")
    print("All uploads complete.")
