from langchain_mcp_adapters.client import MultiServerMCPClient  

client = MultiServerMCPClient(
        {
            "Learning-mcp-server": {
                "transport": "http",  # HTTP-based remote server
                # Ensure you start your weather server on port 8000
                "url": "http://127.0.0.1:8080/mcp",
            }
        } # type: ignore
    )

