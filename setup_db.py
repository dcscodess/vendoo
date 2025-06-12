import sqlite3

conn = sqlite3.connect('vending.db')

conn.execute("PRAGMA foreign_keys = ON")

# Products
conn.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price INTEGER,
    stock INTEGER,
    image TEXT
)
''')

# Price Links with relation to product_id
conn.execute('''
CREATE TABLE IF NOT EXISTS price_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    quantity INTEGER,
    price INTEGER,
    payment_link TEXT,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
)
''')

# Transactions table to track everything
conn.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    quantity INTEGER,
    payment_link TEXT,
    payment_status TEXT DEFAULT 'pending',
    esp_status TEXT DEFAULT 'pending',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
)
''')

# Sample Data
conn.execute("DELETE FROM products")
conn.execute("INSERT INTO products (id, name, description, price, stock, image) VALUES (1, 'Pads', 'Soft sanitary pads', 5, 50, 'pads.jpg')")
conn.execute("INSERT INTO products (id, name, description, price, stock, image) VALUES (2, 'First Aid Kit', 'Compact emergency kit', 10, 10, 'kit.jpeg')")
conn.execute("INSERT INTO products (id, name, description, price, stock, image) VALUES (3, 'Band-Aids', 'Pack of 10 band-aids', 12, 30, 'bandaid.jpeg')")

conn.execute("DELETE FROM price_links")
conn.execute("INSERT INTO price_links (product_id, quantity, price, payment_link) VALUES (1, 1, 5, 'https://rzp.io/rzp/dcGjH4BJ')")
conn.execute("INSERT INTO price_links (product_id, quantity, price, payment_link) VALUES (1, 2, 10, 'https://rzp.io/rzp/ZYLX0SAx')")
conn.execute("INSERT INTO price_links (product_id, quantity, price, payment_link) VALUES (1, 3, 15, 'https://rzp.io/rzp/35mjHQ96')")
conn.execute("INSERT INTO price_links (product_id, quantity, price, payment_link) VALUES (1, 5, 25, 'https://rzp.io/rzp/ou0n7db')")


conn.commit()
conn.close()
print("Database updated with correct relationships.")
