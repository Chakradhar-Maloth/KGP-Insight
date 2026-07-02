import os
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def main():
    logging.info("=============================================")
    logging.info("Starting KGP Insight: Phase 1 Data Pipeline")
    logging.info("=============================================")

    # 1. Run the layout-aware PDF parser
    logging.info("Step 1: Running Layout-Aware PDF Parser on UG Academic Regulations...")
    try:
        # Use venv python to execute
        python_bin = os.path.join("venv", "bin", "python")
        if not os.path.exists(python_bin):
            python_bin = "python3" # Fallback
        
        subprocess.run([python_bin, "scraper/pdf_parser.py"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"PDF Parser script failed: {e}")
        return

    # 2. Run the ERP Scraper
    logging.info("Step 2: Running ERP Scraper...")
    try:
        subprocess.run([python_bin, "scraper/erp_scraper.py"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"ERP Scraper script failed: {e}")
        return

    # 3. Report Results
    logging.info("=============================================")
    logging.info("Phase 1 Execution Summary:")
    logging.info("=============================================")
    
    pdf_data_path = "data/parsed_pdf_data.jsonl"
    erp_data_path = "data/raw_erp_data.jsonl"
    
    pdf_pages = get_file_lines(pdf_data_path)
    erp_notices = get_file_lines(erp_data_path)
    
    logging.info(f"✔ PDF Parser Output: {pdf_data_path} ({pdf_pages} layout-aware pages parsed)")
    logging.info(f"✔ ERP Scraper Output: {erp_data_path} ({erp_notices} notice records scraped/mocked)")
    logging.info("✔ Scraper directory contains crawler templates for static sites.")
    logging.info("=============================================")
    logging.info("To run the full static site web crawler (respects robots.txt):")
    logging.info(f"  {python_bin} scraper/static_crawler.py")
    logging.info("=============================================")

if __name__ == "__main__":
    main()
