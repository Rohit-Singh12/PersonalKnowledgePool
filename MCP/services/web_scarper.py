import typer
from crawl4ai import AsyncWebCrawler
import asyncio

app = typer.Typer()


async def scrape_website_async(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
        )
        return result

@app.command()
def scrape_website(url: str):
    result = asyncio.run(scrape_website_async(url))
    # print(result.markdown)
    return result.markdown

if __name__ == '__main__':
	app()
