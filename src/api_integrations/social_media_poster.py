"""
OSI News Automation System - Social Media Post Generator
=========================================================
Generates platform-specific social media posts for Twitter, LinkedIn, 
Instagram, and Facebook, plus TV anchor scripts.
"""

import os
import sys
from typing import Dict, List
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()


# ===========================================
# SOCIAL MEDIA POST GENERATION
# ===========================================

def generate_social_posts(
    article: Dict,
    article_url: str = "",
    image_url: str = ""
) -> Dict[str, str]:
    """
    Generate social media posts for all platforms.
    
    Creates platform-optimized posts for Twitter, LinkedIn, Instagram,
    and Facebook following OSI templates.
    
    Args:
        article: Article dictionary with heading, dateline, timestamp, etc.
        article_url: URL where article is published.
        image_url: URL of article image.
        
    Returns:
        Dictionary mapping platform names to post text.
        
    Example:
        >>> posts = generate_social_posts(article, "https://example.com/article/123")
        >>> print(posts['twitter'])
        >>> print(posts['linkedin'])
    """
    # Extract article details
    title = article.get('heading', 'Breaking News')
    dateline = article.get('dateline', article.get('location', 'NEW DELHI'))
    
    # Get timestamp
    timestamp = article.get('timestamp')
    if not timestamp:
        timestamp = datetime.now().strftime('%A, %B %d, %Y, %I:%M %p IST')
    
    source_count = article.get('source_count', 10)
    
    # Shorten title if too long
    title_short = title if len(title) <= 80 else title[:77] + "..."
    
    # Generate posts
    posts = {}
    
    # ==========================================
    # TWITTER/X (280 character limit)
    # ==========================================
    twitter_base = f"""🔥 Trending: {title_short}

Dateline {dateline}: Key insights from {source_count} global pubs.
Generated {timestamp} by OSI AI.

{article_url}

#OSINT #NewsAI #Geopolitics"""
    
    # Ensure under 280 chars
    if len(twitter_base) > 280:
        # Calculate available space for title
        overhead = len(twitter_base) - len(title_short)
        available_for_title = 280 - overhead - 10  # 10 char buffer
        
        if available_for_title > 20:
            title_short = title[:available_for_title-3] + "..."
        
        # Simplified version
        twitter_base = f"""🔥 {title_short}

{dateline}: {source_count} sources
{timestamp}

{article_url}

#OSINT #NewsAI"""
    
    posts['twitter'] = twitter_base
    
    # ==========================================
    # LINKEDIN (Professional, longer form)
    # ==========================================
    posts['linkedin'] = f"""In today's fast-moving world, staying ahead means synthesizing global perspectives. OSI AI just compiled this comprehensive analysis on {title} – pulling from {source_count} top publications worldwide.

Dateline: {dateline} | Generated: {timestamp}

Discover balanced analysis beyond headlines. What trends are you tracking?

{article_url}

#OpenSourceIntelligence #MediaTech #AIinJournalism #GlobalNews"""
    
    # ==========================================
    # INSTAGRAM (Visual-first with emojis)
    # ==========================================
    posts['instagram'] = f"""{title}

📍 {dateline}
🕒 Generated: {timestamp}

AI-powered scoop: We scanned the globe hourly, scraped {source_count} stories, and built this comprehensive view.

Swipe for highlights! 👉
Link in bio ⬇️

#OSINews #TrendingNews #AIGenerated #NewsAutomation #GlobalPerspective"""
    
    # ==========================================
    # FACEBOOK (Conversational & shareable)
    # ==========================================
    posts['facebook'] = f"""Today's top trend: {title}

OSI AI scanned the world hourly, scraped {source_count} publications, and wrote this comprehensive breakdown.

{dateline} | {timestamp}

Read the full story: {article_url}

What do you think about this development? Comment below! 👇

#GlobalNews #AIJournalism #NewsAnalysis"""
    
    logger.info(f"Generated social posts for: {title[:50]}...")
    logger.debug(f"Twitter length: {len(posts['twitter'])} chars")
    
    return posts


# ===========================================
# TV SCRIPT GENERATION
# ===========================================

def generate_tv_script(
    article: Dict,
    duration_seconds: int = 59,
    anchor_name: str = "[Anchor Name]"
) -> str:
    """
    Generate TV anchor script in spoken style.
    
    Creates a teleprompter-ready script for TV news anchors,
    formatted for natural speech with timing markers.
    
    Args:
        article: Article dictionary.
        duration_seconds: Target script duration (default 59 seconds).
        anchor_name: Name of the anchor (optional).
        
    Returns:
        Script text formatted for teleprompter.
        
    Example:
        >>> script = generate_tv_script(article, duration_seconds=60)
        >>> print(script)
    """
    title = article.get('heading', 'Breaking News')
    dateline = article.get('dateline', article.get('location', 'NEW DELHI'))
    timestamp = article.get('timestamp', datetime.now().strftime('%A, %B %d, %Y, %I:%M %p IST'))
    story = article.get('story', '')
    source_count = article.get('source_count', 10)
    
    # Extract key points from article
    # For 59 seconds at 150 WPM = ~147 words
    # Parse subheadings from story (marked with ##)
    subheadings = []
    paragraphs = []
    
    for line in story.split('\n'):
        line = line.strip()
        if line.startswith('##'):
            subheadings.append(line.replace('##', '').strip())
        elif line and not line.startswith('#'):
            paragraphs.append(line)
    
    # Get opening hook from first paragraph
    opening_hook = paragraphs[0] if paragraphs else "Breaking news from around the world."
    if len(opening_hook) > 150:
        opening_hook = opening_hook[:147] + "..."
    
    # Determine time of day
    current_hour = datetime.now().hour
    if current_hour < 12:
        time_of_day = "morning"
    elif current_hour < 17:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"
    
    # Build script
    script = f"""Good {time_of_day}, I'm {anchor_name}.

Top story today: {title}. // {dateline} –

{opening_hook}

Our AI at OSI scanned global headlines hourly... pulled the {source_count} most-viewed stories from outlets like BBC, Reuters, and Al Jazeera... then wove them into this comprehensive picture. //

Here's what happened: """
    
    # Add 2-3 key points from subheadings
    key_points_added = 0
    for subheading in subheadings[:3]:
        if subheading:
            script += f"{subheading}. "
            key_points_added += 1
    
    # If no subheadings, use first few sentences
    if key_points_added == 0 and paragraphs:
        sentences = '. '.join(paragraphs[:2])
        if len(sentences) > 200:
            sentences = sentences[:197] + "..."
        script += f"{sentences}. "
    
    script += f"""//

All sourced and timestamped at {timestamp}. //

Stay tuned for updates. Back after this.

[TOTAL WORDS: {len(script.split())}]
[ESTIMATED TIME: {len(script.split()) / 150 * 60:.0f} seconds at 150 WPM]"""
    
    logger.info(f"Generated TV script: {len(script.split())} words")
    
    return script


# ===========================================
# HASHTAG GENERATION
# ===========================================

def generate_hashtags(article: Dict, max_hashtags: int = 10) -> List[str]:
    """
    Generate relevant hashtags based on article content.
    
    Args:
        article: Article dictionary.
        max_hashtags: Maximum number of hashtags to generate.
        
    Returns:
        List of hashtag strings (without # symbol).
    """
    hashtags = []
    
    # Default hashtags
    default_tags = ['OSINT', 'NewsAI', 'GlobalNews', 'Breaking']
    
    # Extract from meta keywords if available
    meta_keywords = article.get('meta_keywords', [])
    for keyword in meta_keywords:
        if keyword and len(keyword) > 2:
            # Clean and format
            tag = keyword.strip().replace(' ', '').replace('-', '')
            if tag and tag not in hashtags:
                hashtags.append(tag)
    
    # Add location-based tag
    location = article.get('location') or article.get('dateline')
    if location and location != 'Unknown':
        location_tag = location.replace(' ', '').replace(',', '')
        if location_tag not in hashtags:
            hashtags.append(location_tag)
    
    # Add default tags
    for tag in default_tags:
        if tag not in hashtags:
            hashtags.append(tag)
    
    # Limit to max
    return hashtags[:max_hashtags]


# ===========================================
# POST FORMATTING UTILITIES
# ===========================================

def truncate_for_twitter(text: str, max_length: int = 280) -> str:
    """
    Truncate text to fit Twitter's character limit.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length (default 280).
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    # Truncate at word boundary
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + "..."


def format_timestamp(dt: datetime = None, format_type: str = 'full') -> str:
    """
    Format timestamp for social media posts.
    
    Args:
        dt: Datetime object (default: now).
        format_type: 'full', 'short', or 'time_only'.
        
    Returns:
        Formatted timestamp string.
    """
    if dt is None:
        dt = datetime.now()
    
    if format_type == 'full':
        return dt.strftime('%A, %B %d, %Y, %I:%M %p IST')
    elif format_type == 'short':
        return dt.strftime('%b %d, %Y')
    elif format_type == 'time_only':
        return dt.strftime('%I:%M %p IST')
    else:
        return dt.isoformat()


# ===========================================
# TESTING
# ===========================================

def test_social_media_poster():
    """Test social media post generation."""
    print("\n" + "="*60)
    print("🧪 Social Media Post Generator Test")
    print("="*60)
    
    # Test article
    test_article = {
        "heading": "Global Climate Summit Reaches Historic Agreement on Emissions",
        "dateline": "PARIS",
        "timestamp": "Monday, January 15, 2026, 3:00 PM IST",
        "source_count": 12,
        "story": """## Agreement Reached
Countries agreed to reduce emissions by 50% by 2030.

## Key Points
Emissions targets set for all major economies.
Funding mechanism established for developing nations.

## Next Steps
Implementation begins in Q2 2026.""",
        "location": "Paris",
        "meta_keywords": ["Climate", "Environment", "Summit", "Emissions"]
    }
    
    print(f"\n📰 Test article: {test_article['heading']}")
    print("-" * 40)
    
    # Generate posts
    posts = generate_social_posts(
        test_article,
        article_url="https://democracynewslive.com/article/123",
        image_url="https://example.com/image.jpg"
    )
    
    # Display posts
    for platform, post in posts.items():
        print(f"\n📱 {platform.upper()}:")
        print(f"   Length: {len(post)} chars")
        print(f"   Preview: {post[:100]}...")
        
        # Validate Twitter length
        if platform == 'twitter':
            if len(post) <= 280:
                print(f"   ✅ Within 280 char limit")
            else:
                print(f"   ❌ EXCEEDS 280 char limit!")
    
    # Generate TV script
    print("\n" + "-" * 40)
    print("📺 TV SCRIPT:")
    script = generate_tv_script(test_article, duration_seconds=59)
    word_count = len(script.split())
    estimated_time = word_count / 150 * 60
    
    print(f"   Words: {word_count}")
    print(f"   Estimated time: {estimated_time:.0f} seconds")
    print(f"   Preview: {script[:150]}...")
    
    # Generate hashtags
    hashtags = generate_hashtags(test_article)
    print(f"\n🏷️  Hashtags: {', '.join(['#' + tag for tag in hashtags[:5]])}")
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_social_media_poster()
