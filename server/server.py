"""
GhostCSS Demo Server

Flask application that serves GhostCSS demo pages and logs exfiltration
attempts. Includes a real-time dashboard via WebSocket for monitoring.

Usage:
    pip install flask flask-socketio
    python server.py

Routes:
    /              - Demo index page
    /blog          - Blog demo (Attack 02: sr-only)
    /bank          - Banking demo (Attack 07: composite)
    /email         - Email demo (Attack 03: CSS content)
    /collect       - Exfiltration endpoint (logs all requests)
    /dashboard     - Real-time exfiltration viewer
    /api/events    - JSON API for logged events
    /attacks/<n>   - Serve individual attack demos

All exfiltration is logged locally. No data leaves the server.
"""

import json
import os
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "ghostcss-research-demo"
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory event log
exfil_events = []


def log_event(source, data, metadata=None):
    """Log an exfiltration event and broadcast to dashboard clients."""
    event = {
        "id": len(exfil_events) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "data": data,
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "referer": request.headers.get("Referer", ""),
        "metadata": metadata or {},
    }
    exfil_events.append(event)
    socketio.emit("new_event", event)
    print(f"[EXFIL] {event['timestamp']} | {source} | {data} | {event['ip']}")
    return event


# --- Demo Routes ---


@app.route("/")
def index():
    """Demo index page with links to all demos."""
    return render_template("index.html")


@app.route("/blog")
def blog():
    """Blog demo - normal-looking article with sr-only injection."""
    return render_template("blog.html")


@app.route("/bank")
def bank():
    """Banking demo - financial article with composite injection."""
    return render_template("bank.html")


@app.route("/email")
def email():
    """Email demo - webmail interface with CSS content injection."""
    return render_template("email.html")


# --- Exfiltration Endpoint ---


@app.route("/collect")
def collect():
    """
    Exfiltration collection endpoint. Logs all incoming requests.

    Expected query parameters:
        source: Attack variant that triggered the exfil (e.g., 'sr-only')
        data:   The exfiltrated data payload

    Any additional query parameters are logged as metadata.
    """
    source = request.args.get("source", "unknown")
    data = request.args.get("data", "")

    # Capture all query parameters as metadata
    metadata = {k: v for k, v in request.args.items() if k not in ("source", "data")}

    event = log_event(source, data, metadata)

    # Return innocuous response (the agent shouldn't see anything suspicious)
    return jsonify({"status": "ok", "message": "Content verified."})


@app.route("/collect", methods=["POST"])
def collect_post():
    """POST variant of the exfiltration endpoint for larger payloads."""
    source = request.form.get("source", request.args.get("source", "unknown"))
    data = request.form.get("data", request.get_data(as_text=True))

    metadata = {}
    if request.is_json:
        body = request.get_json(silent=True) or {}
        source = body.get("source", source)
        data = body.get("data", data)
        metadata = {k: v for k, v in body.items() if k not in ("source", "data")}

    event = log_event(source, data, metadata)
    return jsonify({"status": "ok", "message": "Content verified."})


# --- Dashboard ---


@app.route("/dashboard")
def dashboard():
    """Real-time exfiltration event dashboard."""
    return render_template("dashboard.html")


@app.route("/api/events")
def api_events():
    """JSON API returning all logged exfiltration events."""
    return jsonify({"events": exfil_events, "count": len(exfil_events)})


@app.route("/api/events/clear", methods=["POST"])
def api_events_clear():
    """Clear all logged events."""
    exfil_events.clear()
    socketio.emit("events_cleared")
    return jsonify({"status": "cleared"})


# --- Attack File Serving ---


@app.route("/attacks/<path:filename>")
def serve_attack(filename):
    """Serve individual attack demo files."""
    attacks_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "attacks")
    return send_from_directory(attacks_dir, filename)


# --- WebSocket Events ---


@socketio.on("connect")
def handle_connect():
    """Send existing events to newly connected dashboard clients."""
    for event in exfil_events:
        socketio.emit("new_event", event)


if __name__ == "__main__":
    print("=" * 60)
    print("GhostCSS Demo Server")
    print("=" * 60)
    print()
    print("Routes:")
    print("  http://localhost:5000/           - Demo index")
    print("  http://localhost:5000/blog       - Blog demo (sr-only)")
    print("  http://localhost:5000/bank       - Banking demo (composite)")
    print("  http://localhost:5000/email      - Email demo (CSS content)")
    print("  http://localhost:5000/dashboard  - Exfiltration dashboard")
    print()
    print("Point an AI browser agent at a demo page and ask it to")
    print("summarize the content. Watch the dashboard for exfil events.")
    print("=" * 60)

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
