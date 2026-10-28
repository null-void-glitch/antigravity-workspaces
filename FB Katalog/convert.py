import xml.etree.ElementTree as ET
import csv

def parse_and_convert(xml_file, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'description', 'availability', 'condition', 'price', 'link', 'image_link', 'brand'])

        # Use iterparse for memory efficiency just in case, though 42MB is okay
        context = ET.iterparse(xml_file, events=('end',))
        for event, elem in context:
            if elem.tag == 'immo':
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
                
                writer.writerow([ad_id, title, description, availability, condition, price, link, image_link, brand])
                
                # Free memory
                elem.clear()

if __name__ == '__main__':
    parse_and_convert('export.xml', 'regionalimmobilien24.csv')
