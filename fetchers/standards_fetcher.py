"""
Fetcher for 3GPP standardization data.
Uses MCP client to connect to mcp-3gpp-ftp server for real data.
Falls back to HTTP download, then sample data when MCP is unavailable.
"""
import shutil
import httpx
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import AsyncExitStack
import asyncio
import structlog
from parsers.work_item_parser import WorkItemParser
from parsers.meeting_report_parser import MeetingReportParser
from bs4 import BeautifulSoup
import re
import json

# MCP client imports - with graceful fallback if not available
try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.types import CallToolResult
    from mcp import ClientSession
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = structlog.get_logger()


class StandardsFetcher:
    """Fetch and parse 3GPP standardization data"""
    
    # 3GPP FTP URLs
    WORK_PLAN_DIR = "Information/WORK_PLAN/"
    WORK_PLAN_BASE_URL = f"https://www.3gpp.org/ftp/{WORK_PLAN_DIR}"
    # Default fallback if discovery fails (the one we know works now)
    DEFAULT_WORK_PLAN_FILE = "Work_plan_3gpp_260106.xlsx"
    
    MEETING_REPORT_URLS = {
        "RAN1": "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1/",
        "SA2": "https://www.3gpp.org/ftp/tsg_sa/WG2_Arch/",
    }
    
    # User agent for FTP access
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    # Cache duration in seconds (24 hours)
    CACHE_DURATION = 86400

    # Framing parameters - Ensure we don't get overwhelmed by the huge history
    TARGET_RELEASE = "Rel-21"  # Focus on the 6G evolution phase
    MAX_MEETINGS_PER_WG = 3    # Only track the last 3 meetings for each group
    MEETING_FRESHNESS_DAYS = 180  # approx 6 months
    
    def __init__(self, cache_dir: str = "/tmp/3gpp_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client: Optional[httpx.AsyncClient] = None
        self.mcp_session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
    
    async def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in PATH"""
        return shutil.which(cmd) is not None
    
    async def _detect_mcp_server_command(self) -> Optional[Tuple[str, List[str]]]:
        """
        Detect how to start the 3GPP MCP server.
        Returns (command, args) or None if no valid method is available.
        """

        import sys
        logger.info("detecting_mcp_server_command", target="mcp-3gpp-ftp")

        # Use a direct import and run to ensure we use the correct environment
        # and avoid PATH/shebang issues in CI.
        return (sys.executable, ["-c", "from mcp_3gpp_ftp.server import main; main()"])
    
    async def _init_mcp_session(self):
        """Initialize MCP session with timeout and proper error handling."""

        server_cmd = await self._detect_mcp_server_command()
        if not server_cmd:
            raise RuntimeError("MCP server command not found")

        command, args = server_cmd

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env={
                "PYTHONUNBUFFERED": "1",
                "TERM": "dumb",
                "PYTHONIOENCODING": "utf-8"
            }
        )

      
        logger.info("starting_mcp_server", command=command, args=args)

        # Use AsyncExitStack to manage multiple async contexts
        self.exit_stack = AsyncExitStack()
        
        try:
            # 1. Connect stdio transport
            read_stream, write_stream = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            logger.info("mcp_streams_connected")

            # 2. Start MCP session (this starts the message listener task)
            self.mcp_session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            logger.info("mcp_session_entered")

            # 3. Perform initialization handshake
            logger.info("mcp_starting_handshake")
            await self.mcp_session.initialize()
            logger.info("mcp_handshake_completed")

            logger.info("mcp_session_initialized")

        except Exception as e:
            logger.error("mcp_init_error", error=str(e))
            if self.exit_stack:
                await self.exit_stack.aclose()
                self.exit_stack = None
            self.mcp_session = None
            raise
    
    async def _test_mcp_health(self) -> bool:
        """Check if MCP server responds to basic commands."""
        try:
            tools = await self.mcp_session.list_tools()
            logger.info("mcp_health_check_passed", tool_count=len(tools.tools))
            return True
        except Exception as e:
            logger.error("mcp_health_check_failed", error=str(e), error_type=type(e).__name__)
            return False
    
    async def __aenter__(self):
        """Async context manager entry - start MCP client connection"""
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        # Try to connect to mcp-3gpp-ftp server (optional, graceful degradation if unavailable)
        if MCP_AVAILABLE:
            try:
                logger.info("attempting_mcp_connection", server="mcp-3gpp-ftp")
                
                # Initialize with 60s timeout (buffer for heavy-loaded CI environments)
                start_time = time.time()
                
                await asyncio.wait_for(
                    self._init_mcp_session(),
                    timeout=60.0
                )
                
                init_elapsed = time.time() - start_time
                logger.info("mcp_init_completed", elapsed_seconds=round(init_elapsed, 2))
                
                # Health check with 10s timeout
                health_ok = await asyncio.wait_for(
                    self._test_mcp_health(),
                    timeout=10.0
                )
                
                if not health_ok:
                    logger.warning("mcp_health_check_failed_disabling")
                    if self.exit_stack:
                        await self.exit_stack.aclose()
                        self.exit_stack = None
                    self.mcp_session = None
                
            except asyncio.TimeoutError:
                logger.error("mcp_timeout", 
                            msg="MCP server initialization timed out after 60 seconds",
                            timeout_seconds=60)
                if self.exit_stack:
                    try:
                        await self.exit_stack.aclose()
                    except Exception:
                        pass
                    self.exit_stack = None
                self.mcp_session = None
                
            except Exception as e:
                logger.error("mcp_session_init_failed", 
                            error=str(e), 
                            error_type=type(e).__name__)
                if self.exit_stack:
                    try:
                        await self.exit_stack.aclose()
                    except Exception:
                        pass
                    self.exit_stack = None
                self.mcp_session = None
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect MCP client"""
        if self.client:
            await self.client.aclose()
        
        # Close MCP session
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
                self.exit_stack = None
                self.mcp_session = None
                logger.info("mcp_resources_cleaned_up")
            except Exception as e:
                logger.warning("mcp_session_close_error", error=str(e))
    
    async def fetch_all(self) -> Dict:
        """
        Fetch all standardization data.
        
        Returns:
            Dict with structure:
            {
                "release_21_progress": {...},
                "recent_meetings": [...],
                "work_items_by_group": {...}
            }
        """
        logger.info("standards_fetch_started")
        
        try:
            # Fetch work plan and meeting reports in parallel
            work_plan_task = self.fetch_work_plan()
            meetings_task = self.fetch_recent_meetings()
            
            work_plan_data, meetings_data = await asyncio.gather(
                work_plan_task,
                meetings_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(work_plan_data, Exception):
                logger.error("work_plan_fetch_failed", error=str(work_plan_data))
                work_plan_data = self._empty_work_plan()
            
            if isinstance(meetings_data, Exception):
                logger.error("meetings_fetch_failed", error=str(meetings_data))
                meetings_data = []
            
            # Combine results
            result = {
                "release_21_progress": work_plan_data,
                "recent_meetings": meetings_data,
                "work_items_by_group": work_plan_data.get("work_items_by_group", {})
            }
            
            logger.info("standards_fetch_completed", meetings=len(meetings_data))
            return result
            
        except Exception as e:
            logger.error("standards_fetch_error", error=str(e))
            return self._empty_result()
    
    async def fetch_work_plan(self) -> Dict:
        """
        Fetch and parse 3GPP Work Plan using MCP client or HTTP fallback.
        Falls back to sample data when all methods fail.
        
        Returns:
            Dict with Release 21 progress data
        """
        # Try MCP method first
        if self.mcp_session:
            try:
                return await self._fetch_work_plan_via_mcp()
            except Exception as e:
                logger.error("mcp_work_plan_fetch_failed", error=str(e), error_type=type(e).__name__)
                # Fall through to HTTP method
        
        # Try HTTP method
        try:
            # Try to discover the latest file first
            dynamic_url = await self._discover_latest_work_plan()
            url = dynamic_url or f"{self.WORK_PLAN_BASE_URL}{self.DEFAULT_WORK_PLAN_FILE}"
            logger.info("fetching_work_plan", url=url)
            
            # Check cache first (24 hour cache)
            cache_file = self.cache_dir / "work_plan.xlsx"
            if cache_file.exists():
                age = time.time() - cache_file.stat().st_mtime
                if age < self.CACHE_DURATION:
                    logger.info("using_cached_work_plan", age_hours=round(age/3600, 1))
                    parser = WorkItemParser(str(cache_file))
                    result = parser.parse()
                    # Add data source indicator
                    if result and "data_source" not in result:
                        result["data_source"] = "cached"
                    return result
            
            # 3. HTTP Download
            # Try HTTP download
            if not self.client:
                self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            
            # Add user agent to avoid 403
            headers = {'User-Agent': self.USER_AGENT}
            
            logger.info("fetching_work_plan", url=url)
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # Save to cache
            cache_file.write_bytes(response.content)
            logger.info("work_plan_downloaded", size=len(response.content))
            
            # Parse the file
            parser = WorkItemParser(str(cache_file))
            result = parser.parse()
            # Add data source indicator
            if result:
                result["data_source"] = "live"
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(
                    "work_plan_access_denied", 
                    msg="3GPP FTP server denied access. Using sample data."
                )
            else:
                logger.error("work_plan_http_error", status=e.response.status_code, error=str(e))
            return self._empty_work_plan()
        except Exception as e:
            logger.error("work_plan_fetch_error", error=str(e))
            return self._empty_work_plan()
    
    def _validate_mcp_client(self):
        """
        Validate that MCP client session is properly initialized.
        
        Raises:
            AttributeError: If MCP session is not initialized or missing call_tool method
        """
        if not self.mcp_session:
            raise AttributeError("MCP session is None - not initialized")
        
        if not hasattr(self.mcp_session, 'call_tool'):
            available_methods = [m for m in dir(self.mcp_session) if not m.startswith('_')]
            logger.error("mcp_session_missing_call_tool", 
                        available_methods=available_methods,
                        session_type=type(self.mcp_session).__name__)
            raise AttributeError(f"MCP session (type: {type(self.mcp_session).__name__}) does not have call_tool method")
    
    async def _fetch_work_plan_via_mcp(self) -> Dict:
        """
        Fetch Work Plan using MCP tools from mcp-3gpp-ftp server.
        Note: This requires the mcp-3gpp-ftp server to be running and accessible.
        """
        logger.info("fetching_work_plan_via_mcp")
        
        # Validate MCP client
        self._validate_mcp_client()
        
        start_time = time.time()
        
        try:
            # 1. Discover latest file URL
            work_plan_url = await self._discover_latest_work_plan()
            if not work_plan_url:
                # Fallback to known default if discovery fails but MCP is up
                work_plan_url = f"{self.WORK_PLAN_BASE_URL}{self.DEFAULT_WORK_PLAN_FILE}"
                logger.warning("mcp_work_plan_using_default", url=work_plan_url)

            # 2. Call MCP tool with 60s timeout (Excel download + parsing)
            # Map of internal name to actual Excel column name
            col_map = {
                "Unique_ID": "WI/SI",
                "Name": "Title",
                "Release": "Release",
                "Resource_Names": "Responsible WG"
            }
            
            result: CallToolResult = await asyncio.wait_for(
                self.mcp_session.call_tool(
                    name="filter_excel_columns_from_url",
                    arguments={
                        "file_url": work_plan_url,
                        "columns": ["Unique_ID", "Name", "Release", "Resource_Names", "Completion"],
                        "filters": {"Release": self.TARGET_RELEASE}
                    }
                ),
                timeout=60.0
            )
            
            elapsed = time.time() - start_time
            logger.info("mcp_work_plan_tool_completed", elapsed_seconds=round(elapsed, 2))
            
            # Parse result
            if result.content and len(result.content) > 0:
                # Check for tool-level errors reported in raw text
                first_text = result.content[0].text
                if first_text.startswith("Error executing tool"):
                    raise RuntimeError(f"MCP Tool Error: {first_text}")
                
                # Collect all text items
                texts = [c.text for c in result.content if hasattr(c, 'text')]
                
                try:
                    # Case 1: Single item is a JSON-encoded list
                    if len(texts) == 1:
                        rel21_items = json.loads(texts[0])
                        if not isinstance(rel21_items, list):
                            rel21_items = [rel21_items]
                    else:
                        # Case 2: Multi-item response, check if each item is a dict
                        # (FastMCP usually serializes objects to JSON strings)
                        rel21_items = []
                        for t in texts:
                             try:
                                 item = json.loads(t)
                                 rel21_items.append(item)
                             except json.JSONDecodeError:
                                 # Skip non-json items in multi-item result
                                 continue
                    
                    logger.info("mcp_work_plan_fetched", items=len(rel21_items))
                    # Aggregate into our data structure
                    return self._aggregate_work_items(rel21_items)
                    
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error("mcp_work_plan_parse_error", 
                                error=str(e), 
                                first_text=first_text[:200])
                    raise RuntimeError(f"Failed to parse MCP result: {str(e)}")
            else:
                logger.warning("mcp_empty_result")
                raise RuntimeError("MCP server returned empty result")
                
        except asyncio.TimeoutError:
            raise RuntimeError("MCP work plan tool timed out")
        except Exception as e:
            # Let it propagate to trigger HTTP fallback in fetch_work_plan
            raise
    
    async def _discover_latest_work_plan(self) -> Optional[str]:
        """
        Dynamically find the latest Work Plan Excel file in Information/WORK_PLAN/
        """
        if not self.mcp_session:
            return None
            
        try:
            logger.info("discovering_latest_work_plan")
            result = await self.mcp_session.call_tool(
                "list_files", {"path": self.WORK_PLAN_DIR}
            )
            
            if not result.content:
                return None
                
            # Collect all file names
            files = []
            for item in result.content:
                if hasattr(item, 'text'):
                    # MCP might return multi-item list or single JSON list
                    try:
                        parsed = json.loads(item.text)
                        if isinstance(parsed, list):
                            files.extend(parsed)
                        else:
                            files.append(item.text)
                    except json.JSONDecodeError:
                        files.append(item.text)
            
            # Filter for .xlsx work plan files
            # Pattern: Work_plan_3gpp_YYMMDD.xlsx
            wp_files = []
            for f in files:
                fname = f.split('/')[-1] if '/' in f else f
                if fname.lower().startswith("work_plan_3gpp_") and fname.lower().endswith(".xlsx"):
                    wp_files.append(fname)
            
            if not wp_files:
                logger.warning("no_work_plan_files_found_in_dir", files_checked=len(files))
                return None
                
            # Sort by name (which includes date YYMMDD) to get latest
            latest_file = sorted(wp_files, reverse=True)[0]
            discovered_url = f"{self.WORK_PLAN_BASE_URL}{latest_file}"
            logger.info("discovered_latest_work_plan", file=latest_file, url=discovered_url)
            return discovered_url
            
        except Exception as e:
            logger.error("work_plan_discovery_failed", error=str(e))
            return None

    def _aggregate_work_items(self, items: List[Dict]) -> Dict:
        """Convert MCP result to our data structure"""
        from datetime import datetime
        from collections import defaultdict
        
        # Mapping from MCP column names (new Excel) back to our internal keys
        mapping = {
            "Unique_ID": "name",        # We use name as the primary ID/label in the dashboard
            "Name": "title",
            "Release": "release",
            "Resource_Names": "working_group"
        }
        
        work_items = []
        for item in items:
            mapped_item = {}
            for mcp_key, internal_key in mapping.items():
                mapped_item[internal_key] = str(item.get(mcp_key, "")).strip()
            
            # Since the new Excel might not have a clear "Status" column yet,
            # we'll look at "Completion" or default to "In Progress"
            completion = item.get("Completion", "0%")
            if "100" in str(completion):
                mapped_item["status"] = "Completed"
            else:
                mapped_item["status"] = "In Progress"
                
            work_items.append(mapped_item)
        
        by_group = defaultdict(lambda: {"total": 0, "completed": 0, "in_progress": 0, "postponed": 0})
        
        total = len(work_items)
        completed = 0
        in_progress = 0
        postponed = 0
        
        for item in work_items:
            status = item.get("status", "").lower()
            wg = item.get("working_group", "Other")
            
            by_group[wg]["total"] += 1
            
            if status == "completed":
                completed += 1
                by_group[wg]["completed"] += 1
            elif any(kw in status for kw in ["postpone", "delay", "suspend"]):
                postponed += 1
                by_group[wg]["postponed"] += 1
            else:
                in_progress += 1
                by_group[wg]["in_progress"] += 1
        
        # Calculate progress percentages
        progress_pct = round((completed / total * 100) if total > 0 else 0, 1)
        
        for group_data in by_group.values():
            group_data["progress"] = round(
                (group_data["completed"] / group_data["total"] * 100) 
                if group_data["total"] > 0 else 0, 
                1
            )
        
        return {
            "total_work_items": total,
            "completed": completed,
            "in_progress": in_progress,
            "postponed": postponed,
            "progress_percentage": progress_pct,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "live",  # Real data from MCP!
            "work_items_by_group": dict(by_group)
        }
    
    async def fetch_recent_meetings(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch recent meeting reports using MCP or HTTP fallback.
        Falls back to sample data when all methods fail.
        
        Args:
            limit: Maximum number of recent meetings per working group
        
        Returns:
            List of meeting data dictionaries
        """
        meetings = []
        
        # Try MCP method first
        if self.mcp_session:
            try:
                meetings = await self._fetch_meetings_via_mcp(limit)
                if meetings:
                    return meetings
            except Exception as e:
                logger.error("mcp_meetings_fetch_failed", error=str(e), error_type=type(e).__name__)
        
        # Try HTTP method for meetings
        for wg, base_url in self.MEETING_REPORT_URLS.items():
            try:
                wg_meetings = await self._fetch_working_group_meetings(wg, base_url, limit)
                meetings.extend(wg_meetings)
            except Exception as e:
                logger.error("meeting_fetch_error", wg=wg, error=str(e))
        
        # If no meetings found, use sample data
        if not meetings:
            meetings = self._sample_meetings()
        
        # Sort by date (most recent first)
        meetings.sort(key=lambda m: m.get("date", ""), reverse=True)
        
        return meetings
    
    async def _fetch_meetings_via_mcp(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Fetch recent meetings using MCP tools.
        Note: This requires the mcp-3gpp-ftp server to be running and accessible.
        """
        from datetime import datetime   
        
        # Use class constant if limit not provided
        fetch_limit = limit or self.MAX_MEETINGS_PER_WG
        
        # Validate MCP client
        self._validate_mcp_client()
        
        meetings = []
        
        for wg, path in {"RAN1": "/tsg_ran/WG1_RL1/", "SA2": "/tsg_sa/WG2_Arch/"}.items():
            try:
                start_time = time.time()
                
                # List directories with 30s timeout
                result = await asyncio.wait_for(
                    self.mcp_session.call_tool(
                        name="list_directories",
                        arguments={"path": path}
                    ),
                    timeout=30.0
                )
                
                elapsed = time.time() - start_time
                logger.info(
                    "mcp_directory_list_completed", 
                     wg=wg, 
                     elapsed_seconds=round(elapsed, 2)
                )
                
                if not result.content or len(result.content) == 0:
                    continue
                
                # Check for tool-level errors
                first_text = result.content[0].text
                if first_text.startswith("Error executing tool"):
                    logger.warning("mcp_meeting_tool_error", wg=wg, error=first_text)
                    continue
                    
                # Collect all text items
                texts = [c.text for c in result.content if hasattr(c, 'text')]
                
                try:
                    # Try to parse as single JSON list first
                    if len(texts) == 1:
                        try:
                            dirs = json.loads(texts[0])
                            if not isinstance(dirs, list):
                                dirs = [dirs]
                        except json.JSONDecodeError:
                            # Not JSON, treat as plain text item
                            dirs = texts
                    else:
                        # Multi-item list, check if items are JSON-encoded
                        dirs = []
                        for t in texts:
                            try:
                                item = json.loads(t)
                                dirs.append(item)
                            except json.JSONDecodeError:
                                # Not JSON, treat as plain text (e.g. dir name)
                                dirs.append(t)
                                
                    # Get most recent meetings (assume sorted by name/date)
                    recent_dirs = sorted(dirs, reverse=True)[:fetch_limit]
                except Exception as e:
                    logger.error("mcp_meeting_parse_error", 
                                wg=wg, 
                                error=str(e), 
                                first_text=first_text[:200])
                    continue
                
                for meeting_dir in recent_dirs:
                    # Create meeting data structure
                    # (simplified - real implementation would download and parse reports)
                    meeting_data = {
                        "meeting_id": meeting_dir.rstrip('/'),
                        "working_group": wg,
                        "date": datetime.now().strftime("%Y-%m-%d"),  # Would parse from report
                        "location": "TBD",
                        "key_agreements": [],  # Would extract from TDocs
                        "tdoc_references": [],
                        "sentiment": "neutral",
                        "data_source": "live"
                    }
                    meetings.append(meeting_data)
                    
            except asyncio.TimeoutError:
                logger.error("mcp_directory_list_timeout", 
                            wg=wg, 
                            timeout_seconds=30)
            except Exception as e:
                logger.error("mcp_meeting_fetch_failed", 
                            wg=wg, 
                            error=str(e), 
                            error_type=type(e).__name__)
        
        return meetings
    
    async def _fetch_working_group_meetings(self, wg: str, base_url: str, limit: int) -> List[Dict]:
        """Fetch meetings for a specific working group"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            
            # Add user agent to avoid 403
            headers = {'User-Agent': self.USER_AGENT}
            
            # Get directory listing
            response = await self.client.get(base_url, headers=headers)
            response.raise_for_status()
            
            # Parse directory listing (HTML)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find meeting directories (e.g., TSGR1_115/, TSGS2_165/)
            meeting_dirs = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                # Match patterns like TSGR1_115/ or TSGS2_165/
                if re.match(r'TSG[RS]\d+_\d+/', href):
                    meeting_dirs.append(href)
            
            # Sort and get most recent
            meeting_dirs = sorted(meeting_dirs, reverse=True)[:limit]
            
            # Fetch reports from each meeting
            meetings = []
            for meeting_dir in meeting_dirs:
                meeting_url = base_url + meeting_dir + "Report/"
                meeting_data = await self._fetch_meeting_report(wg, meeting_dir.rstrip('/'), meeting_url)
                if meeting_data:
                    meetings.append(meeting_data)
            
            return meetings
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("wg_meeting_access_denied", wg=wg,
                              msg="3GPP FTP server denied access. This is expected.")
            else:
                logger.error("wg_meeting_http_error", wg=wg, status=e.response.status_code)
            return []
        except Exception as e:
            logger.error("wg_meeting_fetch_error", wg=wg, error=str(e))
            return []

    async def _fetch_meeting_report(self, wg: str, meeting_id: str, report_url: str) -> Optional[Dict]:
        """Fetch and parse a single meeting report"""
        try:
            # Try to get the report HTML/text
            response = await self.client.get(report_url)
            
            # If 404, try alternate paths
            if response.status_code == 404:
                # Try without /Report/
                report_url = report_url.replace("/Report/", "/")
                response = await self.client.get(report_url)
            
            if response.status_code != 200:
                return None
            
            # Get directory listing and find report file
            soup = BeautifulSoup(response.text, 'html.parser')
            report_file = None
            
            for link in soup.find_all('a'):
                href = link.get('href', '')
                # Look for report files (HTML, DOC, PDF)
                if any(ext in href.lower() for ext in ['.htm', '.html', '.doc', '.pdf']) and \
                   any(keyword in href.lower() for keyword in ['report', 'summary', 'final']):
                    report_file = href
                    break
            
            if not report_file:
                logger.warning("no_report_file_found", meeting_id=meeting_id)
                return None
            
            # Download the report
            report_content_url = report_url + report_file
            report_response = await self.client.get(report_content_url)
            report_response.raise_for_status()
            
            # Parse the report
            content_type = "html" if any(ext in report_file.lower() for ext in ['.htm', '.html']) else "text"
            parser = MeetingReportParser(report_response.text, content_type)
            meeting_data = parser.parse(meeting_id, wg)
            
            return meeting_data
            
        except Exception as e:
            logger.warning("meeting_report_fetch_error", meeting_id=meeting_id, error=str(e))
            return None
    
    def _empty_work_plan(self) -> Dict:
        """Return sample work plan structure when fetch fails"""
        from datetime import datetime
        
        logger.warning("using_sample_3gpp_data", 
                      msg="Using sample data - Real 3GPP access via mcp-3gpp-ftp failed")
        
        return {
            "total_work_items": 45,
            "completed": 15,
            "in_progress": 25,
            "postponed": 5,
            "progress_percentage": 33.3,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "sample",  # Indicate this is sample data
            "work_items_by_group": {
                "RAN1": {"total": 12, "completed": 4, "in_progress": 7, "postponed": 1, "progress": 33.3},
                "RAN2": {"total": 8, "completed": 3, "in_progress": 4, "postponed": 1, "progress": 37.5},
                "SA2": {"total": 10, "completed": 5, "in_progress": 4, "postponed": 1, "progress": 50.0},
                "SA6": {"total": 8, "completed": 2, "in_progress": 5, "postponed": 1, "progress": 25.0},
                "RAN3": {"total": 7, "completed": 1, "in_progress": 5, "postponed": 1, "progress": 14.3}
            }
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "release_21_progress": self._empty_work_plan(),
            "recent_meetings": self._sample_meetings(),
            "work_items_by_group": {}
        }
    
    def _sample_meetings(self) -> List[Dict]:
        """Return sample meeting data when fetch fails"""
        from datetime import datetime, timedelta
        
        logger.info("using_sample_meeting_data", msg="Using sample meeting data")
        
        base_date = datetime.now() - timedelta(days=30)
        
        return [
            {
                "meeting_id": "TSGR1_115",
                "working_group": "RAN1",
                "date": (base_date + timedelta(days=0)).strftime("%Y-%m-%d"),
                "location": "Virtual",
                "key_agreements": [
                    "Agreed: AI/ML framework for CSI feedback enhancements",
                    "Decision: Proceed with sub-THz channel modeling for 100-300 GHz",
                    "Conclusion: Finalize positioning accuracy requirements for Release 21"
                ],
                "tdoc_references": ["R1-2312345", "R1-2312456", "R1-2312567"],
                "sentiment": "positive",
                "data_source": "sample"
            },
            {
                "meeting_id": "TSGS2_165",
                "working_group": "SA2",
                "date": (base_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                "location": "Virtual",
                "key_agreements": [
                    "Agreed: Network architecture for AI-native RAN",
                    "Way forward: Study XRM framework for cross-domain resource management",
                    "Decision: Approve Release 21 architecture baseline"
                ],
                "tdoc_references": ["S2-2401234", "S2-2401345", "S2-2401456"],
                "sentiment": "positive",
                "data_source": "sample"
            },
            {
                "meeting_id": "TSGR2_128",
                "working_group": "RAN2",
                "date": (base_date + timedelta(days=20)).strftime("%Y-%m-%d"),
                "location": "Virtual",
                "key_agreements": [
                    "Agreed: L2/L3 procedures for NTN integration",
                    "Further study needed: Handover optimization for LEO satellites"
                ],
                "tdoc_references": ["R2-2345678", "R2-2345789"],
                "sentiment": "mixed",
                "data_source": "sample"
            }
        ]


async def fetch_standardization_data() -> Dict:
    """
    Convenience function to fetch all standardization data.
    
    Returns:
        Dict with standardization data
    """
    async with StandardsFetcher() as fetcher:
        return await fetcher.fetch_all()

