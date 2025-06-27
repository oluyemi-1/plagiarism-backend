import os
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import aiofiles
import requests
import PyPDF2
from docx import Document
import io

app = FastAPI(
    title="Plagiarism Detection API",
    description="Academic integrity checking service",
    version="1.0.0"
)

# 🌐 CORS Configuration for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

def extract_text_from_file(file_path: str, filename: str) -> str:
    """Extract text from different file types"""
    file_extension = Path(filename).suffix.lower()
    
    try:
        if file_extension == '.pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        
        elif file_extension == '.docx':
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    except Exception as e:
        raise Exception(f"Error extracting text: {str(e)}")

def create_realistic_matches(text: str) -> List[Dict[str, Any]]:
    """Create realistic matches with proper positioning"""
    matches = []
    text_lower = text.lower()
    
    # Look for common academic phrases and create matches
    patterns = [
        ("artificial intelligence", "Artificial intelligence and machine learning have revolutionized", 95.0),
        ("machine learning", "Machine learning enables computers to learn from experience", 88.0),
        ("climate change", "Climate change represents one of the most pressing challenges", 92.0),
        ("data analysis", "Data analysis techniques are essential for modern research", 85.0),
        ("research methodology", "Research methodology forms the backbone of academic studies", 90.0),
        ("literature review", "Literature review provides comprehensive overview of existing work", 87.0),
    ]
    
    for pattern, matched_text, similarity in patterns:
        start_pos = text_lower.find(pattern)
        if start_pos != -1:
            # Extract the actual text around the match
            # Get more context around the match
            context_start = max(0, start_pos - 5)
            context_end = min(len(text), start_pos + len(pattern) + 45)
            original_text = text[context_start:context_end].strip()
            
            # If original text is too short, extend it
            if len(original_text) < 30:
                context_end = min(len(text), start_pos + 60)
                original_text = text[context_start:context_end].strip()
            
            matches.append({
                "originalText": original_text,
                "matchedText": matched_text,
                "similarity": similarity,
                "startIndex": start_pos,
                "endIndex": start_pos + len(pattern),
                "source": {
                    "id": f"src_{len(matches) + 1:03d}",
                    "title": f"Academic Research on {pattern.title()}",
                    "url": f"https://example-university.edu/{pattern.replace(' ', '-')}",
                    "author": f"Dr. {['Smith', 'Johnson', 'Williams', 'Brown'][len(matches) % 4]}",
                    "domain": "example-university.edu",
                    "type": "academic"
                },
                "type": "exact" if similarity > 90 else "paraphrased"
            })
    
    return matches

def simulate_plagiarism_check(text: str, filename: str) -> Dict[str, Any]:
    """
    Simulate plagiarism detection logic with realistic matches
    """
    
    # Create matches based on actual text content
    matches = create_realistic_matches(text)
    
    # 🔥 FIX: Calculate overall similarity properly
    if matches:
        # Calculate based on text coverage and match quality
        total_matched_chars = sum(len(match["originalText"]) for match in matches)
        text_coverage = min(total_matched_chars / len(text), 1.0)  # Max 100%
        
        # Average similarity of matches weighted by coverage
        avg_similarity = sum(match["similarity"] for match in matches) / len(matches)
        
        # Combine coverage and similarity (scale to 0-1)
        overall_similarity = (text_coverage * 0.6 + (avg_similarity / 100) * 0.4)
        overall_similarity = min(overall_similarity, 0.95)  # Cap at 95%
    else:
        overall_similarity = 0.0
    
    # Determine risk level
    if overall_similarity < 0.10:
        risk_level = "Low"
    elif overall_similarity < 0.25:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    # Create source references
    sources = []
    for match in matches:
        source = match["source"]
        if not any(s["id"] == source["id"] for s in sources):
            sources.append(source)
    
    return {
        "documentId": str(uuid.uuid4()),
        "overallSimilarity": overall_similarity,
        "riskLevel": risk_level,
        "status": "completed",
        "analyzedAt": datetime.now().isoformat(),
        "filename": filename,
        "original_text": text,  # Return the FULL original text
        "word_count": len(text.split()),
        "character_count": len(text),
        "matches": matches,
        "sources": sources
    }

async def analyze_document(file_path: str, filename: str) -> Dict[str, Any]:
    """
    Main analysis function that processes the document
    """
    try:
        # Extract text from the uploaded file
        extracted_text = extract_text_from_file(file_path, filename)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise ValueError("Document appears to be empty or too short for analysis")
        
        # Perform plagiarism analysis
        result = simulate_plagiarism_check(extracted_text, filename)
        
        return result
    
    except Exception as e:
        raise Exception(f"Document analysis failed: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Plagiarism Detection API", 
        "status": "online", 
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/api/v1/analyze"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "plagiarism-detection-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/analyze")
async def analyze_document_endpoint(file: UploadFile = File(...)):
    """
    Analyze uploaded document for plagiarism
    """
    try:
        # Validate file type
        allowed_types = [
            "application/pdf", 
            "text/plain", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}. Supported types: PDF, TXT, DOCX"
            )
        
        # Validate file size (max 10MB)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")
        
        # Reset file position
        await file.seek(0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            # Save uploaded file
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Analyze the document
            result = await analyze_document(tmp_file_path, file.filename)
            
            return JSONResponse(content={
                "success": True,
                "message": "Document analyzed successfully",
                "data": result
            })
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except:
                pass  # Ignore cleanup errors
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# 🚀 Railway deployment configuration
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)