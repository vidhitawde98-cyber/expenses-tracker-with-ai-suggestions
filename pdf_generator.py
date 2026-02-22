from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
from collections import defaultdict
import io
import base64

class NumberedCanvas(canvas.Canvas):
    """Custom canvas for page numbers and headers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        self.drawRightString(7.5*inch, 0.5*inch, f"Page {self._pageNumber} of {page_count}")

def format_amount(amount):
    """Format amount with Rs. prefix"""
    return f"Rs. {int(amount):,}"

def create_cover_page(story, username):
    """Create an impressive cover page"""
    styles = getSampleStyleSheet()
    
    # Add some space from top
    story.append(Spacer(1, 1.5*inch))
    
    # Main title with color
    cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontSize=42,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=50
    )
    story.append(Paragraph("EXPENSE ANALYSIS", cover_title))
    story.append(Paragraph("FINANCIAL REPORT", cover_title))
    
    story.append(Spacer(1, 0.5*inch))
    
    # Decorative line
    line_data = [['', '', '']]
    line_table = Table(line_data, colWidths=[2*inch, 2.5*inch, 2*inch])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (1, 0), (1, 0), 3, colors.HexColor('#667eea')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    story.append(line_table)
    
    story.append(Spacer(1, 0.5*inch))
    
    # Subtitle
    cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontSize=18,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph(f"Prepared for: {username.upper()}", cover_subtitle))
    
    # Date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.grey,
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", date_style))
    
    story.append(Spacer(1, 2*inch))
    
    # Confidential notice
    conf_style = ParagraphStyle(
        'Confidential',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#dc3545'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("CONFIDENTIAL - FOR YOUR EYES ONLY", conf_style))
    
    story.append(PageBreak())

def create_executive_summary(story, expenses):
    """Create executive summary page"""
    styles = getSampleStyleSheet()
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#198754'),
        spaceAfter=20,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        borderWidth=2,
        borderColor=colors.HexColor('#198754'),
        borderPadding=10,
        backColor=colors.HexColor('#f0f9f4')
    )
    
    story.append(Paragraph("EXECUTIVE SUMMARY", heading_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Calculate metrics
    total_expenses = sum(exp['amount'] for exp in expenses)
    avg_transaction = total_expenses / len(expenses) if expenses else 0
    
    category_totals = defaultdict(float)
    monthly_totals = defaultdict(float)
    
    for exp in expenses:
        category_totals[exp['category']] += exp['amount']
        month = exp['date'].strftime('%Y-%m')
        monthly_totals[month] += exp['amount']
    
    highest_category = max(category_totals.items(), key=lambda x: x[1]) if category_totals else ("None", 0)
    
    # Key metrics in colored boxes
    metrics_data = [
        ['Total Spending', format_amount(total_expenses), 'Your complete expenditure'],
        ['Transactions', str(len(expenses)), 'Number of recorded expenses'],
        ['Average/Transaction', format_amount(avg_transaction), 'Mean spending per entry'],
        ['Top Category', highest_category[0], format_amount(highest_category[1]) + ' spent'],
        ['Reporting Period', f"{len(monthly_totals)} months", 'Data coverage span']
    ]
    
    for metric in metrics_data:
        metric_table = Table([[metric[0], metric[1]]], colWidths=[3*inch, 3.5*inch])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#0d6efd')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#e7f1ff')),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#0d6efd')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 12),
            ('FONTSIZE', (1, 0), (1, 0), 18),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#0d6efd'))
        ]))
        story.append(metric_table)
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())

def create_monthly_analysis(story, expenses):
    """Create month-by-month analysis"""
    styles = getSampleStyleSheet()
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#dc3545'),
        spaceAfter=20,
        fontName='Helvetica-Bold',
        borderWidth=2,
        borderColor=colors.HexColor('#dc3545'),
        borderPadding=10,
        backColor=colors.HexColor('#fff0f0')
    )
    
    story.append(Paragraph("MONTHLY BREAKDOWN ANALYSIS", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Group by month
    monthly_data = defaultdict(lambda: {'total': 0, 'count': 0, 'categories': defaultdict(float)})
    
    for exp in expenses:
        month = exp['date'].strftime('%B %Y')
        monthly_data[month]['total'] += exp['amount']
        monthly_data[month]['count'] += 1
        monthly_data[month]['categories'][exp['category']] += exp['amount']
    
    # Create table
    table_data = [['Month', 'Total Spent', 'Transactions', 'Avg/Transaction', 'Top Category']]
    
    for month in sorted(monthly_data.keys(), reverse=True):
        data = monthly_data[month]
        avg = data['total'] / data['count']
        top_cat = max(data['categories'].items(), key=lambda x: x[1])
        
        table_data.append([
            month,
            format_amount(data['total']),
            str(data['count']),
            format_amount(avg),
            f"{top_cat[0]} ({format_amount(top_cat[1])})"
        ])
    
    monthly_table = Table(table_data, colWidths=[1.5*inch, 1.3*inch, 1*inch, 1.2*inch, 1.5*inch])
    monthly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')])
    ]))
    story.append(monthly_table)
    story.append(PageBreak())

def create_pdf_report(expenses, username, category_chart=None, trend_chart=None):
    """Generate premium PDF expense report"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=0.75*inch, 
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Cover page
    create_cover_page(story, username)
    
    if expenses:
        # Executive summary
        create_executive_summary(story, expenses)
        
        # Monthly analysis
        create_monthly_analysis(story, expenses)
        
        # Category breakdown with enhanced styling
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#198754'),
            spaceAfter=20,
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=colors.HexColor('#198754'),
            borderPadding=10,
            backColor=colors.HexColor('#f0f9f4')
        )
        
        story.append(Paragraph("CATEGORY ANALYSIS", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        category_totals = defaultdict(float)
        for exp in expenses:
            category_totals[exp['category']] += exp['amount']
        
        total = sum(category_totals.values())
        
        category_data = [['Rank', 'Category', 'Amount', 'Percentage', 'Status']]
        for idx, (category, amount) in enumerate(sorted(category_totals.items(), key=lambda x: x[1], reverse=True), 1):
            percentage = (amount / total) * 100
            if percentage > 30:
                status = 'HIGH'
            elif percentage > 20:
                status = 'MEDIUM'
            else:
                status = 'LOW'
            
            category_data.append([
                str(idx),
                category,
                format_amount(amount),
                f"{percentage:.1f}%",
                status
            ])
        
        category_table = Table(category_data, colWidths=[0.6*inch, 1.5*inch, 1.5*inch, 1.2*inch, 0.8*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#198754')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f9f4')])
        ]))
        story.append(category_table)
        
        # Add charts
        if category_chart:
            story.append(PageBreak())
            story.append(Paragraph("VISUAL INSIGHTS", heading_style))
            story.append(Spacer(1, 0.3*inch))
            
            chart_data = category_chart.split(',')[1]
            chart_buffer = io.BytesIO(base64.b64decode(chart_data))
            img = Image(chart_buffer, width=6*inch, height=6*inch)
            story.append(img)
        
        # Transaction details
        story.append(PageBreak())
        story.append(Paragraph("TRANSACTION LEDGER", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        sorted_expenses = sorted(expenses, key=lambda x: x['date'], reverse=True)
        
        transaction_data = [['Date', 'Category', 'Amount', 'Notes']]
        for exp in sorted_expenses[:30]:
            transaction_data.append([
                exp['date'].strftime('%Y-%m-%d'),
                exp['category'],
                format_amount(exp['amount']),
                exp.get('note', '-')[:25]
            ])
        
        transaction_table = Table(transaction_data, colWidths=[1.2*inch, 1.3*inch, 1.2*inch, 2.8*inch])
        transaction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        story.append(transaction_table)
    
    # Build with page numbers
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer