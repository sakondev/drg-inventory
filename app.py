# VERSION 3.5

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
import shutil  # ใช้สำหรับย้ายไฟล์
import warnings

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

# Set the download folder path
download_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'excel_temp')
os.makedirs(download_folder, exist_ok=True)

# Set up headless options
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # ใช้ headless รุ่นใหม่ของ Chrome (เวอร์ชัน 109 ขึ้นไป)
chrome_options.add_argument("--window-position=-10000,-10000")   # แก้บั๊ก Chrome 129
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")  # ปิดการใช้ GPU
chrome_options.add_argument("--disable-software-rasterizer")  # ปิดการใช้ software renderer
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # ปิดการตรวจจับ selenium
chrome_options.add_argument("--disable-extensions")  # ปิดส่วนขยายที่ไม่จำเป็น
chrome_options.add_argument("--disable-infobars")  # ปิดแถบข้อมูลที่เกี่ยวกับ automation

chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_folder,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Initialize the WebDriver as a background service
driver = webdriver.Chrome(service=service, options=chrome_options)

# Function to wait for an element to be clickable
def wait_for_clickable(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))

# Function to wait for an element to be present
def wait_for_element(by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

# Function to clean up a specific file
def delete_file(file_path):
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            logging.info(f"Deleted file: {file_path}")
    except Exception as e:
        logging.error(f"Failed to delete {file_path}. Reason: {e}")

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

    # Download and process data for each branch with retry logic
    for branch, (id_, template_id) in branches.items():
        success = False
        retries = 0
        max_retries = 5
        delay = 5

        while not success and retries < max_retries:
            try:
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

                # Check if the file is valid (e.g., check if it's a valid Excel file)
                if downloaded_file.endswith('.xlsx'):
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

                    logging.info(f"Successfully processed data for: {branch}")
                    success = True  # Mark success to exit the retry loop

                else:
                    raise Exception("Downloaded file is not a valid Excel file.")

            except Exception as e:
                retries += 1
                logging.warning(f"Attempt {retries} failed for branch {branch}: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)

        if not success:
            logging.error(f"Failed to download and process data for: {branch} after {max_retries} attempts.")

    logging.info("ChocoCard data has been processed for all branches.")
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

# ฟังก์ชันสำหรับดาวน์โหลดและเขียนทับไฟล์ vending machine
@retry(max_retries=5, delay=5)
def download_vending_data():
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

    # Wait for the download to complete (ปรับเวลาตามความจำเป็น)
    time.sleep(5)

    # ค้นหาไฟล์ล่าสุดที่ดาวน์โหลดในโฟลเดอร์
    downloaded_file = max(
        [os.path.join(download_folder, f) for f in os.listdir(download_folder) if f.endswith('.xlsx')],
        key=os.path.getctime
    )

    # ชื่อไฟล์ที่จะเขียนทับ
    renamed_file = os.path.join(download_folder, 'vending_stock.xlsx')

    # ถ้าไฟล์ vending_stock.xlsx มีอยู่แล้ว ให้ลบทิ้งก่อน
    if os.path.exists(renamed_file):
        try:
            os.remove(renamed_file)
            logging.info(f"Deleted existing file: {renamed_file}")
        except Exception as e:
            logging.error(f"Failed to delete the existing file. Reason: {e}")
            raise

    # ย้ายไฟล์ที่ดาวน์โหลดมาและตั้งชื่อใหม่
    try:
        shutil.move(downloaded_file, renamed_file)
        logging.info(f"Downloaded vending machine file renamed to: {renamed_file}")
    except Exception as e:
        logging.error(f"Failed to move the file. Reason: {e}")
        raise

# ฟังก์ชันสำหรับดาวน์โหลด Google Sheets เป็น CSV
@retry(max_retries=5, delay=5)
def download_google_sheet():
    logging.info("Downloading data from HQ")
    
    # Google Sheets URL และการตั้งค่าเพื่อดาวน์โหลดเป็น CSV
    sheet_url = "https://docs.google.com/spreadsheets/d/1jGJw7N9fYjFZtVtvGQc7dyeCdjQRXNzr/export?format=csv&gid=1922842361"
    
    # ดาวน์โหลดไฟล์ CSV ไปยังโฟลเดอร์ที่กำหนด
    csv_filename = os.path.join(download_folder, "google_sheet_data.csv")
    
    try:
        # ใช้ requests ในการดาวน์โหลดไฟล์ CSV
        response = requests.get(sheet_url)
        response.raise_for_status()  # ตรวจสอบข้อผิดพลาด HTTP
        
        # เขียนข้อมูลที่ดาวน์โหลดมาเป็นไฟล์ CSV
        with open(csv_filename, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"Google Sheets file downloaded successfully: {csv_filename}")
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download Google Sheets file. Reason: {e}")
        raise  # ส่งต่อข้อผิดพลาดเพื่อให้ `retry` ทำงาน
    
    return csv_filename

# ฟังก์ชันสำหรับประมวลผลข้อมูลจาก Google Sheets CSV
def process_google_sheet_data(reorganized_inventory):
    # ดาวน์โหลดไฟล์ CSV จาก Google Sheets
    csv_file = download_google_sheet()

    # อ่านไฟล์ CSV
    df = pd.read_csv(csv_file)

    # เราจะเริ่มต้นการอ่านข้อมูลจาก row ที่ 4 และใช้ column C (SKU), D (Item), H (Qty)
    df = df.iloc[2:, [2, 3, 7]]  # เลือก rows และ columns ที่ต้องการ
    df.columns = ['SKU', 'Item', 'Qty']  # ตั้งชื่อ columns ใหม่

    # แปลงค่า Qty เป็น float
    df['Qty'] = df['Qty'].astype(float)

    # เพิ่มข้อมูลของ branch "HQ" ลงใน `reorganized_inventory`
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

    logging.info("Processed data from Google Sheets and added to inventory.")
    
# Process Data From Saimai.xlsx
def process_saimai_data(reorganized_inventory):
    # โหลดไฟล์ saimai.xlsx โดยข้ามแถวแรก
    saimai_file = 'saimai.xlsx'
    df_saimai = pd.read_excel(saimai_file, engine='openpyxl')

    # โหลดไฟล์ sku_mapping.csv
    sku_mapping_file = 'sku_mapping.csv'
    sku_mapping_df = pd.read_csv(sku_mapping_file)

    # สร้าง dictionary สำหรับ sku mapping
    sku_mapping = dict(zip(sku_mapping_df['Saimai'], sku_mapping_df['SKU']))

    # ประมวลผลข้อมูลจาก saimai.xlsx
    for _, row in df_saimai.iterrows():
        sku = row.iloc[0]  # SKU จาก Column A (index 0)
        item = row.iloc[1]  # ชื่อสินค้า จาก Column B (index 1)
        qty = float(row.iloc[4])  # จำนวน จาก Column E (index 4)

        # ตรวจสอบ SKU และทำ mapping
        mapped_sku = sku_mapping.get(sku, sku)

        # เพิ่มข้อมูลใน reorganized_inventory
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

    # Process Vending Machine data using the saved 'vending_stock.xlsx'
    logging.info("Processing Vending Machine data...")
    sku_mapping_file = 'sku_mapping.csv'  # Specify the path to your SKU mapping CSV file
    vending_file = os.path.join(download_folder, 'vending_stock.xlsx')  # Use the renamed file

    if os.path.exists(vending_file):
        df = pd.read_excel(vending_file, engine='openpyxl')

        # Drop the first row (which doesn't contain headers)
        df = df.drop(index=0)

        # Load SKU mapping CSV (this maps Goods Name to SKU)
        sku_mapping_df = pd.read_csv(sku_mapping_file)

        # Create a dictionary for quick SKU lookup
        sku_mapping = dict(zip(sku_mapping_df['Goods Name'], sku_mapping_df['SKU']))

        # Iterate through the DataFrame
        for _, row in df.iterrows():
            item = row.iloc[4]
            branch = row.iloc[2]
            qty = float(row.iloc[7])

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
    json_filename = 'inventory_data.json'
    final_result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inventory": result_inventory
    }
    with open(json_filename, 'w', encoding='utf-8') as json_file:
        json.dump(final_result, json_file, ensure_ascii=False, indent=4)

    logging.info(f"Inventory data exported to {json_filename}")

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