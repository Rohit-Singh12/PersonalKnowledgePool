import requests
import typer
import urllib.parse

from schemas.search_result_model import SearchResults, SearchResult

app = typer.Typer()

def query_web(topic: str, base_url: str = "http://searxng:8080") -> SearchResults:
    """
    Queries a local SearXNG instance and extracts titles and URLs for a given topic.
    """
    # Safe encoding for the query string
    encoded_query = urllib.parse.quote(topic)

    # We append &format=json to get machine-readable output
    # categories=news,general ensures we target articles and web pages
    search_url = f"{base_url}/search?q={encoded_query}&format=json&categories=general,news&language=en"
    headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }

    try:
        response = requests.get(search_url, headers, timeout=10)
        response.raise_for_status() # Raise exception for 4XX/5XX errors

        search_data = response.json()
        results = search_data.get("results", [])

        extracted_feeds = SearchResults(results=[])
        for item in results:
            # We want to make sure the item has a valid URL and Title
            if "url" in item and "title" in item:
                extracted_feeds.results.append(SearchResult(
                    title = item["title"],
                    url = item["url"],
                    snippet =  item.get("content", "") # The brief text summary from search
                ))

        return extracted_feeds

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to SearXNG: {e}")
        return SearchResults(results=[])

if __name__ == "__main__":
    app()
