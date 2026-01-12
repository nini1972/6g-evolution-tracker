import asyncio
import structlog
from fetchers.standards_fetcher import StandardsFetcher

# Configure logging
structlog.configure()
logger = structlog.get_logger()

async def test_handshake():
    print("🚀 Starting MCP Handshake Test...")
    
    try:
        async with StandardsFetcher() as fetcher:
            print("📡 Connection established to MCP Session.")
            
            # Test 1: Fetch small amount of meetings
            print("🔍 Testing meeting fetch (limit 1)...")
            meetings = await fetcher.fetch_recent_meetings(limit=1)
            
            if meetings:
                print(f"✅ Success! Fetched {len(meetings)} meeting(s).")
                print(f"   Sample Meeting: {meetings[0].get('meeting_id')}")
            else:
                print("⚠️ No meetings found, but connection was successful.")
                
            # Test 2: Check work plan discovery
            print("🔍 Testing work plan discovery...")
            url = await fetcher._discover_latest_work_plan()
            if url:
                print(f"✅ Success! Discovered Work Plan URL: {url}")
            else:
                print("⚠️ Work plan discovery returned None (this might be normal if MCP server is simplified).")
                
            print("\n✨ Handshake test completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Handshake test FAILED with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_handshake())
    if not result:
        exit(1)
