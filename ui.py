# ui.py
import os
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
import datetime
import logging
from database import Database
from models import CashierSystem, Product
from utils import export_inventory_csv, import_inventory_csv, generate_txt_receipt, generate_pdf_receipt

logger = logging.getLogger("POS_System.UI")

class CashierUI:
    def __init__(self, db: Database, config=None):
        self.db = db
        self.config = config or {"receipt_dir": "receipts", "export_dir": "exports", "theme": "default", "currency": "$"}
        self.sys = CashierSystem(db)
        
        # Initialize main window with ttkbootstrap
        theme = self.config.get("theme", "default")
        # Map our theme names to ttkbootstrap theme names
        bootstrap_themes = {
            "dark": "darkly",
            "light": "cosmo",
            "default": "cosmo"
        }
        bootstrap_theme = bootstrap_themes.get(theme, "cosmo")
        
        # Create the ttkbootstrap window with the appropriate theme
        self.root = ttk.Window(themename=bootstrap_theme)
        self.root.title("Advanced POS System")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)
        
        # Initialize variables
        self.currency = self.config.get("currency", "$")
        self.discount_var = tk.DoubleVar(value=0.0)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_change)
        
        # Build the GUI
        self._build_gui()

    def _set_theme(self, theme_name):
        """Set the application theme using ttkbootstrap"""
        # Map our theme names to ttkbootstrap theme names
        bootstrap_themes = {
            "dark": "darkly",
            "light": "cosmo",
            "default": "cosmo"
        }
        
        # Get the corresponding bootstrap theme
        bootstrap_theme = bootstrap_themes.get(theme_name, "cosmo")
        
        # Change the theme
        style = ttk.Style()
        style.theme_use(bootstrap_theme)
        
        logger.info(f"Applied theme: {theme_name} (bootstrap: {bootstrap_theme})")

    def _build_gui(self):
        """Build the main GUI interface"""
        # Create main frame with ttkbootstrap styling
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self._create_status_bar()
        
        # Create notebook (tabs) with boosted styling
        self.notebook = ttk.Notebook(main_frame, bootstyle="primary")
        self.notebook.pack(expand=True, fill='both')
        
        # --- Tab 1: Scan & Cart ---
        self.frame1 = ttk.Frame(self.notebook)
        self.notebook.add(self.frame1, text="Scan & Sell")
        
        # Create two main sections with boosted styling
        self.left_frame = ttk.Frame(self.frame1, bootstyle="light")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.right_frame = ttk.Frame(self.frame1, bootstyle="light")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5, expand=False, ipadx=10)
        
        # Left section - Scanning and cart
        scan_frame = ttk.LabelFrame(self.left_frame, text="Scan Product", bootstyle="primary")
        scan_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Barcode entry with scan button
        ttk.Label(scan_frame, text="Barcode:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.barcode_var = tk.StringVar()
        barcode_entry = ttk.Entry(scan_frame, textvariable=self.barcode_var, width=20)
        barcode_entry.grid(row=0, column=1, padx=5, pady=5)
        barcode_entry.bind('<Return>', lambda e: self._add_to_cart())
        
        # Scan button with icon (would use an actual icon in production)
        scan_btn = ttk.Button(scan_frame, text="Scan", command=self._simulate_scan, bootstyle="info")
        scan_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Quantity entry
        ttk.Label(scan_frame, text="Quantity:").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.qty_var = tk.IntVar(value=1)
        qty_entry = ttk.Entry(scan_frame, textvariable=self.qty_var, width=5)
        qty_entry.grid(row=0, column=4, padx=5, pady=5)
        
        # Add to cart button
        add_btn = ttk.Button(scan_frame, text="Add to Cart", command=self._add_to_cart, bootstyle="success")
        add_btn.grid(row=0, column=5, padx=5, pady=5)
        
        # Product search
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search Products:").pack(side=tk.LEFT, padx=5)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Cart Treeview with scrollbar
        cart_frame = ttk.LabelFrame(self.left_frame, text="Shopping Cart", bootstyle="primary")
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar
        cart_scroll = ttk.Scrollbar(cart_frame)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        cols = ("Product", "Qty", "Price", "Line Total")
        self.cart_tv = ttk.Treeview(cart_frame, columns=cols, show='headings', height=10, 
                                   yscrollcommand=cart_scroll.set)
        
        # Configure columns
        self.cart_tv.column("Product", width=200, anchor=tk.W)
        self.cart_tv.column("Qty", width=50, anchor=tk.CENTER)
        self.cart_tv.column("Price", width=100, anchor=tk.E)
        self.cart_tv.column("Line Total", width=100, anchor=tk.E)
        
        for c in cols:
            self.cart_tv.heading(c, text=c)
        
        self.cart_tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_scroll.config(command=self.cart_tv.yview)
        
        # Add right-click menu to cart
        self._add_cart_context_menu()
        
        # Cart buttons
        cart_btn_frame = ttk.Frame(self.left_frame)
        cart_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(cart_btn_frame, text="Remove Selected", command=self._remove_selected, bootstyle="danger").pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btn_frame, text="Clear Cart", command=self._clear_cart, bootstyle="warning").pack(side=tk.LEFT, padx=5)
        
        # Right section - Checkout panel
        checkout_frame = ttk.LabelFrame(self.right_frame, text="Checkout", bootstyle="primary")
        checkout_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Subtotal display
        ttk.Label(checkout_frame, text="Subtotal:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        self.subtotal_var = tk.StringVar(value=f"{self.currency}0.00")
        ttk.Label(checkout_frame, textvariable=self.subtotal_var, font=("Arial", 12)).grid(row=0, column=1, padx=5, pady=10, sticky=tk.E)
        
        # Discount entry
        ttk.Label(checkout_frame, text=f"Discount ({self.currency}):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        discount_entry = ttk.Entry(checkout_frame, textvariable=self.discount_var, width=10)
        discount_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.E)
        
        # Calculate button
        ttk.Button(checkout_frame, text="Calculate Total", command=self._calculate_total, bootstyle="success").grid(row=2, column=0, columnspan=2, padx=5, pady=10)
        
        # Total display
        ttk.Separator(checkout_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        ttk.Label(checkout_frame, text="TOTAL:", font=("Arial", 12, "bold")).grid(row=4, column=0, padx=5, pady=10, sticky=tk.W)
        self.total_var = tk.StringVar(value=f"{self.currency}0.00")
        ttk.Label(checkout_frame, textvariable=self.total_var, font=("Arial", 14, "bold")).grid(row=4, column=1, padx=5, pady=10, sticky=tk.E)
        
        # Payment method
        ttk.Label(checkout_frame, text="Payment Method:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.payment_var = tk.StringVar(value="Cash")
        payment_combo = ttk.Combobox(checkout_frame, textvariable=self.payment_var, state="readonly")
        payment_combo["values"] = ("Cash", "Credit Card", "Debit Card", "Mobile Payment")
        payment_combo.grid(row=5, column=1, padx=5, pady=5, sticky=tk.E)
        
        # Checkout button
        checkout_btn = ttk.Button(checkout_frame, text="CHECKOUT", command=self._checkout, bootstyle="success-outline")
        checkout_btn.grid(row=6, column=0, columnspan=2, padx=5, pady=20, sticky=tk.EW)
        
        # Receipt options
        receipt_frame = ttk.LabelFrame(self.right_frame, text="Receipt Options", bootstyle="secondary")
        receipt_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.receipt_type_var = tk.StringVar(value="txt")
        ttk.Radiobutton(receipt_frame, text="Text Receipt", variable=self.receipt_type_var, value="txt").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(receipt_frame, text="PDF Receipt", variable=self.receipt_type_var, value="pdf").pack(anchor=tk.W, padx=5, pady=2)
        
        # --- Tab 2: Inventory Management ---
        frame2 = ttk.Frame(self.notebook)
        self.notebook.add(frame2, text="Inventory Management")
        
        # Split into left and right panes
        inv_left_frame = ttk.Frame(frame2, bootstyle="light")
        inv_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        inv_right_frame = ttk.Frame(frame2, bootstyle="light")
        inv_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5, ipadx=10)
        
        # Inventory search
        search_frame = ttk.LabelFrame(inv_left_frame, text="Search Inventory", bootstyle="primary")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5, pady=5)
        self.inv_search_var = tk.StringVar()
        self.inv_search_var.trace("w", self._on_inventory_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.inv_search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Inventory Treeview with scrollbar
        inv_tree_frame = ttk.Frame(inv_left_frame)
        inv_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbars
        inv_y_scroll = ttk.Scrollbar(inv_tree_frame)
        inv_y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        inv_x_scroll = ttk.Scrollbar(inv_tree_frame, orient=tk.HORIZONTAL)
        inv_x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create treeview
        cols2 = ("ID", "Barcode", "Name", "Price", "Stock", "Status")
        self.inv_tv = ttk.Treeview(inv_tree_frame, columns=cols2, show='headings', height=15,
                                  yscrollcommand=inv_y_scroll.set,
                                  xscrollcommand=inv_x_scroll.set)
        
        # Configure columns
        self.inv_tv.column("ID", width=50, anchor=tk.CENTER)
        self.inv_tv.column("Barcode", width=120, anchor=tk.W)
        self.inv_tv.column("Name", width=200, anchor=tk.W)
        self.inv_tv.column("Price", width=80, anchor=tk.E)
        self.inv_tv.column("Stock", width=80, anchor=tk.CENTER)
        self.inv_tv.column("Status", width=100, anchor=tk.CENTER)
        
        for c in cols2:
            self.inv_tv.heading(c, text=c, command=lambda _c=c: self._treeview_sort_column(self.inv_tv, _c, False))
        
        self.inv_tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_y_scroll.config(command=self.inv_tv.yview)
        inv_x_scroll.config(command=self.inv_tv.xview)
        
        # Add right-click menu to inventory
        self._add_inventory_context_menu()
        
        # Bind double-click to edit
        self.inv_tv.bind("<Double-1>", self._on_inventory_double_click)
        
        # Inventory action buttons
        inv_btn_frame = ttk.Frame(inv_left_frame)
        inv_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(inv_btn_frame, text="Add New Product", command=self._show_add_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(inv_btn_frame, text="Edit Selected", command=self._edit_selected_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(inv_btn_frame, text="Delete Selected", command=self._delete_selected_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(inv_btn_frame, text="Refresh", command=self._refresh_inventory).pack(side=tk.LEFT, padx=5)
        
        # Import / Export frame
        imp_exp_frame = ttk.LabelFrame(inv_left_frame, text="Import / Export", bootstyle="primary")
        imp_exp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(imp_exp_frame, text="Export to CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(imp_exp_frame, text="Import from CSV", command=self._import_csv).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(imp_exp_frame, text="Export to Excel", command=self._export_excel).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(imp_exp_frame, text="Import from Excel", command=self._import_excel).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Right side - Product form
        form_frame = ttk.LabelFrame(inv_right_frame, text="Product Details", bootstyle="primary")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Form fields
        labels = ["Barcode", "Name", "Price ($)", "Quantity", "Reorder Level"]
        self.inv_vars = [tk.StringVar(), tk.StringVar(), tk.DoubleVar(), tk.IntVar(), tk.IntVar(value=10)]
        
        for i, txt in enumerate(labels):
            ttk.Label(form_frame, text=txt + ":").grid(row=i, column=0, padx=5, pady=10, sticky=tk.E)
            ttk.Entry(form_frame, textvariable=self.inv_vars[i], width=20).grid(row=i, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Form buttons
        form_btn_frame = ttk.Frame(form_frame)
        form_btn_frame.grid(row=len(labels), column=0, columnspan=2, pady=15)
        
        ttk.Button(form_btn_frame, text="Save", command=self._save_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_btn_frame, text="Clear", command=self._clear_form).pack(side=tk.LEFT, padx=5)
        
        # Initialize inventory
        self._refresh_inventory()
        
        # --- Tab 3: Sales Reports ---
        frame3 = ttk.Frame(self.notebook, bootstyle="light")
        self.notebook.add(frame3, text="Sales Reports")
        
        # Date range selection
        date_frame = ttk.LabelFrame(frame3, text="Date Range", bootstyle="primary")
        date_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(date_frame, text="From:").grid(row=0, column=0, padx=5, pady=5)
        self.date_from_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_from_var, width=12).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(date_frame, text="Select", command=lambda: self._select_date(self.date_from_var)).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(date_frame, text="To:").grid(row=0, column=3, padx=5, pady=5)
        self.date_to_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.date_to_var, width=12).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(date_frame, text="Select", command=lambda: self._select_date(self.date_to_var)).grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(date_frame, text="Generate Report", command=self._generate_sales_report).grid(row=0, column=6, padx=20, pady=5)
        
        # Sales report display
        report_frame = ttk.LabelFrame(frame3, text="Sales Report", bootstyle="primary")
        report_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbars
        report_y_scroll = ttk.Scrollbar(report_frame)
        report_y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview for sales
        sales_cols = ("ID", "Date", "Time", "Items", "Total", "Payment Method")
        self.sales_tv = ttk.Treeview(report_frame, columns=sales_cols, show='headings', height=10,
                                    yscrollcommand=report_y_scroll.set)
        
        # Configure columns
        self.sales_tv.column("ID", width=50, anchor=tk.CENTER)
        self.sales_tv.column("Date", width=100, anchor=tk.CENTER)
        self.sales_tv.column("Time", width=100, anchor=tk.CENTER)
        self.sales_tv.column("Items", width=80, anchor=tk.CENTER)
        self.sales_tv.column("Total", width=100, anchor=tk.E)
        self.sales_tv.column("Payment Method", width=150, anchor=tk.CENTER)
        
        for c in sales_cols:
            self.sales_tv.heading(c, text=c)
        
        self.sales_tv.pack(fill=tk.BOTH, expand=True)
        report_y_scroll.config(command=self.sales_tv.yview)
        
        # Bind double-click to view sale details
        self.sales_tv.bind("<Double-1>", self._view_sale_details)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(frame3, text="Summary", bootstyle="primary")
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Summary statistics
        ttk.Label(summary_frame, text="Total Sales:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.total_sales_var = tk.StringVar(value=f"{self.currency}0.00")
        ttk.Label(summary_frame, textvariable=self.total_sales_var, font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(summary_frame, text="Number of Transactions:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.num_trans_var = tk.StringVar(value="0")
        ttk.Label(summary_frame, textvariable=self.num_trans_var, font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(summary_frame, text="Average Sale:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.avg_sale_var = tk.StringVar(value=f"{self.currency}0.00")
        ttk.Label(summary_frame, textvariable=self.avg_sale_var, font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(summary_frame, text="Best Selling Item:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.best_item_var = tk.StringVar(value="None")
        ttk.Label(summary_frame, textvariable=self.best_item_var, font=("Arial", 10, "bold")).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Export report button
        ttk.Button(summary_frame, text="Export Report", bootstyle="success", command=self._export_sales_report).grid(row=2, column=0, columnspan=4, pady=10)
        
        # Force update to ensure widgets are displayed
        self.root.update_idletasks()

    def _create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Inventory", command=self._export_csv)
        file_menu.add_command(label="Import Inventory", command=self._import_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Default", command=lambda: self._change_theme("default"))
        theme_menu.add_command(label="Light", command=lambda: self._change_theme("light"))
        theme_menu.add_command(label="Dark", command=lambda: self._change_theme("dark"))
        
        # Reports menu
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        reports_menu.add_command(label="Daily Sales", command=self._show_daily_sales)
        reports_menu.add_command(label="Inventory Status", command=self._show_inventory_status)
        reports_menu.add_command(label="Low Stock Alert", command=self._show_low_stock)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_status_bar(self):
        """Create status bar at the bottom of the window"""
        self.status_bar = ttk.Frame(self.root, bootstyle="secondary")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var, padding=(5, 2), bootstyle="inverse-secondary")
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Date/time display
        self.datetime_var = tk.StringVar()
        datetime_label = ttk.Label(self.status_bar, textvariable=self.datetime_var, padding=(5, 2), bootstyle="inverse-secondary")
        datetime_label.pack(side=tk.RIGHT)
        
        # Start datetime updates
        self._update_datetime()
        
    def _show_daily_sales(self):
        """Show daily sales report"""
        try:
            # Create date selection dialog
            date_dialog = tk.Toplevel(self.root)
            date_dialog.title("Select Date Range")
            date_dialog.geometry("300x200")
            date_dialog.resizable(False, False)
            date_dialog.transient(self.root)
            date_dialog.grab_set()
            
            ttk.Label(date_dialog, text="Select date range for sales report:").pack(pady=10)
            
            # Date range frame
            date_frame = ttk.Frame(date_dialog)
            date_frame.pack(pady=5, fill=tk.X, padx=10)
            
            # Start date
            ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky=tk.W, pady=5)
            start_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
            start_entry = ttk.Entry(date_frame, textvariable=start_date)
            start_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            # End date
            ttk.Label(date_frame, text="End Date:").grid(row=1, column=0, sticky=tk.W, pady=5)
            end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
            end_entry = ttk.Entry(date_frame, textvariable=end_date)
            end_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Format options
            format_frame = ttk.Frame(date_dialog)
            format_frame.pack(pady=5, fill=tk.X, padx=10)
            ttk.Label(format_frame, text="Export Format:").pack(side=tk.LEFT)
            format_var = tk.StringVar(value="pdf")
            ttk.Radiobutton(format_frame, text="PDF", variable=format_var, value="pdf").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="Excel", variable=format_var, value="excel").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="CSV", variable=format_var, value="csv").pack(side=tk.LEFT)
            
            # Buttons
            btn_frame = ttk.Frame(date_dialog)
            btn_frame.pack(pady=10, fill=tk.X, padx=10)
            
            def generate_report():
                try:
                    start = start_date.get()
                    end = end_date.get()
                    report_format = format_var.get()
                    
                    # Validate dates
                    datetime.strptime(start, "%Y-%m-%d")
                    datetime.strptime(end, "%Y-%m-%d")
                    
                    # Generate report based on format
                    export_dir = self.config.get('export', {}).get('default_dir', 'exports')
                    if report_format == "pdf":
                        from utils import generate_pdf_report
                        sales_data = self.db.get_sales_by_date_range(start, end)
                        file_path = generate_pdf_report(sales_data, "Sales Report", start, end, export_dir)
                    elif report_format == "excel":
                        from utils import generate_sales_report
                        file_path = generate_sales_report(self.db, start, end, "excel", export_dir)
                    else:  # CSV
                        from utils import generate_sales_report
                        file_path = generate_sales_report(self.db, start, end, "csv", export_dir)
                    
                    date_dialog.destroy()
                    messagebox.showinfo("Report Generated", f"Sales report has been generated and saved to:\n{file_path}")
                    
                except ValueError as e:
                    messagebox.showerror("Invalid Date", "Please enter dates in YYYY-MM-DD format")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            
            ttk.Button(btn_frame, text="Generate", command=generate_report).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=date_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open sales report dialog: {str(e)}")
    
    def _show_inventory_status(self):
        """Show inventory status report"""
        try:
            # Create format selection dialog
            format_dialog = tk.Toplevel(self.root)
            format_dialog.title("Inventory Report")
            format_dialog.geometry("300x150")
            format_dialog.resizable(False, False)
            format_dialog.transient(self.root)
            format_dialog.grab_set()
            
            ttk.Label(format_dialog, text="Generate inventory status report:").pack(pady=10)
            
            # Format options
            format_frame = ttk.Frame(format_dialog)
            format_frame.pack(pady=5, fill=tk.X, padx=10)
            ttk.Label(format_frame, text="Export Format:").pack(side=tk.LEFT)
            format_var = tk.StringVar(value="pdf")
            ttk.Radiobutton(format_frame, text="PDF", variable=format_var, value="pdf").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="Excel", variable=format_var, value="excel").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="CSV", variable=format_var, value="csv").pack(side=tk.LEFT)
            
            # Buttons
            btn_frame = ttk.Frame(format_dialog)
            btn_frame.pack(pady=10, fill=tk.X, padx=10)
            
            def generate_report():
                try:
                    report_format = format_var.get()
                    export_dir = self.config.get('export', {}).get('default_dir', 'exports')
                    
                    # Generate report based on format
                    if report_format == "pdf":
                        from utils import generate_pdf_report
                        inventory_data = self.db.list_inventory()
                        file_path = generate_pdf_report(inventory_data, "Inventory Status", None, None, export_dir)
                    else:  # Excel or CSV
                        from utils import generate_inventory_report
                        file_path = generate_inventory_report(self.db, report_format, export_dir)
                    
                    format_dialog.destroy()
                    messagebox.showinfo("Report Generated", f"Inventory report has been generated and saved to:\n{file_path}")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            
            ttk.Button(btn_frame, text="Generate", command=generate_report).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=format_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open inventory report dialog: {str(e)}")
    
    def _show_low_stock(self):
        """Show low stock alert report"""
        try:
            # Create threshold selection dialog
            threshold_dialog = tk.Toplevel(self.root)
            threshold_dialog.title("Low Stock Alert")
            threshold_dialog.geometry("300x180")
            threshold_dialog.resizable(False, False)
            threshold_dialog.transient(self.root)
            threshold_dialog.grab_set()
            
            ttk.Label(threshold_dialog, text="Generate low stock alert report:").pack(pady=10)
            
            # Threshold setting
            threshold_frame = ttk.Frame(threshold_dialog)
            threshold_frame.pack(pady=5, fill=tk.X, padx=10)
            ttk.Label(threshold_frame, text="Stock Threshold:").grid(row=0, column=0, sticky=tk.W, pady=5)
            threshold_var = tk.StringVar(value=str(self.config.get('low_stock_threshold', 10)))
            threshold_entry = ttk.Entry(threshold_frame, textvariable=threshold_var, width=10)
            threshold_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Format options
            format_frame = ttk.Frame(threshold_dialog)
            format_frame.pack(pady=5, fill=tk.X, padx=10)
            ttk.Label(format_frame, text="Export Format:").pack(side=tk.LEFT)
            format_var = tk.StringVar(value="pdf")
            ttk.Radiobutton(format_frame, text="PDF", variable=format_var, value="pdf").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="Excel", variable=format_var, value="excel").pack(side=tk.LEFT)
            ttk.Radiobutton(format_frame, text="CSV", variable=format_var, value="csv").pack(side=tk.LEFT)
            
            # Buttons
            btn_frame = ttk.Frame(threshold_dialog)
            btn_frame.pack(pady=10, fill=tk.X, padx=10)
            
            def generate_report():
                try:
                    threshold = int(threshold_var.get())
                    report_format = format_var.get()
                    export_dir = self.config.get('export', {}).get('default_dir', 'exports')
                    
                    # Get low stock items
                    low_stock_items = self.db.get_low_stock_products(threshold)
                    
                    if not low_stock_items:
                        threshold_dialog.destroy()
                        messagebox.showinfo("No Low Stock", "There are no items below the specified threshold.")
                        return
                    
                    # Generate report based on format
                    if report_format == "pdf":
                        from utils import generate_pdf_report
                        file_path = generate_pdf_report(low_stock_items, "Low Stock Alert", None, None, export_dir)
                    else:  # Excel or CSV
                        from utils import generate_inventory_report
                        file_path = generate_inventory_report(self.db, report_format, export_dir, low_stock_only=True, threshold=threshold)
                    
                    threshold_dialog.destroy()
                    messagebox.showinfo("Report Generated", f"Low stock report has been generated and saved to:\n{file_path}")
                    
                except ValueError:
                    messagebox.showerror("Invalid Threshold", "Please enter a valid number for the threshold")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            
            ttk.Button(btn_frame, text="Generate", command=generate_report).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=threshold_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open low stock report dialog: {str(e)}")
    
    def _show_about(self):
        """Show about dialog"""
        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About")
        about_dialog.geometry("400x300")
        about_dialog.resizable(False, False)
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        
        # App info
        app_name = self.config.get('app_name', 'Advanced POS System')
        version = self.config.get('version', '1.0.0')
        
        # Create content
        content_frame = ttk.Frame(about_dialog, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(content_frame, text=app_name, font=("Helvetica", 16, "bold")).pack(pady=(0, 10))
        ttk.Label(content_frame, text=f"Version {version}").pack(pady=(0, 20))
        
        description = (
            "A comprehensive point-of-sale system with inventory management, \n"
            "sales tracking, and reporting capabilities."
        )
        ttk.Label(content_frame, text=description, justify=tk.CENTER).pack(pady=(0, 20))
        
        # Credits
        ttk.Label(content_frame, text="Developed by: Your Company", justify=tk.CENTER).pack()
        ttk.Label(content_frame, text="© 2025 All Rights Reserved", justify=tk.CENTER).pack()
        
        # Close button
        ttk.Button(content_frame, text="Close", command=about_dialog.destroy).pack(pady=20)
        
    def _change_theme(self, theme_name):
        """Change the application theme"""
        try:
            # Update config
            if 'ui' in self.config:
                self.config['ui']['theme'] = theme_name
            else:
                self.config['ui'] = {'theme': theme_name}
            
            # Show message about restart
            messagebox.showinfo("Theme Change", "The theme will be applied after restarting the application.")
            
            # Update status
            self._update_status(f"Theme will be changed to {theme_name} after restart")
            logging.getLogger('POS_System.UI').info(f"Theme will be changed to: {theme_name} after restart")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change theme: {str(e)}")
    
    def _update_datetime(self):
        """Update the datetime display in status bar"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_var.set(now)
        self.root.after(1000, self._update_datetime)
    
    def _update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        logger.info(message)

    def _on_inventory_search(self, *args):
        """Filter inventory items based on search input"""
        search_term = self.inv_search_var.get().lower()
        # Clear the treeview
        for item in self.inv_tv.get_children():
            self.inv_tv.delete(item)
            
        # Repopulate with filtered items
        for product in self.inventory:
            # Check if search term is in product name, barcode, or category
            if (search_term in product.name.lower() or 
                search_term in str(product.barcode).lower() or 
                search_term in product.category.lower()):
                self.inv_tv.insert("", tk.END, values=(
                    product.id,
                    product.barcode,
                    product.name,
                    product.category,
                    f"${product.price:.2f}",
                    product.stock
                ))
    
    def _edit_selected_product(self):
        """Edit the selected product in inventory"""
        selected = self.inv_tv.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a product to edit")
            return
            
        # Get the product ID from the selected item
        item_id = self.inv_tv.item(selected[0], 'values')[0]
        
        # Find the product in inventory
        product = None
        for p in self.inventory:
            if p.id == int(item_id):
                product = p
                break
                
        if not product:
            messagebox.showerror("Error", "Product not found")
            return
            
        # Populate the form with product details
        self.product_id_var.set(product.id)
        self.barcode_var.set(product.barcode)
        self.name_var.set(product.name)
        self.category_var.set(product.category)
        self.price_var.set(f"{product.price:.2f}")
        self.stock_var.set(product.stock)
        
        # Switch to inventory tab if not already there
        self.notebook.select(1)
        
        # Update status
        self._update_status(f"Editing product: {product.name}")
    
    def _delete_selected_product(self):
        """Delete the selected product from inventory"""
        selected = self.inv_tv.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return
            
        # Get the product ID from the selected item
        item_id = self.inv_tv.item(selected[0], 'values')[0]
        product_name = self.inv_tv.item(selected[0], 'values')[2]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {product_name}?"):
            return
            
        try:
            # Delete from database
            self.db.delete_product(int(item_id))
            
            # Refresh inventory
            self._refresh_inventory()
            
            # Update status
            self._update_status(f"Product deleted: {product_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete product: {str(e)}")
    
    def _adjust_stock(self):
        """Adjust stock level for the selected product"""
        selected = self.inv_tv.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a product to adjust stock")
            return
            
        # Get the product ID and current stock from the selected item
        values = self.inv_tv.item(selected[0], 'values')
        item_id = values[0]
        product_name = values[2]
        current_stock = int(values[5])
        
        # Create a simple dialog to adjust stock
        dialog = tk.Toplevel(self.root)
        dialog.title("Adjust Stock")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Current Stock: {current_stock}").pack(pady=10)
        
        # Frame for entry and buttons
        frame = ttk.Frame(dialog)
        frame.pack(pady=10)
        
        ttk.Label(frame, text="New Stock:").grid(row=0, column=0, padx=5, pady=5)
        stock_var = tk.IntVar(value=current_stock)
        stock_entry = ttk.Entry(frame, textvariable=stock_var, width=10)
        stock_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Buttons frame
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def save_stock():
            try:
                new_stock = stock_var.get()
                if new_stock < 0:
                    messagebox.showwarning("Warning", "Stock cannot be negative")
                    return
                    
                # Update in database
                self.db.update_product_stock(int(item_id), new_stock)
                
                # Refresh inventory
                self._refresh_inventory()
                
                # Update status
                self._update_status(f"Stock updated for {product_name}: {current_stock} → {new_stock}")
                
                # Close dialog
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update stock: {str(e)}")
        
        ttk.Button(btn_frame, text="Save", command=save_stock).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Focus on entry
        stock_entry.focus_set()
        stock_entry.select_range(0, tk.END)
    
    def _on_inventory_double_click(self, event):
        """Handle double-click on inventory item"""
        # Get the selected item
        selected = self.inv_tv.selection()
        if not selected:
            return
            
        # Edit the selected product
        self._edit_selected_product()
    
    def _show_add_product(self):
        """Show the add product form"""
        # Clear the form
        self._clear_form()
        
        # Switch to inventory tab if not already there
        self.notebook.select(1)
        
        # Update status
        self._update_status("Adding new product")
    
    def _add_cart_context_menu(self):
        """Add right-click context menu to cart treeview"""
        self.cart_context_menu = tk.Menu(self.root, tearoff=0)
        self.cart_context_menu.add_command(label="Remove Item", command=self._remove_selected)
        self.cart_context_menu.add_command(label="Edit Quantity", command=self._edit_cart_quantity)
        self.cart_context_menu.add_separator()
        self.cart_context_menu.add_command(label="Clear Cart", command=self._clear_cart)
        
        # Bind right-click to show context menu
        self.cart_tv.bind("<Button-3>", self._show_cart_context_menu)
    
    def _show_cart_context_menu(self, event):
        """Show context menu on right-click"""
        # Select row under mouse
        iid = self.cart_tv.identify_row(event.y)
        if iid:
            self.cart_tv.selection_set(iid)
            self.cart_context_menu.post(event.x_root, event.y_root)
    
    def _add_inventory_context_menu(self):
        """Add right-click context menu to inventory treeview"""
        self.inv_context_menu = tk.Menu(self.root, tearoff=0)
        self.inv_context_menu.add_command(label="Edit Product", command=self._edit_selected_product)
        self.inv_context_menu.add_command(label="Delete Product", command=self._delete_selected_product)
        self.inv_context_menu.add_separator()
        self.inv_context_menu.add_command(label="Adjust Stock", command=self._adjust_stock)
        
        # Bind right-click to show context menu
        self.inv_tv.bind("<Button-3>", self._show_inv_context_menu)
    
    def _show_inv_context_menu(self, event):
        """Show inventory context menu on right-click"""
        # Select row under mouse
        iid = self.inv_tv.identify_row(event.y)
        if iid:
            self.inv_tv.selection_set(iid)
            self.inv_context_menu.post(event.x_root, event.y_root)
    
    def _on_search_change(self, *args):
        """Filter products in cart view based on search term"""
        search_term = self.search_var.get().lower()
        if not search_term:
            return
        
        try:
            # Search products and show in a dropdown or list
            results = self.db.search_products(search_term)
            if results:
                self._show_search_results(results)
        except Exception as e:
            self._update_status(f"Search error: {str(e)}")
    
    def _show_search_results(self, results):
        """Display search results in a popup"""
        popup = tk.Toplevel(self.root)
        popup.title("Search Results")
        popup.geometry("400x300")
        popup.transient(self.root)
        
        # Create treeview for results
        cols = ("Barcode", "Name", "Price", "Stock")
        tv = ttk.Treeview(popup, columns=cols, show='headings', height=10)
        
        for c in cols:
            tv.heading(c, text=c)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(popup, orient="vertical", command=tv.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tv.configure(yscrollcommand=scrollbar.set)
        tv.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Add results to treeview
        for row in results:
            tv.insert("", "end", iid=row['id'], values=(
                row['barcode'], row['name'], f"${row['price']:.2f}", row['quantity_in_stock']
            ))
        
        # Bind double-click to select product
        tv.bind("<Double-1>", lambda e: self._select_search_result(tv, popup))
        
        # Add button frame
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Select", 
                  command=lambda: self._select_search_result(tv, popup)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", 
                  command=popup.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _select_search_result(self, tv, popup):
        """Handle selection from search results"""
        selected_id = tv.selection()
        if not selected_id:
            return
        
        # Get product details and set to barcode field
        row = self.db.get_product_by_id(int(selected_id[0]))
        if row:
            self.barcode_var.set(row['barcode'])
            popup.destroy()
    
    def _simulate_scan(self):
        """Simulate barcode scanning (in a real app, would use camera/scanner)"""
        # In a real implementation, this would use a barcode scanner or camera
        # For demo purposes, just show a dialog to select a product
        results = self.db.list_inventory()
        if results:
            self._show_search_results(results)
        else:
            messagebox.showinfo("Scan", "No products in inventory to scan")
    
    def _add_to_cart(self):
        """Add product to cart based on barcode and quantity"""
        bc = self.barcode_var.get().strip()
        qt = self.qty_var.get()
        
        if not bc:
            messagebox.showwarning("Input Error", "Please enter a barcode")
            return
        
        if qt <= 0:
            messagebox.showwarning("Input Error", "Quantity must be greater than zero")
            return
        
        try:
            # Add to cart and update UI
            prod, qty = self.sys.scan_and_add(bc, qt)
            
            # Check if item already in cart (update instead of insert)
            existing = self.cart_tv.exists(prod.id)
            if existing:
                # Update existing item
                current_values = self.cart_tv.item(prod.id, 'values')
                new_qty = int(current_values[1]) + qty
                new_total = prod.price * new_qty
                self.cart_tv.item(prod.id, values=(
                    prod.name, new_qty, f"${prod.price:.2f}", f"${new_total:.2f}"
                ))
            else:
                # Insert new item
                self.cart_tv.insert("", "end", iid=prod.id, values=(
                    prod.name, qty, f"${prod.price:.2f}", f"${prod.price*qty:.2f}"
                ))
            
            # Clear barcode field and reset quantity to 1
            self.barcode_var.set("")
            self.qty_var.set(1)
            
            # Update subtotal
            self._update_cart_total()
            
            # Update status
            self._update_status(f"Added {qty} x {prod.name} to cart")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            logger.error(f"Error adding to cart: {str(e)}")
    
    def _remove_selected(self):
        """Remove selected item from cart"""
        selected = self.cart_tv.selection()
        if not selected:
            messagebox.showinfo("Selection", "Please select an item to remove")
            return
        
        # Remove from cart model and UI
        for item_id in selected:
            self.sys.cart.remove_item(int(item_id))
            self.cart_tv.delete(item_id)
        
        # Update totals
        self._update_cart_total()
        self._update_status("Item(s) removed from cart")
    
    def _clear_cart(self):
        """Clear all items from cart"""
        if not self.cart_tv.get_children():
            return
            
        if messagebox.askyesno("Clear Cart", "Are you sure you want to clear the cart?"):
            self.sys.cart.clear()
            self.cart_tv.delete(*self.cart_tv.get_children())
            self._update_cart_total()
            self._update_status("Cart cleared")
    
    def _edit_cart_quantity(self):
        """Edit quantity of selected cart item"""
        selected = self.cart_tv.selection()
        if not selected:
            messagebox.showinfo("Selection", "Please select an item to edit")
            return
        
        # Get current quantity
        item_id = selected[0]
        current_values = self.cart_tv.item(item_id, 'values')
        current_qty = int(current_values[1])
        
        # Show dialog to edit quantity
        new_qty = simpledialog.askinteger("Edit Quantity", "Enter new quantity:", 
                                        initialvalue=current_qty, minvalue=1)
        
        if new_qty is not None:
            # Update cart model
            for item in self.sys.cart.items:
                if item.product.id == int(item_id):
                    # Check if we have enough stock
                    if new_qty > item.product.stock + current_qty:
                        messagebox.showerror("Stock Error", "Not enough stock available")
                        return
                    
                    # Update quantity and UI
                    item.qty = new_qty
                    new_total = item.product.price * new_qty
                    self.cart_tv.item(item_id, values=(
                        item.product.name, new_qty, f"${item.product.price:.2f}", f"${new_total:.2f}"
                    ))
                    break
            
            # Update totals
            self._update_cart_total()
            self._update_status(f"Updated quantity to {new_qty}")
    
    def _update_cart_total(self):
        """Update the cart subtotal display"""
        subtotal = self.sys.cart.subtotal
        self.subtotal_var.set(f"{self.currency}{subtotal:.2f}")
        
        # Also update the total with current discount and tax
        self._calculate_total()
    
    def _calculate_total(self):
        """Calculate and display the total with discount"""
        discount = self.discount_var.get()
        
        # Calculate totals (with tax_rate=0)
        calc = self.sys.apply_discount_tax(discount, 0)
        
        # Update total display
        self.total_var.set(f"{self.currency}{calc['total']:.2f}")
    
    def _checkout(self):
        """Process checkout with current cart items"""
        if not self.cart_tv.get_children():
            messagebox.showinfo("Checkout", "Cart is empty")
            return
        
        # Get values for checkout
        discount = self.discount_var.get()
        payment_method = self.payment_var.get()
        
        try:
            # Process checkout (with tax_rate=0)
            receipt = self.sys.checkout(discount=discount, tax_rate=0)
            
            # Add payment method to receipt
            receipt['payment_method'] = payment_method
            
            # Generate receipt based on selected type
            receipt_type = self.receipt_type_var.get()
            receipt_dir = self.config.get("receipt_dir", "receipts")
            os.makedirs(receipt_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if receipt_type == "pdf":
                receipt_path = os.path.join(receipt_dir, f"receipt_{timestamp}.pdf")
                generate_pdf_receipt(receipt, receipt_path, currency=self.currency)
            else:  # Default to txt
                receipt_path = os.path.join(receipt_dir, f"receipt_{timestamp}.txt")
                generate_txt_receipt(receipt, receipt_path, currency=self.currency)
            
            # Show success message
            messagebox.showinfo("Checkout Complete", 
                              f"Sale completed successfully!\n\nReceipt saved to {receipt_path}")
            
            # Clear cart and reset fields
            self.cart_tv.delete(*self.cart_tv.get_children())
            self.discount_var.set(0.0)
            self.subtotal_var.set("$0.00")
            self.total_var.set("$0.00")
            
            # Refresh inventory display
            self._refresh_inventory()
            
            # Update status
            self._update_status(f"Checkout complete. Receipt saved to {receipt_path}")
            
        except Exception as e:
            messagebox.showerror("Checkout Error", str(e))
            logger.error(f"Checkout error: {str(e)}")


    def _save_product(self):
        bc, name, price, qty = [v.get() for v in self.inv_vars]
        try:
            existing = self.db.get_product_by_barcode(bc)
            if existing:
                self.db.update_product(existing['id'], name, price, qty)
            else:
                self.db.add_product(bc, name, price, qty)
            messagebox.showinfo("Success", "Product saved.")
            self._clear_form()
            self._refresh_inventory()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_inventory(self):
        for item in self.inv_tv.get_children():
            self.inv_tv.delete(item)
        for row in self.db.list_inventory():
            self.inv_tv.insert("", "end", iid=row['id'], values=(
                row['id'], row['barcode'], row['name'], f"{row['price']:.2f}", row['quantity_in_stock']
            ))

    def _clear_form(self):
        for v in self.inv_vars:
            v.set("" if isinstance(v, tk.StringVar) else 0)

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV Files", "*.csv")])
        if path:
            export_inventory_csv(self.db, path)
            messagebox.showinfo("Export", "Inventory exported.")

    def _import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            import_inventory_csv(self.db, path)
            messagebox.showinfo("Import", "Inventory imported.")
            self._refresh_inventory()
    
    def _export_excel(self):
        """Export inventory to Excel file"""
        try:
            # Check if pandas is available
            import pandas as pd
            
            path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                filetypes=[("Excel Files", "*.xlsx")])
            if path:
                # Get inventory data
                products = self.db.get_all_products()
                
                # Convert to DataFrame
                data = []
                for p in products:
                    data.append({
                        'ID': p.id,
                        'Barcode': p.barcode,
                        'Name': p.name,
                        'Category': p.category,
                        'Price': p.price,
                        'Stock': p.stock
                    })
                
                df = pd.DataFrame(data)
                
                # Export to Excel
                df.to_excel(path, index=False)
                
                messagebox.showinfo("Export", "Inventory exported to Excel.")
        except ImportError:
            messagebox.showerror("Error", "Pandas library not installed. Please install with: pip install pandas openpyxl")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def _import_excel(self):
        """Import inventory from Excel file"""
        try:
            # Check if pandas is available
            import pandas as pd
            from models import Product
            
            path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
            if path:
                # Read Excel file
                df = pd.read_excel(path)
                
                # Import each product
                count = 0
                for _, row in df.iterrows():
                    try:
                        # Create product object
                        product = Product(
                            id=None,  # Let database assign ID
                            barcode=row['Barcode'] if 'Barcode' in df.columns else None,
                            name=row['Name'],
                            category=row['Category'] if 'Category' in df.columns else 'General',
                            price=float(row['Price']),
                            stock=int(row['Stock']) if 'Stock' in df.columns else 0
                        )
                        
                        # Add to database
                        self.db.add_product(product)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error importing row {_}: {str(e)}")
                
                messagebox.showinfo("Import", f"{count} products imported from Excel.")
                self._refresh_inventory()
        except ImportError:
            messagebox.showerror("Error", "Pandas library not installed. Please install with: pip install pandas openpyxl")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import: {str(e)}")
    
    def _generate_sales_report(self):
        """Generate sales report based on date range"""
        try:
            # Get date range
            date_from = self.date_from_var.get()
            date_to = self.date_to_var.get()
            
            # Validate dates
            if not date_from or not date_to:
                messagebox.showwarning("Warning", "Please select both start and end dates")
                return
                
            try:
                # Parse dates
                from_date = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
                to_date = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()
                
                # Add one day to to_date to include the end date in the range
                to_date = to_date + datetime.timedelta(days=1)
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
                return
                
            # Get sales from database
            sales = self.db.get_sales_by_date_range(from_date, to_date)
            
            # Clear the treeview
            for item in self.sales_tv.get_children():
                self.sales_tv.delete(item)
                
            # Populate treeview with sales data
            total_sales = 0.0
            items_count = {}
            
            for sale in sales:
                # Parse the sale date and time
                sale_datetime = datetime.datetime.fromisoformat(sale.date)
                sale_date = sale_datetime.strftime("%Y-%m-%d")
                sale_time = sale_datetime.strftime("%H:%M:%S")
                
                # Count items for best selling product
                for item in sale.items:
                    if item.product_name in items_count:
                        items_count[item.product_name] += item.quantity
                    else:
                        items_count[item.product_name] = item.quantity
                
                # Add to treeview
                self.sales_tv.insert("", tk.END, values=(
                    sale.id,
                    sale_date,
                    sale_time,
                    len(sale.items),
                    f"{self.currency}{sale.total:.2f}",
                    sale.payment_method
                ))
                
                total_sales += sale.total
            
            # Update summary statistics
            self.total_sales_var.set(f"{self.currency}{total_sales:.2f}")
            self.num_trans_var.set(str(len(sales)))
            
            # Calculate average sale
            avg_sale = total_sales / len(sales) if sales else 0
            self.avg_sale_var.set(f"{self.currency}{avg_sale:.2f}")
            
            # Find best selling item
            best_item = max(items_count.items(), key=lambda x: x[1])[0] if items_count else "None"
            self.best_item_var.set(best_item)
            
            # Update status
            self._update_status(f"Generated sales report from {date_from} to {date_to}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            logger.error(f"Error generating sales report: {str(e)}")
    
    def _view_sale_details(self, event):
        """View details of a selected sale"""
        try:
            # Get selected item
            selection = self.sales_tv.selection()
            if not selection:
                return
                
            # Get sale ID from the first column
            sale_id = self.sales_tv.item(selection[0], 'values')[0]
            
            # Get sale from database
            sale = self.db.get_sale_by_id(sale_id)
            if not sale:
                messagebox.showerror("Error", f"Sale #{sale_id} not found")
                return
                
            # Create a new dialog window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Sale #{sale_id} Details")
            details_window.geometry("600x400")
            details_window.transient(self.root)  # Set as child window
            details_window.grab_set()  # Modal window
            
            # Sale info frame
            info_frame = ttk.LabelFrame(details_window, text="Sale Information")
            info_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Parse the sale date and time
            sale_datetime = datetime.datetime.fromisoformat(sale.date)
            sale_date = sale_datetime.strftime("%Y-%m-%d")
            sale_time = sale_datetime.strftime("%H:%M:%S")
            
            # Sale info
            ttk.Label(info_frame, text=f"Date: {sale_date}").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
            ttk.Label(info_frame, text=f"Time: {sale_time}").grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
            ttk.Label(info_frame, text=f"Payment: {sale.payment_method}").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
            ttk.Label(info_frame, text=f"Total: {self.currency}{sale.total:.2f}").grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
            
            # Items frame
            items_frame = ttk.LabelFrame(details_window, text="Items")
            items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Create treeview for items
            columns = ("Product", "Price", "Quantity", "Subtotal")
            items_tv = ttk.Treeview(items_frame, columns=columns, show="headings")
            
            # Configure columns
            items_tv.heading("Product", text="Product")
            items_tv.heading("Price", text="Price")
            items_tv.heading("Quantity", text="Quantity")
            items_tv.heading("Subtotal", text="Subtotal")
            
            items_tv.column("Product", width=200)
            items_tv.column("Price", width=100)
            items_tv.column("Quantity", width=100)
            items_tv.column("Subtotal", width=100)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=items_tv.yview)
            items_tv.configure(yscroll=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            items_tv.pack(fill=tk.BOTH, expand=True)
            
            # Add items to treeview
            for item in sale.items:
                subtotal = item.price * item.quantity
                items_tv.insert("", tk.END, values=(
                    item.product_name,
                    f"${item.price:.2f}",
                    item.quantity,
                    f"${subtotal:.2f}"
                ))
                
            # Buttons frame
            buttons_frame = ttk.Frame(details_window)
            buttons_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Print receipt button
            ttk.Button(buttons_frame, text="Print Receipt", 
                      command=lambda: self._print_receipt(sale_id)).pack(side=tk.LEFT, padx=5)
            
            # Close button
            ttk.Button(buttons_frame, text="Close", 
                      command=details_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view sale details: {str(e)}")
            logger.error(f"Error viewing sale details: {str(e)}")
    
    def _print_receipt(self, sale_id):
        """Print receipt for a sale"""
        try:
            # Get sale from database
            sale = self.db.get_sale_by_id(sale_id)
            if not sale:
                messagebox.showerror("Error", f"Sale #{sale_id} not found")
                return
                
            # Try to use ReportLab for PDF generation
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                
                # Ask user for save location
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF Files", "*.pdf")],
                    initialfile=f"Receipt_{sale_id}.pdf"
                )
                
                if not file_path:
                    return  # User cancelled
                    
                # Create PDF document
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                elements = []
                
                # Styles
                styles = getSampleStyleSheet()
                title_style = styles['Heading1']
                subtitle_style = styles['Heading2']
                normal_style = styles['Normal']
                
                # Store name and header
                elements.append(Paragraph(f"{self.config.get('store_name', 'POS System')}", title_style))
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(f"Receipt #{sale_id}", subtitle_style))
                elements.append(Spacer(1, 12))
                
                # Sale info
                sale_datetime = datetime.datetime.fromisoformat(sale.date)
                elements.append(Paragraph(f"Date: {sale_datetime.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
                elements.append(Paragraph(f"Payment Method: {sale.payment_method}", normal_style))
                elements.append(Spacer(1, 12))
                
                # Items table
                data = [["Item", "Price", "Qty", "Subtotal"]]
                for item in sale.items:
                    subtotal = item.price * item.quantity
                    data.append([item.product_name, f"{self.currency}{item.price:.2f}", str(item.quantity), f"{self.currency}{subtotal:.2f}"])
                
                # Add total row
                data.append(["Total", "", "", f"{self.currency}{sale.total:.2f}"])
                
                # Create table
                table = Table(data, colWidths=[250, 75, 50, 100])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                    ('GRID', (0, 0), (-1, -2), 1, colors.black),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 20))
                
                # Footer
                elements.append(Paragraph(f"Thank you for your purchase!", normal_style))
                
                # Build PDF
                doc.build(elements)
                
                # Open the PDF
                import os
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS or Linux
                    subprocess.call(['open', file_path])
                    
                self._update_status(f"Receipt for sale #{sale_id} saved to {file_path}")
                
            except ImportError:
                # ReportLab not available, use text file instead
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text Files", "*.txt")],
                    initialfile=f"Receipt_{sale_id}.txt"
                )
                
                if not file_path:
                    return  # User cancelled
                    
                with open(file_path, 'w') as f:
                    # Store name and header
                    f.write(f"{self.config.get('store_name', 'POS System')}\n")
                    f.write(f"Receipt #{sale_id}\n")
                    f.write("-" * 40 + "\n\n")
                    
                    # Sale info
                    sale_datetime = datetime.datetime.fromisoformat(sale.date)
                    f.write(f"Date: {sale_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Payment Method: {sale.payment_method}\n\n")
                    
                    # Items header
                    f.write(f"{'Item':<30}{'Price':>10}{'Qty':>5}{'Subtotal':>10}\n")
                    f.write("-" * 55 + "\n")
                    
                    # Items
                    for item in sale.items:
                        subtotal = item.price * item.quantity
                        f.write(f"{item.product_name:<30}{self.currency}{item.price:>9.2f}{item.quantity:>5}{self.currency}{subtotal:>9.2f}\n")
                    
                    # Total
                    f.write("-" * 55 + "\n")
                    f.write(f"{'Total':>45}{self.currency}{sale.total:>9.2f}\n\n")
                    
                    # Footer
                    f.write("Thank you for your purchase!\n")
                
                # Open the text file
                import os
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS or Linux
                    subprocess.call(['open', file_path])
                    
                self._update_status(f"Receipt for sale #{sale_id} saved to {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print receipt: {str(e)}")
            logger.error(f"Error printing receipt: {str(e)}")
    
    def _export_sales_report(self):
        """Export sales report to CSV or Excel"""
        try:
            # Get date range
            date_from = self.date_from_var.get()
            date_to = self.date_to_var.get()
            
            # Validate dates
            if not date_from or not date_to:
                messagebox.showwarning("Warning", "Please select both start and end dates")
                return
                
            try:
                # Parse dates
                from_date = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
                to_date = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()
                
                # Add one day to to_date to include the end date in the range
                to_date = to_date + datetime.timedelta(days=1)
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
                return
                
            # Get sales from database
            sales = self.db.get_sales_by_date_range(from_date, to_date)
            
            if not sales:
                messagebox.showinfo("Info", "No sales found in the selected date range")
                return
                
            # Ask user for export format
            export_format = messagebox.askyesno(
                "Export Format", 
                "Would you like to export as Excel? Select 'No' for CSV format."
            )
            
            if export_format:  # Excel
                try:
                    import pandas as pd
                    
                    # Ask user for save location
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".xlsx",
                        filetypes=[("Excel Files", "*.xlsx")],
                        initialfile=f"Sales_Report_{date_from}_to_{date_to}.xlsx"
                    )
                    
                    if not file_path:
                        return  # User cancelled
                        
                    # Prepare data for Excel
                    sales_data = []
                    for sale in sales:
                        sale_datetime = datetime.datetime.fromisoformat(sale.date)
                        sale_date = sale_datetime.strftime("%Y-%m-%d")
                        sale_time = sale_datetime.strftime("%H:%M:%S")
                        
                        # Add each item as a separate row
                        for item in sale.items:
                            sales_data.append({
                                "Sale ID": sale.id,
                                "Date": sale_date,
                                "Time": sale_time,
                                "Product": item.product_name,
                                "Price": item.price,
                                "Quantity": item.quantity,
                                "Subtotal": item.price * item.quantity,
                                "Payment Method": sale.payment_method
                            })
                    
                    # Create DataFrame and export to Excel
                    df = pd.DataFrame(sales_data)
                    
                    # Create Excel writer with multiple sheets
                    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                        # Detailed sales sheet
                        df.to_excel(writer, sheet_name="Detailed Sales", index=False)
                        
                        # Summary sheet
                        summary_data = {
                            "Metric": ["Total Sales", "Number of Transactions", "Average Sale", "Best Selling Item"],
                            "Value": [
                                f"{self.currency}{sum(sale.total for sale in sales):.2f}",
                                str(len(sales)),
                                f"{self.currency}{sum(sale.total for sale in sales) / len(sales):.2f}" if sales else f"{self.currency}0.00",
                                self.best_item_var.get()
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
                        
                        # Product summary sheet (aggregated by product)
                        product_summary = {}
                        for sale in sales:
                            for item in sale.items:
                                if item.product_name in product_summary:
                                    product_summary[item.product_name]["Quantity"] += item.quantity
                                    product_summary[item.product_name]["Total"] += item.price * item.quantity
                                else:
                                    product_summary[item.product_name] = {
                                        "Product": item.product_name,
                                        "Price": item.price,
                                        "Quantity": item.quantity,
                                        "Total": item.price * item.quantity
                                    }
                        
                        pd.DataFrame(list(product_summary.values())).to_excel(
                            writer, sheet_name="Product Summary", index=False
                        )
                    
                    messagebox.showinfo("Export", f"Sales report exported to {file_path}")
                    self._update_status(f"Sales report exported to Excel: {file_path}")
                    
                    # Open the Excel file
                    import os
                    if os.name == 'nt':  # Windows
                        os.startfile(file_path)
                    elif os.name == 'posix':  # macOS or Linux
                        subprocess.call(['open', file_path])
                        
                except ImportError:
                    messagebox.showerror("Error", "Pandas library not installed. Please install with: pip install pandas openpyxl")
                    # Fall back to CSV export
                    export_format = False
            
            if not export_format:  # CSV
                # Ask user for save location
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV Files", "*.csv")],
                    initialfile=f"Sales_Report_{date_from}_to_{date_to}.csv"
                )
                
                if not file_path:
                    return  # User cancelled
                    
                # Write CSV file
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow(["Sale ID", "Date", "Time", "Product", "Price", "Quantity", "Subtotal", "Payment Method"])
                    
                    # Write data
                    for sale in sales:
                        sale_datetime = datetime.datetime.fromisoformat(sale.date)
                        sale_date = sale_datetime.strftime("%Y-%m-%d")
                        sale_time = sale_datetime.strftime("%H:%M:%S")
                        
                        for item in sale.items:
                            writer.writerow([
                                sale.id,
                                sale_date,
                                sale_time,
                                item.product_name,
                                f"{self.currency}{item.price:.2f}",
                                item.quantity,
                                f"{self.currency}{item.price * item.quantity:.2f}",
                                sale.payment_method
                            ])
                
                messagebox.showinfo("Export", f"Sales report exported to {file_path}")
                self._update_status(f"Sales report exported to CSV: {file_path}")
                
                # Open the CSV file
                import os
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # macOS or Linux
                    subprocess.call(['open', file_path])
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export sales report: {str(e)}")
            logger.error(f"Error exporting sales report: {str(e)}")
    

    def run(self):
        self.root.mainloop()
