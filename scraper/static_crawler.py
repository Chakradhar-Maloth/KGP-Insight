import os
import json
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawler.log", mode="w")
    ]
)

class KgpStaticSpider(scrapy.Spider):
    name = "kgp_static_spider"
    allowed_domains = ["iitkgp.ac.in", "hmc.iitkgp.ac.in", "www.hmc.iitkgp.ac.in"]
    start_urls = [
        "https://www.iitkgp.ac.in/navpage/student",
        "http://www.hmc.iitkgp.ac.in/web/",
        "https://www.iitkgp.ac.in/academics"
    ]

    custom_settings = {
        "USER_AGENT": "KgpInsightBot/1.0 (+https://github.com/chakradhar/KgpInsight)",
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 0.5,  # Polite delay
        "COOKIES_ENABLED": False,
        "ROBOTSTXT_OBEY": True,
        "DEPTH_LIMIT": 3,       # Stay close to main student guides
    }

    def __init__(self, output_file="data/raw_web_data.jsonl", *args, **kwargs):
        super(KgpStaticSpider, self).__init__(*args, **kwargs)
        self.output_file = output_file
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        # Open output file in write mode
        self.file = open(self.output_file, "w", encoding="utf-8")
        self.seen_urls = set()

    def closed(self, reason):
        self.file.close()
        self.log(f"Spider closed. Raw web data saved to {self.output_file}", level=logging.INFO)

    def parse(self, response):
        url = response.url
        if url in self.seen_urls:
            return
        self.seen_urls.add(url)

        # Ensure we are parsing an HTML page
        if not response.headers.get("Content-Type", b"").startswith(b"text/html"):
            return

        html_content = response.text
        soup = BeautifulSoup(html_content, "lxml")

        # Strip headers, footers, scripts, styles, and navigation bars to isolate useful text
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
            element.decompose()
        
        # Remove common layout classes or structural navigation divs if possible
        for selector in [".header", ".footer", ".navigation", ".sidebar", "#sidebar", "#header", "#footer", ".menu"]:
            for element in soup.select(selector):
                element.decompose()

        # Extract title
        title = soup.title.string.strip() if soup.title else ""
        
        # Clean text extraction
        text_blocks = []
        for string in soup.stripped_strings:
            # Skip very short or generic strings (e.g. "Home", "Back", ">")
            val = string.strip()
            if len(val) > 10:
                text_blocks.append(val)
        
        clean_text = "\n".join(text_blocks)

        # Extract PDF links on the page
        pdf_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(url, href)
            parsed_full = urlparse(full_url)
            
            # Check if it points to a PDF
            if parsed_full.path.endswith(".pdf"):
                pdf_links.append(full_url)
                
        # Only record pages that contain actual content
        if clean_text:
            data_item = {
                "url": url,
                "title": title,
                "text": clean_text,
                "pdf_links": list(set(pdf_links))
            }
            # Write to JSONL
            self.file.write(json.dumps(data_item) + "\n")
            self.file.flush()
            self.log(f"Successfully scraped: {url} | Found {len(pdf_links)} PDF links", level=logging.INFO)

        # Follow local links recursively
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            next_url = urljoin(url, href)
            parsed_next = urlparse(next_url)

            # Ensure we crawl only allowed domains and stay within http/https
            if parsed_next.netloc in self.allowed_domains and parsed_next.scheme in ["http", "https"]:
                # Exclude links pointing to PDFs (handled separately) or specific media extensions
                if not parsed_next.path.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".zip", ".docx")):
                    yield scrapy.Request(next_url, callback=self.parse)


def run_crawler():
    # Setup configuration logging
    configure_logging()
    
    process = CrawlerProcess()
    process.crawl(KgpStaticSpider)
    process.start()

if __name__ == "__main__":
    run_crawler()
