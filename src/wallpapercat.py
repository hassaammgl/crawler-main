import os
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from .base import BaseScraper

logger = logging.getLogger(__name__)

class WallpaperCatScraper(BaseScraper):
    def __init__(self, base_url, max_wallpapers=10, timeout=15, retries=3, delay_range=(2, 5)):
        """
        Initialize the WallpaperCat scraper.
        
        :param base_url: The starting URL (e.g., https://wallpapercat.com/naruto-wallpapers)
        :param max_wallpapers: Maximum number of images to download
        :param timeout: Request timeout in seconds
        :param retries: Number of retry attempts for failed requests
        :param delay_range: Tuple (min, max) for random delay between requests
        """
        self.base_url = base_url
        self.max_wallpapers = max_wallpapers
        self.timeout = timeout
        self.retries = retries
        self.delay_range = delay_range
        self.downloaded_count = 0
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://wallpapercat.com/',
        })

    def _get_save_path(self, query=None):
        """Create a structured folder based on the query or base URL."""
        if query:
            folder_name = re.sub(r'[\\/*?:"<>|]', "", query)
        else:
            parsed_url = urlparse(self.base_url)
            # e.g., /naruto-wallpapers -> naruto
            path_part = parsed_url.path.strip('/').split('/')[-1]
            folder_name = path_part.replace('-wallpapers', '') or "wallpapers"
        
        path = os.path.join("downloads", "wallpapercat", folder_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _polite_delay(self):
        """Sleep for a random duration to avoid aggressive scraping."""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)

    def fetch_html(self, url):
        """Fetch HTML content from a URL with retries."""
        for attempt in range(self.retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {self.retries} attempts.")
        return None

    def get_wallpaper_links(self, page_html):
        """Extract wallpaper detail links (actually directly image links) from the index page."""
        soup = BeautifulSoup(page_html, 'html.parser')
        links = []
        
        # Look for div with data-fullimg attribute
        # <div id="140909" data-fullimg="/w/full/..." ...>
        for div in soup.find_all('div', attrs={'data-fullimg': True}):
            full_img_path = div.get('data-fullimg')
            if full_img_path:
                full_url = urljoin("https://wallpapercat.com", full_img_path)
                if full_url not in links:
                    links.append(full_url)
        return links

    def get_image_url(self, detail_url):
        """
        For WallpaperCat, detail_url IS the image URL (since we extracted it directly).
        Just return it.
        """
        return detail_url

    def run(self):
        """Orchestrate the scraping process."""
        logger.info(f"Starting scraper for: {self.base_url}")
        
        # Determine query for folder naming
        # Extract query from URL if possible, or pass None to use path
        # In main.py we construct URL like https://wallpapercat.com/naruto-wallpapers
        # So we can infer query from path.
        
        # If the URL is search result, we might handle it differently, but we are using slug URLs.
        parsed = urlparse(self.base_url)
        query = parsed.path.strip('/').replace('-wallpapers', '')
        
        save_dir = self._get_save_path(query)
        current_page_url = self.base_url
        
        while self.downloaded_count < self.max_wallpapers:
            logger.info(f"Scraping page: {current_page_url}")
            page_html = self.fetch_html(current_page_url)
            if not page_html:
                break
            
            wallpaper_links = self.get_wallpaper_links(page_html)
            if not wallpaper_links:
                logger.warning("No wallpaper links found on this page.")
                break
            
            for img_url in wallpaper_links:
                if self.downloaded_count >= self.max_wallpapers:
                    break
                
                logger.info(f"Processing wallpaper: {img_url}")
                # img_url is already the full image url
                
                self._polite_delay()
                if self.download_image(img_url, save_dir):
                    self.downloaded_count += 1
                
                self._polite_delay()
            
            # Pagination support
            # Check for <a rel="next"> or similar
            soup = BeautifulSoup(page_html, 'html.parser')
            # Assuming classic pagination if it exists (hidden in JS otherwise)
            # Let's look for a generic "Next" link just in case
            next_link = soup.find('a', string=re.compile(r'Next|»', re.I)) or soup.find('a', rel='next')
            
            if next_link and next_link.get('href'):
                current_page_url = urljoin("https://wallpapercat.com", next_link['href'])
            else:
                logger.info("No more pages found (or pagination not supported).")
                break

        logger.info(f"Scraping complete. Downloaded {self.downloaded_count} wallpapers.")
