from tools import feed_parser, psql_query, web_scraper, web_search

async def register_tools(mcp):
    feed_parser.register(mcp)
    await psql_query.register(mcp)
    web_search.register(mcp)
    web_scraper.register(mcp)
