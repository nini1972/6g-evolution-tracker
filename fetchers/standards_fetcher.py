"""
Fetcher for 3GPP standardization data.
Downloads Work Plan Excel files and meeting reports.
"""
import asyncio
import httpx
from pathlib import Path
from typing import Dict, List, Optional
import structlog
from parsers.work_item_parser import WorkItemParser
from parsers.meeting_report_parser import MeetingReportParser
from bs4 import BeautifulSoup
import re

logger = structlog.get_logger()


class StandardsFetcher:
    """Fetch and parse 3GPP standardization data"""
    
    # 3GPP FTP URLs
    WORK_PLAN_URL = "https://www.3gpp.org/ftp/Information/WORK_PLAN/TSG_Status_Report.xlsx"
    
    MEETING_REPORT_URLS = {
        "RAN1": "https://www.3gpp.org/ftp/tsg_ran/WG1_RL1/",
        "SA2": "https://www.3gpp.org/ftp/tsg_sa/WG2_Arch/",
    }
    
    def __init__(self, cache_dir: str = "/tmp/3gpp_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
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
        Fetch and parse 3GPP Work Plan Excel file.
        
        Returns:
            Dict with Release 21 progress data
        """
        try:
            logger.info("fetching_work_plan", url=self.WORK_PLAN_URL)
            
            # Check cache first (24 hour cache)
            cache_file = self.cache_dir / "work_plan.xlsx"
            if cache_file.exists():
                age = (Path(__file__).stat().st_mtime - cache_file.stat().st_mtime)
                if age < 86400:  # 24 hours
                    logger.info("using_cached_work_plan")
                    parser = WorkItemParser(str(cache_file))
                    return parser.parse()
            
            # Download Excel file
            if not self.client:
                self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            
            response = await self.client.get(self.WORK_PLAN_URL)
            response.raise_for_status()
            
            # Save to cache
            cache_file.write_bytes(response.content)
            logger.info("work_plan_downloaded", size=len(response.content))
            
            # Parse the file
            parser = WorkItemParser(str(cache_file))
            return parser.parse()
            
        except Exception as e:
            logger.error("work_plan_fetch_error", error=str(e))
            return self._empty_work_plan()
    
    async def fetch_recent_meetings(self, limit: int = 3) -> List[Dict]:
        """
        Fetch recent meeting reports from RAN1 and SA2.
        
        Args:
            limit: Maximum number of recent meetings per working group
        
        Returns:
            List of meeting data dictionaries
        """
        meetings = []
        
        for wg, base_url in self.MEETING_REPORT_URLS.items():
            try:
                wg_meetings = await self._fetch_working_group_meetings(wg, base_url, limit)
                meetings.extend(wg_meetings)
            except Exception as e:
                logger.error("meeting_fetch_error", wg=wg, error=str(e))
        
        # Sort by date (most recent first)
        meetings.sort(key=lambda m: m.get("date", ""), reverse=True)
        
        return meetings
    
    async def _fetch_working_group_meetings(self, wg: str, base_url: str, limit: int) -> List[Dict]:
        """Fetch meetings for a specific working group"""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            
            # Get directory listing
            response = await self.client.get(base_url)
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
        """Return empty work plan structure"""
        from datetime import datetime
        return {
            "total_work_items": 0,
            "completed": 0,
            "in_progress": 0,
            "postponed": 0,
            "progress_percentage": 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "work_items_by_group": {}
        }
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "release_21_progress": self._empty_work_plan(),
            "recent_meetings": [],
            "work_items_by_group": {}
        }


async def fetch_standardization_data() -> Dict:
    """
    Convenience function to fetch all standardization data.
    
    Returns:
        Dict with standardization data
    """
    async with StandardsFetcher() as fetcher:
        return await fetcher.fetch_all()
