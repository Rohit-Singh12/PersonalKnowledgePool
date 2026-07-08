import logging
from fastmcp import FastMCP
from registration.tools import register_tools
import sys
import asyncio

name = "Learning-mcp-server"
logging.basicConfig(
	level = logging.INFO,
	format='%(name)s - %(levelname)s - %(message)s',
    	handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(name)
mcp = FastMCP(name)
port = 8080

# Register TOOLS
asyncio.run(register_tools(mcp))

if __name__=='__main__':
	logger.info(f"Starting Demo MCP Server on port {port}...")
	try:
		mcp.run(transport="http", host="0.0.0.0", port=port)
	except Exception as e:
		logger.error(f"Server error: {str(e)}")
		sys.exit(1)
	finally:
		logger.info("Server terminated")
