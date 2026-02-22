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


# ===========================================
# PROMPT BUILDING
# ===========================================

def detect_story_type(articles: List[Dict], topic: str) -> str:
    """
    Detect story type based on keywords and content.
    
    Returns: 'scientific', 'economic', 'social', 'political', or 'general'
    """
    combined_text = topic.lower() + " "
    for article in articles[:5]:
        combined_text += article.get('heading', '').lower() + " "
        combined_text += article.get('story', '')[:200].lower() + " "
    
    # Scientific indicators
    scientific_keywords = ['study', 'research', 'findings', 'scientist', 'discovery', 
                          'breakthrough', 'published', 'journal', 'peer-reviewed', 
                          'experiment', 'data', 'clinical', 'medical']
    
    # Economic indicators
    economic_keywords = ['economy', 'market', 'gdp', 'inflation', 'stock', 'trade',
                        'financial', 'investment', 'currency', 'recession', 'growth',
                        'employment', 'industry', 'revenue', 'profit']
    
    # Social/Cultural indicators
    social_keywords = ['trend', 'social', 'cultural', 'generation', 'adoption',
                      'behavior', 'demographic', 'movement', 'community', 'society',
                      'lifestyle', 'millennials', 'gen z', 'viral']
    
    # Count matches
    scientific_count = sum(1 for kw in scientific_keywords if kw in combined_text)
    economic_count = sum(1 for kw in economic_keywords if kw in combined_text)
    social_count = sum(1 for kw in social_keywords if kw in combined_text)
    
    # Determine type based on highest count
    if scientific_count >= 3:
        return 'scientific'
    elif economic_count >= 3:
        return 'economic'
    elif social_count >= 3:
        return 'social'
    else:
        return 'general'


def build_synthesis_prompt(
    articles: List[Dict], 
    topic: str, 
    target_words: int,
    include_subheadings: bool = True
) -> str:
    """
    Build the ENHANCED prompt for article synthesis with specialized protocols.
    
    Args:
        articles: List of source articles.
        topic: The trend topic name.
        target_words: Target word count.
        include_subheadings: Whether to include subheadings.
        
    Returns:
        Formatted prompt string with specialized protocol activation.
    """
    # Detect story type
    story_type = detect_story_type(articles, topic)
    
    # Prepare source summaries (limit to 10 articles, 500 chars each)
    source_summaries = []
    
    for i, article in enumerate(articles[:10], 1):
        source_name = article.get('source_name', 'Unknown Source')
        heading = article.get('heading', 'No headline')
        story = article.get('story', '')[:500]  # First 500 chars
        location = article.get('location', 'Unknown')
        
        summary = f"""Source {i} ({source_name}, {location}):
Headline: {heading}
Content: {story}..."""
        
        source_summaries.append(summary)
    
    # Build subheadings instruction
    subheading_instruction = ""
    if include_subheadings:
        subheading_count = int(os.getenv('SUBHEADING_COUNT', 5))
        subheading_instruction = f"""
3. Include {subheading_count} descriptive subheadings (use ## markdown format)"""
    
    # Specialized protocol sections based on story type
    specialized_protocol = ""
    
    if story_type == 'scientific':
        specialized_protocol = """

SPECIALIZED SCIENTIFIC STORY PROTOCOL:
Your article MUST include these analysis elements:
1. **Findings vs. Interpretation**: Separate raw findings from researcher commentary
2. **Research Context**: Place discovery within existing research landscape
3. **Methodology**: Note study strengths and limitations (sample size, peer-review status)
4. **Expert Reception**: Include spectrum of expert opinion (supporters and skeptics)
5. **Path Forward**: Timeline for replication or practical application

REQUIRED SECTIONS for Scientific Stories:
## The Discovery
## Scientific Context
## Methodology & Reliability
## Expert Reception
## Path Forward
"""
    elif story_type == 'economic':
        specialized_protocol = """

SPECIALIZED ECONOMIC STORY PROTOCOL:
Your article MUST include these analysis elements:
1. **Real Economy vs. Markets**: Distinguish actual economic impact from market reactions
2. **Leading vs. Lagging Indicators**: Identify what type of data this represents
3. **Transmission Mechanisms**: Explain HOW effects spread through the economy
4. **Policy Response**: Document government/central bank actions and effectiveness
5. **Historical Context**: Compare to similar past events when relevant

REQUIRED SECTIONS for Economic Stories:
## The Economic Event
## Market Response
## Transmission & Impact
## Policy & Intervention
## Historical Context
"""
    elif story_type == 'social':
        specialized_protocol = """

SPECIALIZED SOCIAL/CULTURAL STORY PROTOCOL:
Your article MUST include these analysis elements:
1. **Demographics**: Break down by age groups, regions, or other relevant demographics
2. **Early Adopters vs. Resistors**: Identify who's leading and who's resisting
3. **Institutional Adaptation**: How organizations/institutions are responding
4. **Velocity**: How fast is this change happening (rapid/moderate/slow)
5. **Substance**: Is this performative or substantive change?

REQUIRED SECTIONS for Social Stories:
## The Shift
## Who's Leading, Who's Resisting
## Institutional Response
## Speed & Scale
## Substance Assessment
"""
    
    # Information triage guidance
    triage_guidance = """

INFORMATION QUALITY TIERS (Apply This Filter):
✅ TIER 1 - MUST INCLUDE: Verified by 3+ sources, high impact, core to story
✅ TIER 2 - SHOULD INCLUDE: 2 sources or credible expert analysis, moderate impact
⚠️ TIER 3 - COULD INCLUDE: Single credible source, clearly label as preliminary
❌ TIER 4 - EXCLUDE: Unverified rumors, promotional content, irrelevant details
"""
    
    prompt = f"""You are a professional journalist for a major news organization writing about: {topic}

STORY TYPE DETECTED: {story_type.upper()}

I have gathered {len(articles)} articles from different sources. Your task is to write ONE comprehensive, factual article about this SINGLE topic.

SOURCE MATERIALS (for reference only):
{chr(10).join(source_summaries)}
{triage_guidance}
{specialized_protocol}

🚨 CRITICAL TOPIC FOCUS RULES - READ CAREFULLY:
1. The MAIN TOPIC is: "{topic}"
2. You MUST write EXCLUSIVELY about this topic
3. If you see MULTIPLE DIFFERENT topics in the sources (e.g., Gaza conflict AND Australian Open tennis), you MUST:
   a) Identify which content relates to the MAIN TOPIC: "{topic}"
   b) COMPLETELY IGNORE all content about other unrelated topics
   c) DO NOT mention, reference, or include ANY information about unrelated topics
4. Even if a source article contains mixed content, extract ONLY the parts relevant to "{topic}"
5. If unsure whether content is related, ASK: "Does this directly relate to {topic}?" If NO, exclude it.

EXAMPLES OF WHAT TO EXCLUDE:
❌ If main topic is "Gaza Conflict" - DO NOT include: sports, entertainment, weather, unrelated countries
❌ If main topic is "Australian Open" - DO NOT include: wars, conflicts, politics in other countries
❌ If main topic is "Climate Summit" - DO NOT include: sports results, celebrity news, unrelated events

CRITICAL WRITING RULES:
1. Write as if YOU are the news organization directly reporting this story
2. DO NOT use phrases like:
   - "According to BBC News..."
   - "As reported by Reuters..."
   - "Sources say..."
   - "Al Jazeera reported..."
   - DO NOT mention any source names in the article
3. Write in DIRECT journalistic voice - state facts directly
4. Focus ONLY on the main topic "{topic}" - ABSOLUTELY NO unrelated news
5. If the sources discuss different events, pick ONLY the content about "{topic}"
6. Use objective, factual, AP Style journalism
7. Apply the SPECIALIZED PROTOCOL sections above based on story type
8. TRIPLE-CHECK before including any sentence: "Is this about {topic}? YES or NO?"

ARTICLE REQUIREMENTS:
1. Write a compelling headline (10-15 words) about "{topic}" ONLY
2. Craft a concise, descriptive subheading summarizing the core event (MAXIMUM 150 characters)
3. Create a comprehensive article of at least {target_words} words{subheading_instruction}
4. Start with proper dateline (e.g., "DUBAI, January 23 –")
5. Strong lead paragraph: who, what, when, where, why - ALL about "{topic}"
6. Use clear subheadings to organize the story (follow specialized protocol if applicable)
7. End with implications or future outlook for "{topic}"
8. Use factual, professional tone throughout
9. EVERY paragraph must be about "{topic}" - no exceptions

IMPORTANT - WHAT TO AVOID:
❌ DO NOT write "according to", "as reported by", "sources say"  
❌ DO NOT mention BBC, Reuters, CNN, or any news organization names
❌ DO NOT combine multiple unrelated stories (e.g., Gaza + Tennis)
❌ DO NOT include content about topics unrelated to "{topic}"
❌ DO NOT include your own opinions or speculation
❌ DO NOT fabricate information not in sources
❌ DO NOT include Tier 4 information (unverified, promotional)
❌ DO NOT mention sports/entertainment if main topic is politics/conflict
❌ DO NOT mention conflicts/wars if main topic is sports/entertainment

WRITING STYLE:
✅ "A car accident in Dubai has claimed the life of 19-year-old Marcus Fakana..."
✅ "The incident occurred when a BMW driven by 20-year-old Marwaan Mohamed Huseen..."
✅ "Police confirmed that the accident took place on..."

❌ NOT: "According to BBC News, a car accident occurred..."
❌ NOT: "Sources report that the incident..."
❌ NOT: "Meanwhile, in a separate development, [unrelated topic]..."

OUTPUT FORMAT:
# [Headline - Direct and Clear - ONLY about "{topic}"]

### [Subheading - MAXIMUM 150 CHARACTERS - concise summary]

[DATELINE], [Date] –

[Lead paragraph stating the main facts directly - ONLY about "{topic}"]

## [First Subheading - follow specialized protocol if applicable]
[Content about this specific aspect of "{topic}"]

## [Second Subheading]  
[Content about another aspect of "{topic}"]

[Continue with relevant subheadings - ALL about "{topic}"...]

FINAL REMINDER: This article is 100% about "{topic}". Do NOT include ANY content about other topics.

Write the article NOW in direct journalistic voice with {story_type.upper()} story analysis:"""
    
    return prompt



def build_fallback_prompt(articles: List[Dict], topic: str) -> str:
    """
    Build a simpler prompt for fallback generation.
    
    Used when primary generation fails.
    """
    headlines = [a.get('heading', '') for a in articles[:5]]
    
    prompt = f"""Write a 500-word news article about: {topic}

Based on these headlines:
{chr(10).join(f'- {h}' for h in headlines)}

Include a headline, dateline, and 3 paragraphs. Use journalistic style.

Begin:"""
    
    return prompt


# ===========================================
# ARTICLE PARSING
# ===========================================

def parse_generated_article(generated_text: str) -> Dict:
    """
    Parse LLM-generated text into structured article.
    
    Args:
        generated_text: Raw text from LLM.
        
    Returns:
        Dictionary with 'heading' and 'story' keys.
    """
    if not generated_text:
        return {"heading": "", "story": ""}
    
    lines = generated_text.strip().split('\n')
    
    # Extract headline (first line starting with #)
    heading = ""
    headline_index = -1
    
    for i, line in enumerate(lines):
        if line.strip().startswith('# ') or line.strip().startswith('## '):
            heading = line.replace('# ', '').replace('## ', '').strip()
            headline_index = i
            break
            
    # Extract subheading (first line starting with ### after headline)
    sub_heading = ""
    subheading_index = -1
    
    if headline_index >= 0:
        for i in range(headline_index + 1, min(headline_index + 10, len(lines))):
            line = lines[i].strip()
            if line.startswith('### '):
                sub_heading = line.replace('### ', '').strip()
                # Enforce 150 char limit strictly
                if len(sub_heading) > 150:
                    sub_heading = sub_heading[:147] + "..."
                subheading_index = i
                break
    
    # If no markdown heading found, use first non-empty line
    if not heading:
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                heading = line.strip()
                headline_index = i
                break
    
    # Extract body (everything after headline/subheading)
    body_start_index = max(headline_index, subheading_index)
    
    body_lines = []
    if body_start_index >= 0:
        body_lines = lines[body_start_index + 1:]
    else:
        body_lines = lines[1:]  # Skip first line
    
    # Clean up body
    story = '\n'.join(body_lines).strip()
    
    # Remove any leading/trailing artifacts
    story = re.sub(r'^[\s\n]+', '', story)
    story = re.sub(r'[\s\n]+$', '', story)
    
    # Dateline is usually the first paragraph now; let's keep it in the story
    
    return {
        "heading": heading,
        "sub_heading": sub_heading,
        "story": story
    }


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
    
    # Build prompt
    prompt = build_synthesis_prompt(
        source_articles, 
        topic, 
        target_words,
        include_subheadings
    )
    
    logger.info(f"🖊️ Generating article for trend: '{topic}'")
    logger.info(f"   Sources: {len(source_articles)} articles")
    
    # Attempt generation with retries
    for attempt in range(max_retries):
        try:
            # Call Groq API
            model = os.getenv('GROQ_MODEL', 'llama3-70b-8192')
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional news journalist for a major international news agency. Write comprehensive, balanced, factual news articles by synthesizing multiple sources. Follow AP style guidelines. CRITICAL: Each article must focus on ONE SINGLE TOPIC ONLY. If you receive sources about multiple different topics, identify the main topic and write EXCLUSIVELY about that topic. NEVER mix unrelated topics (e.g., do not combine Gaza conflict with Australian Open tennis). Focus is paramount."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower for more factual output
                max_tokens=2500,
                top_p=0.9
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
            
            # Validate topic focus - check for unrelated content
            validation = validate_topic_focus(article, topic, source_articles)
            
            if not validation['is_focused']:
                logger.warning(f"⚠️ Article may contain unrelated content about: {', '.join(validation['detected_categories'])}")
                logger.warning(f"Main topic should be: '{topic}'")
                # Log warnings but still proceed - manual review recommended
            
            # Add metadata
            article['dateline'] = infer_dateline(source_articles)
            article['timestamp'] = format_timestamp()
            article['sources_used'] = list(set([
                a.get('source_name', 'Unknown') 
                for a in source_articles
            ]))
            article['word_count'] = word_count
            article['source_count'] = len(source_articles)
            article['topic'] = topic
            article['keywords'] = trend.get('keywords', [])[:10]
            article['generated_at'] = datetime.utcnow().isoformat()
            article['model_used'] = model
            article['validation'] = validation  # Add validation results to metadata
            
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
