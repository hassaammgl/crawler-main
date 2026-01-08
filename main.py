import logging
import sys
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.logging import RichHandler

# Ensure src is importable
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.wallhere import WallHereScraper
from src.wallhaven import WallHavenScraper

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
        "1": "WallHere",
        "2": "WallHaven"
    }

    console.print("\n[bold]Available Scrapers:[/bold]")
    for key, name in options.items():
        console.print(f"[{key}] {name}")

    choice = Prompt.ask("Select scraper", choices=list(options.keys()), default="1")
    
    selected_scraper = options[choice]
    console.print(f"\n[green]Selected: {selected_scraper}[/green]")

    if choice == "1":
        # WallHere defaults
        default_val = "naruto"
        user_input = Prompt.ask("Enter Search URL or Query", default=default_val)
        
        if user_input.startswith("http"):
            url = user_input
        else:
            url = f"https://wallhere.com/en/wallpapers?q={user_input}"
            
        limit = IntPrompt.ask("Max wallpapers to download", default=10)
        
        scraper = WallHereScraper(base_url=url, max_wallpapers=limit)
        
    elif choice == "2":
        # WallHaven defaults
        default_val = "anime"
        user_input = Prompt.ask("Enter Search URL or Query", default=default_val)
        
        if user_input.startswith("http"):
            url = user_input
        else:
            url = f"https://wallhaven.cc/search?q={user_input}"
            
        limit = IntPrompt.ask("Max wallpapers to download", default=10)
        
        scraper = WallHavenScraper(base_url=url, max_wallpapers=limit)

    console.rule("[bold yellow]Starting Scraping")
    try:
        scraper.run()
    except Exception as e:
        logger.exception("An error occurred during scraping")
    
    console.rule("[bold blue]Done")

if __name__ == "__main__":
    main()