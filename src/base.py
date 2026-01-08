from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    def run(self):
        """Run the scraper logic."""
        pass
