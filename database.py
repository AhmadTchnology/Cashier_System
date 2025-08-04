# database.py
import sqlite3
from datetime import datetime

class Database:
    """
    Manages SQLite connection and provides methods to manipulate
    products and sales tables.
    """
    def __init__(self, db_name: str = "pos.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        # Products table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT,
            price REAL,
            quantity_in_stock INTEGER
        )
        """)
        # Sales master table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            total REAL
        )
        """)
        # Sale items (line items)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            sale_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            line_total REAL,
            FOREIGN KEY(sale_id) REFERENCES sales(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """)
        self.conn.commit()

    # Product operations
    def add_product(self, barcode: str, name: str, price: float, qty: int):
        """Insert a new product; barcode must be unique."""
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO products (barcode, name, price, quantity_in_stock)
        VALUES (?, ?, ?, ?)
        """, (barcode, name, price, qty))
        self.conn.commit()

    def get_product_by_barcode(self, barcode: str):
        """Fetch a product row by barcode."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
        return cur.fetchone()
        
    def get_product_by_id(self, product_id: int):
        """Fetch a product row by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        return dict(row) if row else None
        
    def delete_product(self, product_id: int):
        """Delete a product from the database."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()
        return cur.rowcount > 0  # Return True if a row was deleted

    def search_products(self, keyword: str):
        """Search products by name or barcode."""
        cur = self.conn.cursor()
        kw = f"%{keyword}%"
        cur.execute("""
        SELECT * FROM products
        WHERE name LIKE ? OR barcode LIKE ?
        """, (kw, kw))
        return cur.fetchall()

    def update_product(self, product_id: int, name: str, price: float, qty: int):
        """Update product details."""
        cur = self.conn.cursor()
        cur.execute("""
        UPDATE products
        SET name = ?, price = ?, quantity_in_stock = ?
        WHERE id = ?
        """, (name, price, qty, product_id))
        self.conn.commit()

    def adjust_stock(self, product_id: int, delta: int):
        """
        Change stock by delta (negative to reduce).
        Prevents negative stock.
        """
        cur = self.conn.cursor()
        cur.execute("""
        UPDATE products
        SET quantity_in_stock = quantity_in_stock + ?
        WHERE id = ? AND quantity_in_stock + ? >= 0
        """, (delta, product_id, delta))
        self.conn.commit()

    def list_inventory(self):
        """Return all products as list of dicts."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM products")
        return [dict(row) for row in cur.fetchall()]

    # Sales operations
    def record_sale(self, items: list, total: float):
        """
        Record a sale transaction and its line items.
        items: list of dicts with keys product_id, quantity, line_total
        """
        cur = self.conn.cursor()
        ts = datetime.now().isoformat(timespec='seconds')
        cur.execute("INSERT INTO sales (timestamp, total) VALUES (?, ?)", (ts, total))
        sale_id = cur.lastrowid
        for it in items:
            cur.execute("""
            INSERT INTO sale_items (sale_id, product_id, quantity, line_total)
            VALUES (?, ?, ?, ?)
            """, (sale_id, it['product_id'], it['quantity'], it['line_total']))
            # reduce inventory
            self.adjust_stock(it['product_id'], -it['quantity'])
        self.conn.commit()

    def list_sales(self, date_from: str = None, date_to: str = None):
        """List sales within optional date range."""
        cur = self.conn.cursor()
        q = "SELECT * FROM sales"
        params = []
        if date_from and date_to:
            q += " WHERE timestamp BETWEEN ? AND ?"
            params = [date_from, date_to]
        elif date_from:
            q += " WHERE timestamp >= ?"
            params = [date_from]
        elif date_to:
            q += " WHERE timestamp <= ?"
            params = [date_to]
        
        q += " ORDER BY timestamp DESC"
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]
    
    def get_sale_details(self, sale_id: int):
        """Get detailed information about a specific sale."""
        cur = self.conn.cursor()
        # Get sale header
        cur.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
        sale = cur.fetchone()
        if not sale:
            return None
        
        # Get sale items with product details
        cur.execute("""
        SELECT si.*, p.name, p.barcode, p.price
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        WHERE si.sale_id = ?
        """, (sale_id,))
        
        items = [dict(row) for row in cur.fetchall()]
        
        # Return combined data
        return {
            'sale': dict(sale),
            'items': items
        }
    
    def get_low_stock_products(self, threshold: int = 10):
        """Get products with stock below the specified threshold."""
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM products 
        WHERE quantity_in_stock <= ? 
        ORDER BY quantity_in_stock ASC
        """, (threshold,))
        return [dict(row) for row in cur.fetchall()]
    
    def get_sales_by_date_range(self, date_from: str = None, date_to: str = None):
        """Get aggregated sales data by date range."""
        cur = self.conn.cursor()
        q = """
        SELECT 
            date(timestamp) as sale_date,
            COUNT(*) as num_transactions,
            SUM(total) as total_sales
        FROM sales
        """
        
        params = []
        if date_from and date_to:
            q += " WHERE timestamp BETWEEN ? AND ?"
            params = [date_from, date_to]
        elif date_from:
            q += " WHERE timestamp >= ?"
            params = [date_from]
        elif date_to:
            q += " WHERE timestamp <= ?"
            params = [date_to]
        
        q += " GROUP BY date(timestamp) ORDER BY date(timestamp) DESC"
        
        cur.execute(q, params)
        return [dict(row) for row in cur.fetchall()]
