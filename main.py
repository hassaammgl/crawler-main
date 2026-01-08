import logging
import sys
from urllib.parse import quote
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.logging import RichHandler

# Ensure src is importable
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.wallhere import WallHereScraper
from src.wallhaven import WallHavenScraper
from src.wallpapercat import WallpaperCatScraper

# Configure nice logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("scraper")

def main():
    console = Console()
    console.rule("[bold blue]Universal Wallpaper Scraper TUI")

    options = {
        "1": {
            "name": "WallHere",
            "class": WallHereScraper,
            "default": "naruto",
            "idx": "1",
            "url_gen": lambda q: f"https://wallhere.com/en/wallpapers?q={quote(q)}"
        },
        "2": {
            "name": "WallHaven",
            "class": WallHavenScraper,
            "default": "anime",
            "idx": "2",
            "url_gen": lambda q: f"https://wallhaven.cc/search?q={quote(q)}"
        },
        "3": {
            "name": "WallpaperCat",
            "class": WallpaperCatScraper,
            "default": "naruto",
            "idx": "3",
            "url_gen": lambda q: f"https://wallpapercat.com/search?term={quote(q)}"
        }
    }

    console.print("\n[bold]Available Scrapers:[/bold]")
    for key, data in options.items():
        console.print(f"[{key}] {data['name']}")
    console.print("[4] All Scrapers")

    choice = Prompt.ask("Select scraper", choices=list(options.keys()) + ["4"], default="1")
    
    scrapers_to_run = []
    
    if choice == "4":
        console.print(f"\n[green]Selected: All Scrapers[/green]")
        query = Prompt.ask("Enter Search Query for ALL sites", default="anime")
        limit = IntPrompt.ask("Max wallpapers per site", default=10)
        
        for key, data in options.items():
            url = data["url_gen"](query)
            scrapers_to_run.append(data["class"](base_url=url, max_wallpapers=limit))
            
    else:
        selected = options[choice]
        console.print(f"\n[green]Selected: {selected['name']}[/green]")
        
        user_input = Prompt.ask("Enter Search URL or Query", default=selected["default"])
        
        if user_input.startswith("http"):
            url = user_input
        else:
            url = selected["url_gen"](user_input)
            
        limit = IntPrompt.ask("Max wallpapers to download", default=10)
        scrapers_to_run.append(selected["class"](base_url=url, max_wallpapers=limit))

    console.rule("[bold yellow]Starting Scraping")
    
    for i, scraper in enumerate(scrapers_to_run):
        if i > 0:
            console.print("") # spacing
        try:
            scraper.run()
        except Exception as e:
            logger.exception(f"An error occurred during scraping with {type(scraper).__name__}")
    
    console.rule("[bold blue]Done")

if __name__ == "__main__":
    main()