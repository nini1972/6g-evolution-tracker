"""
Example: Using 6G Intelligence MCP Server from Python
"""
import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters

async def main():
    """Connect to 6G intelligence MCP server and query data"""
    # Connect to 6G intelligence MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["api/mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        # Initialize
        await read.initialize()
        
        # List available tools
        tools = await read.list_tools()
        print(f"Available tools: {[t.name for t in tools.tools]}")
        
        # Example 1: Get 3GPP Release 21 status
        result = await write.call_tool("get_3gpp_release21_status", {})
        status = json.loads(result.content[0].text)
        print(f"\n3GPP Release 21: {status['progress_percentage']}% complete")
        print(f"Data source: {status['data_source']}")
        
        # Example 2: Search for AI-RAN topics
        result = await write.call_tool("search_6g_topics", {"topic": "AI-RAN", "min_importance": 7})
        articles = json.loads(result.content[0].text)
        print(f"\nFound {len(articles)} high-impact articles about AI-RAN")
        
        # Example 3: Regional momentum
        result = await write.call_tool("analyze_regional_momentum", {})
        momentum = json.loads(result.content[0].text)
        print(f"\n6G Leader: {momentum['leader']} (score: {momentum['total_scores'][momentum['leader']]})")

if __name__ == "__main__":
    asyncio.run(main())
