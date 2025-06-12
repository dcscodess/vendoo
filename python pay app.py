from flask import Flask, render_template, request, redirect, abort
import sqlite3, requests, json, hmac, hashlib
from datetime import datetime

app = Flask(__name__)
ESP32_URL = "http://192.168.4.1/dispense"
WEBHOOK_SECRET = "your_webhook_secret"

def get_db():
    conn = sqlite3.connect("vending.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    prices = conn.execute("SELECT * FROM product_prices").fetchall()
    conn.close()

    # Group price info by product_id
    price_map = {}
    for price in prices:
        price_map.setdefault(price["product_id"], {})[price["quantity"]] = dict(price)

    return render_template("index.html", products=products, price_map=price_map)

@app.route('/buy', methods=["POST"])
def buy():
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])

    conn = get_db()
    price_entry = conn.execute(
        "SELECT * FROM product_prices WHERE product_id=? AND quantity=?",
        (product_id, quantity)
    ).fetchone()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not price_entry or not product or quantity > product["stock"]:
        return "Invalid purchase", 400

    # Record transaction
    conn.execute("""
        INSERT INTO transactions (product_id, quantity, amount, payment_link, payment_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (product_id, quantity, price_entry["price"], price_entry["payment_link"], "pending", datetime.now()))
    conn.commit()
    conn.close()

    return redirect(price_entry["payment_link"])

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    signature = request.headers.get('X-Razorpay-Signature', '')

    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        abort(400, "Invalid signature")

    data = json.loads(payload)
    if data.get("event") != "payment_link.paid":
        return '', 200

    link_id = data["payload"]["payment_link"]["entity"]["id"]
    conn = get_db()
    txn = conn.execute("SELECT * FROM transactions WHERE payment_link LIKE ? AND payment_status='pending'",
                       (f"%{link_id}",)).fetchone()
    if txn:
        conn.execute("UPDATE transactions SET payment_status='success' WHERE id=?", (txn["id"],))
        conn.execute("UPDATE products SET stock = stock - ? WHERE id=?", (txn["quantity"], txn["product_id"]))
        conn.commit()
        try:
            requests.post(ESP32_URL, json={
                "product_id": txn["product_id"],
                "quantity": txn["quantity"]
            }, timeout=5)
        except Exception as e:
            print("ESP32 error:", e)
    conn.close()
    return '', 200
