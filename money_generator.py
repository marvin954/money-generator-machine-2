import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import webbrowser
import random
import csv
import os
import json
import re

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

# ── colour palette (matches original) ──────────────────────────────────────
BG_DARK   = "#0d1b5e"
BG_LIGHT  = "#f0f0f0"
BTN_GREEN = "#4caf7d"
BTN_BLUE  = "#1565c0"
FG_WHITE  = "#ffffff"
FG_DARK   = "#000000"

DATA_FILE = os.path.join(os.path.dirname(__file__), "mgm_data.json")

def load_data():
    default = {"messages": [], "clients": [], "custom_url": ""}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return default

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── built-in message templates ──────────────────────────────────────────────
INTRO_MESSAGES = [
    "Hi there, I noticed your gig on Craigslist and I am interested in working with you. "
    "If you are looking for better ways to improve your business then you will definitely be "
    "happy with what I can provide. For more info, feel free to contact me on my email address.",

    "Hello! I came across your post and I believe I can help you take your business to the "
    "next level. I specialise in digital services including graphic design, SEO, and social "
    "media marketing. Get in touch and let's discuss how I can help.",

    "Good day! I saw your listing and I'm confident I have exactly what you need. "
    "I offer professional digital services at competitive rates. "
    "Feel free to reach out — I'd love to work with you.",
]

MSG2_MESSAGES = [
    "Following up on my previous message — I just wanted to make sure you received it. "
    "I have helped many clients grow their online presence and I'm sure I can do the same for you. "
    "Looking forward to hearing from you!",

    "Just checking in! I sent you a message earlier about my digital services. "
    "I'm still very interested in working together. Please don't hesitate to reach out.",
]

MSG3_MESSAGES = [
    "This is my final follow-up. I truly believe my services would be a great fit for your needs. "
    "If you change your mind, my contact details are below. Wishing you all the best!",

    "Last message from me — I respect your time. If you ever need digital marketing, "
    "design, or SEO services in the future, don't hesitate to contact me. Take care!",
]

GIG_SITES = [
    ("Fiverr",     "https://www.fiverr.com"),
    ("SEO Clerk",  "https://www.seoclerk.com"),
    ("Zeerk",      "https://zeerk.com"),
    ("Freqoid",    "https://www.fourerr.com"),
    ("Fiver Up",   "https://www.fiverup.com"),
    ("Dollar SEO", "https://www.dollarseo.com"),
]

PAY_SITES = [
    ("Inbox Dollars",   "https://www.inboxdollars.com"),
    ("Enroll",          "https://www.enroll.com"),
    ("Funds For Writers","https://fundsforwriters.com"),
    ("SwagBucks",       "https://www.swagbucks.com"),
    ("Threadless",      "https://www.threadless.com"),
    ("Dollar Dig",      "https://dollardig.com"),
    ("StartUpLift",     "https://startupliclift.com"),
]

PROMO_SITES = [
    ("FollowLike",    "https://followlike.net"),
    ("Link Collider", "https://www.linkcollider.com"),
    ("Like4Like",     "https://www.like4like.org"),
    ("You Like Hits", "https://www.youlikehits.com"),
    ("Followfast",    "https://followfast.com"),
    ("Likes Planet",  "https://www.likesplanet.com"),
    ("AddMeFast",     "https://addmefast.com"),
]

# ── business audit constants ────────────────────────────────────────────────
BOOKING_KEYWORDS = [
    "book now", "book an appointment", "schedule", "calendly", "booksy",
    "appointy", "acuityscheduling", "square appointments", "setmore",
    "simplybook", "vagaro", "fresha", "booker", "mindbody",
]
CHATBOT_SIGNATURES = [
    "intercom", "drift.com", "tidio", "tawk.to", "freshchat",
    "crisp.chat", "zendesk", "hubspot", "livechat", "olark",
    "botpress", "manychat", "chatbase",
]
AI_KEYWORDS = [
    "ai assistant", "artificial intelligence", "chatgpt", "openai",
    "powered by ai", "ai-powered", "smart assistant",
]

PITCH_TEMPLATES = {
    "no_website": (
        "Hi {name}, I noticed {business} doesn't have a website yet. "
        "In today's market, customers search online before they visit. "
        "I build professional websites starting at a very affordable price — "
        "let me put {business} on the map. Happy to chat if interested!"
    ),
    "broken_website": (
        "Hi {name}, I came across {business} online and noticed your website "
        "appears to be down or returning errors. A broken site can cost you "
        "customers daily. I specialise in quick website fixes and rebuilds — "
        "I can have you back online fast. Would you like a free assessment?"
    ),
    "slow_website": (
        "Hi {name}, I ran a quick speed test on the {business} website and "
        "it's loading slowly — Google actually ranks slow sites lower in search "
        "results. I can optimise it so it loads in under 2 seconds. "
        "Want me to send you a free report?"
    ),
    "no_booking": (
        "Hi {name}, I noticed {business} doesn't have online booking yet. "
        "I can build you an AI-powered booking system that lets customers "
        "schedule appointments 24/7 — even while you sleep. "
        "Most of my clients see 30%+ more bookings within the first month. Interested?"
    ),
    "no_chatbot": (
        "Hi {name}, I checked out the {business} website and noticed there's "
        "no live chat or AI assistant. A chatbot can answer customer questions "
        "instantly at any hour and capture leads you'd otherwise lose. "
        "I set these up quickly and affordably — want to see a demo?"
    ),
    "poor_reviews": (
        "Hi {name}, I noticed {business} has some negative reviews online that "
        "may be affecting your reputation. I offer reputation management services "
        "that help businesses respond professionally and encourage happy customers "
        "to leave great reviews. Would a free consultation be helpful?"
    ),
    "multiple": (
        "Hi {name}, I looked up {business} online and spotted a few quick wins "
        "that could bring you more customers: {issues}. "
        "I specialise in exactly these areas and work with small businesses at "
        "very reasonable rates. Would you be open to a free 15-minute call?"
    ),
}

def _check_website(url, timeout=6):
    """Return dict of audit flags for a given URL."""
    result = {
        "reachable": False,
        "broken": False,
        "slow": False,
        "has_booking": False,
        "has_chatbot": False,
        "has_ai": False,
        "load_time": None,
        "status_code": None,
    }
    if not url:
        return result
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import time
        t0 = time.time()
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"},
                         allow_redirects=True)
        elapsed = time.time() - t0
        result["load_time"] = round(elapsed, 2)
        result["status_code"] = r.status_code
        result["reachable"] = r.status_code < 400
        result["broken"] = r.status_code >= 400
        result["slow"] = elapsed > 3.5
        text = r.text.lower()
        result["has_booking"] = any(k in text for k in BOOKING_KEYWORDS)
        result["has_chatbot"] = any(k in text for k in CHATBOT_SIGNATURES)
        result["has_ai"]      = any(k in text for k in AI_KEYWORDS)
    except requests.exceptions.ConnectionError:
        result["broken"] = True
    except Exception:
        result["broken"] = True
    return result


def _issues_summary(biz):
    """Return list of human-readable issues for a business dict."""
    issues = []
    if not biz.get("website"):
        issues.append("no website")
    elif biz.get("audit", {}).get("broken"):
        issues.append("broken website")
    else:
        if biz.get("audit", {}).get("slow"):
            issues.append(f"slow website ({biz['audit']['load_time']}s)")
        if not biz.get("audit", {}).get("has_booking"):
            issues.append("no online booking")
        if not biz.get("audit", {}).get("has_chatbot"):
            issues.append("no chatbot / live chat")
        if not biz.get("audit", {}).get("has_ai"):
            issues.append("no AI assistant")
    rating = biz.get("rating", 0)
    if rating and float(rating) < 3.5:
        issues.append(f"poor reviews ({rating}★)")
    return issues


def _build_pitch(biz):
    name = biz.get("owner", "") or "there"
    business = biz.get("name", "your business")
    issues = _issues_summary(biz)
    if not issues:
        return "No obvious issues found — great business!"
    if not biz.get("website"):
        return PITCH_TEMPLATES["no_website"].format(name=name, business=business)
    if biz.get("audit", {}).get("broken"):
        return PITCH_TEMPLATES["broken_website"].format(name=name, business=business)
    if len(issues) == 1:
        key = {
            f"slow website ({biz.get('audit',{}).get('load_time')}s)": "slow_website",
        }.get(issues[0], issues[0].replace(" ", "_").replace("/", "").replace("-", "_"))
        tmpl = PITCH_TEMPLATES.get(key, PITCH_TEMPLATES["multiple"])
        return tmpl.format(name=name, business=business, issues=issues[0])
    issue_str = ", ".join(issues[:-1]) + " and " + issues[-1]
    return PITCH_TEMPLATES["multiple"].format(name=name, business=business, issues=issue_str)


# OSM amenity tag map — maps plain English to OSM tags
OSM_AMENITY_MAP = {
    "dentist": "dentist", "doctor": "doctors", "pharmacy": "pharmacy",
    "restaurant": "restaurant", "cafe": "cafe", "bar": "bar",
    "gym": "gym", "beauty salon": "beauty", "hairdresser": "hairdresser",
    "hotel": "hotel", "lawyer": "lawyer", "accountant": "accountant",
    "optician": "optician", "veterinary": "veterinary",
}
OSM_SHOP_MAP = {
    "florist": "florist", "bakery": "bakery", "butcher": "butcher",
    "bookshop": "books", "electronics": "electronics",
}
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _geocode(location):
    """Return (south, north, west, east) bounding box for a location string."""
    try:
        r = requests.get(NOMINATIM_URL,
            params={"q": location, "format": "json", "limit": "1"},
            headers={"User-Agent": "MoneyGeneratorMachine/2.0"},
            timeout=8)
        data = r.json()
        if data:
            bb = data[0].get("boundingbox")  # [s, n, w, e]
            if bb:
                return float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
            lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
            d = 0.18
            return lat - d, lat + d, lon - d, lon + d
    except Exception:
        pass
    return None


def _osm_query(tag_key, tag_value, bbox, limit=60):
    """Run an Overpass query and return raw elements list, trying mirrors in order."""
    s, n, w, e = bbox
    box = f"{s},{w},{n},{e}"
    query = (
        f'[out:json][timeout:30];'
        f'(node["{tag_key}"="{tag_value}"]({box});'
        f'way["{tag_key}"="{tag_value}"]({box}););'
        f'out center {limit};'
    )
    headers = {
        "User-Agent": "MoneyGeneratorMachine/2.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    for url in OVERPASS_MIRRORS:
        try:
            r = requests.post(url, data={"data": query}, headers=headers, timeout=25)
            if r.status_code == 200:
                return r.json().get("elements", [])
        except Exception:
            continue
    return []


def search_osm(keyword, location, limit=80):
    """Search OpenStreetMap/Overpass for local businesses. Free, no API key."""
    bbox = _geocode(location)
    if not bbox:
        return []

    kw = keyword.lower().strip()
    results = []
    seen = set()

    # Try amenity tags
    amenity = OSM_AMENITY_MAP.get(kw, kw)
    for el in _osm_query("amenity", amenity, bbox, limit):
        t = el.get("tags", {})
        name = t.get("name")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        results.append({
            "name": name,
            "website": t.get("website") or t.get("contact:website") or "",
            "phone": t.get("phone") or t.get("contact:phone") or "",
            "rating": None,
            "source": "OpenStreetMap",
            "location": location,
        })

    # Also try shop tag
    if not results:
        shop = OSM_SHOP_MAP.get(kw, kw)
        for el in _osm_query("shop", shop, bbox, limit):
            t = el.get("tags", {})
            name = t.get("name")
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            results.append({
                "name": name,
                "website": t.get("website") or t.get("contact:website") or "",
                "phone": t.get("phone") or t.get("contact:phone") or "",
                "rating": None,
                "source": "OpenStreetMap",
                "location": location,
            })

    return results[:limit]


def search_google_maps(keyword, location, api_key, limit=60):
    """Search via Google Places API (Text Search). Free key + $200/mo credit."""
    businesses = []
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "MoneyGeneratorMachine/2.0"})

        # Step 1: Text Search to get place_ids + basic info
        params = {
            "query": f"{keyword} in {location}",
            "key": api_key,
            "fields": "name,rating,formatted_address,place_id",
        }
        r = session.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params=params, timeout=12)
        data = r.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            return [{"name": f"Google Maps error: {data.get('status','?')} — {data.get('error_message','')}",
                     "website": "", "phone": "", "rating": None, "source": "Google Maps", "location": location}]

        place_ids = [(p["place_id"], p.get("name",""), p.get("rating"))
                     for p in data.get("results", [])[:limit]]

        # Step 2: Details call per place to get website + phone
        def get_details(pid_name_rating):
            pid, name, rating = pid_name_rating
            try:
                dr = session.get(
                    "https://maps.googleapis.com/maps/api/place/details/json",
                    params={"place_id": pid, "fields": "name,website,formatted_phone_number,rating", "key": api_key},
                    timeout=8)
                res = dr.json().get("result", {})
                return {
                    "name": res.get("name", name),
                    "website": res.get("website", ""),
                    "phone": res.get("formatted_phone_number", ""),
                    "rating": res.get("rating", rating),
                    "source": "Google Maps",
                    "location": location,
                }
            except Exception:
                return {"name": name, "website": "", "phone": "", "rating": rating,
                        "source": "Google Maps", "location": location}

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            businesses = list(ex.map(get_details, place_ids))

        # Handle pagination (next_page_token) for more results
        token = data.get("next_page_token")
        if token and len(businesses) < limit:
            import time; time.sleep(2)  # Google requires a short delay
            r2 = session.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"pagetoken": token, "key": api_key}, timeout=12)
            for p in r2.json().get("results", []):
                if len(businesses) >= limit:
                    break
                businesses.append({
                    "name": p.get("name", ""),
                    "website": "",
                    "phone": "",
                    "rating": p.get("rating"),
                    "source": "Google Maps",
                    "location": location,
                })
    except Exception as e:
        return [{"name": f"Google Maps error: {e}", "website": "", "phone": "",
                 "rating": None, "source": "Google Maps", "location": location}]
    return businesses


def search_yelp_api(keyword, location, api_key, limit=50):
    """Search via official Yelp Fusion API (requires free API key)."""
    try:
        r = requests.get(
            "https://api.yelp.com/v3/businesses/search",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"term": keyword, "location": location, "limit": min(limit, 50)},
            timeout=10,
        )
        data = r.json()
        results = []
        for b in data.get("businesses", []):
            results.append({
                "name": b.get("name", ""),
                "website": b.get("url", ""),
                "phone": b.get("display_phone", ""),
                "rating": b.get("rating"),
                "source": "Yelp",
                "location": location,
            })
        return results
    except Exception:
        return []


def search_local_businesses(keyword, location, sources, gmaps_api_key="", yelp_api_key="", limit=80):
    """Aggregate results from selected sources and audit each website."""
    all_biz = []
    seen_names = set()

    def add(biz_list):
        for b in biz_list:
            key = b["name"].lower().strip()
            if key not in seen_names:
                seen_names.add(key)
                all_biz.append(b)

    if "OpenStreetMap" in sources:
        add(search_osm(keyword, location, limit))

    if "Google Maps" in sources and gmaps_api_key:
        add(search_google_maps(keyword, location, gmaps_api_key, limit))

    if "Yelp" in sources and yelp_api_key:
        add(search_yelp_api(keyword, location, yelp_api_key, limit))

    # Audit websites concurrently
    import concurrent.futures
    def audit(biz):
        if biz.get("website"):
            biz["audit"] = _check_website(biz["website"])
        else:
            biz["audit"] = {}
        return biz

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        all_biz = list(ex.map(audit, all_biz))

    # Sort: most issues first
    all_biz.sort(key=lambda b: -len(_issues_summary(b)))
    return all_biz


CRAIGSLIST_CITIES = [
    "atlanta","austin","boston","chicago","dallas","denver","houston","losangeles",
    "miami","minneapolis","newyork","philadelphia","phoenix","portland","sandiego",
    "seattle","sfbay","washingtondc","vancouver","toronto","calgary","montreal",
    "london","sydney","melbourne","auckland","capetown","dubai","singapore",
]

# Human-readable labels for the UI
CRAIGSLIST_CITY_LABELS = {
    "atlanta": "Atlanta, GA", "austin": "Austin, TX", "boston": "Boston, MA",
    "chicago": "Chicago, IL", "dallas": "Dallas, TX", "denver": "Denver, CO",
    "houston": "Houston, TX", "losangeles": "Los Angeles, CA", "miami": "Miami, FL",
    "minneapolis": "Minneapolis, MN", "newyork": "New York, NY",
    "philadelphia": "Philadelphia, PA", "phoenix": "Phoenix, AZ",
    "portland": "Portland, OR", "sandiego": "San Diego, CA", "seattle": "Seattle, WA",
    "sfbay": "San Francisco Bay, CA", "washingtondc": "Washington, DC",
    "vancouver": "Vancouver, BC", "toronto": "Toronto, ON", "calgary": "Calgary, AB",
    "montreal": "Montreal, QC", "london": "London, UK", "sydney": "Sydney, AU",
    "melbourne": "Melbourne, AU", "auckland": "Auckland, NZ", "capetown": "Cape Town, ZA",
    "dubai": "Dubai, UAE", "singapore": "Singapore",
}

GRAB_LEADS_QUERIES = [
    "work from home", "make money online", "home business", "extra income",
    "side hustle", "earn extra cash", "online job",
]

# Reddit subreddits most likely to have people looking for freelancers / services
REDDIT_SUBREDDITS = [
    "forhire", "hiring", "slavelabour", "entrepreneur",
    "smallbusiness", "WorkOnline", "digitalnomad", "freelance",
]

def search_reddit(keyword, subreddits=None, limit=50):
    """Search Reddit via RSS (no API key needed, works without OAuth)."""
    if not SCRAPING_AVAILABLE:
        return []

    import xml.etree.ElementTree as ET
    chosen = subreddits if subreddits else REDDIT_SUBREDDITS
    multi  = "+".join(chosen)          # Reddit multi-subreddit syntax
    results = []
    seen = set()

    session = requests.Session()
    # Must use a browser User-Agent — Reddit blocks generic UA
    session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/125.0.0.0 Safari/537.36"})
    try:
        url = f"https://www.reddit.com/r/{multi}/search.rss"
        r = session.get(url, params={"q": keyword, "sort": "new",
                                     "restrict_sr": 1}, timeout=12)
        if r.status_code != 200:
            return []
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(r.text)
        for entry in root.findall("atom:entry", ns):
            link_el  = entry.find("atom:link", ns)
            title_el = entry.find("atom:title", ns)
            cat_el   = entry.find("atom:category", ns)
            href  = link_el.get("href", "") if link_el is not None else ""
            title = title_el.text or href if title_el is not None else href
            sub   = cat_el.get("label", "") if cat_el is not None else ""
            if href and href not in seen:
                seen.add(href)
                results.append({
                    "url":       href,
                    "title":     title,
                    "subreddit": sub,
                    "source":    "Reddit",
                })
                if len(results) >= limit:
                    break
    except Exception:
        pass
    return results


def search_upwork_rss(keyword, limit=40):
    """Search free job boards: RemoteOK API + We Work Remotely RSS."""
    if not SCRAPING_AVAILABLE:
        return []

    import xml.etree.ElementTree as ET
    results = []
    seen    = set()
    kw      = keyword.lower()
    ua      = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

    # ── 1. RemoteOK — JSON API, filter client-side ──────────────────────────
    try:
        r = requests.get("https://remoteok.com/api",
                         headers={"User-Agent": ua}, timeout=12)
        if r.status_code == 200:
            for job in r.json()[1:]:
                title = job.get("position", "")
                tags  = " ".join(job.get("tags") or [])
                if kw not in title.lower() and kw not in tags.lower():
                    continue
                url = (job.get("url") or
                       f"https://remoteok.com/remote-jobs/{job.get('id','')}")
                if url and url not in seen:
                    seen.add(url)
                    results.append({"url": url, "title": title, "source": "RemoteOK"})
    except Exception:
        pass

    # ── 2. We Work Remotely — RSS, filter client-side ───────────────────────
    try:
        r = requests.get("https://weworkremotely.com/remote-jobs.rss",
                         headers={"User-Agent": ua}, timeout=12)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            for item in root.iter("item"):
                title = getattr(item.find("title"), "text", "") or ""
                link  = getattr(item.find("link"),  "text", "") or ""
                desc  = getattr(item.find("description"), "text", "") or ""
                if kw not in title.lower() and kw not in desc.lower():
                    continue
                if link and link not in seen:
                    seen.add(link)
                    results.append({"url": link, "title": title,
                                    "source": "WeWorkRemotely"})
    except Exception:
        pass

    return results[:limit]


def scrape_craigslist(keyword, by_title=False, posted_today=False, cities=None):
    """Return list of matching Craigslist URLs across selected cities."""
    if not SCRAPING_AVAILABLE:
        return ["[requests not installed — run: pip install requests]"]

    results = []
    seen = set()

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})

    categories = ["cpg", "ggg"]  # computer gigs, general gigs
    city_list = cities if cities else CRAIGSLIST_CITIES

    for city in city_list:
        for cat in categories:
            try:
                params = {"s": keyword}
                if posted_today:
                    params["postedToday"] = "1"
                resp = session.get(
                    f"https://{city}.craigslist.org/jsonsearch/{cat}/",
                    params=params, timeout=8
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                clusters = data[0] if data and isinstance(data[0], list) else []

                for item in clusters:
                    # Single post — has a direct PostingURL
                    url = item.get("PostingURL", "")
                    if url and url not in seen:
                        title = item.get("PostingTitle", "")
                        if by_title:
                            if keyword.lower() not in title.lower():
                                continue
                        seen.add(url)
                        results.append(url)

                    # Geo-cluster — expand it
                    cluster_path = item.get("url", "")
                    if cluster_path and "geocluster" in cluster_path:
                        try:
                            cr = session.get(
                                f"https://{city}.craigslist.org{cluster_path}",
                                timeout=6
                            )
                            cdata = cr.json()
                            for sub in (cdata[0] if cdata and isinstance(cdata[0], list) else []):
                                sub_url = sub.get("PostingURL", "")
                                if sub_url and sub_url not in seen:
                                    title = sub.get("PostingTitle", "")
                                    if by_title and keyword.lower() not in title.lower():
                                        continue
                                    seen.add(sub_url)
                                    results.append(sub_url)
                        except Exception:
                            pass
            except Exception:
                continue

    return results if results else ["No results found."]


# ═══════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Money Generator Machine 2.0")
        self.geometry("760x520")
        self.resizable(True, True)
        self.configure(bg=BG_DARK)

        self.data = load_data()
        self._build_header()
        self._build_tabs()

    # ── header ─────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_DARK, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Money Generator Machine",
                 bg=BG_DARK, fg=FG_WHITE,
                 font=("Arial", 18, "bold")).pack(side="left", padx=14)

    # ── tab container ───────────────────────────────────────────────────────
    def _build_tabs(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook",        background=BG_DARK,  borderwidth=0)
        style.configure("TNotebook.Tab",    background="#c8c8c8", foreground=FG_DARK,
                        padding=[8, 3], font=("Arial", 8))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_LIGHT)],
                  foreground=[("selected", FG_DARK)])
        style.configure("TFrame", background=BG_LIGHT)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        tabs = [
            ("Find Leads",            self._tab_find_leads),
            ("Business Finder",       self._tab_business_finder),
            ("Message Generator",     self._tab_message_generator),
            ("Gig Sites",             self._tab_gig_sites),
            ("Clients Contact Details", self._tab_clients),
            ("Promotion",             self._tab_promotion),
            ("Grab Leads",            self._tab_grab_leads),
            ("URL",                   self._tab_url),
        ]
        for name, builder in tabs:
            frame = ttk.Frame(nb)
            nb.add(frame, text=name)
            builder(frame)

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _green_btn(parent, text, cmd, **kw):
        return tk.Button(parent, text=text, command=cmd,
                         bg=BTN_GREEN, fg=FG_WHITE, relief="flat",
                         font=("Arial", 9, "bold"), cursor="hand2",
                         padx=8, pady=3, **kw)

    @staticmethod
    def _blue_btn(parent, text, cmd, **kw):
        return tk.Button(parent, text=text, command=cmd,
                         bg=BTN_BLUE, fg=FG_WHITE, relief="flat",
                         font=("Arial", 9, "bold"), cursor="hand2",
                         padx=8, pady=3, **kw)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — Find Leads
    # ════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════
    # TAB — Business Finder
    # ════════════════════════════════════════════════════════════════════════
    def _tab_business_finder(self, parent):
        parent.configure(style="TFrame")

        # ── search bar ──────────────────────────────────────────────────────
        bar = tk.Frame(parent, bg=BG_LIGHT)
        bar.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(bar, text="Business type:", bg=BG_LIGHT).grid(row=0, column=0, sticky="e", padx=4)
        self._bf_keyword = tk.Entry(bar, width=22)
        self._bf_keyword.insert(0, "dentist")
        self._bf_keyword.grid(row=0, column=1, padx=4)

        tk.Label(bar, text="Location:", bg=BG_LIGHT).grid(row=0, column=2, sticky="e", padx=4)
        self._bf_location = tk.Entry(bar, width=22)
        self._bf_location.insert(0, "Chicago, IL")
        self._bf_location.grid(row=0, column=3, padx=4)

        self._green_btn(bar, "Find Businesses", self._do_biz_search).grid(
            row=0, column=4, padx=10)

        # ── API keys row ────────────────────────────────────────────────────
        key_row = tk.Frame(bar, bg=BG_LIGHT)
        key_row.grid(row=1, column=0, columnspan=7, sticky="w", pady=(4, 0))

        tk.Label(key_row, text="Sources:", bg=BG_LIGHT,
                 font=("Arial", 8, "bold")).pack(side="left", padx=(4,6))

        self._bf_osm   = tk.BooleanVar(value=True)
        self._bf_gmaps = tk.BooleanVar(value=False)
        self._bf_yelp  = tk.BooleanVar(value=False)
        tk.Checkbutton(key_row, text="OpenStreetMap (free)",
                       variable=self._bf_osm,   bg=BG_LIGHT).pack(side="left")
        tk.Checkbutton(key_row, text="Google Maps",
                       variable=self._bf_gmaps, bg=BG_LIGHT).pack(side="left", padx=(8,2))
        tk.Label(key_row, text="API key:", bg=BG_LIGHT, font=("Arial", 8)).pack(side="left")
        self._bf_gmaps_key = tk.Entry(key_row, width=30, show="*")
        self._bf_gmaps_key.pack(side="left", padx=(2, 10))

        tk.Checkbutton(key_row, text="Yelp",
                       variable=self._bf_yelp,  bg=BG_LIGHT).pack(side="left")
        tk.Label(key_row, text="API key:", bg=BG_LIGHT, font=("Arial", 8)).pack(side="left")
        self._bf_yelp_key = tk.Entry(key_row, width=30, show="*")
        self._bf_yelp_key.pack(side="left", padx=2)

        tk.Label(key_row,
                 text="  ← Get free keys: console.cloud.google.com  |  yelp.com/developers",
                 bg=BG_LIGHT, fg="gray", font=("Arial", 7)).pack(side="left", padx=6)

        # ── issue filter checkboxes ─────────────────────────────────────────
        flt = tk.Frame(parent, bg=BG_LIGHT)
        flt.pack(fill="x", padx=10, pady=2)
        tk.Label(flt, text="Show only businesses with:", bg=BG_LIGHT,
                 font=("Arial", 8, "bold")).pack(side="left", padx=4)
        self._bf_filters = {}
        for label in ["no website", "broken website", "slow website",
                      "no booking", "no chatbot", "poor reviews"]:
            v = tk.BooleanVar(value=False)
            self._bf_filters[label] = v
            tk.Checkbutton(flt, text=label, variable=v,
                           bg=BG_LIGHT, command=self._apply_biz_filter).pack(side="left")

        # ── results table ───────────────────────────────────────────────────
        tbl_frame = tk.Frame(parent, bg=BG_LIGHT)
        tbl_frame.pack(fill="both", expand=True, padx=10, pady=4)

        cols = ("Business", "Source", "Phone", "Rating", "Issues", "Website")
        self._bf_tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=12)
        widths = [180, 80, 110, 55, 260, 200]
        for col, w in zip(cols, widths):
            self._bf_tree.heading(col, text=col)
            self._bf_tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical",   command=self._bf_tree.yview)
        hsb = ttk.Scrollbar(tbl_frame, orient="horizontal",  command=self._bf_tree.xview)
        self._bf_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._bf_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        self._bf_tree.bind("<<TreeviewSelect>>", self._on_biz_select)

        # ── pitch panel ─────────────────────────────────────────────────────
        pitch_frame = tk.Frame(parent, bg=BG_LIGHT)
        pitch_frame.pack(fill="x", padx=10, pady=(2, 6))

        tk.Label(pitch_frame, text="Targeted pitch:", bg=BG_LIGHT,
                 font=("Arial", 8, "bold")).pack(anchor="w")
        self._bf_pitch = tk.Text(pitch_frame, height=4, wrap="word",
                                 font=("Arial", 9))
        self._bf_pitch.pack(fill="x", pady=2)

        btn_row = tk.Frame(pitch_frame, bg=BG_LIGHT)
        btn_row.pack(fill="x")
        self._green_btn(btn_row, "Copy Pitch",
                        self._copy_biz_pitch).pack(side="left", padx=4)
        self._green_btn(btn_row, "Open Website",
                        self._open_biz_website).pack(side="left", padx=4)
        self._green_btn(btn_row, "Export CSV",
                        self._export_biz_csv).pack(side="right", padx=4)

        self._bf_status = tk.Label(parent, text="", bg=BG_LIGHT, fg="gray")
        self._bf_status.pack()

        # internal store
        self._bf_all_results  = []
        self._bf_show_results = []

    def _do_biz_search(self):
        keyword  = self._bf_keyword.get().strip()
        location = self._bf_location.get().strip()
        if not keyword or not location:
            messagebox.showwarning("Input needed", "Enter a business type and location.")
            return
        sources = []
        if self._bf_osm.get():   sources.append("OpenStreetMap")
        if self._bf_gmaps.get(): sources.append("Google Maps")
        if self._bf_yelp.get():  sources.append("Yelp")
        if not sources:
            messagebox.showwarning("Sources", "Select at least one source.")
            return

        gmaps_key = self._bf_gmaps_key.get().strip()
        yelp_key  = self._bf_yelp_key.get().strip()
        if "Google Maps" in sources and not gmaps_key:
            messagebox.showwarning("Google Maps key",
                "Paste your Google Maps API key.\n\n"
                "Get a free key at console.cloud.google.com\n"
                "(Enable 'Places API' — $200 free credit/month included)")
            return
        if "Yelp" in sources and not yelp_key:
            messagebox.showwarning("Yelp API key", "Paste your Yelp API key to use Yelp.")
            return

        self._bf_status.config(text="Searching — please wait…")
        self._bf_tree.delete(*self._bf_tree.get_children())
        self._bf_pitch.delete("1.0", "end")

        def worker():
            try:
                results = search_local_businesses(
                    keyword, location, sources,
                    gmaps_api_key=gmaps_key, yelp_api_key=yelp_key)
                self.after(0, lambda: self._populate_biz_table(results))
            except Exception as e:
                self.after(0, lambda: self._bf_status.config(
                    text=f"Error: {e}", fg="red"))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_biz_table(self, results):
        self._bf_all_results  = results
        self._apply_biz_filter()
        count = len(self._bf_show_results)
        self._bf_status.config(
            text=f"{count} businesses found | {sum(1 for b in results if _issues_summary(b))} have issues")

    def _apply_biz_filter(self):
        active = [k for k, v in self._bf_filters.items() if v.get()]
        if active:
            filtered = []
            for b in self._bf_all_results:
                issues = _issues_summary(b)
                issue_str = " ".join(issues).lower()
                if any(f.replace("_", " ") in issue_str for f in active):
                    filtered.append(b)
        else:
            filtered = self._bf_all_results

        self._bf_show_results = filtered
        self._bf_tree.delete(*self._bf_tree.get_children())
        for b in filtered:
            issues = _issues_summary(b)
            tag = "problem" if issues else "ok"
            self._bf_tree.insert("", "end", values=(
                b.get("name", ""),
                b.get("source", ""),
                b.get("phone", ""),
                b.get("rating", "") or "N/A",
                ", ".join(issues) if issues else "✓ No obvious issues",
                b.get("website", "") or "(none)",
            ), tags=(tag,))
        self._bf_tree.tag_configure("problem", foreground="#c0392b")
        self._bf_tree.tag_configure("ok",      foreground="#27ae60")

    def _selected_biz(self):
        sel = self._bf_tree.selection()
        if not sel:
            return None
        idx = self._bf_tree.index(sel[0])
        if idx < len(self._bf_show_results):
            return self._bf_show_results[idx]
        return None

    def _on_biz_select(self, _event=None):
        biz = self._selected_biz()
        if not biz:
            return
        pitch = _build_pitch(biz)
        self._bf_pitch.delete("1.0", "end")
        self._bf_pitch.insert("1.0", pitch)

    def _copy_biz_pitch(self):
        text = self._bf_pitch.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)

    def _open_biz_website(self):
        biz = self._selected_biz()
        if biz:
            url = biz.get("website") or biz.get("yelp_url", "")
            if url:
                webbrowser.open(url)

    def _export_biz_csv(self):
        if not self._bf_show_results:
            messagebox.showinfo("Nothing to export", "Run a search first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Business", "Source", "Phone", "Rating",
                        "Website", "Issues", "Pitch"])
            for b in self._bf_show_results:
                issues = ", ".join(_issues_summary(b))
                w.writerow([b.get("name",""), b.get("source",""),
                             b.get("phone",""), b.get("rating",""),
                             b.get("website",""), issues, _build_pitch(b)])
        messagebox.showinfo("Exported", f"Saved to {path}")

    def _tab_find_leads(self, parent):
        parent.configure(style="TFrame")

        tk.Label(parent, text="Type in Keyword", bg=BG_LIGHT,
                 font=("Arial", 9, "bold")).pack(pady=(10, 0))
        tk.Label(parent, text="Example: logo design, marketing, website design needed",
                 bg=BG_LIGHT, font=("Arial", 8)).pack()

        opts = tk.Frame(parent, bg=BG_LIGHT)
        opts.pack(fill="x", padx=10, pady=4)

        self._by_title   = tk.BooleanVar()
        self._posted_today = tk.BooleanVar()
        tk.Checkbutton(opts, text="Search by Title", variable=self._by_title,
                       bg=BG_LIGHT).pack(side="left")
        tk.Checkbutton(opts, text="Posted Today", variable=self._posted_today,
                       bg=BG_LIGHT).pack(side="right")

        self._kw_entry = tk.Entry(parent, width=80)
        self._kw_entry.pack(padx=10, pady=2)

        # results listbox
        lf = tk.Frame(parent, bg=BG_LIGHT)
        lf.pack(fill="both", expand=True, padx=10, pady=4)
        tk.Label(lf, text="URL", bg=BG_LIGHT).pack()

        sb = tk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        self._results_lb = tk.Listbox(lf, yscrollcommand=sb.set, width=90, height=12)
        self._results_lb.pack(fill="both", expand=True)
        sb.config(command=self._results_lb.yview)
        self._results_lb.bind("<Double-Button-1>", self._open_selected_url)

        self._count_lbl = tk.Label(parent, text="", bg=BG_LIGHT)
        self._count_lbl.pack()

        self._status_lbl = tk.Label(parent, text="", bg=BG_LIGHT, fg="gray")
        self._status_lbl.pack()

        btn_row = tk.Frame(parent, bg=BG_LIGHT)
        btn_row.pack(pady=6)
        self._green_btn(btn_row, "Search", self._do_search).pack(side="left", padx=40)
        self._green_btn(btn_row, "Save",   self._save_results).pack(side="right", padx=40)

    def _open_selected_url(self, _event=None):
        sel = self._results_lb.curselection()
        if sel:
            url = self._results_lb.get(sel[0])
            if url.startswith("http"):
                webbrowser.open(url)

    def _do_search(self):
        keyword = self._kw_entry.get().strip()
        if not keyword:
            messagebox.showwarning("Input needed", "Please enter a keyword.")
            return
        self._results_lb.delete(0, "end")
        self._status_lbl.config(text="Scraping leads… Please wait!")
        self._count_lbl.config(text="")

        def worker():
            urls = scrape_craigslist(keyword,
                                     by_title=self._by_title.get(),
                                     posted_today=self._posted_today.get())
            self.after(0, lambda: self._populate_results(urls))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_results(self, urls):
        self._results_lb.delete(0, "end")
        for u in urls:
            self._results_lb.insert("end", u)
        self._status_lbl.config(text="Done.")
        self._count_lbl.config(text=f"Count: {len(urls)}")

    def _save_results(self):
        items = self._results_lb.get(0, "end")
        if not items:
            messagebox.showinfo("Nothing to save", "Run a search first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, "w") as f:
                f.write("\n".join(items))
            messagebox.showinfo("Saved", f"Results saved to {path}")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — Message Generator
    # ════════════════════════════════════════════════════════════════════════
    def _tab_message_generator(self, parent):
        parent.configure(style="TFrame")

        self._msg_text = tk.Text(parent, width=60, height=10, wrap="word")

        left = tk.Frame(parent, bg=BG_LIGHT)
        left.pack(side="left", padx=10, pady=10, fill="y")

        right = tk.Frame(parent, bg=BG_LIGHT)
        right.pack(side="left", padx=10, pady=10, fill="both", expand=True)

        def gen(pool):
            all_msgs = pool + self.data.get("messages", [])
            msg = random.choice(all_msgs) if all_msgs else "No messages available."
            self._msg_text.delete("1.0", "end")
            self._msg_text.insert("1.0", msg)

        self._green_btn(left, "Generate Intro Message",
                        lambda: gen(INTRO_MESSAGES)).pack(pady=4, fill="x")
        self._green_btn(left, "Generate 2nd Message",
                        lambda: gen(MSG2_MESSAGES)).pack(pady=4, fill="x")
        self._green_btn(left, "Generate 3rd Message",
                        lambda: gen(MSG3_MESSAGES)).pack(pady=4, fill="x")

        btn_row = tk.Frame(right, bg=BG_LIGHT)
        btn_row.pack(fill="x")
        self._green_btn(btn_row, "Copy",
                        lambda: self._copy_msg()).pack(side="right", padx=4, pady=2)
        self._green_btn(btn_row, "Save",
                        lambda: self._save_custom_msg()).pack(side="right", padx=4, pady=2)

        self._msg_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _copy_msg(self):
        text = self._msg_text.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)

    def _save_custom_msg(self):
        text = self._msg_text.get("1.0", "end").strip()
        if text:
            self.data.setdefault("messages", []).append(text)
            save_data(self.data)
            messagebox.showinfo("Saved", "Custom message saved.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — Gig Sites
    # ════════════════════════════════════════════════════════════════════════
    def _tab_gig_sites(self, parent):
        parent.configure(style="TFrame")

        tk.Label(parent, text="Freelancer Sites:", bg=BG_LIGHT,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))

        row1 = tk.Frame(parent, bg=BG_LIGHT)
        row1.pack(fill="x", padx=10)
        for name, url in GIG_SITES:
            self._green_btn(row1, name, lambda u=url: webbrowser.open(u)).pack(
                side="left", padx=4, pady=4)

        tk.Label(parent, text="Sites that Pay you:", bg=BG_LIGHT,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))

        row2 = tk.Frame(parent, bg=BG_LIGHT)
        row2.pack(fill="x", padx=10)
        for name, url in PAY_SITES[:6]:
            self._blue_btn(row2, name, lambda u=url: webbrowser.open(u)).pack(
                side="left", padx=4, pady=4)

        row3 = tk.Frame(parent, bg=BG_LIGHT)
        row3.pack(fill="x", padx=10)
        for name, url in PAY_SITES[6:]:
            self._blue_btn(row3, name, lambda u=url: webbrowser.open(u)).pack(
                side="left", padx=4, pady=4)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — Clients Contact Details
    # ════════════════════════════════════════════════════════════════════════
    def _tab_clients(self, parent):
        parent.configure(style="TFrame")

        form = tk.Frame(parent, bg=BG_LIGHT)
        form.pack(pady=20, padx=20, fill="x")

        labels = ["Name/Username", "Email", "Contact Number"]
        self._client_vars = [tk.StringVar() for _ in labels]

        for i, (lbl, var) in enumerate(zip(labels, self._client_vars)):
            tk.Label(form, text=lbl, bg=BG_LIGHT, width=16,
                     anchor="e").grid(row=i, column=0, pady=6, padx=4, sticky="e")
            tk.Entry(form, textvariable=var, width=36).grid(
                row=i, column=1, pady=6, padx=4, sticky="w")

        self._green_btn(form, "Save", self._save_client).grid(
            row=len(labels), column=1, pady=10, sticky="w")

        # saved clients list
        tk.Label(parent, text="Saved Clients", bg=BG_LIGHT,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=20)
        self._clients_lb = tk.Listbox(parent, height=8, width=70)
        self._clients_lb.pack(padx=20, pady=4, fill="both", expand=True)
        self._refresh_clients_lb()

        btn_row = tk.Frame(parent, bg=BG_LIGHT)
        btn_row.pack(pady=4)
        self._green_btn(btn_row, "Export CSV", self._export_clients).pack(side="left", padx=6)
        self._green_btn(btn_row, "Delete Selected", self._delete_client).pack(side="left", padx=6)

    def _save_client(self):
        vals = [v.get().strip() for v in self._client_vars]
        if not any(vals):
            return
        self.data.setdefault("clients", []).append(vals)
        save_data(self.data)
        for v in self._client_vars:
            v.set("")
        self._refresh_clients_lb()

    def _refresh_clients_lb(self):
        self._clients_lb.delete(0, "end")
        for c in self.data.get("clients", []):
            self._clients_lb.insert("end", "  |  ".join(c))

    def _delete_client(self):
        sel = self._clients_lb.curselection()
        if sel:
            del self.data["clients"][sel[0]]
            save_data(self.data)
            self._refresh_clients_lb()

    def _export_clients(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Name/Username", "Email", "Contact Number"])
                w.writerows(self.data.get("clients", []))
            messagebox.showinfo("Exported", f"Clients exported to {path}")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 — Promotion
    # ════════════════════════════════════════════════════════════════════════
    def _tab_promotion(self, parent):
        parent.configure(style="TFrame")

        row = tk.Frame(parent, bg=BG_LIGHT)
        row.pack(padx=10, pady=20, fill="x")
        for name, url in PROMO_SITES[:5]:
            self._green_btn(row, name, lambda u=url: webbrowser.open(u)).pack(
                side="left", padx=4, pady=4)

        row2 = tk.Frame(parent, bg=BG_LIGHT)
        row2.pack(padx=10, fill="x")
        for name, url in PROMO_SITES[5:]:
            self._green_btn(row2, name, lambda u=url: webbrowser.open(u)).pack(
                side="left", padx=4, pady=4)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 6 — Grab Leads
    # ════════════════════════════════════════════════════════════════════════
    def _tab_grab_leads(self, parent):
        parent.configure(style="TFrame")

        tk.Label(parent,
                 text="Click the button below to get automatic leads",
                 bg=BG_LIGHT, font=("Arial", 10, "bold")).pack(pady=(20, 4))
        tk.Label(parent,
                 text=("These are people looking to earn extra cash. "
                       "If you have a work from home business,\n"
                       "these are the leads you can promote your business to."),
                 bg=BG_LIGHT, justify="center").pack(pady=4)

        self._grab_lb = tk.Listbox(parent, height=10, width=90)
        self._grab_lb.pack(padx=20, pady=4, fill="both", expand=True)
        self._grab_lb.bind("<Double-Button-1>", self._open_grab_url)

        self._grab_status = tk.Label(parent, text="", bg=BG_LIGHT, fg="gray")
        self._grab_status.pack()

        self._green_btn(parent, "Search", self._do_grab_leads).pack(pady=8)

    def _open_grab_url(self, _=None):
        sel = self._grab_lb.curselection()
        if sel:
            url = self._grab_lb.get(sel[0])
            if url.startswith("http"):
                webbrowser.open(url)

    def _do_grab_leads(self):
        self._grab_lb.delete(0, "end")
        self._grab_status.config(text="Searching… Please wait!")

        def worker():
            query = random.choice(GRAB_LEADS_QUERIES)
            urls = scrape_craigslist(query)
            self.after(0, lambda: self._populate_grab(urls))

        threading.Thread(target=worker, daemon=True).start()

    def _populate_grab(self, urls):
        for u in urls:
            self._grab_lb.insert("end", u)
        self._grab_status.config(text=f"Done. {len(urls)} leads found.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 7 — URL
    # ════════════════════════════════════════════════════════════════════════
    def _tab_url(self, parent):
        parent.configure(style="TFrame")

        tk.Label(parent, text="Paste in URL", bg=BG_LIGHT,
                 font=("Arial", 10, "bold")).pack(pady=(20, 6))

        self._url_var = tk.StringVar(value=self.data.get("custom_url", ""))
        tk.Entry(parent, textvariable=self._url_var, width=60).pack(pady=4)

        btn_row = tk.Frame(parent, bg=BG_LIGHT)
        btn_row.pack(pady=8)
        self._green_btn(btn_row, "Open",
                        lambda: webbrowser.open(self._url_var.get())).pack(pady=4)
        self._green_btn(btn_row, "Clear",
                        lambda: self._url_var.set("")).pack(pady=4)


if __name__ == "__main__":
    app = App()
    app.mainloop()
