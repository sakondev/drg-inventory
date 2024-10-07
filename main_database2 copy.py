import os
import json
from collections import defaultdict

def load_json_files(folder_path):
    data = {
        "items": [],
        "branches": [],
        "inventory": defaultdict(lambda: [])
    }
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.json') and filename != 'file_list.json':
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r') as f:
                json_data = json.load(f)
                process_json_data(json_data, data)

    data['inventory'] = dict(data['inventory'])
    return data

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
        "PDTFS", "PDTTC", "P5460", "P_EW-US", "Vending_No45", "SPB",
        "P_OP_SP", "PPLFL_MI36", "PPLFL_TR", "PTBMM", "P_EN1450",
        "PBIWS", "PHydrosonic_BIW", "P_Velvet", "PBYOU60_PE", "PBYOU60_AP",
        "PBYOU60_BB", "P29_CTSB", "PBIW_TB", "P_EW-US", "P_EW-INT",
        "P_EW-PO", "PEW-WJ180", "P_EW-GUM75", "P_EW-TW75", "P_EW-FT70",
        "T_GREEN", "PFELE"
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
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_database2.json')

    merged_data = load_json_files(folder_path)
    add_only_skus(merged_data)
    save_to_json(merged_data, output_file)
    print(f"ข้อมูลถูกบันทึกลงใน {output_file}")

if __name__ == "__main__":
    main()