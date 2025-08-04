# utils.py
import os
import pandas as pd
import datetime
from database import Database

# For PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not installed. PDF generation will not be available.")
    print("Install with: pip install reportlab")

def export_inventory_csv(db: Database, file_path: str):
    """Dump inventory to CSV."""
    df = pd.DataFrame(db.list_inventory())
    df.to_csv(file_path, index=False)
    return file_path

def export_inventory_excel(db: Database, file_path: str):
    """Export inventory to Excel format."""
    try:
        df = pd.DataFrame(db.list_inventory())
        df.to_excel(file_path, index=False, sheet_name='Inventory')
        return file_path
    except Exception as e:
        raise Exception(f"Failed to export to Excel: {str(e)}")

def import_inventory_csv(db: Database, file_path: str):
    """
    Read CSV with columns barcode,name,price,quantity_in_stock
    and upsert into products table.
    """
    df = pd.read_csv(file_path)
    for _, row in df.iterrows():
        existing = db.get_product_by_barcode(row['barcode'])
        if existing:
            db.update_product(existing['id'], row['name'],
                              float(row['price']), int(row['quantity_in_stock']))
        else:
            db.add_product(row['barcode'], row['name'],
                           float(row['price']), int(row['quantity_in_stock']))
    return len(df)

def import_inventory_excel(db: Database, file_path: str):
    """
    Read Excel file with columns barcode,name,price,quantity_in_stock
    and upsert into products table.
    """
    try:
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            existing = db.get_product_by_barcode(row['barcode'])
            if existing:
                db.update_product(existing['id'], row['name'],
                                float(row['price']), int(row['quantity_in_stock']))
            else:
                db.add_product(row['barcode'], row['name'],
                            float(row['price']), int(row['quantity_in_stock']))
        return len(df)
    except Exception as e:
        raise Exception(f"Failed to import from Excel: {str(e)}")

def generate_txt_receipt(receipt: dict, file_path: str, currency="$"):
    """Write a simple text receipt."""
    with open(file_path, 'w') as f:
        f.write(f"Date: {receipt['timestamp']}\n")
        f.write("-" * 30 + "\n")
        f.write("Item               QTY   Price   Total\n")
        for name, qty, price, line in receipt['items']:
            f.write(f"{name[:15]:15} {qty:3}  {currency}{price:6.2f} {currency}{line:7.2f}\n")
        f.write("-" * 30 + "\n")
        f.write(f"Subtotal:     {currency}{receipt['subtotal']:8.2f}\n")
        f.write(f"Taxed:        {currency}{receipt['taxed']:8.2f}\n")
        f.write(f"Discount:     {currency}{receipt['discount']:8.2f}\n")
        f.write(f"Total:        {currency}{receipt['total']:8.2f}\n")
        
        # Add payment method if available
        if 'payment_method' in receipt:
            f.write(f"Payment:      {receipt['payment_method']}\n")
            
        f.write("-" * 30 + "\n")
        f.write("Thank you for your purchase!\n")
    return file_path


def generate_pdf_receipt(receipt: dict, file_path: str, currency="$"):
    """Generate a PDF receipt using ReportLab."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is not installed. Cannot generate PDF.")
    
    # Create the PDF document
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name='RightAlign',
        parent=styles['Normal'],
        alignment=2,  # 2 is right alignment
    ))
    
    # Add title
    elements.append(Paragraph("Receipt", title_style))
    
    # Add date
    timestamp = receipt['timestamp']
    if isinstance(timestamp, str):
        try:
            # Parse ISO format timestamp
            dt = datetime.datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            date_str = timestamp
    else:
        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    elements.append(Paragraph(f"Date: {date_str}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Create table for items
    data = [["Item", "Quantity", "Price", "Total"]]
    for name, qty, price, line in receipt['items']:
        data.append([name, str(qty), f"{currency}{price:.2f}", f"{currency}{line:.2f}"])
    
    # Add summary rows
    data.append(["" for _ in range(4)])
    data.append(["Subtotal:", "", "", f"{currency}{receipt['subtotal']:.2f}"])
    data.append(["Tax:", "", "", f"{currency}{receipt['taxed'] - receipt['subtotal']:.2f}"])
    data.append(["Discount:", "", "", f"{currency}{receipt['discount']:.2f}"])
    data.append(["Total:", "", "", f"{currency}{receipt['total']:.2f}"])
    
    # Add payment method if available
    if 'payment_method' in receipt:
        data.append(["Payment Method:", receipt['payment_method'], "", ""])
    
    # Create the table
    table = Table(data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])
    
    # Style the table
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (3, 0), 12),
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        ('BACKGROUND', (0, 1), (3, -1), colors.white),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('ALIGN', (1, 1), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, -5), (3, -1), 'Helvetica-Bold'),
    ])
    table.setStyle(table_style)
    
    elements.append(table)
    elements.append(Spacer(1, 0.5 * inch))
    
    # Add thank you message
    elements.append(Paragraph("Thank you for your purchase!", styles['RightAlign']))
    
    # Build the PDF
    doc.build(elements)
    
    return file_path


def generate_sales_report(db: Database, start_date=None, end_date=None, file_path=None, format='csv'):
    """Generate a sales report for a given date range."""
    # Get sales data
    sales = db.list_sales(start_date, end_date)
    
    if not sales:
        return None, "No sales data found for the specified period."
    
    # Create DataFrame
    df = pd.DataFrame(sales)
    
    # Calculate summary statistics
    total_sales = df['total_amount'].sum()
    avg_sale = df['total_amount'].mean()
    num_transactions = len(df)
    
    # Format dates for better readability
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    
    # Create summary dict
    summary = {
        'total_sales': total_sales,
        'average_sale': avg_sale,
        'num_transactions': num_transactions,
        'start_date': start_date or df['date'].min(),
        'end_date': end_date or df['date'].max()
    }
    
    # Export to file if path provided
    if file_path:
        if format.lower() == 'excel':
            df.to_excel(file_path, index=False, sheet_name='Sales')
        else:  # Default to CSV
            df.to_csv(file_path, index=False)
    
    return df, summary


def generate_inventory_report(db: Database, file_path=None, format='csv', low_stock_threshold=10):
    """Generate an inventory report, optionally highlighting low stock items."""
    # Get inventory data
    inventory = db.list_inventory()
    
    if not inventory:
        return None, "No inventory data found."
    
    # Create DataFrame
    df = pd.DataFrame(inventory)
    
    # Calculate summary statistics
    total_items = len(df)
    total_value = (df['price'] * df['quantity_in_stock']).sum()
    low_stock_items = df[df['quantity_in_stock'] <= low_stock_threshold]
    
    # Create summary dict
    summary = {
        'total_items': total_items,
        'total_value': total_value,
        'low_stock_count': len(low_stock_items),
        'low_stock_items': low_stock_items.to_dict('records') if not low_stock_items.empty else []
    }
    
    # Export to file if path provided
    if file_path:
        if format.lower() == 'excel':
            df.to_excel(file_path, index=False, sheet_name='Inventory')
        else:  # Default to CSV
            df.to_csv(file_path, index=False)
    
    return df, summary


def generate_pdf_report(title, data, summary, file_path):
    """Generate a PDF report with data and summary statistics."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is not installed. Cannot generate PDF report.")
    
    # Create the PDF document
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Add date
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Generated: {current_date}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Add summary section
    elements.append(Paragraph("Summary", subtitle_style))
    
    # Create summary table
    summary_data = [["Metric", "Value"]]
    for key, value in summary.items():
        if key not in ['low_stock_items']:  # Skip complex nested data
            if isinstance(value, (int, float)):
                if 'total' in key or 'value' in key or 'sale' in key:
                    formatted_value = f"${value:.2f}"
                else:
                    formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            
            # Format key for display
            display_key = key.replace('_', ' ').title()
            summary_data.append([display_key, formatted_value])
    
    # Create the summary table
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.white),
        ('GRID', (0, 0), (1, -1), 1, colors.black),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Add data section if we have a DataFrame
    if isinstance(data, pd.DataFrame) and not data.empty:
        elements.append(Paragraph("Detailed Data", subtitle_style))
        
        # Convert DataFrame to a list of lists for the table
        table_data = [data.columns.tolist()]
        for _, row in data.iterrows():
            table_data.append([str(x) for x in row.tolist()])
        
        # Create the data table (limit to first 50 rows to avoid huge PDFs)
        max_rows = min(50, len(table_data))
        data_table = Table(table_data[:max_rows], colWidths=None)  # Auto-width
        
        # Style the table
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ])
        data_table.setStyle(table_style)
        
        elements.append(data_table)
        
        # Add note if we limited the rows
        if len(table_data) > max_rows:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph(f"Note: Showing {max_rows} of {len(table_data)-1} rows", 
                                    styles['Italic']))
    
    # Build the PDF
    doc.build(elements)
    
    return file_path
