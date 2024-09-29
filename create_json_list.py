import os
import json

# Specify the directory containing the JSON files
data_directory = './data'

# List to hold the names of JSON files
json_files = []

# Iterate over files in the specified directory
for filename in os.listdir(data_directory):
    if filename.endswith('.json'):
        json_files.append(filename)

# Create the file_list.json in the data directory
file_list_path = os.path.join(data_directory, 'file_list.json')

# Write the list of JSON files to file_list.json
with open(file_list_path, 'w', encoding='utf-8') as file:
    json.dump(json_files, file, ensure_ascii=False, indent=4)

print(f"Generated {file_list_path} with {len(json_files)} JSON files.")