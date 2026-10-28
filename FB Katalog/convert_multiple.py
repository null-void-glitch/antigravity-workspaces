import xml.etree.ElementTree as ET
import csv
import requests
import os
from dotenv import load_dotenv

def download_xml(url, username, password, output_file):
    print(f"Downloading {url}...")
    with requests.get(url, auth=(username, password), stream=True, timeout=30) as response:
        response.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download complete.")

def parse_and_convert(xml_file):
    target_zip_codes = {
        '08485', '08261', '08239', '08223', '08258', '08626', '08237', '08539',
        '07952', '07919', '08527', '08548', '08525', '08523', '08547', '08529',
        '08541', '08684', '08626', '08606', '08538', '08233', '08645', '08499',
        '08491', '08468', '08236', '08228', '08543', '08248', '08267', '08496',
        '08209', '08262', '07985'
    }

    files = {
        'haeuser': open('ri24_haeuser_vogtland.csv', 'w', newline='', encoding='utf-8'),
        'etw': open('ri24_etw_vogtland.csv', 'w', newline='', encoding='utf-8'),
        'grundstueck': open('ri24_grundstueck_vogtland.csv', 'w', newline='', encoding='utf-8'),
        'mietwhg': open('ri24_mietwhg_vogtland.csv', 'w', newline='', encoding='utf-8')
    }
    
    writers = {
        k: csv.writer(f) for k, f in files.items()
    }
    
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
                    
                    description = elem.findtext('description') or ''
                    description = description.strip()
                    
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

if __name__ == '__main__':
    load_dotenv()
    
    username = os.getenv("XML_USERNAME")
    password = os.getenv("XML_PASSWORD")
    
    if not username or not password:
        print("Error: XML_USERNAME and XML_PASSWORD must be set in the .env file.")
        exit(1)

    url = "https://zbv.regionalimmobilien24.de/webapi/xml/export.xml"
    xml_file = "export_downloaded.xml"
    download_xml(url, username, password, xml_file)
    print("Parsing and converting...")
    parse_and_convert(xml_file)
    print("Done.")