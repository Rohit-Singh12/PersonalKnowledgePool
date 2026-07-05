import logging
import os
import random
import sys
import requests
from mcp.server.fastmcp import FastMCP

name = "demo-mcp-server"
logging.basicConfig(
	level = logging.INFO,
	format='%(name)s - %(levelname)s - %(message)s',
    	handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(name)
port = int(os.environ.get('PORT', 8080))
mcp = FastMCP(name, port=port)

@mcp.tool()
def give_random_sample() -> int:
	"""Give a random integer when asked to generate random sample"""
	return random.randint(1, 100)


if __name__=='__main__':
	logger.info(f"Starting Demo MCP Server on port {port}...")
	try:
		mcp.run(transport="sse")
	except Exception as e:
		logger.error(f"Server error: {str(e)}")
		sys.exit(1)
	finally:
		logger.info("Server terminated")

