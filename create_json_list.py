import os
import json
from datetime import datetime

def generate_file_list(data_directory='./data'):
    # List to hold the names of JSON files
    json_files = []

    # Iterate over files in the specified directory
    for filename in os.listdir(data_directory):
        if filename.endswith('.json') and filename != 'file_list.json':
            json_files.append(filename)

    # Sort the json_files by date and time extracted from the filename
    json_files.sort(key=lambda x: datetime.strptime(x[:-5], '%d%m%y_%H%M%S'), reverse=True)

    # Create or overwrite the file_list.json in the data directory
    file_list_path = os.path.join(data_directory, 'file_list.json')

    # Write the list of JSON files to file_list.json
    with open(file_list_path, 'w', encoding='utf-8') as file:
        json.dump(json_files, file, ensure_ascii=False, indent=4)

    print(f"Generated {file_list_path} with {len(json_files)} JSON files.")

generate_file_list()