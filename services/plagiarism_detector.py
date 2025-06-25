# services/plagiarism_detector.py - Phase 3: Fixed Web Search
import asyncio
import logging
import re
import requests
from typing import Dict, List, Any, Tuple
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
import difflib
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PlagiarismDetector:
    """
    Advanced plagiarism detection service with web search integration
    """
    
    def __init__(self):
        self.similarity_threshold = 0.6  # 60% similarity threshold
        self.min_sentence_length = 10   # Minimum words per sentence
        self.max_search_results = 5     # Results per search
        
        # Headers to avoid bot detection
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def analyze_document(self, text: str, document_title: str) -> Dict[str, Any]:
        """
        Main method to analyze document for plagiarism
        """
        try:
            logger.info(f"Starting plagiarism analysis for document: {document_title}")
            
            # Split text into sentences
            sentences = self._split_into_sentences(text)
            
            # Filter sentences by length
            valid_sentences = [s for s in sentences if len(s.split()) >= self.min_sentence_length]
            
            logger.info(f"Analyzing {len(valid_sentences)} sentences")
            
            if not valid_sentences:
                return self._create_empty_result()
            
            # Search for each sentence in batches
            all_matches = []
            batch_size = 3  # Process 3 sentences at a time to avoid rate limiting
            
            for i in range(0, len(valid_sentences), batch_size):
                batch = valid_sentences[i:i + batch_size]
                batch_matches = await self._search_batch(batch, i)
                all_matches.extend(batch_matches)
                
                # Small delay between batches
                if i + batch_size < len(valid_sentences):
                    await asyncio.sleep(2)
            
            # Calculate overall similarity
            overall_similarity = self._calculate_overall_similarity(valid_sentences, all_matches)
            
            # Extract unique sources
            sources = self._extract_sources(all_matches)
            
            result = {
                "overall_similarity": overall_similarity,
                "matches": all_matches,
                "sources": sources,
                "total_sentences_analyzed": len(valid_sentences),
                "matches_found": len(all_matches)
            }
            
            logger.info(f"Analysis complete: {len(all_matches)} matches found, {overall_similarity:.2%} similarity")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return self._create_error_result(str(e))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using basic punctuation"""
        # Simple sentence splitting - can be enhanced with NLTK
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _search_batch(self, sentences: List[str], start_index: int) -> List[Dict[str, Any]]:
        """Search for a batch of sentences"""
        matches = []
        
        for i, sentence in enumerate(sentences):
            try:
                sentence_index = start_index + i
                logger.info(f"Searching sentence {sentence_index + 1}: '{sentence[:50]}...'")
                
                # Search using multiple methods
                search_results = await self._search_sentence_comprehensive(sentence)
                
                # Analyze each search result
                for result in search_results:
                    try:
                        similarity = self._calculate_similarity(sentence, result['snippet'])
                        
                        if similarity >= self.similarity_threshold:
                            match = {
                                'original_text': sentence,
                                'matched_text': result['snippet'],
                                'similarity': similarity,
                                'source_url': result['url'],
                                'source_title': result['title'],
                                'match_type': self._classify_match(similarity),
                                'sentence_index': sentence_index
                            }
                            matches.append(match)
                            logger.info(f"Match found: {similarity:.2%} similarity with {result['title']}")
                    
                    except Exception as e:
                        logger.error(f"Error analyzing result: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Error searching sentence {sentence_index + 1}: {e}")
                continue
        
        return matches
    
    async def _search_sentence_comprehensive(self, sentence: str) -> List[Dict[str, str]]:
        """Comprehensive search using multiple methods"""
        all_results = []
        
        # Method 1: Google search (if available)
        try:
            google_results = await self._search_google(sentence)
            all_results.extend(google_results)
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
        
        # Method 2: Bing search
        try:
            bing_results = await self._search_bing(sentence)
            all_results.extend(bing_results)
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")
        
        # Method 3: DuckDuckGo search (fallback)
        try:
            if not all_results:  # Only if other methods failed
                ddg_results = await self._search_duckduckgo(sentence)
                all_results.extend(ddg_results)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        
        # Remove duplicates and limit results
        unique_results = self._deduplicate_results(all_results)
        return unique_results[:self.max_search_results]
    
    async def _search_google(self, sentence: str) -> List[Dict[str, str]]:
        """Search using Google Custom Search API (requires API key)"""
        # This would require a Google Custom Search API key
        # For now, return empty list
        return []
    
    async def _search_bing(self, sentence: str) -> List[Dict[str, str]]:
        """Search using Bing Web Search API"""
        try:
            query = sentence[:100]  # Limit query length
            encoded_query = quote_plus(query)
            
            # Bing Web Search (free tier available)
            url = f"https://www.bing.com/search?q={encoded_query}&form=QBLH&sp=-1&ghc=1&lq=0&pq={encoded_query}&sc=0-0&qs=n&sk=&cvid=123"
            
            logger.info(f"Bing search URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Bing response status: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            
            # Parse Bing search results
            search_results = soup.find_all('li', {'class': 'b_algo'})
            logger.info(f"Found {len(search_results)} Bing results")
            
            for result in search_results[:self.max_search_results]:
                try:
                    title_elem = result.find('h2')
                    link_elem = title_elem.find('a') if title_elem else None
                    snippet_elem = result.find('p')
                    
                    if link_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True)
                        
                        if title and url and snippet:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'bing'
                            })
                
                except Exception as e:
                    logger.error(f"Error parsing Bing result: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(results)} Bing results")
            return results
            
        except requests.RequestException as e:
            logger.error(f"Bing search request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []
    
    async def _search_duckduckgo(self, sentence: str) -> List[Dict[str, str]]:
        """Search using DuckDuckGo (backup method)"""
        try:
            query = sentence[:100]
            encoded_query = quote_plus(query)
            
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            logger.info(f"DuckDuckGo search URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"DuckDuckGo response status: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            
            # Parse DuckDuckGo results - updated selectors
            search_results = soup.find_all('div', {'class': 'web-result'})
            if not search_results:
                search_results = soup.find_all('div', class_=re.compile(r'result'))
            
            logger.info(f"Found {len(search_results)} DuckDuckGo results")
            
            for result in search_results[:self.max_search_results]:
                try:
                    title_elem = result.find('a', {'class': 'result__a'}) or result.find('h2')
                    snippet_elem = result.find('div', {'class': 'result__snippet'}) or result.find('p')
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True)
                        
                        # Fix relative URLs
                        if url.startswith('/'):
                            url = 'https://duckduckgo.com' + url
                        
                        if title and url and snippet:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'source': 'duckduckgo'
                            })
                
                except Exception as e:
                    logger.error(f"Error parsing DuckDuckGo result: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(results)} DuckDuckGo results")
            return results
            
        except requests.RequestException as e:
            logger.error(f"DuckDuckGo search request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def _deduplicate_results(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicate search results"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using difflib"""
        # Normalize texts
        text1_normalized = re.sub(r'[^\w\s]', '', text1.lower())
        text2_normalized = re.sub(r'[^\w\s]', '', text2.lower())
        
        # Calculate sequence similarity
        similarity = difflib.SequenceMatcher(None, text1_normalized, text2_normalized).ratio()
        
        return similarity
    
    def _classify_match(self, similarity: float) -> str:
        """Classify the type of match based on similarity score"""
        if similarity >= 0.9:
            return 'exact'
        elif similarity >= 0.75:
            return 'near_exact'
        elif similarity >= 0.6:
            return 'paraphrased'
        else:
            return 'semantic'
    
    def _calculate_overall_similarity(self, sentences: List[str], matches: List[Dict]) -> float:
        """Calculate overall document similarity percentage"""
        if not sentences or not matches:
            return 0.0
        
        # Count unique sentences with matches
        matched_sentences = set(match['sentence_index'] for match in matches)
        similarity_percentage = len(matched_sentences) / len(sentences)
        
        return min(similarity_percentage, 1.0)
    
    def _extract_sources(self, matches: List[Dict]) -> List[Dict]:
        """Extract unique sources from matches"""
        sources = {}
        
        for match in matches:
            url = match.get('source_url', '')
            if url and url not in sources:
                domain = urlparse(url).netloc
                
                sources[url] = {
                    'id': str(hash(url))[-8:],  # Simple ID generation
                    'title': match.get('source_title', 'Unknown Title'),
                    'url': url,
                    'domain': domain,
                    'source_type': self._determine_source_type(domain)
                }
        
        return list(sources.values())
    
    def _determine_source_type(self, domain: str) -> str:
        """Determine the type of source based on domain"""
        if any(academic in domain.lower() for academic in ['edu', 'scholar', 'researchgate', 'arxiv', 'pubmed']):
            return 'academic'
        elif any(news in domain.lower() for news in ['news', 'cnn', 'bbc', 'reuters', 'times']):
            return 'news'
        elif 'wikipedia' in domain.lower():
            return 'encyclopedia'
        else:
            return 'web'
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result when no analysis possible"""
        return {
            "overall_similarity": 0.0,
            "matches": [],
            "sources": [],
            "total_sentences_analyzed": 0,
            "matches_found": 0
        }
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            "overall_similarity": 0.0,
            "matches": [],
            "sources": [],
            "total_sentences_analyzed": 0,
            "matches_found": 0,
            "error": error_message
        }

    # Utility method for direct search testing
    async def search_text_directly(self, text: str) -> Dict[str, Any]:
        """Direct search method for testing"""
        try:
            logger.info(f"Direct search for: '{text[:50]}...'")
            
            # Search using all available methods
            results = await self._search_sentence_comprehensive(text)
            
            return {
                "query": text,
                "results": results,
                "total_found": len(results)
            }
            
        except Exception as e:
            logger.error(f"Direct search failed: {e}")
            return {
                "query": text,
                "results": [],
                "total_found": 0,
                "error": str(e)
            }