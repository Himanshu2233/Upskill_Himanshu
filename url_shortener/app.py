# app.py - URL Shortener Application (Final Version)
import random
import string
from urllib.parse import urlparse                        # ← validates URLs
from flask import Flask, redirect, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ─────────────────────────────────────────
# DATABASE MODEL
# ─────────────────────────────────────────
class URL(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    original   = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    clicks     = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<URL {self.short_code} → {self.original}>'


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def generate_short_code(length=6):
    """Generates a unique 6-character alphanumeric code."""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if not URL.query.filter_by(short_code=code).first():
            return code


def is_valid_url(url):
    """Returns True if the URL has a valid scheme (http/https) and hostname."""
    try:
        result = urlparse(url)
        return result.scheme in ('http', 'https') and bool(result.netloc)
    except Exception:
        return False


def get_stats():
    """Returns (total_urls, total_clicks) for the stats section."""
    total_urls   = URL.query.count()
    total_clicks = db.session.query(db.func.sum(URL.clicks)).scalar() or 0
    return total_urls, total_clicks


def get_recent_links(limit=5):
    """Returns the most recently added URLs."""
    return URL.query.order_by(URL.id.desc()).limit(limit).all()


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

# ─────────────────────────────────────────
# API ROUTE — returns live data as JSON
# ─────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    """
    This is a mini API endpoint.
    Instead of returning HTML, it returns JSON — raw data.
    JavaScript will call this every few seconds to update the page live.
    """
    total_urls, total_clicks = get_stats()
    recent = get_recent_links()

    # Build a list of recent links as plain Python dicts
    recent_data = [
        {
            'original':   url.original,
            'short_code': url.short_code,
            'clicks':     url.clicks
        }
        for url in recent
    ]

    # jsonify() converts a Python dict → JSON response
    return jsonify({
        'total_urls':   total_urls,
        'total_clicks': total_clicks,
        'recent':       recent_data
    })


# HOME PAGE
@app.route('/')
def home():
    total_urls, total_clicks = get_stats()
    recent = get_recent_links()
    return render_template('index.html',
                           total_urls=total_urls,
                           total_clicks=total_clicks,
                           recent=recent)


# SHORTEN ROUTE
@app.route('/shorten', methods=['POST'])
def shorten():
    original_url             = request.form.get('original_url', '').strip()
    total_urls, total_clicks = get_stats()
    recent                   = get_recent_links()

    # Validation 1 — empty input
    if not original_url:
        return render_template('index.html', error='Please enter a URL!',
                               total_urls=total_urls, total_clicks=total_clicks,
                               recent=recent)

    # Validation 2 — not a real URL
    if not is_valid_url(original_url):
        return render_template('index.html',
                               error='Invalid URL. Make sure it starts with http:// or https://',
                               total_urls=total_urls, total_clicks=total_clicks,
                               recent=recent)

    # Already shortened before? Return existing code
    existing = URL.query.filter_by(original=original_url).first()
    if existing:
        short_url = request.host_url + existing.short_code
        return render_template('index.html', short_url=short_url,
                               total_urls=total_urls, total_clicks=total_clicks,
                               recent=recent)

    # New URL — generate code and save
    code    = generate_short_code()
    new_url = URL(original=original_url, short_code=code)
    db.session.add(new_url)
    db.session.commit()

    short_url                = request.host_url + code
    total_urls, total_clicks = get_stats()
    recent                   = get_recent_links()
    return render_template('index.html', short_url=short_url,
                           total_urls=total_urls, total_clicks=total_clicks,
                           recent=recent)


# REDIRECT ROUTE
@app.route('/<short_code>')
def redirect_url(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()
    if url_entry:
        url_entry.clicks += 1
        db.session.commit()
        return redirect(url_entry.original)
    # Show a nice 404 page
    return render_template('404.html'), 404


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('✅ Database ready!')
    app.run(debug=True)
