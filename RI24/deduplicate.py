import json

input_file = "results2_copy.json"
output_file = "results2_copy.json"

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

original_count = len(data)

seen = set()
deduped = []
for item in data:
    website = item.get("website")
    if website not in seen:
        seen.add(website)
        deduped.append(item)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(deduped, f, indent=2, ensure_ascii=False)

print(f"Original: {original_count} items")
print(f"After dedup: {len(deduped)} items")
print(f"Removed: {original_count - len(deduped)} duplicates")
