# services/report_generator.py - Simplified Version for Quick Fix
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
import base64
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generate comprehensive PDF reports for plagiarism analysis (Simplified Version)
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def generate_comprehensive_report(self, analysis_data: Dict[str, Any], include_citations: bool = True) -> str:
        """
        Generate a comprehensive PDF report and return as base64 string
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=25*mm,
                bottomMargin=25*mm
            )
            
            # Build report content
            story = []
            
            # Title
            title = Paragraph("Plagiarism Analysis Report", self.styles['Title'])
            story.append(title)
            story.append(Spacer(1, 20))
            
            # Document Information
            doc_info_data = [
                ['Document Title:', analysis_data.get('document_title', 'N/A')],
                ['Analysis Date:', self._format_datetime(analysis_data.get('analyzed_at'))],
                ['Word Count:', f"{analysis_data.get('word_count', 0):,}"],
                ['Overall Similarity:', f"{analysis_data.get('overall_similarity', 0):.1%}"],
                ['Matches Found:', str(len(analysis_data.get('matches', [])))]
            ]
            
            doc_table = Table(doc_info_data, colWidths=[60*mm, 90*mm])
            doc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(doc_table)
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", self.styles['Heading1']))
            
            similarity = analysis_data.get('overall_similarity', 0)
            matches_count = len(analysis_data.get('matches', []))
            
            summary_text = f"""
            This report presents the results of a comprehensive plagiarism analysis. 
            The analysis identified an overall similarity score of {similarity:.1%} and 
            detected {matches_count} potential matches.
            """
            
            story.append(Paragraph(summary_text, self.styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Detailed Findings
            if analysis_data.get('matches'):
                story.append(Paragraph("Detailed Findings", self.styles['Heading1']))
                
                matches = analysis_data.get('matches', [])
                sorted_matches = sorted(matches, key=lambda x: x.get('similarity', 0), reverse=True)
                
                for i, match in enumerate(sorted_matches[:5], 1):  # Show top 5 matches
                    story.append(Paragraph(f"Match {i}", self.styles['Heading2']))
                    
                    match_info = f"""
                    Similarity: {match.get('similarity', 0):.1%}<br/>
                    Source: {match.get('source_title', 'Unknown')}<br/>
                    Type: {match.get('match_type', 'Unknown').title()}<br/>
                    Original: "{match.get('original_text', '')[:100]}..."<br/>
                    Found: "{match.get('matched_text', '')[:100]}..."
                    """
                    
                    story.append(Paragraph(match_info, self.styles['Normal']))
                    story.append(Spacer(1, 10))
            
            # Sources
            if analysis_data.get('sources'):
                story.append(Paragraph("Sources Found", self.styles['Heading1']))
                
                sources_data = [['Title', 'Type', 'Domain']]
                for source in analysis_data.get('sources', []):
                    sources_data.append([
                        source.get('title', 'Unknown')[:40],
                        source.get('source_type', 'Unknown').title(),
                        source.get('domain', 'Unknown')[:30]
                    ])
                
                sources_table = Table(sources_data, colWidths=[60*mm, 40*mm, 40*mm])
                sources_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(sources_table)
            
            # Recommendations
            story.append(Spacer(1, 20))
            story.append(Paragraph("Recommendations", self.styles['Heading1']))
            
            if similarity < 0.1:
                rec_text = "The document shows minimal similarity. Continue with current practices."
            elif similarity < 0.25:
                rec_text = "Low similarity detected. Review citations for completeness."
            elif similarity < 0.5:
                rec_text = "Moderate similarity found. Review and revise as needed."
            else:
                rec_text = "High similarity detected. Significant revision recommended."
            
            story.append(Paragraph(rec_text, self.styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            # Convert to base64
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
            logger.info("PDF report generated successfully")
            return base64_pdf
            
        except Exception as e:
            logger.error(f"PDF report generation failed: {e}")
            raise Exception(f"Report generation failed: {str(e)}")
    
    def generate_summary_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate a shorter summary report"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            
            story = []
            
            # Title
            story.append(Paragraph("Plagiarism Analysis Summary", self.styles['Title']))
            story.append(Spacer(1, 20))
            
            # Basic info
            similarity = analysis_data.get('overall_similarity', 0)
            matches_count = len(analysis_data.get('matches', []))
            
            summary = f"""
            Document: {analysis_data.get('document_title', 'N/A')}<br/>
            Overall Similarity: {similarity:.1%}<br/>
            Matches Found: {matches_count}<br/>
            Analysis Date: {self._format_datetime(analysis_data.get('analyzed_at'))}
            """
            
            story.append(Paragraph(summary, self.styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Top matches
            if analysis_data.get('matches'):
                story.append(Paragraph("Top Matches:", self.styles['Heading2']))
                matches = sorted(analysis_data['matches'], 
                               key=lambda x: x.get('similarity', 0), 
                               reverse=True)[:3]
                
                for i, match in enumerate(matches, 1):
                    match_text = f"{i}. {match.get('similarity', 0):.1%} - {match.get('source_title', 'Unknown')}"
                    story.append(Paragraph(match_text, self.styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            return base64.b64encode(pdf_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Summary report generation failed: {e}")
            raise Exception(f"Summary report generation failed: {str(e)}")
    
    def _format_datetime(self, datetime_str: str) -> str:
        """Format datetime string for display"""
        try:
            if datetime_str:
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                return dt.strftime("%B %d, %Y at %I:%M %p")
            return "Unknown"
        except:
            return "Unknown"