# Advanced POS (Point of Sale) System

A feature-rich Point of Sale system built with Python, designed for small to medium-sized retail businesses. This application provides inventory management, sales processing, receipt generation, and reporting capabilities.

## Features

- **Modern User Interface**: Clean, intuitive Tkinter-based UI with theme support
- **Product Management**: Add, edit, delete, and search products
- **Sales Processing**: Scan products, manage cart, apply discounts and taxes
- **Receipt Generation**: Generate receipts in both text and PDF formats
- **Reporting**: Generate sales and inventory reports
- **Data Import/Export**: Import and export data in CSV and Excel formats
- **Configuration**: Easily customize application settings via config.json

## System Architecture

The application follows a layered architecture:

1. **Database Layer** (`database.py`): Handles data persistence using SQLite
2. **Model Layer** (`models.py`): Implements business logic and data structures
3. **Utility Layer** (`utils.py`): Provides helper functions for file I/O, reporting, etc.
4. **UI Layer** (`ui.py`): Implements the graphical user interface using Tkinter
5. **Entry Point** (`main.py`): Initializes and starts the application

## Installation

### Prerequisites

- Python 3.7 or higher
- Required packages (install via pip):

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py
```

You can also specify a custom configuration file:

```bash
python main.py --config my_config.json
```

## Configuration

The application can be configured via the `config.json` file. Key settings include:

- Database configuration
- UI theme and window size
- Receipt customization
- Tax rates
- Low stock thresholds
- Logging settings

## Usage

### Inventory Management

- Add new products with barcode, name, price, and quantity
- Edit existing products
- Delete products
- Import/export inventory data

### Sales Processing

- Scan products by barcode
- Add items to cart
- Edit quantities
- Apply discounts
- Process checkout with different payment methods
- Generate receipts

### Reporting

- Generate sales reports by date range
- View inventory status
- Get low stock alerts

## Extending the System

The modular design makes it easy to extend the system with new features:

- Add new payment methods
- Implement customer loyalty programs
- Connect to external hardware (barcode scanners, receipt printers)
- Integrate with accounting software

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Made with ❤️ by uTech Team