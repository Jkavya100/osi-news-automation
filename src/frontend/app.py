"""
OSI News Automation System - Results Viewer Frontend
=====================================================
A Flask-based web interface to view scraped articles and their formatting.
"""

import os
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

# Get absolute path to project root (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Add project root to path for imports
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv(PROJECT_ROOT / '.env')

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Data storage
SCRAPED_ARTICLES = []
OUTPUT_DIR = PROJECT_ROOT / 'output' / 'json'


def ensure_output_dir():
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', 
                         article_count=len(SCRAPED_ARTICLES),
                         last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/api/articles')
def get_articles():
    """Get all scraped articles as JSON."""
    return jsonify({
        'status': 'success',
        'count': len(SCRAPED_ARTICLES),
        'articles': SCRAPED_ARTICLES
    })


@app.route('/api/articles/<int:index>')
def get_article(index):
    """Get single article by index."""
    if 0 <= index < len(SCRAPED_ARTICLES):
        return jsonify({
            'status': 'success',
            'article': SCRAPED_ARTICLES[index]
        })
    return jsonify({'status': 'error', 'message': 'Article not found'}), 404


@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Trigger a new scraping run."""
    global SCRAPED_ARTICLES
    
    try:
        max_articles = 10
        if request.json:
            max_articles = request.json.get('max_articles', 10)
        
        # Import here to ensure proper path setup
        from src.scrapers.batch_scraper import scrape_news_batch
        
        print(f"Starting scrape for {max_articles} articles...")
        articles = scrape_news_batch(max_articles=max_articles)
        SCRAPED_ARTICLES = articles
        
        # Save to JSON
        filepath = save_articles_to_json(articles)
        print(f"Saved to: {filepath}")
        
        return jsonify({
            'status': 'success',
            'message': f'Scraped {len(articles)} articles',
            'count': len(articles)
        })
    except Exception as e:
        print(f"Scrape error: {e}")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/save', methods=['POST'])
def save_to_json_route():
    """Save current articles to JSON file."""
    if not SCRAPED_ARTICLES:
        return jsonify({'status': 'error', 'message': 'No articles to save'}), 400
    
    filepath = save_articles_to_json(SCRAPED_ARTICLES)
    return jsonify({
        'status': 'success',
        'message': f'Saved {len(SCRAPED_ARTICLES)} articles',
        'filepath': str(filepath)
    })


@app.route('/api/load', methods=['POST'])
def load_from_json():
    """Load articles from a JSON file."""
    global SCRAPED_ARTICLES
    
    try:
        filename = None
        if request.json:
            filename = request.json.get('filename')
        
        if filename:
            filepath = OUTPUT_DIR / filename
        else:
            # Load most recent file
            ensure_output_dir()
            json_files = list(OUTPUT_DIR.glob('scraped_*.json'))
            if not json_files:
                return jsonify({'status': 'error', 'message': 'No saved files found'}), 404
            filepath = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            SCRAPED_ARTICLES = data.get('articles', data)
        
        return jsonify({
            'status': 'success',
            'message': f'Loaded {len(SCRAPED_ARTICLES)} articles',
            'filepath': str(filepath)
        })
    except Exception as e:
        print(f"Load error: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def save_articles_to_json(articles):
    """Save articles to JSON file."""
    ensure_output_dir()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'scraped_{timestamp}.json'
    filepath = OUTPUT_DIR / filename
    
    data = {
        'scraped_at': datetime.now().isoformat(),
        'count': len(articles),
        'articles': articles
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Saved articles to: {filepath}")
    return filepath


def load_articles(articles_list):
    """Load articles into the global state."""
    global SCRAPED_ARTICLES
    SCRAPED_ARTICLES = articles_list


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌐 OSI News Automation - Results Viewer")
    print("="*60)
    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Output dir: {OUTPUT_DIR}")
    print("\nStarting server at http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
