"""
Parser for 3GPP meeting reports.
Extracts key agreements, TDoc references, and sentiment from meeting summaries.
"""
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()


class MeetingReportParser:
    """Parse 3GPP meeting reports to extract agreements and TDocs"""
    
    # Patterns for TDoc references
    TDOC_PATTERNS = [
        r'R1-\d{7}',  # RAN1 TDocs
        r'R2-\d{7}',  # RAN2 TDocs
        r'R3-\d{7}',  # RAN3 TDocs
        r'R4-\d{7}',  # RAN4 TDocs
        r'S2-\d{7}',  # SA2 TDocs
        r'S6-\d{7}',  # SA6 TDocs
    ]
    
    # Keywords for agreement extraction
    AGREEMENT_KEYWORDS = [
        "agreed:", "decision:", "conclusion:", 
        "way forward:", "agreement:", "decided:"
    ]
    
    # Sentiment indicators
    SENTIMENT_POSITIVE = ["agreed", "approved", "accepted", "confirmed", "decision"]
    SENTIMENT_NEUTRAL = ["further study needed", "ffs", "for further study", "to be studied"]
    SENTIMENT_NEGATIVE = ["postponed", "rejected", "not agreed", "no consensus", "delayed"]
    
    def __init__(self, content: str, content_type: str = "html"):
        """
        Initialize parser.
        
        Args:
            content: Raw content (HTML or text)
            content_type: Either "html" or "text"
        """
        self.content = content
        self.content_type = content_type
        self.text = self._extract_text()
    
    def _extract_text(self) -> str:
        """Extract plain text from content"""
        if self.content_type == "html":
            try:
                soup = BeautifulSoup(self.content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator=' ', strip=True)
            except Exception as e:
                logger.warning("html_parse_error", error=str(e))
                return self.content
        return self.content
    
    def parse(self, meeting_id: str = "", working_group: str = "") -> Dict:
        """
        Parse meeting report to extract structured data.
        
        Args:
            meeting_id: Meeting identifier (e.g., "R1-115")
            working_group: Working group name (e.g., "RAN1")
        
        Returns:
            Dict with structure:
            {
                "meeting_id": str,
                "working_group": str,
                "date": str,
                "location": str,
                "key_agreements": List[str],
                "tdoc_references": List[str],
                "sentiment": str
            }
        """
        try:
            # Extract metadata
            date = self._extract_date()
            location = self._extract_location()
            
            # Extract agreements
            agreements = self._extract_agreements()
            
            # Extract TDoc references
            tdocs = self._extract_tdocs()
            
            # Calculate sentiment
            sentiment = self._calculate_sentiment()
            
            result = {
                "meeting_id": meeting_id,
                "working_group": working_group,
                "date": date,
                "location": location,
                "key_agreements": agreements[:10],  # Limit to top 10
                "tdoc_references": list(set(tdocs))[:20],  # Limit to 20 unique
                "sentiment": sentiment
            }
            
            logger.info("meeting_parsed", meeting_id=meeting_id, agreements=len(agreements), tdocs=len(tdocs))
            return result
            
        except Exception as e:
            logger.error("meeting_parser_error", error=str(e))
            return self._empty_result(meeting_id, working_group)
    
    def _extract_date(self) -> str:
        """Extract meeting date from text"""
        # Common date patterns
        patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # DD Month YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_location(self) -> str:
        """Extract meeting location from text"""
        # Look for location patterns
        patterns = [
            r'(?:held\s+in|location:|venue:)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s*[A-Z][a-z]+)',
            r'([A-Z][a-z]+,\s*[A-Z][a-z]+)(?:\s+meeting)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_agreements(self) -> List[str]:
        """Extract key agreements from text"""
        agreements = []
        
        # Split into sentences
        sentences = re.split(r'[.!?\n]+', self.text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains agreement keywords
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in self.AGREEMENT_KEYWORDS):
                # Clean up the sentence
                cleaned = sentence[:200]  # Limit length
                agreements.append(cleaned)
        
        return agreements
    
    def _extract_tdocs(self) -> List[str]:
        """Extract TDoc references from text"""
        tdocs = []
        
        for pattern in self.TDOC_PATTERNS:
            matches = re.findall(pattern, self.text)
            tdocs.extend(matches)
        
        return tdocs
    
    def _calculate_sentiment(self) -> str:
        """Calculate overall sentiment based on keywords"""
        text_lower = self.text.lower()
        
        positive_count = sum(1 for keyword in self.SENTIMENT_POSITIVE if keyword in text_lower)
        neutral_count = sum(1 for keyword in self.SENTIMENT_NEUTRAL if keyword in text_lower)
        negative_count = sum(1 for keyword in self.SENTIMENT_NEGATIVE if keyword in text_lower)
        
        total = positive_count + neutral_count + negative_count
        if total == 0:
            return "neutral"
        
        # Calculate sentiment score
        if positive_count > negative_count and positive_count > neutral_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "mixed"
    
    def _empty_result(self, meeting_id: str = "", working_group: str = "") -> Dict:
        """Return empty result structure"""
        return {
            "meeting_id": meeting_id,
            "working_group": working_group,
            "date": "",
            "location": "",
            "key_agreements": [],
            "tdoc_references": [],
            "sentiment": "neutral"
        }
