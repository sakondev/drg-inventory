import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_script(script_name):
    try:
        subprocess.run(['python', script_name], check=True)
        logging.info(f"Successfully executed {script_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {script_name}: {e}")
        raise

def main():
    try:
        logging.info("Starting the data processing pipeline")
        
        # Run main_download.py
        run_script('main_download.py')
        
        # Run main_database.py
        run_script('main_database.py')
        
        logging.info("Data processing pipeline completed successfully")
    except Exception as e:
        logging.error(f"An error occurred in the data processing pipeline: {e}")

if __name__ == "__main__":
    main()