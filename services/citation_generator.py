# services/citation_generator.py - Phase 4: Citation Generator
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class CitationGenerator:
    """
    Generate proper citations in multiple academic formats
    """
    
    def __init__(self):
        # Academic domain patterns for source type detection
        self.academic_domains = {
            'arxiv.org': 'preprint',
            'pubmed.ncbi.nlm.nih.gov': 'journal',
            'scholar.google.com': 'academic',
            'researchgate.net': 'academic',
            'jstor.org': 'journal',
            'springer.com': 'journal',
            'sciencedirect.com': 'journal',
            'ieee.org': 'conference',
            'acm.org': 'conference',
            'mit.edu': 'academic',
            'harvard.edu': 'academic',
            'stanford.edu': 'academic',
            'wikipedia.org': 'encyclopedia',
            'britannica.com': 'encyclopedia'
        }
        
        # News domain patterns
        self.news_domains = {
            'cnn.com', 'bbc.com', 'reuters.com', 'nytimes.com', 
            'washingtonpost.com', 'theguardian.com', 'wsj.com'
        }
    
    def generate_citations_for_source(self, source: Dict[str, str]) -> Dict[str, str]:
        """
        Generate citations in multiple formats for a single source
        """
        try:
            # Extract and clean source information
            title = self._clean_title(source.get('title', 'Untitled'))
            url = source.get('url', '')
            domain = urlparse(url).netloc if url else ''
            
            # Extract additional metadata
            author = self._extract_author_from_source(source)
            date = self._extract_date_from_source(source)
            source_type = self._determine_source_type(domain)
            
            # Generate all citation formats
            citations = {
                'apa': self._generate_apa_citation(title, author, date, url, domain, source_type),
                'mla': self._generate_mla_citation(title, author, date, url, domain, source_type),
                'chicago': self._generate_chicago_citation(title, author, date, url, domain, source_type),
                'harvard': self._generate_harvard_citation(title, author, date, url, domain, source_type),
                'ieee': self._generate_ieee_citation(title, author, date, url, domain, source_type)
            }
            
            return citations
            
        except Exception as e:
            logger.error(f"Citation generation failed: {e}")
            return self._generate_fallback_citations(source)
    
    def generate_bibliography(self, sources: List[Dict], style: str = 'apa') -> str:
        """
        Generate a complete bibliography in the specified style
        """
        try:
            bibliography_entries = []
            
            for i, source in enumerate(sources, 1):
                citations = self.generate_citations_for_source(source)
                citation = citations.get(style.lower(), citations.get('apa', ''))
                
                if citation:
                    # Add numbering for some styles
                    if style.lower() in ['ieee']:
                        bibliography_entries.append(f"[{i}] {citation}")
                    else:
                        bibliography_entries.append(citation)
            
            # Join with appropriate separators
            if style.lower() == 'apa':
                return '\n\n'.join(bibliography_entries)
            else:
                return '\n'.join(bibliography_entries)
                
        except Exception as e:
            logger.error(f"Bibliography generation failed: {e}")
            return "Bibliography generation failed. Please check source data."
    
    def _generate_apa_citation(self, title: str, author: str, date: str, url: str, domain: str, source_type: str) -> str:
        """Generate APA format citation"""
        try:
            # Clean components
            author = author if author != "Unknown Author" else ""
            year = self._extract_year(date) if date else "n.d."
            
            # Build citation based on source type
            if source_type == 'journal':
                if author:
                    return f"{author} ({year}). {title}. Retrieved from {url}"
                else:
                    return f"{title}. ({year}). Retrieved from {url}"
            
            elif source_type == 'encyclopedia':
                if author:
                    return f"{author} ({year}). {title}. In {domain}. Retrieved from {url}"
                else:
                    return f"{title}. ({year}). In {domain}. Retrieved from {url}"
            
            elif source_type == 'news':
                if author:
                    return f"{author} ({year}). {title}. {domain}. Retrieved from {url}"
                else:
                    return f"{title}. ({year}). {domain}. Retrieved from {url}"
            
            else:  # web or academic
                if author:
                    return f"{author} ({year}). {title}. Retrieved from {url}"
                else:
                    return f"{title}. ({year}). Retrieved from {url}"
                    
        except Exception as e:
            logger.error(f"APA citation generation failed: {e}")
            return f"{title}. Retrieved from {url}"
    
    def _generate_mla_citation(self, title: str, author: str, date: str, url: str, domain: str, source_type: str) -> str:
        """Generate MLA format citation"""
        try:
            # Format date for MLA
            formatted_date = self._format_date_mla(date) if date else "n.d."
            access_date = datetime.now().strftime("%d %b %Y")
            
            # Build citation
            if author and author != "Unknown Author":
                citation = f'{author}. "{title}." {domain}, {formatted_date}. Web. {access_date}.'
            else:
                citation = f'"{title}." {domain}, {formatted_date}. Web. {access_date}.'
            
            return citation
            
        except Exception as e:
            logger.error(f"MLA citation generation failed: {e}")
            return f'"{title}." {domain}. Web. {datetime.now().strftime("%d %b %Y")}.'
    
    def _generate_chicago_citation(self, title: str, author: str, date: str, url: str, domain: str, source_type: str) -> str:
        """Generate Chicago format citation"""
        try:
            access_date = datetime.now().strftime("%B %d, %Y")
            
            # Build citation
            if author and author != "Unknown Author":
                citation = f'{author}. "{title}." {domain}. Accessed {access_date}. {url}.'
            else:
                citation = f'"{title}." {domain}. Accessed {access_date}. {url}.'
            
            return citation
            
        except Exception as e:
            logger.error(f"Chicago citation generation failed: {e}")
            return f'"{title}." {domain}. Accessed {datetime.now().strftime("%B %d, %Y")}. {url}.'
    
    def _generate_harvard_citation(self, title: str, author: str, date: str, url: str, domain: str, source_type: str) -> str:
        """Generate Harvard format citation"""
        try:
            year = self._extract_year(date) if date else "n.d."
            
            # Build citation
            if author and author != "Unknown Author":
                citation = f"{author} ({year}) '{title}', {domain}, viewed {datetime.now().strftime('%d %B %Y')}, <{url}>."
            else:
                citation = f"'{title}' ({year}), {domain}, viewed {datetime.now().strftime('%d %B %Y')}, <{url}>."
            
            return citation
            
        except Exception as e:
            logger.error(f"Harvard citation generation failed: {e}")
            return f"'{title}' ({self._extract_year(date) if date else 'n.d.'}), {domain}, <{url}>."
    
    def _generate_ieee_citation(self, title: str, author: str, date: str, url: str, domain: str, source_type: str) -> str:
        """Generate IEEE format citation"""
        try:
            year = self._extract_year(date) if date else "n.d."
            
            # Build citation
            if author and author != "Unknown Author":
                citation = f'{author}, "{title}," {domain}, {year}. [Online]. Available: {url}'
            else:
                citation = f'"{title}," {domain}, {year}. [Online]. Available: {url}'
            
            return citation
            
        except Exception as e:
            logger.error(f"IEEE citation generation failed: {e}")
            return f'"{title}," {domain}. [Online]. Available: {url}'
    
    def _clean_title(self, title: str) -> str:
        """Clean and format title"""
        # Remove extra whitespace and common suffixes
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Remove common website suffixes
        suffixes_to_remove = [
            ' - Wikipedia',
            ' | Wikipedia',
            ' - Google Scholar',
            ' | Google Scholar',
            ' - ResearchGate',
            ' | ResearchGate'
        ]
        
        for suffix in suffixes_to_remove:
            if title.endswith(suffix):
                title = title[:-len(suffix)].strip()
        
        return title
    
    def _extract_author_from_source(self, source: Dict[str, str]) -> str:
        """Extract author information from source"""
        # Try to extract author from title or other fields
        title = source.get('title', '')
        
        # Look for author patterns in title
        author_patterns = [
            r'by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "by John Doe"
            r'([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)',  # "John A. Doe"
            r'([A-Z][a-z]+,\s+[A-Z]\.)' # "Doe, J."
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1).strip()
        
        return "Unknown Author"
    
    def _extract_date_from_source(self, source: Dict[str, str]) -> Optional[str]:
        """Extract publication date from source"""
        # This would typically come from metadata or web scraping
        # For now, return None - can be enhanced with actual date extraction
        return None
    
    def _determine_source_type(self, domain: str) -> str:
        """Determine the type of source based on domain"""
        domain_lower = domain.lower()
        
        # Check academic domains
        for academic_domain, source_type in self.academic_domains.items():
            if academic_domain in domain_lower:
                return source_type
        
        # Check news domains
        for news_domain in self.news_domains:
            if news_domain in domain_lower:
                return 'news'
        
        # Check for educational institutions
        if '.edu' in domain_lower:
            return 'academic'
        
        # Check for government sites
        if '.gov' in domain_lower:
            return 'government'
        
        # Default to web
        return 'web'
    
    def _extract_year(self, date_str: Optional[str]) -> str:
        """Extract year from date string"""
        if not date_str:
            return "n.d."
        
        # Look for 4-digit year
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            return year_match.group()
        
        return "n.d."
    
    def _format_date_mla(self, date_str: Optional[str]) -> str:
        """Format date for MLA style"""
        if not date_str:
            return "n.d."
        
        try:
            # Try to parse and format date
            # This is a simplified version - can be enhanced with dateutil
            year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
            if year_match:
                return year_match.group()
            return "n.d."
        except:
            return "n.d."
    
    def _generate_fallback_citations(self, source: Dict[str, str]) -> Dict[str, str]:
        """Generate basic citations when full generation fails"""
        title = source.get('title', 'Untitled')
        url = source.get('url', '')
        
        fallback = f'"{title}." Retrieved from {url}'
        
        return {
            'apa': fallback,
            'mla': fallback,
            'chicago': fallback,
            'harvard': fallback,
            'ieee': fallback
        }
    
    def get_citation_guidelines(self, style: str) -> Dict[str, str]:
        """Get formatting guidelines for citation styles"""
        guidelines = {
            'apa': {
                'name': 'APA (American Psychological Association)',
                'description': 'Commonly used in psychology, education, and social sciences',
                'example': 'Author, A. A. (Year). Title of work. Retrieved from URL'
            },
            'mla': {
                'name': 'MLA (Modern Language Association)', 
                'description': 'Commonly used in literature, arts, and humanities',
                'example': 'Author. "Title of Work." Website, Date. Web. Access Date.'
            },
            'chicago': {
                'name': 'Chicago Manual of Style',
                'description': 'Commonly used in history, literature, and arts',
                'example': 'Author. "Title of Work." Website. Accessed Date. URL.'
            },
            'harvard': {
                'name': 'Harvard Referencing',
                'description': 'Commonly used in sciences and social sciences',
                'example': "Author (Year) 'Title', Website, viewed Date, <URL>."
            },
            'ieee': {
                'name': 'IEEE Citation Style',
                'description': 'Commonly used in engineering and computer science',
                'example': 'Author, "Title," Website, Year. [Online]. Available: URL'
            }
        }
        
        return guidelines.get(style.lower(), {})