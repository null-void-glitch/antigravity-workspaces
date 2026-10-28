import os
import sys

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("Error: Required Google API libraries are not installed.")
    print("Please install them by running:")
    print("pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_credentials():
    """Authenticate using OAuth (Personal Google Account)"""
    creds = None

    if not os.path.exists('credentials.json'):
        print("Error: credentials.json not found.")
        print("Download OAuth Desktop credentials from Google Cloud Console.")
        sys.exit(1)

    # Load saved token if exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials → login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google login...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def upload_csv_as_sheets(service, filepath):
    filename = os.path.basename(filepath)
    print(f"Uploading {filename} to Google Drive...")

    file_metadata = {
        'name': filename.replace('.csv', ''),
        'mimeType': 'application/vnd.google-apps.spreadsheet'
    }

    media = MediaFileUpload(filepath, mimetype='text/csv', resumable=True)

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    print(f"Successfully uploaded {filename}")
    print(f"View link: {file.get('webViewLink')}")
    return file.get('id')


if __name__ == '__main__':
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

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
