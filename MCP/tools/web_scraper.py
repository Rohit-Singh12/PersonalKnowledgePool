from services.web_scarper import scrape_website

def register(mcp):
    
    @mcp.tool
    def scrape_url(url: str) -> str:
        """
        Fetches and extracts the main content of a webpage as clean Markdown.

        Use this tool when you need to read, analyze, summarize, or retrieve information from a specific URL. The tool removes most navigation, advertisements, and page chrome, returning the primary textual content in Markdown format suitable for LLM processing.

        Input:
        - url: The webpage URL to scrape.

        Returns:
        - The extracted page content in Markdown format, optionally including page metadata such as title and source URL.

        Best for:
        - Reading articles and blog posts
        - Extracting documentation pages
        - Analyzing web content
        - Gathering context before answering questions
        """
        
        return scrape_website(url)
