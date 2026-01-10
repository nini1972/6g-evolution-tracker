import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
import structlog

from fastmcp import FastMCP
from mcp_3gpp_ftp import create_server

logger = structlog.get_logger()


class MeetingReportParser:
    """
    Very lightweight placeholder parser.
    Replace with your real implementation if needed.
    """

    def __init__(self, content: str, content_type: str = "html"):
        self.content = content
        self.content_type = content_type

    def parse(self, meeting_id: str, wg: str) -> Dict:
        # For now, just return a minimal structure. You can expand this later.
        return {
            "meeting_id": meeting_id,
            "working_group": wg,
            "raw_content_length": len(self.content),
            "content_type": self.content_type,
            "parsed": False,
        }


class StandardsFetcher:
    """
    Fetch 3GPP standardization data (Work Plan + meetings),
    using a Python-native MCP server (mcp-3gpp-ftp) when available,
    and HTTP/sample fallbacks otherwise.
    """

    def __init__(self, use_mcp: bool = True):
        self.use_mcp = use_mcp
        self.client: Optional[httpx.AsyncClient] = None
        self.mcp_session: Optional[FastMCP] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _command_exists(self, cmd: str) -> bool:
        """
        Kept for compatibility, but no longer used for MCP.
        You can safely remove this later if not needed anywhere else.
        """
        import shutil

        return shutil.which(cmd) is not None

    async def _start_python_mcp(self):
        """
        Start the lightweight Python-native MCP server for 3GPP FTP access.
        This replaces the Node-based 3gpp-mcp-charging server.
        """
        try:
            server = create_server()
            self.mcp_session = FastMCP(server)
            await self.mcp_session.start()
            logger.info("mcp_python_server_started")
        except Exception as e:
            logger.error("mcp_python_server_failed", error=str(e))
            self.use_mcp = False
            self.mcp_session = None

    async def __aenter__(self):
        """
        Async context manager entry — initialize HTTP client and MCP session.
        """
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

        if self.use_mcp:
            logger.info("attempting_python_mcp")
            await self._start_python_mcp()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit — close HTTP client and MCP session.
        """
        if self.client:
            await self.client.aclose()

        if self.mcp_session:
            logger.info("mcp_python_session_closed")

    # ------------------------------------------------------------------
    # MCP-based fetchers
    # ------------------------------------------------------------------

    async def _fetch_work_plan_via_mcp(self) -> Optional[Dict]:
        """
        Fetch and filter the 3GPP Work Plan via MCP (Excel → JSON).
        Uses mcp-3gpp-ftp's filter_excel_columns_from_url tool.
        """
        if not self.mcp_session:
            return None

        work_plan_url = (
            "https://www.3gpp.org/ftp/Information/WORK_PLAN/TSG_Status_Report.xlsx"
        )

        try:
            logger.info("mcp_work_plan_fetch_started", url=work_plan_url)

            result = await self.mcp_session.call_tool(
                name="filter_excel_columns_from_url",
                arguments={
                    "file_url": work_plan_url,
                    "columns": [
                        "WI/SI",
                        "Title",
                        "Status",
                        "Release",
                        "Responsible WG",
                    ],
                    "filters": {"Release": "Rel-21"},
                },
            )

            rows = result.data if hasattr(result, "data") else result
            if not rows:
                logger.warning("mcp_work_plan_no_rows")
                return None

            total = len(rows)
            completed = sum(
                1 for r in rows if str(r.get("Status", "")).lower().startswith("cp")
            )
            in_progress = sum(
                1
                for r in rows
                if str(r.get("Status", "")).lower().startswith(("ps", "wip"))
            )
            postponed = total - completed - in_progress

            progress_pct = (completed / total * 100.0) if total else 0.0

            logger.info(
                "mcp_work_plan_fetch_completed",
                total=total,
                completed=completed,
                in_progress=in_progress,
                postponed=postponed,
                progress_percentage=progress_pct,
            )

            return {
                "total_work_items": total,
                "completed": completed,
                "in_progress": in_progress,
                "postponed": postponed,
                "progress_percentage": round(progress_pct, 1),
                "data_source": "mcp",
                "work_items_raw": rows,
            }

        except Exception as e:
            logger.warning("mcp_work_plan_fetch_error", error=str(e))
            return None

    async def _fetch_meetings_via_mcp(self) -> List[Dict]:
        """
        Fetch recent meetings via MCP by navigating the 3GPP FTP tree.
        This is intentionally simple and can be expanded later.
        """
        if not self.mcp_session:
            return []

        meetings: List[Dict] = []

        try:
            # Example: look into a few key WG directories
            wg_paths = {
                "RAN1": "/tsg_ran/WG1_RL1/",
                "RAN2": "/tsg_ran/WG2_RL2/",
                "SA2": "/tsg_sa/WG2_Arch/",
                "SA6": "/tsg_sa/WG6_MissionCritical/",
                "RAN3": "/tsg_ran/WG3_RL3/",
            }

            for wg, base_path in wg_paths.items():
                try:
                    dir_result = await self.mcp_session.call_tool(
                        name="list_directories",
                        arguments={"path": base_path},
                    )
                    dir_list = (
                        dir_result.data if hasattr(dir_result, "data") else dir_result
                    )
                    if not dir_list:
                        continue

                    # Take the last directory (most recent meeting) as a heuristic
                    dir_list_sorted = sorted(dir_list)
                    latest = dir_list_sorted[-1]
                    meeting_id = latest.strip("/")

                    meetings.append(
                        {
                            "meeting_id": meeting_id,
                            "working_group": wg,
                            "location": "Unknown",
                            "key_agreements": [],
                            "tdoc_references": [],
                            "sentiment": "unknown",
                            "data_source": "mcp",
                        }
                    )
                except Exception as inner:
                    logger.warning(
                        "mcp_meeting_dir_fetch_error",
                        working_group=wg,
                        error=str(inner),
                    )
                    continue

            logger.info("mcp_meetings_fetch_completed", meetings=len(meetings))
            return meetings

        except Exception as e:
            logger.warning("mcp_meetings_fetch_error", error=str(e))
            return []

    # ------------------------------------------------------------------
    # HTTP / fallback fetchers
    # ------------------------------------------------------------------

    async def _fetch_work_plan_via_http(self) -> Optional[Dict]:
        """
        HTTP fallback to fetch the 3GPP Work Plan Excel and derive basic stats.
        For now, this just fails gracefully and lets _empty_work_plan() handle it.
        """
        if not self.client:
            return None

        url = "https://www.3gpp.org/ftp/Information/WORK_PLAN/TSG_Status_Report.xlsx"
        logger.info("fetching_work_plan", url=url)

        try:
            resp = await self.client.get(url)
            if resp.status_code == 403:
                logger.warning(
                    "work_plan_access_denied",
                    msg="3GPP FTP server denied access. Using sample data.",
                )
                return None
            resp.raise_for_status()

            # You can add real Excel parsing here later (openpyxl + BytesIO)
            logger.info(
                "work_plan_http_downloaded", content_length=len(resp.content)
            )
            return None

        except Exception as e:
            logger.warning("work_plan_http_fetch_error", error=str(e))
            return None

    async def _fetch_meeting_report(
        self, wg: str, meeting_id: str, report_url: str
    ) -> Optional[Dict]:
        """Fetch and parse a single meeting report via HTTP."""
        if not self.client:
            return None

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
            soup = BeautifulSoup(response.text, "html.parser")
            report_file = None

            for link in soup.find_all("a"):
                href = link.get("href", "")
                # Look for report files (HTML, DOC, PDF)
                if any(
                    ext in href.lower() for ext in [".htm", ".html", ".doc", ".pdf"]
                ) and any(
                    keyword in href.lower()
                    for keyword in ["report", "summary", "final"]
                ):
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
            content_type = (
                "html"
                if any(ext in report_file.lower() for ext in [".htm", ".html"])
                else "text"
            )
            parser = MeetingReportParser(report_response.text, content_type)
            meeting_data = parser.parse(meeting_id, wg)

            return meeting_data

        except Exception as e:
            logger.warning(
                "meeting_report_fetch_error",
                meeting_id=meeting_id,
                error=str(e),
            )
            return None

    # ------------------------------------------------------------------
    # Sample / fallback data
    # ------------------------------------------------------------------

    def _empty_work_plan(self) -> Dict:
        """Return sample work plan structure when fetch fails"""
        from datetime import datetime

        logger.warning(
            "using_sample_3gpp_data",
            msg="Using sample data - Real 3GPP access via 3gpp-mcp-charging failed",
        )

        return {
            "total_work_items": 45,
            "completed": 15,
            "in_progress": 25,
            "postponed": 5,
            "progress_percentage": 33.3,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "sample",  # Indicate this is sample data
            "work_items_by_group": {
                "RAN1": {
                    "total": 12,
                    "completed": 4,
                    "in_progress": 7,
                    "postponed": 1,
                    "progress": 33.3,
                },
                "RAN2": {
                    "total": 8,
                    "completed": 3,
                    "in_progress": 4,
                    "postponed": 1,
                    "progress": 37.5,
                },
                "SA2": {
                    "total": 10,
                    "completed": 5,
                    "in_progress": 4,
                    "postponed": 1,
                    "progress": 50.0,
                },
                "SA6": {
                    "total": 8,
                    "completed": 2,
                    "in_progress": 5,
                    "postponed": 1,
                    "progress": 25.0,
                },
                "RAN3": {
                    "total": 7,
                    "completed": 1,
                    "in_progress": 5,
                    "postponed": 1,
                    "progress": 14.3,
                },
            },
        }

    def _sample_meetings(self) -> List[Dict]:
        """Return sample meeting data when fetch fails"""
        from datetime import datetime, timedelta

        logger.info(
            "using_sample_meeting_data", msg="Using sample meeting data"
        )

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
                    "Conclusion: Finalize positioning accuracy requirements for Release 21",
                ],
                "tdoc_references": [
                    "R1-2312345",
                    "R1-2312456",
                    "R1-2312567",
                ],
                "sentiment": "positive",
                "data_source": "sample",
            },
            {
                "meeting_id": "TSGS2_165",
                "working_group": "SA2",
                "date": (base_date + timedelta(days=15)).strftime("%Y-%m-%d"),
                "location": "Virtual",
                "key_agreements": [
                    "Agreed: Network architecture for AI-native RAN",
                    "Way forward: Study XRM framework for cross-domain resource management",
                    "Decision: Approve Release 21 architecture baseline",
                ],
                "tdoc_references": [
                    "S2-2401234",
                    "S2-2401345",
                    "S2-2401456",
                ],
                "sentiment": "positive",
                "data_source": "sample",
            },
            {
                "meeting_id": "TSGR2_128",
                "working_group": "RAN2",
                "date": (base_date + timedelta(days=20)).strftime("%Y-%m-%d"),
                "location": "Virtual",
                "key_agreements": [
                    "Agreed: L2/L3 procedures for NTN integration",
                    "Further study needed: Handover optimization for LEO satellites",
                ],
                "tdoc_references": [
                    "R2-2345678",
                    "R2-2345789",
                ],
                "sentiment": "mixed",
                "data_source": "sample",
            },
        ]

    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "release_21_progress": self._empty_work_plan(),
            "recent_meetings": self._sample_meetings(),
            "work_items_by_group": {},
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_all(self) -> Dict:
        """
        Fetch all standardization data (Work Plan + recent meetings),
        using MCP when available and falling back to HTTP/sample data.
        """
        # Default structure
        result: Dict = self._empty_result()

        # Try MCP first
        work_plan_data: Optional[Dict] = None
        meetings_data: List[Dict] = []

        if self.use_mcp and self.mcp_session:
            work_plan_data = await self._fetch_work_plan_via_mcp()
            meetings_data = await self._fetch_meetings_via_mcp()

        # If MCP failed, try HTTP where possible
        if work_plan_data is None:
            http_work_plan = await self._fetch_work_plan_via_http()
            if http_work_plan is not None:
                work_plan_data = http_work_plan

        # Apply fallbacks if still missing
        if work_plan_data is None:
            work_plan_data = self._empty_work_plan()

        if not meetings_data:
            meetings_data = self._sample_meetings()

        result["release_21_progress"] = work_plan_data
        result["recent_meetings"] = meetings_data

        # Optionally derive work_items_by_group here in the future
        result["work_items_by_group"] = work_plan_data.get(
            "work_items_by_group", {}
        )

        return result


async def fetch_standardization_data() -> Dict:
    """
    Convenience function to fetch all standardization data.

    Returns:
        Dict with standardization data
    """
    async with StandardsFetcher() as fetcher:
        return await fetcher.fetch_all()
