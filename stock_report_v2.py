from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import requests
import json
import subprocess

# Load environment variables from the .env file
load_dotenv()

# Access the credentials
choco_username = os.getenv('MY_USERNAME')
choco_password = os.getenv('MY_PASSWORD')

# Set the path for the WebDriver
driver_path = r'D:\Coding\chromedriver-win64\chromedriver.exe'
service = Service(driver_path)

# Set the download folder path
download_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'excel_temp')

# Set up headless options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_folder,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Initialize the WebDriver
driver = webdriver.Chrome(service=service, options=chrome_options)

# Function to wait for an element to be present
def wait_for_element(by, value, timeout=10):
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

# Step 1: Login to ChocoCard
driver.get('https://mychococard.com/Account/Login')
wait_for_element(By.NAME, 'username').send_keys(choco_username)
wait_for_element(By.NAME, 'password').send_keys(choco_password)
wait_for_element(By.ID, 'loginBtn').click()

print("Logging into ChocoCard...")
wait_for_element(By.XPATH, "//h3[contains(text(), 'Group / Branch List')]")

# Base URL for branches
base_url = "https://mychococard.com/CRM/v2/Restaurant/{}/Inventory/DownloadTemplate/{}"

# List of branches with their respective identifiers
branches = {
    "Samyan": (7485, 2209),
    "Circle": (7487, 2207),
    "Rama 9": (7484, 2206),
    "Eastville": (7483, 2205),
    "Mega": (7482, 2204),
    "Embassy": (7481, 2203),
    "EmQuartier": (7480, 2202)
}

# Initialize the reorganized inventory dictionary
reorganized_inventory = {}

# Download and process data for each branch
for branch, (id_, template_id) in branches.items():
    url = base_url.format(id_, template_id)
    print(f"Downloading file for: {branch}...")
    driver.get(url)
    
    # Wait for download to complete
    time.sleep(0.5)  # Adjust this if necessary

    # Find the latest downloaded file
    downloaded_file = max(
        [os.path.join(download_folder, f) for f in os.listdir(download_folder)],
        key=os.path.getctime
    )

    # Read the downloaded Excel file
    df = pd.read_excel(downloaded_file, engine='openpyxl')
    df = df[['Item', 'SKU', 'Available Qty.']]
    df.columns = ['Item', 'SKU', 'Qty']

    # Directly reorganize the data
    for _, row in df.iterrows():
        item = row['Item']
        sku = row['SKU']
        qty = row['Qty']
        
        if item not in reorganized_inventory:
            reorganized_inventory[item] = {
                "SKU": sku,
                "Branch": {}
            }
        reorganized_inventory[item]["Branch"][branch] = qty

# Step 2: Fetch data from the API
api_url = "https://open-api.zortout.com/v4/Product/GetProducts"
headers = {
    "storename": "ontime30@zortout.com",
    "apikey": "IUhv2DbmmwjrE1plAMZJEV9ZfwaOeBmMZEbzdutE7M=",
    "apisecret": "FNNdo59jrYCGAGJoqdQn2GxmkS/rgSmzwz/q4aW4="
}

response = requests.get(api_url, headers=headers)

# Process API data
if response.status_code == 200:
    api_data = response.json()

    if 'list' in api_data:
        products = api_data['list']
        
        for product in products:
            item = product['name']
            sku = product['sku']
            qty = product['availablestock']
            
            if item not in reorganized_inventory:
                reorganized_inventory[item] = {
                    "SKU": sku,
                    "Branch": {}
                }
            reorganized_inventory[item]["Branch"]['On Time'] = qty

# Convert to the desired structure
result_inventory = []
for item, details in reorganized_inventory.items():
    result_inventory.append({
        "Item": item,
        "SKU": details["SKU"],
        "Branch": details["Branch"]
    })

# Export Inventory Data
json_filename = 'inventory_data_v2.json'
final_result = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "inventory": result_inventory
}
with open(json_filename, 'w', encoding='utf-8') as json_file:
    json.dump(final_result, json_file, ensure_ascii=False, indent=4)

print(f"Inventory data exported to {json_filename}")

# Git commands to add, commit, and push changes
try:
    commit_message = f"Update inventory data - Last updated: {final_result['last_updated']}"
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    subprocess.run(['git', 'push', '--set-upstream', 'origin', 'main'], check=True)
    print("Changes pushed to Git repository.")
except subprocess.CalledProcessError as e:
    print(f"Error during Git operation: {e}")

# Cleanup: Delete all files in the specified download folder
for file in os.listdir(download_folder):
    file_path = os.path.join(download_folder, file)
    if os.path.isfile(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")

# Close the browser
print("Closing the browser...")
driver.quit()