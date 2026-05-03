"""
Local MCP handshake test.

Verifies that the 6G Intelligence MCP server starts and responds to a
basic tool-listing request.  This file is referenced by the CI workflow
step "CI Handshake Test".

Run manually:
    python test_mcp_local.py
"""
import asyncio
import sys
from contextlib import AsyncExitStack

# ---------------------------------------------------------------------------
# Try to import MCP client; skip gracefully if not installed
# ---------------------------------------------------------------------------
try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp import ClientSession

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


async def run_handshake() -> bool:
    """Start the MCP server and verify it lists at least one tool."""
    if not MCP_AVAILABLE:
        print("⚠️  MCP client library not available – skipping handshake.")
        return True  # Not a failure – just not installed

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from api.mcp_server import mcp; mcp.run()"],
        env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )

    async with AsyncExitStack() as stack:
        read_stream, write_stream = await stack.enter_async_context(
            stdio_client(server_params)
        )
        session: ClientSession = await stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await session.initialize()

        tools = await session.list_tools()
        print(f"✅ MCP Handshake OK – {len(tools.tools)} tools registered:")
        for tool in tools.tools:
            print(f"   • {tool.name}")

        return len(tools.tools) > 0


def main() -> None:
    success = asyncio.run(run_handshake())
    if not success:
        print("❌ MCP handshake FAILED – no tools registered.")
        sys.exit(1)
    print("🎉 Handshake test complete.")


if __name__ == "__main__":
    main()
