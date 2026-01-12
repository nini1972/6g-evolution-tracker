
import asyncio
import sys
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def diag_columns():
    print("Testing MCP Excel Column Listing...")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from mcp_3gpp_ftp.server import main; main()"],
        env={"PYTHONUNBUFFERED": "1"}
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                url = "https://www.3gpp.org/ftp/Information/WORK_PLAN/Work_plan_3gpp_260106.xlsx"
                print(f"Listing columns for: {url}")
                
                # list_excel_columns tool
                result = await session.call_tool("list_excel_columns", {"file_url": url})
                print("\nColumns found:")
                for content in result.content:
                    print(content.text)

    except Exception as e:
        print(f"Error during diagnostic: {e}")

if __name__ == "__main__":
    asyncio.run(diag_columns())
