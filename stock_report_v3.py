from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import requests
import json
from collections import OrderedDict
import logging
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from the .env file
load_dotenv()

# Access the credentials
choco_username = os.getenv('MY_USERNAME')
choco_password = os.getenv('MY_PASSWORD')
vend_username = os.getenv('VEND_USERNAME')
vend_password = os.getenv('VEND_PASSWORD')
zort_storename = os.getenv('STORENAME')
zort_apikey = os.getenv('APIKEY')
zort_apisecret = os.getenv('APISECRET')

# Set the path for the WebDriver
driver_path = os.getenv('CHROMEDRIVER_PATH', r'D:\Coding\chromedriver-win64\chromedriver.exe')
service = Service(driver_path)

# Set the download folder path
download_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'excel_temp')
os.makedirs(download_folder, exist_ok=True)

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

# Function to wait for an element to be clickable
def wait_for_clickable(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))

# Function to wait for an element to be present
def wait_for_element(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

# Download and process data from ChocoCard
def download_chococard_data():
    try:
        logging.info("Starting ChocoCard data download...")
        
        # Log in to ChocoCard
        driver.get('https://mychococard.com/Account/Login')
        wait_for_element(By.NAME, 'username').send_keys(choco_username)
        wait_for_element(By.NAME, 'password').send_keys(choco_password)
        wait_for_clickable(By.ID, 'loginBtn').click()

        logging.info("Logged into ChocoCard")
        wait_for_element(By.XPATH, "//h3[contains(text(), 'Group / Branch List')]")

        # Base URL for downloading branch inventory
        base_url = "https://mychococard.com/CRM/v2/Restaurant/{}/Inventory/DownloadTemplate/{}"
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
            logging.info(f"Downloading file for: {branch}...")
            driver.get(url)
            
            # Wait for download to complete (adjust if necessary)
            time.sleep(2)
            
            # Find the latest downloaded file
            downloaded_file = max(
                [os.path.join(download_folder, f) for f in os.listdir(download_folder)],
                key=os.path.getctime
            )

            # Read the downloaded Excel file
            df = pd.read_excel(downloaded_file, engine='openpyxl')
            df = df[['Item', 'SKU', 'Available Qty.']]  # Extract necessary columns
            df.columns = ['Item', 'SKU', 'Qty']  # Rename columns

            # Reorganize data and add it to the inventory
            for _, row in df.iterrows():
                item = row['Item']
                sku = row['SKU']
                qty = float(row['Qty'])  # Ensure quantity is a float
                
                if item not in reorganized_inventory:
                    reorganized_inventory[item] = {
                        "SKU": sku,
                        "Branch": OrderedDict()
                    }
                reorganized_inventory[item]["Branch"][branch] = qty

        logging.info("ChocoCard data has been processed for all branches.")
        return reorganized_inventory  # Return the organized data

    except Exception as e:
        logging.error(f"Error downloading ChocoCard data: {e}")
        return {}

# Fetch data from the API
def fetch_api_data():
    api_url = "https://open-api.zortout.com/v4/Product/GetProducts"
    headers = {
        "storename": zort_storename,
        "apikey": zort_apikey,
        "apisecret": zort_apisecret
    }

    try:
        logging.info("Fetching data from ZORT API...")
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        logging.info("ZORT API data fetched successfully.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching API data: {e}")
        return {}

# Download and process data from Vending Machine
def download_vending_data():
    try:
        logging.info("Logging into Worldwide Vending...")
        driver.get('https://www.worldwidevending-vms.com/sys/login.do')
        wait_for_element(By.NAME, 'loginname').send_keys(vend_username)
        wait_for_element(By.NAME, 'loginpwd').send_keys(vend_password)
        wait_for_clickable(By.ID, 'loginsubmit').click()

        driver.get('https://www.worldwidevending-vms.com/page/multi_states.do')
        logging.info("Downloading file for: Vending Machine...")
        wait_for_clickable(By.XPATH, "//button[@onclick='export_inventory_list()']").click()
        driver.switch_to.frame(0)
        wait_for_clickable(By.ID, 'selAll').click()
        wait_for_clickable(By.XPATH, "//button[@onclick='execute_export()']").click()

        # Wait for the download to complete (adjust this time if necessary)
        time.sleep(1)

        # Find the latest downloaded file
        downloaded_file = max(
            [os.path.join(download_folder, f) for f in os.listdir(download_folder) if f.endswith('.xlsx')],
            key=os.path.getctime
        )

        # Rename the file to 'vending_stock.xlsx' to ensure consistency
        renamed_file = os.path.join(download_folder, 'vending_stock.xlsx')
        os.rename(downloaded_file, renamed_file)
        logging.info(f"Downloaded vending machine file renamed to: {renamed_file}")

    except Exception as e:
        logging.error(f"Error downloading Vending Machine data: {e}")

# Process all data
def process_data():
    # Process ChocoCard data first
    reorganized_inventory = download_chococard_data()  # Start with ChocoCard data
    
    # Log the reorganized inventory after ChocoCard processing
    # logging.info("Reorganized inventory after ChocoCard processing:")
    # logging.info(json.dumps(reorganized_inventory, indent=4, ensure_ascii=False))  # Pretty-print the dictionary

    # Process API data (ZORT)
    logging.info("Processing API data...")
    api_data = fetch_api_data()
    if 'list' in api_data:
        for product in api_data['list']:
            item = product['name']
            sku = product['sku']
            qty = float(product['availablestock'])

            if item not in reorganized_inventory:
                reorganized_inventory[item] = {
                    "SKU": sku,
                    "Branch": OrderedDict()
                }
            reorganized_inventory[item]["Branch"]['On Time'] = qty

    # Process Vending Machine data using the saved 'vending_stock.xlsx'
    logging.info("Processing Vending Machine data...")
    sku_mapping_file = 'sku_mapping.csv'  # Specify the path to your SKU mapping CSV file
    vending_file = os.path.join(download_folder, 'vending_stock.xlsx')  # Use the renamed file

    if os.path.exists(vending_file):
        df = pd.read_excel(vending_file, engine='openpyxl')

        # Drop the first row (which doesn't contain headers)
        # logging.info(f"Vending Machine DataFrame head before processing:\n{df.head()}")
        df = df.drop(index=0)

        # Now, set the second row as the header and reset the DataFrame
        df.columns = df.iloc[0]  # Set second row as header
        df = df.drop(index=1).reset_index(drop=True)  # Drop the old header row
        # logging.info(f"Vending Machine DataFrame head after setting headers:\n{df.head()}")

        # Load SKU mapping CSV (this maps Goods Name to SKU)
        sku_mapping_df = pd.read_csv(sku_mapping_file)
        # logging.info(f"SKU Mapping DataFrame head:\n{sku_mapping_df.head()}")

        # Create a dictionary for quick SKU lookup
        sku_mapping = dict(zip(sku_mapping_df['Goods Name'], sku_mapping_df['SKU']))

        # Iterate through the DataFrame
        for _, row in df.iterrows():
            item = row.iloc[4]
            branch = row.iloc[2]
            qty = float(row.iloc[7])

            # Debugging log
            # logging.info(f"Processing item: {item}, branch: {branch}, quantity: {qty}")

            # Retrieve SKU using the item name
            sku = sku_mapping.get(item, None)
            if not sku:
                logging.warning(f"SKU not found for item: {item}")
                continue

            # Organize data in the dictionary
            if item not in reorganized_inventory:
                reorganized_inventory[item] = {
                    "SKU": sku,
                    "Branch": OrderedDict()
                }
            reorganized_inventory[item]["Branch"][branch] = qty
        logging.info(f"Finished processing Vending Machine data for vending_stock.xlsx")
    else:
        logging.error(f"Vending machine file 'vending_stock.xlsx' not found in: {download_folder}")

    # Sum quantities for all branches and create a "Total" branch
    logging.info("Summing quantities for all branches...")
    for item, details in reorganized_inventory.items():
        total_qty = sum(details["Branch"].values())
        details["Branch"]["Total"] = total_qty
        details["Branch"] = OrderedDict(sorted(details["Branch"].items(), key=lambda x: x[0] != "Total"))

    # Convert to the desired structure
    result_inventory = []
    for item, details in reorganized_inventory.items():
        result_inventory.append({
            "Item": item,
            "SKU": details["SKU"],
            "Branch": details["Branch"]
        })

    # Export Inventory Data
    json_filename = 'inventory_data.json'
    final_result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inventory": result_inventory
    }
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(final_result, json_file, ensure_ascii=False, indent=4)

    logging.info(f"Inventory data exported to {json_filename}")
    
    # Git commit and push
    try:
        commit_message = f"Update inventory data - Last updated: {final_result['last_updated']}"
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        subprocess.run(['git', 'push', '--set-upstream', 'origin', 'main'], check=True)
        print("Changes pushed to Git repository.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Git operation: {e}")

# Function to clean up all files in the download folder
def clean_download_folder(download_folder):
    try:
        logging.info(f"Cleaning up the download folder: {download_folder}")
        # List all files in the folder
        for filename in os.listdir(download_folder):
            file_path = os.path.join(download_folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)  # Remove the file
                    logging.info(f"Deleted file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete {file_path}. Reason: {e}")
        logging.info(f"Download folder cleaned successfully.")
    except Exception as e:
        logging.error(f"Error during cleanup of download folder: {e}")

# Run the functions
try:
    download_vending_data()
    process_data()
finally:
    # Clean up the download folder
    clean_download_folder(download_folder)
    
    # Close the browser
    logging.info("Closing the browser...")
    driver.quit()