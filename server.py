import json, queue, sqlite3
from flask import Flask, request, jsonify, render_template_string, Response

app = Flask(__name__)
subscribers = []
DB_FILE = "monitoring_data.db"

# --- DATABASE SETUP ---
def init_db():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            details TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the DB when the server starts
init_db()

@app.route('/log', methods=['POST'])
def log_event():
    data = request.json
    etype = data.get("event_type")
    ts = data.get("timestamp")
    # Convert the data dictionary to a string to save in DB
    details = json.dumps(data.get("data", {}))

    # 1. Save to Database Permanently
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (timestamp, event_type, details) VALUES (?, ?, ?)", 
                       (ts, etype, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

    # 2. Push to Live Browser Feed
    for sub in subscribers: 
        sub.put(json.dumps(data))
    
    return jsonify({"status": "ok"}), 201

@app.route('/stream')
def stream():
    q = queue.Queue(); subscribers.append(q)
    def event_stream():
        try:
            while True: yield f"data: {q.get()}\n\n"
        finally: subscribers.remove(q)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Feed</title>
    <style>
        body { font-family: -apple-system, sans-serif; background-color: #f4f6f9; padding: 15px; margin: 0; }
        h2 { color: #334e68; margin-bottom: 20px; font-size: 24px; padding-left: 5px; }
        .card { 
            background: white; border-radius: 12px; padding: 18px; margin-bottom: 12px; 
            border-left: 6px solid #2ecc71; box-shadow: 0 2px 8px rgba(0,0,0,0.06); 
            animation: fadeIn 0.4s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        .ts { color: #b0bcc8; font-size: 13px; font-weight: 400; }
        .type { font-weight: 800; text-transform: uppercase; font-size: 13px; margin-left: 6px; }
        .details { color: #243b53; font-size: 16px; font-weight: 600; margin-top: 10px; line-height: 1.4; }
        .source-box { 
            background: #eef2f7; color: #476282; font-size: 11px; margin-top: 10px; 
            padding: 8px 12px; border-radius: 6px; word-break: break-all; font-family: monospace;
            border: 1px solid #d1d9e2; line-height: 1.5;
        }
        .usb-card { border-left-color: #f1c40f; }
        .db-status { font-size: 12px; color: #27ae60; margin-bottom: 10px; padding-left: 5px; }
    </style>
</head>
<body>
    <h2>LIVE MONITORING FEED</h2>
    <div class="db-status">● Database Connected: monitoring_data.db</div>
    <div id="list"></div>
    <script>
        new EventSource("/stream").onmessage = function(e) {
            const d = JSON.parse(e.data);
            const container = document.getElementById("list");
            let info = ""; let sourceHtml = ""; let extraClass = "";

            if (d.event_type === "WINDOW_CHANGE") {
                info = d.data.to_app;
                if (d.data.source) sourceHtml = `<div class="source-box">Source: ${d.data.source}</div>`;
            } else if (d.event_type === "CLIPBOARD") {
                info = "Clipboard: " + d.data.content;
            } else if (d.event_type === "USB_EVENT") {
                info = d.data.action + ": " + d.data.device;
                extraClass = " usb-card";
            }

            const card = document.createElement("div");
            card.className = "card" + extraClass;
            card.innerHTML = `
                <div>
                    <span class="ts">[${d.timestamp.split(' ')[1]}]</span>
                    <span class="type" style="color:${extraClass ? '#f39c12' : '#3498db'}">${d.event_type}</span>
                </div>
                <div class="details">${info}</div>
                ${sourceHtml}
            `;
            container.prepend(card);
            if (container.children.length > 50) container.removeChild(container.lastChild);
        };
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)