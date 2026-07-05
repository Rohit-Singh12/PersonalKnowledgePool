from collections import defaultdict
import feedparser
import requests
from typing import List, Dict
import xml.etree.ElementTree as ET
from schemas.feed_model import FeedMetadata, FeedMetadataResponse, StrList

def fetch_articles_from_rss_feeds(urls: StrList) -> FeedMetadataResponse:
    """Fetches all the articles from the urls.

    Args:
        urls (list[str]): List of URLs which is to be parsed.

    Returns:
        list[dict]: Articles metadata.
    """
    aggregated_articles = FeedMetadataResponse()
    if isinstance(urls, dict):
        urls = StrList(**urls)
    print(urls)
    print("Fetching articles ...")
    for url in urls.results:
        try:
            feed = feedparser.parse(url)
            print("Parsed Successfully ...")
            for entry in feed.entries:
                aggregated_articles.result[url].append(FeedMetadata(title=entry.get("title", "No Title"), 
				link=entry.get("link", "No Link")))

        except Exception as e: 
            print(f"Error fetching articles from {url}: {e}")

    return aggregated_articles


def fetch_articles_from_sitemap(urls: StrList) -> Dict[str, List[str]]:
    """Fetch articles metadata from website sitemap.xml URLs.

    Args:
        urls (list[str]): List of sitemap URLs to parse.

    Returns:
        list[str]: Extracted article URLs.
    """
    extracted_urls: Dict[str, List[str]] =  defaultdict(list)
    if isinstance(urls, dict):
        urls = StrList(**urls)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "MCP-Sitemap-Bot/1.0"
        )
    }
    
    for url in urls.results:
        try:
            print(f"Fetching data for {url} ...")

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            namespaces = {
                "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            for url_node in root.findall(".//ns:url", namespaces):
                loc_node = url_node.find("ns:loc", namespaces)

                if loc_node is not None and loc_node.text:
                    extracted_urls[url].append(loc_node.text.strip())

        except Exception as e:
            print(f"Error fetching from {url}: {e}")

    return extracted_urls
