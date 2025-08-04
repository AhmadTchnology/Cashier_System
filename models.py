# models.py
from database import Database

class Product:
    """Represents a product fetched from DB."""
    def __init__(self, row):
        self.id = row['id']
        self.barcode = row['barcode']
        self.name = row['name']
        self.price = row['price']
        self.stock = row['quantity_in_stock']

class CartItem:
    """One line in the current cart."""
    def __init__(self, product: Product, qty: int):
        self.product = product
        self.qty = qty

    @property
    def line_total(self):
        return round(self.product.price * self.qty, 2)

class Cart:
    """Holds current sale items."""
    def __init__(self):
        self.items = []

    def add_item(self, product: Product, qty: int):
        # merge if same product
        for ci in self.items:
            if ci.product.id == product.id:
                ci.qty += qty
                return
        self.items.append(CartItem(product, qty))

    def remove_item(self, product_id: int):
        self.items = [ci for ci in self.items if ci.product.id != product_id]

    def clear(self):
        self.items = []

    @property
    def subtotal(self):
        return round(sum(ci.line_total for ci in self.items), 2)

class CashierSystem:
    """
    Coordinates scanning, cart management, checkout.
    """
    def __init__(self, db: Database, config=None):
        self.db = db
        self.cart = Cart()
        self.config = config or {}

    def scan_and_add(self, barcode: str, qty: int):
        """
        Fetch product by barcode, validate stock, add to cart.
        Raises ValueError if not found or insufficient stock.
        """
        row = self.db.get_product_by_barcode(barcode)
        if not row:
            raise ValueError("Product not found.")
        prod = Product(row)
        if qty > prod.stock:
            raise ValueError("Not enough stock.")
        self.cart.add_item(prod, qty)
        return prod, qty

    def apply_discount_tax(self, discount: float = 0, tax_rate: float = 0):
        """
        discount: flat amount
        tax_rate: parameter kept for backward compatibility but not used
        """
        sub = self.cart.subtotal
        total = round(sub - discount, 2)
        return {
            'subtotal': sub,
            'taxed': sub,  # No tax applied
            'discount': discount,
            'total': max(total, 0)
        }

    def checkout(self, discount: float = 0, tax_rate: float = 0):
        """
        Finalize sale: record in DB and clear cart.
        Returns receipt dict.
        tax_rate: parameter kept for backward compatibility but not used
        """
        calc = self.apply_discount_tax(discount, 0)  # Always use 0 for tax_rate
        items_data = [{
            'product_id': ci.product.id,
            'quantity': ci.qty,
            'line_total': ci.line_total
        } for ci in self.cart.items]
        self.db.record_sale(items_data, calc['total'])
        receipt = {
            'items': [(ci.product.name, ci.qty, ci.product.price, ci.line_total)
                      for ci in self.cart.items],
            **calc,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        self.cart.clear()
        return receipt
