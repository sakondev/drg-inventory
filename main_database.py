import os
import json
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_json_files(folder_path):
    data = {
        "items": [],
        "branches": [],
        "inventory": defaultdict(lambda: [])
    }
    
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith('.json') and filename != 'file_list.json':
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r') as f:
                    json_data = json.load(f)
                    process_json_data(json_data, data)
                logging.info(f"Processed file: {filename}")

        data['inventory'] = dict(data['inventory'])
        return data
    except Exception as e:
        logging.error(f"Error loading JSON files: {e}")
        raise

def process_json_data(json_data, data):
    item_map = {item['sku']: item['id'] for item in data['items']}
    branch_map = {branch['name']: branch['id'] for branch in data['branches']}
    
    for inventory_item in json_data['inventory']:
        item_id = item_map.setdefault(inventory_item['SKU'], len(data['items']) + 1)
        
        if item_id == len(data['items']) + 1:
            data['items'].append({
                "id": item_id,
                "name": inventory_item['Item'],
                "sku": inventory_item['SKU']
            })

        for branch_name, stock in inventory_item['Branch'].items():
            branch_id = branch_map.setdefault(branch_name, len(data['branches']) + 1)
            
            if branch_id == len(data['branches']) + 1:
                data['branches'].append({
                    "id": branch_id,
                    "name": branch_name
                })

            # เช็คและรวม stock ในกรณีที่ข้อมูลซ้ำ
            existing_stocks = data['inventory'][json_data['last_updated']]
            found = False
            for entry in existing_stocks:
                if entry['item_id'] == item_id and entry['branch_id'] == branch_id:
                    entry['stock'] += stock
                    found = True
                    break
            
            if not found:
                data['inventory'][json_data['last_updated']].append({
                    "item_id": item_id,
                    "branch_id": branch_id,
                    "stock": stock
                })

def add_only_skus(data):
    vmSKUs = [
        "24100912667", "24100905930", "24071292189", "24100966354", "24100918573",
        "24071665142", "24071216537", "24071267010", "24071200892", "24071156867",
        "24071118031", "24071624573", "24071122424", "24071142828", "24071613548",
        "24100939935", "24100987248", "24071147958", "24071241987", "24071110715",
        "24071144702", "24071290463", "24071246675", "24071299410", "24071219455",
        "24071277255", "24100976269", "24100971195", "24100983316", "24071282389",
        "24071206849", "24071227918", "24071216191", "24100952029", "24100988667"
    ]

    only_skus = {
        10: [
            "PEW-US-Duo", "P_EW-US", "P_EW-SE", "P_EW-INT", "P_EW-Refill-DC",
            "EW-CC", "P_EW-TW75", "P_EW-GUM75", "P_EW-PO", "EW-USF",
            "P_F_EW_WHT12", "P_EW-Refill-TF", "P_EW-SF", "PEW-WJ180",
            "P_EW-Refill-WH", "EW-WJR2", "P_F_EW_CRF12", "EW-PC70", "P_EW-FT70",
            "EW-SG8PLUS", "EW-PL5", "P_EW-FTGR", "P_EW-OT75", "P_EW-SG8",
            "P_EW-SR75", "P_EW-US-P3", "P_F_EW_OSM12", "P_F_EW_STS12"
        ],
        11: vmSKUs,
        12: vmSKUs
    }

    for branch in data['branches']:
        if branch['id'] in only_skus:
            branch['onlySKUs'] = only_skus[branch['id']]
    
    existing_branch_ids = set(branch['id'] for branch in data['branches'])
    for branch_id, skus in only_skus.items():
        if branch_id not in existing_branch_ids:
            data['branches'].append({
                "id": branch_id,
                "name": f"Branch {branch_id}",
                "onlySKUs": skus
            })

def save_to_json(data, output_file):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        logging.info(f"Data saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving data to JSON: {e}")
        raise

def main():
    try:
        folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_database2.json')

        logging.info("Starting data processing")
        merged_data = load_json_files(folder_path)
        add_only_skus(merged_data)
        save_to_json(merged_data, output_file)
        logging.info("Data processing completed successfully")
    except Exception as e:
        logging.error(f"An error occurred during data processing: {e}")

if __name__ == "__main__":
    main()
