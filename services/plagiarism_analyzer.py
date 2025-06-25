# services/plagiarism_analyzer.py
import uuid
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PlagiarismAnalyzer:
    def __init__(self):
        # Database of known phrases/sentences for demo purposes
        # In production, this would connect to academic databases
        self.known_sources = {
            "artificial intelligence": {
                "source": {
                    "id": "src_001",
                    "title": "Introduction to Artificial Intelligence and Machine Learning",
                    "url": "https://example-university.edu/ai-ml-intro",
                    "author": "Dr. Jane Smith",
                    "domain": "example-university.edu",
                    "type": "academic",
                    "published": "2023-06-15"
                },
                "phrases": [
                    "artificial intelligence and machine learning have revolutionized",
                    "machine learning algorithms",
                    "artificial intelligence systems",
                    "deep learning networks",
                    "neural networks and artificial intelligence"
                ]
            },
            "climate change": {
                "source": {
                    "id": "src_002", 
                    "title": "Climate Change and Environmental Impact",
                    "url": "https://climate-research.org/environmental-study",
                    "author": "Dr. Michael Johnson",
                    "domain": "climate-research.org",
                    "type": "academic",
                    "published": "2023-08-20"
                },
                "phrases": [
                    "climate change represents one of the most pressing challenges",
                    "global warming and climate change",
                    "rising temperatures and melting ice caps",
                    "environmental impact of climate change"
                ]
            },
            "human brain": {
                "source": {
                    "id": "src_003",
                    "title": "Neuroscience and Brain Function Research", 
                    "url": "https://neuro-institute.edu/brain-research",
                    "author": "Dr. Sarah Wilson",
                    "domain": "neuro-institute.edu",
                    "type": "academic",
                    "published": "2023-04-10"
                },
                "phrases": [
                    "human brain contains approximately 86 billion neurons",
                    "neurons connected through synapses",
                    "brain neural networks",
                    "cognitive neuroscience research"
                ]
            },
            "machine learning": {
                "source": {
                    "id": "src_004",
                    "title": "Advanced Machine Learning Techniques",
                    "url": "https://tech-university.edu/ml-advanced",
                    "author": "Prof. David Chen", 
                    "domain": "tech-university.edu",
                    "type": "academic",
                    "published": "2023-09-12"
                },
                "phrases": [
                    "machine learning enables computers to learn from experience",
                    "supervised and unsupervised learning",
                    "machine learning algorithms and data processing",
                    "predictive modeling with machine learning"
                ]
            }
        }

    def analyze_document(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Analyze document for plagiarism by checking against known sources
        """
        try:
            logger.info(f"Starting analysis of {filename}")
            
            # Clean and prepare text
            clean_text = self._clean_text(text)
            sentences = self._split_into_sentences(clean_text)
            
            # Find matches
            matches = self._find_matches(clean_text, sentences)
            
            # Calculate similarity
            overall_similarity = self._calculate_overall_similarity(clean_text, matches)
            risk_level = self._determine_risk_level(overall_similarity)
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Build response
            result = {
                "documentId": doc_id,
                "overallSimilarity": overall_similarity,
                "riskLevel": risk_level,
                "status": "completed",
                "analyzedAt": datetime.now().isoformat(),
                "filename": filename,
                "original_text": text,
                "word_count": len(text.split()),
                "character_count": len(text),
                "matches": matches,
                "analysis_summary": {
                    "total_matches": len(matches),
                    "sources_found": len(set(match.get("source", {}).get("id", "") for match in matches)),
                    "highest_similarity": max([match.get("similarity", 0) for match in matches]) if matches else 0,
                    "match_types": self._categorize_matches(matches)
                }
            }
            
            logger.info(f"Analysis completed: {overall_similarity:.1%} similarity, {len(matches)} matches")
            return result
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            raise Exception(f"Failed to analyze document: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Convert to lowercase for matching
        return text.lower()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _find_matches(self, clean_text: str, sentences: List[str]) -> List[Dict[str, Any]]:
        """Find matches against known sources"""
        matches = []
        
        for category, source_data in self.known_sources.items():
            source_info = source_data["source"]
            phrases = source_data["phrases"]
            
            # Check each known phrase against the text
            for phrase in phrases:
                phrase_lower = phrase.lower()
                
                # Find exact and partial matches
                if phrase_lower in clean_text:
                    # Find the position in original text
                    start_pos = clean_text.find(phrase_lower)
                    end_pos = start_pos + len(phrase_lower)
                    
                    # Calculate similarity (exact match = 95%, partial = lower)
                    similarity = 95 if phrase_lower == clean_text[start_pos:end_pos] else 85
                    
                    # Extract the actual matched text from original
                    original_match = clean_text[start_pos:end_pos]
                    
                    match = {
                        "originalText": original_match,
                        "matchedText": phrase,
                        "similarity": similarity,
                        "startIndex": start_pos,
                        "endIndex": end_pos,
                        "source": source_info,
                        "matchType": "exact" if similarity >= 95 else "paraphrased",
                        "confidence": similarity / 100.0
                    }
                    
                    matches.append(match)
                    logger.info(f"Found match: '{original_match}' -> {similarity}% similarity")
        
        # Also check for partial phrase matches
        matches.extend(self._find_partial_matches(clean_text))
        
        # Remove duplicates and sort by similarity
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        return matches

    def _find_partial_matches(self, text: str) -> List[Dict[str, Any]]:
        """Find partial matches using word overlap"""
        partial_matches = []
        
        # Check for common academic phrases
        common_phrases = [
            ("research shows that", "Common academic phrase"),
            ("studies have shown", "Common academic phrase"), 
            ("according to research", "Common academic phrase"),
            ("it is important to note", "Common academic phrase"),
            ("in conclusion", "Common academic phrase"),
            ("furthermore", "Common academic phrase"),
            ("however", "Common transition word"),
            ("therefore", "Common transition word")
        ]
        
        for phrase, description in common_phrases:
            if phrase in text:
                start_pos = text.find(phrase)
                end_pos = start_pos + len(phrase)
                
                partial_match = {
                    "originalText": phrase,
                    "matchedText": phrase,
                    "similarity": 70,
                    "startIndex": start_pos,
                    "endIndex": end_pos,
                    "source": {
                        "id": "common_phrase",
                        "title": "Common Academic Phrases",
                        "url": "https://academic-writing.edu/common-phrases",
                        "author": "Academic Writing Guide",
                        "domain": "academic-writing.edu",
                        "type": "reference"
                    },
                    "matchType": "common_phrase",
                    "confidence": 0.7
                }
                partial_matches.append(partial_match)
        
        return partial_matches

    def _deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate matches"""
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Create a unique key based on position and text
            key = (match["startIndex"], match["endIndex"], match["originalText"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches

    def _calculate_overall_similarity(self, text: str, matches: List[Dict[str, Any]]) -> float:
        """Calculate overall document similarity percentage"""
        if not matches:
            return 0.0
        
        # Calculate based on character coverage
        total_chars = len(text)
        matched_chars = 0
        
        # Track overlapping regions to avoid double counting
        covered_positions = set()
        
        for match in matches:
            start = match["startIndex"]
            end = match["endIndex"]
            
            # Count non-overlapping characters
            for pos in range(start, end):
                if pos not in covered_positions:
                    covered_positions.add(pos)
                    matched_chars += 1
        
        # Calculate percentage
        similarity = (matched_chars / total_chars) if total_chars > 0 else 0.0
        
        # Ensure it's between 0 and 1
        return min(max(similarity, 0.0), 1.0)

    def _determine_risk_level(self, similarity: float) -> str:
        """Determine risk level based on similarity percentage"""
        if similarity >= 0.8:
            return "High"
        elif similarity >= 0.4:
            return "Medium"
        else:
            return "Low"

    def _categorize_matches(self, matches: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize matches by type"""
        categories = {"exact": 0, "paraphrased": 0, "common_phrase": 0}
        
        for match in matches:
            match_type = match.get("matchType", "paraphrased")
            if match_type in categories:
                categories[match_type] += 1
        
        return categories

    def generate_citation(self, source: Dict[str, Any], style: str = "APA") -> str:
        """Generate citation in requested style"""
        try:
            author = source.get("author", "Unknown Author")
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            published = source.get("published", "n.d.")
            
            if style.upper() == "APA":
                # APA format: Author, A. A. (Year). Title. Website Name. URL
                return f"{author} ({published}). {title}. Retrieved from {url}"
            elif style.upper() == "MLA":
                # MLA format: Author. "Title." Website Name, Date, URL.
                return f'{author}. "{title}." {source.get("domain", "Website")}, {published}, {url}.'
            else:
                return f"{author}. {title}. {url}"
                
        except Exception as e:
            logger.error(f"Citation generation error: {str(e)}")
            return "Citation format error"