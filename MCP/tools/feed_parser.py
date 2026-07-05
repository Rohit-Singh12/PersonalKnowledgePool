"""
Contains tools for parsing RSS feeds or Sitemap URL and fetch public links.
"""
from typing import Dict, List

from services.feed_service import fetch_articles_from_rss_feeds, fetch_articles_from_sitemap
from schemas.feed_model import StrList, FeedMetadataResponse

def register(mcp):
    
    @mcp.tool
    def fetch_metadata(urls: StrList) -> FeedMetadataResponse:
        """
        Retrieves article metadata from RSS or Atom feeds.

        Use this tool when the user wants:
            - Latest posts from a blog
            - Articles from an RSS feed
            - Feed entries from a known feed URL
        
        Inputs:
            {
                "results": ["https://lilianweng.github.io/index.xml"]
            }
        
        
        Returns:
            {
                "result": {
                    "https://lilianweng.github.io/index.xml":[
                        {
                            "title": "Scaling Laws, Carefully","link":"https://lilianweng.github.io/posts/2026-06-24-scaling-laws/"
                        },
                        ...
                        ]
                    }
            }
                    
        Do not use this tool for:
            - General web search.
            - Scraping arbitrary webpages.
            - Retrieving article content.

        This tool only reads RSS/Atom feeds and returns metadata.    
        """
        return fetch_articles_from_rss_feeds(urls)
    
    @mcp.tool
    def fetch_link_from_sitemap(urls: StrList) -> Dict[str, List[str]]:
        """
        Retrieved public URL from the website sitemap.xml URL

        Use this tool:
        - ONLY when there is /sitemap.xml in the URL
        - user asks to fetch link from the URL and URL is sitemap URL
        """
        return fetch_articles_from_sitemap(urls)
    