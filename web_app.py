from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import threading, queue, json, csv, io, random, os

# ── reuse all logic from money_generator ────────────────────────────────────
from money_generator import (
    load_data, save_data,
    INTRO_MESSAGES, MSG2_MESSAGES, MSG3_MESSAGES,
    GIG_SITES, PAY_SITES, PROMO_SITES,
    GRAB_LEADS_QUERIES,
    CRAIGSLIST_CITIES, CRAIGSLIST_CITY_LABELS,
    scrape_craigslist,
    search_local_businesses,
    _issues_summary, _build_pitch,
    SCRAPING_AVAILABLE,
)

app = Flask(__name__)
CORS(app)

# ── SSE helper ───────────────────────────────────────────────────────────────
def sse(data):
    return f"data: {json.dumps(data)}\n\n"


# ── pages ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── data ─────────────────────────────────────────────────────────────────────
@app.route("/api/data")
def get_data():
    return jsonify(load_data())


# ── find leads (Craigslist) ──────────────────────────────────────────────────
@app.route("/api/find-leads")
def find_leads_stream():
    keyword      = request.args.get("keyword", "")
    by_title     = request.args.get("by_title") == "true"
    posted_today = request.args.get("posted_today") == "true"
    cities       = request.args.getlist("cities") or None

    city_names = ", ".join(CRAIGSLIST_CITY_LABELS.get(c, c) for c in (cities or CRAIGSLIST_CITIES))

    def generate():
        yield sse({"status": f"Scraping leads in: {city_names}… please wait"})
        try:
            urls = scrape_craigslist(keyword, by_title=by_title, posted_today=posted_today, cities=cities)
            yield sse({"done": True, "urls": urls})
        except Exception as e:
            yield sse({"error": str(e)})

    return Response(generate(), mimetype="text/event-stream")


# ── business finder ──────────────────────────────────────────────────────────
@app.route("/api/business-finder")
def business_finder_stream():
    keyword   = request.args.get("keyword", "dentist")
    location  = request.args.get("location", "")
    sources   = request.args.getlist("sources")
    gmaps_key = request.args.get("gmaps_key", "")
    yelp_key  = request.args.get("yelp_key", "")

    def generate():
        yield sse({"status": f"Searching {', '.join(sources)} for {keyword} in {location}…"})
        try:
            results = search_local_businesses(
                keyword, location, sources,
                gmaps_api_key=gmaps_key, yelp_api_key=yelp_key)
            payload = []
            for b in results:
                issues = _issues_summary(b)
                payload.append({
                    "name":    b.get("name", ""),
                    "source":  b.get("source", ""),
                    "phone":   b.get("phone", ""),
                    "rating":  b.get("rating"),
                    "website": b.get("website", ""),
                    "issues":  issues,
                    "pitch":   _build_pitch(b),
                })
            yield sse({"done": True, "results": payload})
        except Exception as e:
            yield sse({"error": str(e)})

    return Response(generate(), mimetype="text/event-stream")


# ── grab leads ───────────────────────────────────────────────────────────────
@app.route("/api/grab-leads")
def grab_leads_stream():
    cities = request.args.getlist("cities") or None

    def generate():
        yield sse({"status": "Grabbing leads… please wait"})
        try:
            query = random.choice(GRAB_LEADS_QUERIES)
            urls  = scrape_craigslist(query, cities=cities)
            yield sse({"done": True, "urls": urls, "query": query})
        except Exception as e:
            yield sse({"error": str(e)})

    return Response(generate(), mimetype="text/event-stream")


# ── messages ─────────────────────────────────────────────────────────────────
@app.route("/api/message/random")
def random_message():
    pool_name = request.args.get("pool", "intro")
    data = load_data()
    pools = {
        "intro": INTRO_MESSAGES,
        "msg2":  MSG2_MESSAGES,
        "msg3":  MSG3_MESSAGES,
    }
    pool = pools.get(pool_name, INTRO_MESSAGES) + data.get("messages", [])
    return jsonify({"message": random.choice(pool) if pool else ""})


@app.route("/api/message/save", methods=["POST"])
def save_message():
    text = (request.json or {}).get("text", "").strip()
    if text:
        data = load_data()
        data.setdefault("messages", []).append(text)
        save_data(data)
    return jsonify({"ok": True})


# ── clients ──────────────────────────────────────────────────────────────────
@app.route("/api/clients", methods=["GET"])
def get_clients():
    return jsonify(load_data().get("clients", []))


@app.route("/api/clients", methods=["POST"])
def add_client():
    body = request.json or {}
    row = [body.get("name",""), body.get("email",""), body.get("phone","")]
    data = load_data()
    data.setdefault("clients", []).append(row)
    save_data(data)
    return jsonify({"ok": True})


@app.route("/api/clients/<int:idx>", methods=["DELETE"])
def delete_client(idx):
    data = load_data()
    clients = data.get("clients", [])
    if 0 <= idx < len(clients):
        clients.pop(idx)
        save_data(data)
    return jsonify({"ok": True})


@app.route("/api/clients/export")
def export_clients():
    data = load_data()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Name/Username", "Email", "Contact Number"])
    w.writerows(data.get("clients", []))
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=clients.csv"})


# ── URL save ─────────────────────────────────────────────────────────────────
@app.route("/api/url", methods=["POST"])
def save_url():
    url = (request.json or {}).get("url", "")
    data = load_data()
    data["custom_url"] = url
    save_data(data)
    return jsonify({"ok": True})


# ── static lists ─────────────────────────────────────────────────────────────
@app.route("/api/sites")
def sites():
    return jsonify({
        "gig":   GIG_SITES,
        "pay":   PAY_SITES,
        "promo": PROMO_SITES,
    })


@app.route("/api/cities")
def cities():
    return jsonify([
        {"id": c, "label": CRAIGSLIST_CITY_LABELS.get(c, c)}
        for c in CRAIGSLIST_CITIES
    ])


if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser")
    app.run(debug=False, port=5000)
