from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.units import inch
import datetime

def generate_pdf_report(report_data, filename="market_research_report.pdf"):
    """
    Generate a PDF report from the market research data.
    """
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
    )

    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph(report_data['title'], title_style))
    story.append(Spacer(1, 12))

    # Summary
    story.append(Paragraph("Summary", heading_style))
    story.append(Paragraph(report_data['summary'], normal_style))
    story.append(Spacer(1, 12))

    # Key Findings
    story.append(Paragraph("Key Findings", heading_style))
    for finding in report_data['key_findings']:
        story.append(Paragraph(f"• {finding}", normal_style))
    story.append(Spacer(1, 12))

    # Facts
    story.append(Paragraph("Supporting Facts", heading_style))
    for i, fact in enumerate(report_data['facts'], 1):
        story.append(Paragraph(f"{i}. {fact['source']}", styles['Heading3']))
        if fact.get('excerpt'):
            story.append(Paragraph(f"Excerpt: {fact['excerpt']}", normal_style))
        if fact.get('url'):
            story.append(Paragraph(f"URL: {fact['url']}", normal_style))
        story.append(Spacer(1, 6))

    # Generated at
    story.append(Spacer(1, 12))
    generated_at = report_data.get('generated_at', datetime.datetime.now().isoformat())
    if isinstance(generated_at, str):
        generated_at = generated_at
    else:
        generated_at = generated_at.isoformat()
    story.append(Paragraph(f"Report generated at: {generated_at}", styles['Italic']))

    doc.build(story)
    return filename
