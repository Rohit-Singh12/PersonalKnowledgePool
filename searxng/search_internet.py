import requests
import urllib.parse

def fetch_article_urls(topic: str, base_url: str = "http://localhost:8888") -> list:
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
        
        extracted_feeds = []
        for item in results:
            # We want to make sure the item has a valid URL and Title
            if "url" in item and "title" in item:
                extracted_feeds.append({
                    "title": item["title"],
                    "url": item["url"],
                    "snippet": item.get("content", "") # The brief text summary from search
                })
                
        return extracted_feeds

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to SearXNG: {e}")
        return []

# --- Run the Example ---
if __name__ == "__main__":
    # Target topic
    topic_to_search = "Solid state battery breakthroughs 2026"
    
    print(f"Searching SearXNG for: '{topic_to_search}'...\n")
    articles = fetch_article_urls(topic_to_search)
    
    if articles:
        print(f"Found {len(articles)} relevant articles:\n")
        for idx, article in enumerate(articles, 1):
            print(f"{idx}. {article['title']}")
            print(f"   URL: {article['url']}")
            print(f"   Snippet: {article['snippet'][:120]}...\n")
    else:
        print("No articles found or SearXNG is unreachable.")
