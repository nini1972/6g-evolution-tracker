
import asyncio
import sys
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def diag_data():
    print("Inspecting MCP Work Plan Data...")
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
                print(f"Fetching rows for: {url}")
                
                # filter_excel_columns_from_url tool
                # Filter for Rel-21 specifically
                result = await session.call_tool(
                    "filter_excel_columns_from_url", 
                    {
                        "file_url": url,
                        "columns": ["Unique_ID", "Name", "Release", "Completion", "Resource_Names"],
                        "filters": {"Release": "Rel-21"}
                    }
                )
                
                print("\nRel-21 items found:")
                raw_text = "".join([c.text for c in result.content])
                try:
                    data = json.loads(raw_text)
                    print(f"Total Rel-21 items: {len(data)}")
                    for item in data:
                        print(json.dumps(item, indent=2))
                except Exception as e:
                    print(f"Parse error: {e}. Raw text: {raw_text}")

    except Exception as e:
        print(f"Error during diagnostic: {e}")

if __name__ == "__main__":
    asyncio.run(diag_data())
