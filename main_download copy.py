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
import warnings
from io import BytesIO
import io
import tempfile

warnings.simplefilter("ignore", UserWarning)

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

# Set up headless options
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-position=-10000,-10000")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-software-rasterizer")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")

# Initialize the WebDriver as a background service
driver = webdriver.Chrome(service=service, options=chrome_options)

# Function to wait for an element to be clickable
def wait_for_clickable(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))

# Function to wait for an element to be present
def wait_for_element(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

# Retry decorator
def retry(max_retries=5, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    logging.warning(f"Attempt {retries} failed: {e}. Retrying...")
                    time.sleep(delay)
            logging.error(f"Failed after {max_retries} attempts.")
            return None
        return wrapper
    return decorator

# Download and process data from ChocoCard with retry logic for each branch
def download_chococard_data():
    logging.info("Starting ChocoCard data download...")

    # Log in to ChocoCard
    driver.get('https://mychococard.com/Account/Login')
    wait_for_element(By.NAME, 'username').send_keys(choco_username)
    wait_for_element(By.NAME, 'password').send_keys(choco_password)
    wait_for_clickable(By.ID, 'loginBtn').click()

    logging.info("Logged into ChocoCard successfully")
    wait_for_element(By.XPATH, "//h3[contains(text(), 'Group / Branch List')]")

    # Base URL for downloading branch inventory data
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

    # Prepare dictionary for storing organized inventory data
    reorganized_inventory = {}

    # Download and process data for each branch
    for branch_name, (id_, template_id) in branches.items():
        success = False
        retries = 0
        max_retries = 5
        delay = 5

        while not success and retries < max_retries:
            try:
                url = base_url.format(id_, template_id)
                
                # Send GET request
                response = requests.get(url, cookies={c['name']: c['value'] for c in driver.get_cookies()})
                
                # Check response status
                if response.status_code == 200:
                    excel_file = BytesIO(response.content)
                    
                    # Read Excel file
                    df = pd.read_excel(excel_file, engine='openpyxl')
                    df = df[['Item', 'SKU', 'Available Qty.']]  # Select necessary columns
                    df.columns = ['Item', 'SKU', 'Qty']  # Rename columns

                    # Organize data and add to inventory
                    for _, row in df.iterrows():
                        item = row['Item']
                        sku = row['SKU']
                        qty = int(row['Qty'])  # Convert quantity to integer

                        if item not in reorganized_inventory:
                            reorganized_inventory[item] = {
                                "SKU": sku,
                                "Branch": OrderedDict()
                            }
                        reorganized_inventory[item]["Branch"][branch_name] = qty

                    logging.info(f"Successfully processed data for branch: {branch_name}")
                    success = True  # Mark as successful to exit the retry loop

                else:
                    raise Exception(f"File download failed. Status: {response.status_code}")

            except Exception as e:
                retries += 1
                logging.warning(f"Attempt {retries} for branch {branch_name} failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)

        if not success:
            logging.error(f"Failed to download and process data for branch: {branch_name} after {max_retries} attempts")

    logging.info("ChocoCard data has been processed for all branches")
    return reorganized_inventory  # Return the organized data

# Fetch data from the API
@retry(max_retries=5, delay=5)
def fetch_api_data():
    api_url = "https://open-api.zortout.com/v4/Product/GetProducts"
    headers = {
        "storename": zort_storename,
        "apikey": zort_apikey,
        "apisecret": zort_apisecret
    }

    logging.info("Fetching data from ZORT API...")
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    logging.info("ZORT API data fetched successfully.")
    return response.json()

# Function for downloading vending machine data
@retry(max_retries=5, delay=5)
def download_vending_data():
    global driver  # Use global variable to reset driver
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        try:
            if attempt > 0:
                logging.info(f"Attempt {attempt + 1} to download vending data")
            
            # Reset WebDriver
            if 'driver' in globals():
                driver.quit()
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Create a temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                # Set Chrome options for download
                chrome_options.add_experimental_option("prefs", {
                    "download.default_directory": temp_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True
                })

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

                # Wait for the download to complete
                time.sleep(10)  # Adjust this time as needed

                # Check if file is downloaded
                downloaded_files = os.listdir(temp_dir)
                if not downloaded_files:
                    raise Exception("No file was downloaded")

                # Assume the first file is our target
                file_path = os.path.join(temp_dir, downloaded_files[0])

                # Read the Excel file
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                    # Drop the first row (which doesn't contain headers)
                    df = df.drop(index=0)
                    logging.info("Successfully read vending machine data")
                    return df
                except Exception as e:
                    raise Exception(f"Failed to read Excel data: {e}")

        except Exception as e:
            attempt += 1
            if attempt < max_attempts:
                logging.error(f"Attempt {attempt} failed: {e}")
                time.sleep(5)  # Wait before retrying
            else:
                raise  # Raise exception if all attempts are exhausted

    raise Exception("Failed to download vending data after multiple attempts")

# Function for downloading Google Sheets as CSV
@retry(max_retries=5, delay=5)
def download_google_sheet():
    logging.info("Downloading data from HQ")
    
    # Google Sheets URL and settings for CSV download
    sheet_url = "https://docs.google.com/spreadsheets/d/1jGJw7N9fYjFZtVtvGQc7dyeCdjQRXNzr/export?format=csv&gid=1922842361"
    
    try:
        # Use requests to download CSV data
        response = requests.get(sheet_url)
        response.raise_for_status()  # Check for HTTP errors
        
        # Create DataFrame directly from CSV data
        csv_data = io.StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(csv_data)
        
        logging.info("Successfully downloaded Google Sheets data")
        return df
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Unable to download Google Sheets file. Reason: {e}")
        raise  # Propagate the error for the `retry` decorator to handle

# Update process_google_sheet_data function to use the DataFrame from download_google_sheet
def process_google_sheet_data(reorganized_inventory):
    # Download data from Google Sheets
    df = download_google_sheet()

    # We'll start reading data from row 4 and use columns C (SKU), D (Item), H (Qty)
    df = df.iloc[2:, [2, 3, 7]]  # Select desired rows and columns
    df.columns = ['SKU', 'Item', 'Qty']  # Rename columns

    # Convert Qty to int
    df['Qty'] = df['Qty'].astype(int)

    # Add data for "HQ" branch to `reorganized_inventory`
    for _, row in df.iterrows():
        item = row['Item']
        sku = row['SKU']
        qty = row['Qty']

        if item not in reorganized_inventory:
            reorganized_inventory[item] = {
                "SKU": sku,
                "Branch": OrderedDict()
            }
        reorganized_inventory[item]["Branch"]['HQ'] = qty

    logging.info("Processed Google Sheets data and added to inventory")

# Process Data From Saimai.xlsx
def process_saimai_data(reorganized_inventory):
    # Load saimai.xlsx file, skipping the first row
    saimai_file = 'saimai.xlsx'
    df_saimai = pd.read_excel(saimai_file, engine='openpyxl')

    # Load sku_mapping.csv file
    sku_mapping_file = 'sku_mapping.csv'
    sku_mapping_df = pd.read_csv(sku_mapping_file)

    # Create dictionary for sku mapping
    sku_mapping = dict(zip(sku_mapping_df['Saimai'], sku_mapping_df['SKU']))

    # Process data from saimai.xlsx
    for _, row in df_saimai.iterrows():
        sku = row.iloc[0]  # SKU from Column A (index 0)
        item = row.iloc[1]  # Item name from Column B (index 1)
        qty = float(row.iloc[4])  # Quantity from Column E (index 4)

        # Check SKU and do mapping
        mapped_sku = sku_mapping.get(sku, sku)

        # Add data to reorganized_inventory
        if item not in reorganized_inventory:
            reorganized_inventory[item] = {
                "SKU": mapped_sku,
                "Branch": OrderedDict()
            }
        reorganized_inventory[item]["Branch"]['Saimai'] = qty

    logging.info("Processed data from saimai.xlsx and added to inventory.")

# Process all data
def process_data():
    # Process ChocoCard data first
    reorganized_inventory = download_chococard_data()  # Start with ChocoCard data
    
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

    # Process Vending Machine data
    logging.info("Starting Vending Machine data download...")
    try:
        df = download_vending_data()  # This now returns a DataFrame

        if df is not None and not df.empty:
            # Iterate through the DataFrame
            for _, row in df.iterrows():
                item = row.iloc[4]
                branch = row.iloc[2]
                sku = row.iloc[3]
                qty = int(row.iloc[7])

                # Organize data in the dictionary
                if item not in reorganized_inventory:
                    reorganized_inventory[item] = {
                        "SKU": sku,
                        "Branch": OrderedDict()
                    }
                reorganized_inventory[item]["Branch"][branch] = qty
            logging.info("Finished processing Vending Machine data")
        else:
            logging.error("Vending machine data is empty or None")
    except Exception as e:
        logging.error(f"Error processing Vending Machine data: {e}")

    # Process Google Sheets data
    logging.info("Processing Google Sheets data...")
    process_google_sheet_data(reorganized_inventory)
    
    # Process saimai data
    logging.info("Processing Saimai.xlsx data...")
    process_saimai_data(reorganized_inventory)

    # Convert to the desired structure
    result_inventory = []
    for item, details in reorganized_inventory.items():
        result_inventory.append({
            "Item": item,
            "SKU": details["SKU"],
            "Branch": details["Branch"]
        })

    # Export Inventory Data
    json_filename = 'inventory_data3.json'
    final_result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inventory": result_inventory
    }
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(final_result, json_file, ensure_ascii=False, separators=(',', ':'))

    logging.info(f"Inventory data exported to {json_filename}")
    
    # Save another file to /data
    data_folder = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_folder, exist_ok=True)

    # Generate filename with DDMMYY_Timestamp
    timestamp = datetime.now().strftime("%H%M%S")
    date_str = datetime.now().strftime("%d%m%y")
    data_json_filename = os.path.join(data_folder, f"{date_str}_{timestamp}.json")

    # Write the inventory to the new JSON file
    with open(data_json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(final_result, json_file, ensure_ascii=False, separators=(',', ':'))

    logging.info(f"Inventory data exported to {data_json_filename}")
    
    # Send notification when file creation is complete
    timestamp = datetime.now().strftime('%d%m%y - %H:%M:%S')
    message = f"Successfully created inventory data file on {timestamp}"
    send_line_notify(message)
    logging.info(message)

# Function to send message to Line Notify
def send_line_notify(message):
    line_notify_token = os.getenv('LINE_NOTIFY_TOKEN')  # Set Access Token in .env
    headers = {
        "Authorization": f"Bearer {line_notify_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {'message': message}
    response = requests.post("https://notify-api.line.me/api/notify", headers=headers, params=payload)
    return response.status_code

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
        json.dump(json_files, file, ensure_ascii=False, separators=(',', ':'))

    print(f"Generated {file_list_path} with {len(json_files)} JSON files.")

# Run the functions
try:
    process_data()
finally:
    # Generate JSON List in /data
    # generate_file_list()
    
    # Close the browser
    logging.info("Closing the browser...")
    driver.quit()
