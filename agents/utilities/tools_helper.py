from typing import Literal, Any
from langchain_mcp_adapters.client import MultiServerMCPClient
from init_client import client


async def get_tool(tool_name: Literal['web_search', 'scrape_url', 'read_schema', 'read_sql_queury', 'write_sql_query']):
    
    tools = {tool.name: tool for tool in await client.get_tools()}

    if tool_name == 'web_search':
        return tools["web_search"]
    if tool_name == 'scrape_url':
        return tools["scrape_url"]
    if tool_name == 'read_schema':
        return tools["read_schema"]
    if tool_name == 'read_sql_queury':
        return tools["read_sql_queury"]
    if tool_name == 'write_sql_query':
        return tools["write_sql_query"]

async def get_tool_spec(tool_name: Literal['web_search', 'scrape_url', 'read_schema', 'read_sql_queury', 'write_sql_query']):
    
    tool = await get_tool(tool_name)
    
    assert tool.args_schema is not None
    schema = (
        tool.args_schema.model_json_schema() #type: ignore
        if tool.args_schema
        else {}
    )

    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": schema
    }

async def get_tool_specs() -> list[dict[str, Any]]:

    tools = await client.get_tools()

    tool_specs = []

    for tool in tools:

        if hasattr(tool, "args_schema"):

            if isinstance(tool.args_schema, dict):
                input_schema = tool.args_schema

            elif hasattr(tool.args_schema, "model_json_schema"):
                input_schema = tool.args_schema.model_json_schema() # type: ignore

            else:
                input_schema = {}

        else:
            input_schema = {}

        tool_specs.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": input_schema,
                "response_format": getattr(
                    tool,
                    "response_format",
                    None,
                ),
                "metadata": getattr(
                    tool,
                    "metadata",
                    {},
                ),
            }
        )

    return tool_specs