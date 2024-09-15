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
    "The Circle": (7487, 2207),
    "Central Rama 9": (7484, 2206),
    "Central Eastville": (7483, 2205),
    "Mega Bangna": (7482, 2204),
    "Central Embassy": (7481, 2203),
    "The EmQuartier": (7480, 2202)
}

# Create a DataFrame to collect all data
total_inventory = pd.DataFrame()

# Download data for each branch
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
    df['Branch'] = branch

    total_inventory = pd.concat([total_inventory, df], ignore_index=True)

# Step 2: Fetch data from the API
api_url = "https://open-api.zortout.com/v4/Product/GetProducts"
headers = {
    "storename": "ontime30@zortout.com",
    "apikey": "IUhv2DbmmwjrE1plAMZJEV9ZfwaOeBmMZEbzdutE7M=",
    "apisecret": "FNNdo59jrYCGAGJoqdQn2GxmkS/rgSmzwz/q4aW4="
}

response = requests.get(api_url, headers=headers)

# Check if the response was successful
if response.status_code == 200:
    api_data = response.json()

    print(f"Fetching Data From Zort...")

    # Check if 'list' exists in the response
    if 'list' in api_data:
        products = api_data['list']
        
        # Create a DataFrame from the extracted data
        if products:
            api_inventory = pd.DataFrame(products)

            # Select required columns and rename them
            api_inventory = api_inventory[['name', 'sku', 'availablestock']].rename(columns={
                'name': 'Item',
                'sku': 'SKU',
                'availablestock': 'Qty'
            })
            
            api_inventory['Branch'] = 'On Time'  # Add branch "On Time" to API data

            # Combine API data with total inventory
            total_inventory = pd.concat([total_inventory, api_inventory], ignore_index=True)
            print(f"Combined Inventory...")
        else:
            print("No products found in the API response.")
    else:
        print("Expected 'list' not found in the API response.")
else:
    print(f"Failed to fetch data from API. Status code: {response.status_code}")

# Ensure that 'Qty' is numeric, converting any non-numeric values to NaN
total_inventory['Qty'] = pd.to_numeric(total_inventory['Qty'], errors='coerce')

# Create a separate branch for summed quantities
if not total_inventory.empty:
    summed_quantities = total_inventory.groupby('SKU', as_index=False).agg({'Qty': 'sum', 'Item': 'first'})
    summed_quantities['Branch'] = 'Total'  # Add a new branch for summed quantities
    
    # Combine the summed quantities back into total_inventory
    total_inventory = pd.concat([total_inventory, summed_quantities[['Item', 'SKU', 'Qty', 'Branch']]], ignore_index=True)

# Export Inventory Data
if not total_inventory.empty:
    current_time = datetime.now().strftime("%y%m%d_%H%M")
    
    # Export data to Excel
    # output_filename = f'inventory_report_{current_time}.xlsx'
    # total_inventory.to_excel(output_filename, index=False)
    
    # print(f"Inventory data exported to {output_filename}")

    # Get the current timestamp for the last updated date
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Export data to JSON, overwriting any existing file
    json_filename = 'inventory_data.json'
    json_data = {
        "last_updated": last_updated,
        "inventory": total_inventory.to_dict(orient='records')
    }
    with open(json_filename, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)
    
    print(f"Inventory data exported to {json_filename}")

    # Git commands to add, commit, and push changes
    try:
        commit_message = f"Update inventory data - Last updated: {last_updated}"
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    
    # Set the upstream branch and push
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