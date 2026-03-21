"""
OSI News Automation System - Article Generator
===============================================
Generates comprehensive news articles from trend clusters using Groq API (LLaMA).
Synthesizes multiple source articles into one balanced, well-structured article.
"""

import os
import sys
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter

from loguru import logger
from dotenv import load_dotenv

from src.content_generation.prompt_builder import (
    build_synthesis_prompt,
    detect_story_type,
    extract_source_digest,
    resolve_dateline,
    extract_newsworthiness_signals,
    parse_generated_article,
    SYSTEM_MESSAGE,
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()


# ===========================================
# GROQ CLIENT INITIALIZATION
# ===========================================

_groq_client = None


def get_groq_client():
    """
    Get or initialize the Groq client.
    
    Returns:
        Groq client instance or None if API key missing.
    """
    global _groq_client
    
    if _groq_client is not None:
        return _groq_client
    
    api_key = os.getenv('GROQ_API_KEY')
    
    if not api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        return None
    
    try:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
        logger.info("Groq client initialized successfully")
        return _groq_client
    except ImportError:
        logger.error("Groq package not installed. Run: pip install groq")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None





def validate_topic_focus(article: Dict, topic: str, source_articles: List[Dict]) -> Dict:
    """
    Validate that the generated article stays focused on the main topic.
    
    Checks for potential topic drift by looking for unrelated content.
    
    Args:
        article: Generated article dictionary
        topic: Main topic name
        source_articles: Original source articles
        
    Returns:
        Dictionary with validation results
    """
    story_lower = article.get('story', '').lower()
    heading_lower = article.get('heading', '').lower()
    topic_lower = topic.lower()
    
    # Common unrelated topic indicators
    unrelated_signals = {
        'sports': ['tennis', 'football', 'basketball', 'cricket', 'match', 'tournament', 
                  'championship', 'semifinals', 'finals', 'player', 'scored', 'defeated'],
        'entertainment': ['movie', 'film', 'actor', 'actress', 'celebrity', 'album', 
                         'concert', 'performance', 'singer', 'artist'],
        'conflict': ['war', 'military', 'conflict', 'gaza', 'ukraine', 'soldiers', 
                    'bombing', 'attack', 'humanitarian crisis'],
        'politics': ['election', 'government', 'president', 'parliament', 'minister', 
                    'political party', 'vote', 'legislation'],
        'weather': ['storm', 'hurricane', 'weather', 'temperature', 'forecast', 
                   'precipitation', 'climate pattern']
    }
    
    # Determine main topic category from the topic name
    main_category = None
    for category, keywords in unrelated_signals.items():
        if any(kw in topic_lower for kw in keywords):
            main_category = category
            break
    
    if not main_category:
        # Generic topic - less strict validation
        return {'is_focused': True, 'warnings': []}
    
    # Check for keywords from OTHER categories
    warnings = []
    detected_categories = set()
    
    for category, keywords in unrelated_signals.items():
        if category == main_category:
            continue
            
        # Check if unrelated keywords appear in the article
        found_keywords = [kw for kw in keywords if kw in story_lower or kw in heading_lower]
        
        if found_keywords:
            detected_categories.add(category)
            warnings.append(f"⚠️ Detected {category} content: {', '.join(found_keywords[:3])}")
    
    is_focused = len(detected_categories) == 0
    
    if not is_focused:
        logger.warning(f"Topic drift detected in article about '{topic}':")
        for warning in warnings:
            logger.warning(f"  {warning}")
    
    return {
        'is_focused': is_focused,
        'warnings': warnings,
        'detected_categories': list(detected_categories)
    }



# ===========================================
# DATELINE INFERENCE
# ===========================================

def infer_dateline(articles: List[Dict]) -> str:
    """
    Infer the dateline from source articles.
    
    Uses the most common location or defaults to NEW DELHI.
    
    Args:
        articles: List of source articles.
        
    Returns:
        Dateline string in uppercase.
    """
    locations = [a.get('location', 'Unknown') for a in articles]
    locations = [loc for loc in locations if loc and loc != 'Unknown']
    
    if not locations:
        return "NEW DELHI"
    
    location_counts = Counter(locations)
    most_common = location_counts.most_common(1)[0][0]
    
    return most_common.upper()


def format_timestamp(timezone: str = 'Asia/Kolkata') -> str:
    """
    Format current timestamp for article.
    
    Args:
        timezone: Timezone string.
        
    Returns:
        Formatted timestamp string.
    """
    try:
        import pytz
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        return now.strftime('%A, %B %d, %Y, %I:%M %p IST')
    except ImportError:
        # Fallback without timezone
        return datetime.now().strftime('%A, %B %d, %Y, %I:%M %p')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ===========================================
# MAIN GENERATION FUNCTION
# ===========================================

def generate_article(
    trend: Dict, 
    target_words: int = 800,
    max_retries: int = 3,
    include_subheadings: bool = True
) -> Optional[Dict]:
    """
    Generate a comprehensive article from a trend cluster using Groq API.
    
    Takes multiple source articles about a topic and synthesizes them
    into one well-structured, comprehensive news article.
    
    Args:
        trend: Trend dictionary with 'topic', 'articles', and 'keywords'.
        target_words: Minimum word count for generated article.
        max_retries: Maximum retry attempts on failure.
        include_subheadings: Whether to include subheadings.
        
    Returns:
        Generated article dictionary with:
        - heading: Article headline
        - story: Full article text
        - dateline: Location dateline
        - timestamp: Generation timestamp
        - sources_used: List of source names
        - word_count: Final word count
        - source_count: Number of source articles used
        
    Example:
        >>> article = generate_article(trend_data, target_words=800)
        >>> print(article['heading'])
        >>> print(f"Word count: {article['word_count']}")
    """
    if not trend or 'articles' not in trend:
        logger.error("Invalid trend data provided")
        return None
    
    source_articles = trend.get('articles', [])
    topic = trend.get('topic', 'News Update')
    
    if not source_articles:
        logger.error("No source articles in trend")
        return None
    
    # Get Groq client
    client = get_groq_client()
    
    if not client:
        logger.warning("Groq client unavailable, using fallback")
        return generate_fallback_article(trend)
    
    # Build prompt — dateline resolved once, shared by prompt and metadata
    system_msg, user_prompt, dateline, story_type = build_synthesis_prompt(
        articles=source_articles,
        topic=topic,
        target_words=target_words,
        include_subheadings=include_subheadings,
    )
    
    # Dynamic max_tokens based on target word count
    max_tokens = min(2300, int(target_words * 1.45) + 300)
    
    logger.info(f"🖊️ Generating article for trend: '{topic}'")
    logger.info(f"   Sources: {len(source_articles)} articles")
    logger.info(f"   Story type: {story_type.name}")
    
    # Attempt generation with retries
    for attempt in range(max_retries):
        try:
            # Call Groq API
            model = os.getenv('GROQ_MODEL', 'llama3-70b-8192')
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.28,
                max_tokens=max_tokens,
                top_p=0.9,
            )
            
            # Extract generated content
            generated_text = response.choices[0].message.content
            
            if not generated_text:
                logger.warning(f"Empty response from Groq (attempt {attempt + 1})")
                continue
            
            # Parse article
            article = parse_generated_article(generated_text)
            
            # Validate
            word_count = len(article['story'].split())
            
            if word_count < 300:
                logger.warning(f"Article too short ({word_count} words), retrying...")
                continue
            
            # Add metadata
            article.update({
                "dateline":     dateline,
                "topic":        topic,
                "timestamp":    format_timestamp(),
                "sources_used": list({a.get("source_name", "Unknown") for a in source_articles}),
                "source_count": len(source_articles),
                "word_count":   len(article["story"].split()),
                "keywords":     trend.get("keywords", [])[:10],
                "generated_at": datetime.utcnow().isoformat(),
                "model_used":   model,
                "story_type":   story_type.name,
            })
            
            logger.info(f"✅ Generated article: '{article['heading'][:50]}...'")
            logger.info(f"   Word count: {article['word_count']}")
            logger.info(f"   Dateline: {article['dateline']}")
            
            return article
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle rate limiting
            if '429' in error_msg or 'rate' in error_msg.lower():
                wait_time = 60 * (attempt + 1)  # Exponential backoff
                logger.warning(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # Handle timeout
            if 'timeout' in error_msg.lower():
                logger.warning(f"Timeout on attempt {attempt + 1}")
                continue
            
            logger.error(f"Generation error (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                logger.error("Max retries reached, using fallback")
                return generate_fallback_article(trend)
    
    return generate_fallback_article(trend)


def generate_fallback_article(trend: Dict) -> Optional[Dict]:
    """
    Generate a simple fallback article without LLM.
    
    Used when Groq API is unavailable or fails.
    
    Args:
        trend: Trend dictionary with articles.
        
    Returns:
        Simple article dictionary.
    """
    try:
        source_articles = trend.get('articles', [])
        topic = trend.get('topic', 'News Update')
        
        if not source_articles:
            return None
        
        # Create simple headline
        heading = f"Multiple Sources Report on {topic}"
        
        # Combine article summaries
        story_parts = [f"**{topic}**\n"]
        
        dateline = infer_dateline(source_articles)
        story_parts.append(f"{dateline}, {datetime.now().strftime('%B %d')} – ")
        story_parts.append(f"Multiple news sources are reporting on developments related to {topic}.\n\n")
        
        for i, article in enumerate(source_articles[:5], 1):
            source = article.get('source_name', 'Unknown')
            headline = article.get('heading', '')
            preview = article.get('story', '')[:200]
            
            story_parts.append(f"## Report from {source}\n\n")
            story_parts.append(f"**{headline}**\n\n")
            story_parts.append(f"{preview}...\n\n")
        
        story = ''.join(story_parts)
        
        return {
            "heading": heading,
            "story": story,
            "dateline": dateline,
            "timestamp": format_timestamp(),
            "sources_used": [a.get('source_name', 'Unknown') for a in source_articles],
            "word_count": len(story.split()),
            "source_count": len(source_articles),
            "topic": topic,
            "keywords": trend.get('keywords', []),
            "generated_at": datetime.utcnow().isoformat(),
            "model_used": "fallback",
            "is_fallback": True
        }
        
    except Exception as e:
        logger.error(f"Fallback generation failed: {e}")
        return None


def generate_articles_for_trends(
    trends: List[Dict],
    target_words: int = 800,
    max_articles: int = 5
) -> List[Dict]:
    """
    Generate articles for multiple trends.
    
    Args:
        trends: List of trend dictionaries.
        target_words: Target word count per article.
        max_articles: Maximum number of articles to generate.
        
    Returns:
        List of generated article dictionaries.
    """
    generated = []
    
    for i, trend in enumerate(trends[:max_articles]):
        logger.info(f"\nGenerating article {i + 1}/{min(len(trends), max_articles)}...")
        
        article = generate_article(trend, target_words)
        
        if article:
            generated.append(article)
        
        # Small delay between generations to avoid rate limits
        if i < len(trends) - 1:
            time.sleep(2)
    
    logger.info(f"Generated {len(generated)} articles from {len(trends)} trends")
    return generated


# ===========================================
# TESTING
# ===========================================

def test_article_generator():
    """Test article generation with sample trend."""
    print("\n" + "="*60)
    print("🧪 Article Generator Test")
    print("="*60)
    
    # Check Groq API key
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("\n⚠️ GROQ_API_KEY not set in environment")
        print("   Set it in .env file or environment variables")
        print("   Get free API key at: https://console.groq.com/")
        print("\n   Testing fallback generation instead...\n")
    
    # Create test trend
    test_trend = {
        "topic": "Global Climate Summit",
        "keywords": ["climate", "summit", "emissions", "agreement"],
        "articles": [
            {
                "heading": "World leaders reach historic climate agreement",
                "story": "In a landmark decision, world leaders at the Global Climate Summit have agreed to reduce carbon emissions by 50% by 2030. The agreement covers over 190 countries and includes financial commitments to support developing nations in their transition to clean energy. Environmental groups have cautiously welcomed the deal.",
                "source_name": "BBC News",
                "location": "Paris"
            },
            {
                "heading": "Climate summit produces breakthrough on emissions",
                "story": "After days of intense negotiations, delegates at the climate summit have reached a breakthrough agreement on emissions targets. The deal sets binding targets for major polluters and establishes a new fund for climate adaptation. Critics say the targets don't go far enough to limit warming to 1.5 degrees.",
                "source_name": "Reuters",
                "location": "Paris"
            },
            {
                "heading": "Environmental groups react to climate deal",
                "story": "Environmental organizations have given mixed reactions to the new climate agreement. While some praised the historic nature of the deal, others criticized the lack of enforcement mechanisms. Youth activists called for more ambitious action to address the climate crisis.",
                "source_name": "The Guardian",
                "location": "London"
            }
        ]
    }
    
    print(f"📰 Test trend: {test_trend['topic']}")
    print(f"   Sources: {len(test_trend['articles'])} articles")
    print("-" * 40)
    
    article = generate_article(test_trend, target_words=600)
    
    if article:
        print(f"\n✅ Article generated successfully!")
        print(f"\n📝 Headline: {article['heading']}")
        print(f"📍 Dateline: {article['dateline']}")
        print(f"📊 Word count: {article['word_count']}")
        print(f"📰 Sources: {', '.join(article['sources_used'])}")
        print(f"🤖 Model: {article.get('model_used', 'unknown')}")
        
        # Show preview
        preview = article['story'][:500]
        print(f"\n📖 Preview:\n{preview}...")
    else:
        print("\n❌ Article generation failed")
    
    print("\n" + "="*60 + "\n")
    
    return article


if __name__ == "__main__":
    test_article_generator()
