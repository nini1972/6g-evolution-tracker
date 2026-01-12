
import asyncio
import sys
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def diag_workplan():
    print("Testing MCP Work Plan directory listing...")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from mcp_3gpp_ftp.server import main; main()"],
        env={"PYTHONUNBUFFERED": "1"}
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                path = "Information/WORK_PLAN/"
                print(f"Listing files in: {path}")
                
                # crawl_ftp tool
                print(f"\nCrawling FTP: {path}")
                result_crawl = await session.call_tool("crawl_ftp", {"path": path, "depth": 1})
                print("\nCrawl results:")
                for content in result_crawl.content:
                    print(content.text)

    except Exception as e:
        print(f"Error during diagnostic: {e}")

if __name__ == "__main__":
    asyncio.run(diag_workplan())
