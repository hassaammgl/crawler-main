import os
import re
import logging
from abc import ABC, abstractmethod
from tqdm import tqdm

logger = logging.getLogger("scraper")

class BaseScraper(ABC):
    @abstractmethod
    def run(self):
        """Run the scraper logic."""
        pass

    def _sanitize_and_shorten_filename(self, filename, max_length=64):
        """Sanitize filename and shorten if it exceeds max_length."""
        # Remove invalid characters
        filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
        
        # Split extension
        name, ext = os.path.splitext(filename)
        
        # Shorten if needed
        if len(name) > max_length:
            # Keep the start and a bit of the end or just truncate? 
            # User said "shortername", truncation is safest/simplest, 
            # maybe add a hash if collision is a worry, but scraper loop usually handles unique URLs.
            # Let's just truncate the name part.
            name = name[:max_length] + "..."
            
        return name + ext

    def download_image(self, img_url, save_dir):
        """Download image using streamed requests to save memory."""
        try:
            # Extract filename from URL
            original_filename = os.path.basename(img_url).split('?')[0]
            
            # Sanitize and shorten
            filename = self._sanitize_and_shorten_filename(original_filename)
            save_path = os.path.join(save_dir, filename)

            if os.path.exists(save_path):
                logger.info(f"Skipping already-downloaded image: {filename}")
                return True

            # Ensure session is available
            if not hasattr(self, 'session'):
                raise AttributeError("Scraper instance must have a 'session' attribute.")
            
            timeout = getattr(self, 'timeout', 15)

            response = self.session.get(img_url, stream=True, timeout=timeout)
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
            if 'save_path' in locals() and os.path.exists(save_path):
                os.remove(save_path)  # Clean up partial download
            return False
