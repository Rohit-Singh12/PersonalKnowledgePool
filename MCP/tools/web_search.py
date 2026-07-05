from services.web_search_service import query_web
from schemas.search_result_model import SearchResults

def register(mcp):
    
    @mcp.tool
    def web_search(url: str) -> SearchResults:
        """
        Performs a web search using a local SearXNG instance and returns relevant webpages for a query.

        This tool is intended for information discovery. Given a topic or search query, it finds potentially relevant webpages and returns their titles, URLs, and snippets. Use this tool when you need to locate sources, articles, documentation, tutorials, news, or reference material related to a subject.

        The returned snippets are only previews and may not contain complete information. If detailed analysis of a result is required, use a webpage scraping or content extraction tool on the returned URL.

        Returns:
        - SearchResults
        - results: List of search results
            - title: Page title
            - url: Page URL
            - snippet: Short summary or excerpt from the page
        """
        
        return query_web(url)
