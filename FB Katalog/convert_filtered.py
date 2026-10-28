import xml.etree.ElementTree as ET
import csv

def parse_and_convert(xml_file, csv_file):
    target_zip_codes = {
        '09355', '09353', '09350', '09243', '08060', '08451', '09356', '09337',
        '08132', '08459', '08141', '08412', '08134', '08107', '08427', '08396',
        '08118', '09212', '08373', '08144', '08428', '08112', '08371', '08147',
        '08393'
    }

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'description', 'availability', 'condition', 'price', 'link', 'image_link', 'brand'])

        context = ET.iterparse(xml_file, events=('end',))
        for event, elem in context:
            if elem.tag == 'immo':
                obj_type = elem.findtext('object_type')
                payment_type = elem.findtext('payment_type')
                zip_code = elem.findtext('zip_code')

                if obj_type == 'Haus' and payment_type == 'buy' and zip_code in target_zip_codes:
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
    parse_and_convert('export.xml', 'regionalimmobilien24_filtered.csv')
