from src.web_scraper import WebScraper
from src.config import DEFAULT_CONFIG

def main():
    scraper = WebScraper(
        base_url=DEFAULT_CONFIG['TARGET_URL'],
        output_dir=DEFAULT_CONFIG['OUTPUT_DIR']
    )
    scraper.run()

if __name__ == '__main__':
    main()