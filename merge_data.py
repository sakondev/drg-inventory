import os
import json

def load_json_files(folder_path):
    data = {
        "items": [],
        "branches": [],
        "inventory": []
    }
    
    # ตรวจสอบไฟล์ในโฟลเดอร์
    for filename in os.listdir(folder_path):
        if filename.endswith('.json') and filename != 'file_list.json':
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r') as f:
                json_data = json.load(f)
                process_json_data(json_data, data)

    return data

def process_json_data(json_data, data):
    # สร้าง item map และ branch map
    item_map = {item['sku']: item['id'] for item in data['items']}
    branch_map = {branch['name']: branch['id'] for branch in data['branches']}
    
    for inventory_item in json_data['inventory']:
        item_id = item_map.setdefault(inventory_item['SKU'], len(data['items']) + 1)
        
        # เพิ่ม item ถ้ายังไม่มี
        if item_id == len(data['items']) + 1:
            data['items'].append({
                "id": item_id,
                "name": inventory_item['Item'],
                "sku": inventory_item['SKU']
            })

        for branch_name, stock in inventory_item['Branch'].items():
            branch_id = branch_map.setdefault(branch_name, len(data['branches']) + 1)
            
            # เพิ่ม branch ถ้ายังไม่มี
            if branch_id == len(data['branches']) + 1:
                data['branches'].append({
                    "id": branch_id,
                    "name": branch_name
                })

            data['inventory'].append({
                "item_id": item_id,
                "branch_id": branch_id,
                "stock": stock,
                "date": json_data['last_updated']  # ใช้ last_updated เป็นวันที่
            })

def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')  # โฟลเดอร์ data
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory_database.json')  # ชื่อไฟล์ output

    merged_data = load_json_files(folder_path)
    save_to_json(merged_data, output_file)
    print(f"ข้อมูลถูกบันทึกลงใน {output_file}")

if __name__ == "__main__":
    main()