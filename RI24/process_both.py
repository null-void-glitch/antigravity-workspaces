import json
import csv

def process_csv():
    print("Processing crm_export.csv...")
    rows = []
    try:
        with open('crm_export.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                if len(row) > 0:
                    # Remove the last column (Source URL)
                    rows.append(row[:-1])
        
        with open('crm_export.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(rows)
        print(f"Updated crm_export.csv: {len(rows)} rows, removed Source URL column\n")
    except Exception as e:
        print(f"Error processing CSV: {e}\n")

def process_results2():
    print("Processing results2.json...")
    try:
        with open('results2.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Original items in results2.json: {len(data)}")
        
        filtered_data = []
        seen_contacts = set()
        removed_ausland = 0
        removed_dupes = 0
        
        for item in data:
            # 1. Check for /ausland/ in URL
            url = item.get('url', '')
            if '/ausland/' in url:
                removed_ausland += 1
                continue
                
            # 2. Check for duplicate contact_person
            contact = item.get('contact_person')
            # If contact_person is missing/empty, we probably still want to keep one, 
            # or maybe we keep all. The prompt says "remove all duplicates by checking 
            # the value of contact_person". Let's assume we treat None/"" as a value 
            # and only keep the first one, OR we only deduplicate if it exists.
            # Usually it's safer to only deduplicate if it exists, or treat empty as a valid deduplication key.
            # Let's treat it as a key.
            contact_key = str(contact).strip().lower() if contact else ""
            
            if contact_key in seen_contacts:
                removed_dupes += 1
                continue
                
            seen_contacts.add(contact_key)
            filtered_data.append(item)
            
        print(f"Items removed because of '/ausland/': {removed_ausland}")
        print(f"Items removed because of duplicate contact_person: {removed_dupes}")
        print(f"Remaining items: {len(filtered_data)}")
        
        with open('results2.json', 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2, ensure_ascii=False)
            
        print("results2.json updated successfully.\n")
        
    except Exception as e:
        print(f"Error processing results2.json: {e}\n")

if __name__ == '__main__':
    process_csv()
    process_results2()
