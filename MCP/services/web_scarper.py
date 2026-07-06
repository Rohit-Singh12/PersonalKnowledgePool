import asyncio

import typer
from crawl4ai import AsyncWebCrawler

app = typer.Typer()


async def scrape_website_async(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        res = str(result.markdown)
        print("=========")
        print(res)
        return res


@app.command()
def scrape_website(url: str) -> str:
    return asyncio.run(scrape_website_async(url))


if __name__ == '__main__':
    app()
