import os
import json
import logging
import requests
import pdfplumber

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PDF_TARGETS = [
    {
        "url": "https://www.iitkgp.ac.in/assets/pdf/Rules_and_RegulationsHMC.pdf",
        "local_path": "data/Rules_and_RegulationsHMC.pdf"
    },
    {
        "url": "https://www.iitkgp.ac.in/assets/pdf/AdministrativeCalendar.pdf",
        "local_path": "data/AdministrativeCalendar.pdf"
    }
]
OUTPUT_FILE = "data/parsed_pdf_data.jsonl"

def download_pdf(url, local_path):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    if os.path.exists(local_path):
        logging.info(f"PDF already exists locally at {local_path}. Skipping download.")
        return True
    
    logging.info(f"Downloading PDF from: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info("Download completed successfully.")
        return True
    except Exception as e:
        logging.error(f"Failed to download PDF: {e}")
        return False

def parse_pdf_layout_aware(pdf_path, source_url):
    if not os.path.exists(pdf_path):
        logging.error(f"File not found: {pdf_path}")
        return []

    logging.info(f"Opening PDF for layout-aware parsing: {pdf_path}")
    parsed_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages):
            page_num = idx + 1
            
            # 1. Locate tables on the page
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]
            
            md_tables = []
            for t in tables:
                grid = t.extract()
                if not grid:
                    continue
                
                # Format grid as clean Markdown table
                clean_grid = []
                for row in grid:
                    if row:
                        clean_row = [
                            (cell or "").replace("\n", " ").strip() 
                            for cell in row
                        ]
                        # Keep rows that aren't entirely empty
                        if any(clean_row):
                            clean_grid.append(clean_row)
                
                if not clean_grid or not clean_grid[0]:
                    continue
                
                headers = clean_grid[0]
                rows = clean_grid[1:]
                
                # Assemble Markdown table
                md_table = "| " + " | ".join(headers) + " |\n"
                md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                for r in rows:
                    # Align columns if row is shorter
                    if len(r) < len(headers):
                        r += [""] * (len(headers) - len(r))
                    elif len(r) > len(headers):
                        r = r[:len(headers)]
                    md_table += "| " + " | ".join(r) + " |\n"
                
                md_tables.append(md_table)

            # 2. Filter character layout to extract non-table text
            def not_within_table_bboxes(obj):
                x0 = obj.get("x0")
                y0 = obj.get("top")
                x1 = obj.get("x1")
                y1 = obj.get("bottom")
                if None in (x0, y0, x1, y1):
                    return True
                for tx0, ty0, tx1, ty1 in table_bboxes:
                    # Check if character coordinates lie within table bbox
                    if x0 >= tx0 and x1 <= tx1 and y0 >= ty0 and y1 <= ty1:
                        return False
                return True

            # Extract text excluding table boxes
            filtered_page = page.filter(not_within_table_bboxes)
            non_table_text = filtered_page.extract_text() or ""
            
            # Clean up consecutive newlines in textual context
            clean_text_blocks = [
                line.strip() 
                for line in non_table_text.split("\n") 
                if line.strip()
            ]
            clean_non_table_text = "\n".join(clean_text_blocks)

            # Combine plain text and markdown table layouts
            page_markdown_content = clean_non_table_text
            if md_tables:
                page_markdown_content += "\n\n### Tabular Data:\n" + "\n\n".join(md_tables)

            if page_markdown_content.strip():
                parsed_pages.append({
                    "page_number": page_num,
                    "source_path": pdf_path,
                    "source_url": source_url,
                    "text": page_markdown_content.strip()
                })
                
    return parsed_pages

def run_pipeline():
    all_pages = []
    
    # Process all targets
    for target in PDF_TARGETS:
        url = target["url"]
        path = target["local_path"]
        
        success = download_pdf(url, path)
        if success:
            pages = parse_pdf_layout_aware(path, url)
            all_pages.extend(pages)
        else:
            logging.error(f"Failed to process: {url}")
            
    # Write aggregated parsed pages to file
    if all_pages:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for p in all_pages:
                f.write(json.dumps(p) + "\n")
        logging.info(f"Aggregate parsing completed. Saved {len(all_pages)} pages to {OUTPUT_FILE}")
    else:
        logging.error("No pages parsed successfully.")

if __name__ == "__main__":
    run_pipeline()
