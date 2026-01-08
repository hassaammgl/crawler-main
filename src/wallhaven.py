import os
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import re
from .base import BaseScraper

logger = logging.getLogger(__name__)

class WallHavenScraper(BaseScraper):
    def __init__(self, base_url, max_wallpapers=10, timeout=15, retries=3, delay_range=(2, 5)):
        """
        Initialize the WallHaven scraper.
        
        :param base_url: The starting URL (e.g., https://wallhaven.cc/search?q=anime)
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
            'Referer': 'https://wallhaven.cc/',
        })

    def _get_save_path(self, query=None):
        """Create a structured folder based on the query or base URL."""
        if query:
            folder_name = re.sub(r'[\\/*?:"<>|]', "", query)
        else:
            parsed_url = urlparse(self.base_url)
            folder_name = parsed_url.path.strip('/').split('/')[-1] or "wallpapers"
        
        path = os.path.join("downloads", "wallhaven", folder_name)
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
        """Extract wallpaper detail links from the index page."""
        soup = BeautifulSoup(page_html, 'html.parser')
        links = []
        # Wallhaven typically lists wallpapers as <a class="preview" href="...">
        for a in soup.find_all('a', class_='preview'):
            href = a.get('href')
            if href:
                full_url = urljoin("https://wallhaven.cc", href)
                if full_url not in links:
                    links.append(full_url)
        return links

    def get_image_url(self, detail_url):
        """Extract the full-resolution image URL from the wallpaper detail page."""
        html = self.fetch_html(detail_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Wallhaven detail page usually has <img id="wallpaper" src="..." />
        img_tag = soup.find('img', id='wallpaper')
        if img_tag and img_tag.get('src'):
            return img_tag['src']
            
        logger.warning(f"Could not find full-res image URL for {detail_url}")
        return None

    def download_image(self, img_url, save_dir):
        """Download image using streamed requests to save memory."""
        try:
            filename = os.path.basename(img_url).split('?')[0]
            # Sanitize filename
            filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
            save_path = os.path.join(save_dir, filename)

            if os.path.exists(save_path):
                logger.info(f"Skipping already-downloaded image: {filename}")
                return True

            response = self.session.get(img_url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            
            with open(save_path, 'wb') as f, tqdm(
                total=total_size, unit='iB', unit_scale=True, desc=filename, leave=False
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
            
            logger.info(f"Successfully downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {img_url}: {e}")
            if os.path.exists(save_path):
                os.remove(save_path)  # Clean up partial download
            return False

    def run(self):
        """Orchestrate the scraping process."""
        logger.info(f"Starting scraper for: {self.base_url}")
        
        # Determine query for folder naming
        parsed = urlparse(self.base_url)
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        query = qs.get('q', [None])[0]
        
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
            
            for detail_url in wallpaper_links:
                if self.downloaded_count >= self.max_wallpapers:
                    break
                
                logger.info(f"Processing wallpaper: {detail_url}")
                img_url = self.get_image_url(detail_url)
                
                if img_url:
                    self._polite_delay()
                    if self.download_image(img_url, save_dir):
                        self.downloaded_count += 1
                
                self._polite_delay()
            
            # Pagination support
            soup = BeautifulSoup(page_html, 'html.parser')
            # Look for next page link. Usually <a class="next" href="...">
            next_link = soup.find('a', class_='next')
            if next_link and next_link.get('href'):
                current_page_url = urljoin("https://wallhaven.cc", next_link['href'])
            else:
                logger.info("No more pages found.")
                break

        logger.info(f"Scraping complete. Downloaded {self.downloaded_count} wallpapers.")
