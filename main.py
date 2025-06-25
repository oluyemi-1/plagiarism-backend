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
                return text
        
        elif file_extension == '.docx':
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    except Exception as e:
        raise Exception(f"Error extracting text: {str(e)}")

def simulate_plagiarism_check(text: str, filename: str) -> Dict[str, Any]:
    """
    Simulate plagiarism detection logic
    In production, this would connect to real plagiarism detection APIs
    """
    
    # Simulate different similarity levels based on content
    text_lower = text.lower()
    
    # Simulate high similarity for certain patterns
    if any(phrase in text_lower for phrase in ["artificial intelligence", "machine learning", "climate change"]):
        similarity = 68.7
        risk_level = "HIGH"
        matches = [
            {
                "id": str(uuid.uuid4()),
                "text": "artificial intelligence and machine learning have...",
                "similarity": 95.0,
                "source": "academic-journal-2023.pdf",
                "url": "https://example.com/source1"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "machine learning enables computers to learn from e...",
                "similarity": 95.0,
                "source": "research-paper-ai.docx",
                "url": "https://example.com/source2"
            }
        ]
    elif any(phrase in text_lower for phrase in ["lorem ipsum", "sample text", "test document"]):
        similarity = 50.8
        risk_level = "HIGH"
        matches = [
            {
                "id": str(uuid.uuid4()),
                "text": "lorem ipsum dolor sit amet consectetur...",
                "similarity": 85.0,
                "source": "template-document.txt",
                "url": "https://example.com/source3"
            }
        ]
    elif len(text) < 100:
        similarity = 0.0
        risk_level = "LOW"
        matches = []
    else:
        # Random similarity for other content
        import random
        similarity = random.uniform(15.0, 45.0)
        risk_level = "MEDIUM" if similarity > 30 else "LOW"
        matches = [
            {
                "id": str(uuid.uuid4()),
                "text": text[:50] + "...",
                "similarity": similarity + 10,
                "source": "online-source.html",
                "url": "https://example.com/source4"
            }
        ] if similarity > 25 else []
    
    sources = [
        {
            "id": str(uuid.uuid4()),
            "title": "Academic Research Database",
            "url": "https://academic-db.example.com",
            "type": "academic"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Web Content Scanner",
            "url": "https://web-scanner.example.com",
            "type": "web"
        }
    ]
    
    return {
        "document_id": str(uuid.uuid4()),
        "overall_similarity": round(similarity, 1),
        "risk_level": risk_level,
        "matches": matches,
        "sources": sources,
        "analyzed_at": datetime.now().isoformat(),
        "original_text": text[:500] + "..." if len(text) > 500 else text,
        "word_count": len(text.split()),
        "character_count": len(text)
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