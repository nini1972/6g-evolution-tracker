
import asyncio
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def test_mcp_init():
    print("Testing MCP initialization...")
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from mcp_3gpp_ftp.server import main; main()"],
        env={"PYTHONUNBUFFERED": "1"}
    )
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("Connected to streams.")
            async with ClientSession(read_stream, write_stream) as session:
                print("Starting handshake...")
                # Use a timeout for the handshake itself
                await asyncio.wait_for(session.initialize(), timeout=10)
                print("Handshake completed successfully!")
                
                print("Listing tools...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools.")
                for tool in tools.tools:
                    print(f" - {tool.name}")
                    
    except asyncio.TimeoutError:
        print("Error: Handshake timed out after 10 seconds.")
    except Exception as e:
        print(f"Error during initialization: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_init())
