from flask import Flask, render_template, request, jsonify
import sqlite3
import requests

app = Flask(__name__)
ESP32_IP = "http://192.168.137.117"  # Replace with your ESP32 IP

def get_db_connection():
    conn = sqlite3.connect('vending.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/get_price_link', methods=['POST'])
def get_price_link():
    data = request.json
    pid = data['product_id']
    qty = data['quantity']

    conn = get_db_connection()
    row = conn.execute(
        "SELECT price, payment_link FROM price_links WHERE product_id = ? AND quantity = ?",
        (pid, qty)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Payment link not found"}), 404

    return jsonify({
        "price": row["price"],
        "link": row["payment_link"]
    })

@app.route('/confirm_payment', methods=['POST'])
def confirm_payment():
    data = request.json
    pid = data['product_id']
    qty = data['quantity']

    conn = get_db_connection()
    txn = conn.execute("""
        SELECT id FROM transactions 
        WHERE product_id = ? AND quantity = ? AND payment_status = 'pending'
        ORDER BY timestamp DESC LIMIT 1
    """, (pid, qty)).fetchone()

    if not txn:
        conn.close()
        return jsonify({"success": False, "message": "No pending transaction"}), 404

    txn_id = txn["id"]

    try:
        # Notify ESP32 to dispense
        resp = requests.post(f"{ESP32_IP}/dispense", json={"product_id": pid, "quantity": qty})
        result = resp.json()

        if resp.status_code == 200 and result.get("status") == "dispensed":
            conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))
            conn.execute("UPDATE transactions SET payment_status = 'success', esp_status = 'dispensed' WHERE id = ?", (txn_id,))
            conn.commit()
            return jsonify({"success": True})
        else:
            conn.execute("UPDATE transactions SET payment_status = 'success', esp_status = 'failed' WHERE id = ?", (txn_id,))
            conn.commit()
            return jsonify({"success": False, "message": "ESP32 failed to dispense"}), 500

    except Exception as e:
        conn.execute("UPDATE transactions SET payment_status = 'success', esp_status = 'error' WHERE id = ?", (txn_id,))
        conn.commit()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

@app.route('/record_transaction', methods=['POST'])
def record_transaction():
    data = request.json
    pid = data['product_id']
    qty = data['quantity']
    payment_link = data['payment_link']

    conn = get_db_connection()
    conn.execute("INSERT INTO transactions (product_id, quantity, payment_link) VALUES (?, ?, ?)", (pid, qty, payment_link))
    conn.commit()
    conn.close()

    return jsonify({"status": "recorded"})

if __name__ == '__main__':
    app.run(debug=True)
