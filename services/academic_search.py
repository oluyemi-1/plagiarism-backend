# services/academic_search.py - Phase 4: Academic Database Integration
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import re

logger = logging.getLogger(__name__)

class AcademicSearch:
    """
    Search academic databases for scholarly content
    """
    
    def __init__(self):
        # API endpoints
        self.arxiv_base = "http://export.arxiv.org/api/query"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.crossref_base = "https://api.crossref.org/works"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        
        # Request headers
        self.headers = {
            'User-Agent': 'Academic-Plagiarism-Detector/1.0 (research@example.com)',
            'Accept': 'application/json, application/xml, text/xml'
        }
        
        # Rate limiting
        self.request_delay = 1.0  # Seconds between requests
    
    async def search_all_academic_sources(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search all available academic databases
        """
        all_results = []
        
        try:
            # Search different academic sources
            search_tasks = [
                self._search_arxiv(query, max_results // 4),
                self._search_crossref(query, max_results // 4),
                self._search_semantic_scholar(query, max_results // 4),
                self._search_pubmed(query, max_results // 4)
            ]
            
            # Execute searches concurrently with rate limiting
            results = await self._execute_with_rate_limit(search_tasks)
            
            # Combine results
            for result_list in results:
                if result_list:
                    all_results.extend(result_list)
            
            # Remove duplicates and limit results
            unique_results = self._deduplicate_academic_results(all_results)
            return unique_results[:max_results]
            
        except Exception as e:
            logger.error(f"Academic search failed: {e}")
            return []
    
    async def _search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search arXiv preprint server"""
        try:
            logger.info(f"Searching arXiv for: {query[:50]}...")
            
            # Prepare search parameters
            search_query = self._clean_query_for_arxiv(query)
            params = {
                'search_query': f'all:{search_query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.arxiv_base,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        results = self._parse_arxiv_xml(content)
                        logger.info(f"Found {len(results)} arXiv results")
                        return results
                    else:
                        logger.warning(f"arXiv search failed with status {response.status}")
            
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        
        return []
    
    async def _search_crossref(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search CrossRef for published academic papers"""
        try:
            logger.info(f"Searching CrossRef for: {query[:50]}...")
            
            params = {
                'query': query[:500],  # Limit query length
                'rows': max_results,
                'sort': 'relevance',
                'order': 'desc'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.crossref_base,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_crossref_results(data)
                        logger.info(f"Found {len(results)} CrossRef results")
                        return results
                    else:
                        logger.warning(f"CrossRef search failed with status {response.status}")
            
        except Exception as e:
            logger.error(f"CrossRef search error: {e}")
        
        return []
    
    async def _search_semantic_scholar(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API"""
        try:
            logger.info(f"Searching Semantic Scholar for: {query[:50]}...")
            
            search_url = f"{self.semantic_scholar_base}/paper/search"
            params = {
                'query': query[:500],
                'limit': max_results,
                'fields': 'title,authors,year,abstract,url,venue,citationCount'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_semantic_scholar_results(data)
                        logger.info(f"Found {len(results)} Semantic Scholar results")
                        return results
                    else:
                        logger.warning(f"Semantic Scholar search failed with status {response.status}")
            
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
        
        return []
    
    async def _search_pubmed(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search PubMed for medical/life science papers"""
        try:
            logger.info(f"Searching PubMed for: {query[:50]}...")
            
            # First, search for PMIDs
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': query[:500],
                'retmax': max_results,
                'retmode': 'json',
                'sort': 'relevance'
            }
            
            async with aiohttp.ClientSession() as session:
                # Get PMIDs
                async with session.get(
                    search_url,
                    params=search_params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"PubMed search failed with status {response.status}")
                        return []
                    
                    search_data = await response.json()
                    pmids = search_data.get('esearchresult', {}).get('idlist', [])
                    
                    if not pmids:
                        logger.info("No PubMed results found")
                        return []
                
                # Get paper details
                summary_url = f"{self.pubmed_base}/esummary.fcgi"
                summary_params = {
                    'db': 'pubmed',
                    'id': ','.join(pmids),
                    'retmode': 'json'
                }
                
                async with session.get(
                    summary_url,
                    params=summary_params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        summary_data = await response.json()
                        results = self._parse_pubmed_results(summary_data, pmids)
                        logger.info(f"Found {len(results)} PubMed results")
                        return results
            
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
        
        return []
    
    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse arXiv XML response"""
        results = []
        try:
            root = ET.fromstring(xml_content)
            
            # Handle namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                try:
                    title_elem = entry.find('atom:title', namespaces)
                    summary_elem = entry.find('atom:summary', namespaces)
                    id_elem = entry.find('atom:id', namespaces)
                    published_elem = entry.find('atom:published', namespaces)
                    
                    # Extract authors
                    authors = []
                    author_elems = entry.findall('atom:author', namespaces)
                    for author_elem in author_elems:
                        name_elem = author_elem.find('atom:name', namespaces)
                        if name_elem is not None:
                            authors.append(name_elem.text.strip())
                    
                    if title_elem is not None and summary_elem is not None:
                        # Clean and format data
                        title = re.sub(r'\s+', ' ', title_elem.text.strip())
                        abstract = re.sub(r'\s+', ' ', summary_elem.text.strip())
                        paper_id = id_elem.text if id_elem is not None else ''
                        published = published_elem.text if published_elem is not None else ''
                        
                        results.append({
                            'title': title,
                            'authors': ', '.join(authors[:3]),  # Limit to first 3 authors
                            'abstract': abstract[:300] + '...' if len(abstract) > 300 else abstract,
                            'url': paper_id,
                            'published_date': published.split('T')[0] if published else '',
                            'source': 'arXiv',
                            'source_type': 'preprint',
                            'snippet': abstract[:200] + '...' if len(abstract) > 200 else abstract
                        })
                
                except Exception as e:
                    logger.error(f"Error parsing arXiv entry: {e}")
                    continue
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML: {e}")
        
        return results
    
    def _parse_crossref_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse CrossRef JSON response"""
        results = []
        
        try:
            items = data.get('message', {}).get('items', [])
            
            for item in items:
                try:
                    # Extract basic information
                    title_list = item.get('title', [])
                    title = title_list[0] if title_list else 'Untitled'
                    
                    # Extract authors
                    authors = []
                    author_list = item.get('author', [])
                    for author in author_list[:3]:  # Limit to first 3 authors
                        given = author.get('given', '')
                        family = author.get('family', '')
                        if family:
                            authors.append(f"{given} {family}".strip())
                    
                    # Extract other fields
                    journal = item.get('container-title', [''])[0] if item.get('container-title') else ''
                    year = ''
                    if 'published-print' in item:
                        year = str(item['published-print']['date-parts'][0][0])
                    elif 'published-online' in item:
                        year = str(item['published-online']['date-parts'][0][0])
                    
                    url = item.get('URL', '')
                    doi = item.get('DOI', '')
                    if doi and not url:
                        url = f"https://doi.org/{doi}"
                    
                    # Create snippet from available text
                    snippet_parts = []
                    if journal:
                        snippet_parts.append(f"Published in {journal}")
                    if year:
                        snippet_parts.append(f"({year})")
                    
                    results.append({
                        'title': title,
                        'authors': ', '.join(authors),
                        'journal': journal,
                        'year': year,
                        'url': url,
                        'doi': doi,
                        'source': 'CrossRef',
                        'source_type': 'journal',
                        'snippet': '. '.join(snippet_parts) if snippet_parts else 'Academic publication'
                    })
                
                except Exception as e:
                    logger.error(f"Error parsing CrossRef item: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing CrossRef results: {e}")
        
        return results
    
    def _parse_semantic_scholar_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse Semantic Scholar JSON response"""
        results = []
        
        try:
            papers = data.get('data', [])
            
            for paper in papers:
                try:
                    title = paper.get('title', 'Untitled')
                    
                    # Extract authors
                    authors = []
                    author_list = paper.get('authors', [])
                    for author in author_list[:3]:  # Limit to first 3 authors
                        name = author.get('name', '')
                        if name:
                            authors.append(name)
                    
                    # Extract other fields
                    year = str(paper.get('year', '')) if paper.get('year') else ''
                    abstract = paper.get('abstract', '')
                    url = paper.get('url', '')
                    venue = paper.get('venue', '')
                    citation_count = paper.get('citationCount', 0)
                    
                    # Create snippet
                    snippet_parts = []
                    if venue:
                        snippet_parts.append(f"Published in {venue}")
                    if year:
                        snippet_parts.append(f"({year})")
                    if citation_count:
                        snippet_parts.append(f"Cited {citation_count} times")
                    if abstract:
                        snippet_parts.append(abstract[:150] + '...' if len(abstract) > 150 else abstract)
                    
                    results.append({
                        'title': title,
                        'authors': ', '.join(authors),
                        'year': year,
                        'abstract': abstract[:300] + '...' if len(abstract) > 300 else abstract,
                        'url': url,
                        'venue': venue,
                        'citation_count': citation_count,
                        'source': 'Semantic Scholar',
                        'source_type': 'academic',
                        'snippet': '. '.join(snippet_parts) if snippet_parts else 'Academic paper'
                    })
                
                except Exception as e:
                    logger.error(f"Error parsing Semantic Scholar paper: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing Semantic Scholar results: {e}")
        
        return results
    
    def _parse_pubmed_results(self, data: Dict, pmids: List[str]) -> List[Dict[str, Any]]:
        """Parse PubMed JSON response"""
        results = []
        
        try:
            result_data = data.get('result', {})
            
            for pmid in pmids:
                try:
                    paper_data = result_data.get(pmid, {})
                    
                    if not paper_data:
                        continue
                    
                    title = paper_data.get('title', 'Untitled')
                    
                    # Extract authors
                    authors = []
                    author_list = paper_data.get('authors', [])
                    for author in author_list[:3]:  # Limit to first 3 authors
                        name = author.get('name', '')
                        if name:
                            authors.append(name)
                    
                    # Extract other fields
                    journal = paper_data.get('fulljournalname', '')
                    pub_date = paper_data.get('pubdate', '')
                    year = pub_date.split()[0] if pub_date else ''
                    
                    # Create URL
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    
                    # Create snippet
                    snippet_parts = []
                    if journal:
                        snippet_parts.append(f"Published in {journal}")
                    if year:
                        snippet_parts.append(f"({year})")
                    snippet_parts.append("Medical/Life Sciences research")
                    
                    results.append({
                        'title': title,
                        'authors': ', '.join(authors),
                        'journal': journal,
                        'year': year,
                        'pmid': pmid,
                        'url': url,
                        'source': 'PubMed',
                        'source_type': 'journal',
                        'snippet': '. '.join(snippet_parts)
                    })
                
                except Exception as e:
                    logger.error(f"Error parsing PubMed paper {pmid}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error parsing PubMed results: {e}")
        
        return results
    
    def _clean_query_for_arxiv(self, query: str) -> str:
        """Clean query for arXiv search"""
        # Remove special characters that might cause issues
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Limit length
        return cleaned[:200]
    
    def _deduplicate_academic_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on title similarity"""
        if not results:
            return []
        
        unique_results = []
        seen_titles = set()
        
        for result in results:
            title = result.get('title', '').lower().strip()
            
            # Simple deduplication based on title
            title_key = re.sub(r'[^\w\s]', '', title)[:50]
            
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_results.append(result)
        
        return unique_results
    
    async def _execute_with_rate_limit(self, tasks: List) -> List:
        """Execute tasks with rate limiting"""
        results = []
        
        for task in tasks:
            try:
                result = await task
                results.append(result)
                # Rate limiting delay
                await asyncio.sleep(self.request_delay)
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                results.append([])
        
        return results
    
    async def get_paper_details(self, paper_id: str, source: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific paper"""
        try:
            if source.lower() == 'arxiv':
                return await self._get_arxiv_details(paper_id)
            elif source.lower() == 'semantic scholar':
                return await self._get_semantic_scholar_details(paper_id)
            elif source.lower() == 'pubmed':
                return await self._get_pubmed_details(paper_id)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get paper details: {e}")
            return None
    
    async def _get_arxiv_details(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed arXiv paper information"""
        try:
            params = {
                'id_list': arxiv_id,
                'max_results': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.arxiv_base,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        results = self._parse_arxiv_xml(content)
                        return results[0] if results else None
        except Exception as e:
            logger.error(f"arXiv details fetch failed: {e}")
        
        return None
    
    async def _get_semantic_scholar_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed Semantic Scholar paper information"""
        try:
            url = f"{self.semantic_scholar_base}/paper/{paper_id}"
            params = {
                'fields': 'title,authors,year,abstract,url,venue,citationCount,references,citations'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_semantic_scholar_results({'data': [data]})[0]
        except Exception as e:
            logger.error(f"Semantic Scholar details fetch failed: {e}")
        
        return None
    
    async def _get_pubmed_details(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Get detailed PubMed paper information"""
        try:
            # Get full record
            fetch_url = f"{self.pubmed_base}/efetch.fcgi"
            params = {
                'db': 'pubmed',
                'id': pmid,
                'retmode': 'xml',
                'rettype': 'abstract'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    fetch_url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_pubmed_xml_details(content, pmid)
        except Exception as e:
            logger.error(f"PubMed details fetch failed: {e}")
        
        return None
    
    def _parse_pubmed_xml_details(self, xml_content: str, pmid: str) -> Optional[Dict[str, Any]]:
        """Parse detailed PubMed XML response"""
        try:
            root = ET.fromstring(xml_content)
            
            # Extract detailed information
            article = root.find('.//Article')
            if article is None:
                return None
            
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else 'Untitled'
            
            # Extract abstract
            abstract_elem = article.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ''
            
            # Extract authors
            authors = []
            author_list = article.findall('.//Author')
            for author in author_list[:5]:
                last_name = author.find('LastName')
                first_name = author.find('ForeName')
                if last_name is not None:
                    name = last_name.text
                    if first_name is not None:
                        name = f"{first_name.text} {name}"
                    authors.append(name)
            
            # Extract journal info
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ''
            
            return {
                'title': title,
                'abstract': abstract,
                'authors': ', '.join(authors),
                'journal': journal,
                'pmid': pmid,
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                'source': 'PubMed',
                'source_type': 'journal'
            }
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed XML details: {e}")
        
        return None