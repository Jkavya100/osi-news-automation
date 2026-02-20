"""
OSI News Automation System - Image Generator
=============================================
Generates AI images for articles using TogetherAI FLUX.1 Schnell API.
Falls back to placeholder images if the API is unavailable.

API: https://api.together.xyz/v1/images/generations
Model: black-forest-labs/FLUX.1-schnell
"""

import os
import sys
import io
import base64
import hashlib
import requests
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()


# ===========================================
# CONFIGURATION
# ===========================================

TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
TOGETHER_MODEL_FREE = "black-forest-labs/FLUX.1-schnell-Free"


def is_image_generation_enabled() -> bool:
    """Check if image generation is enabled in config."""
    return os.getenv('ENABLE_IMAGE_GENERATION', 'false').lower() == 'true'


def get_together_api_key() -> Optional[str]:
    """Get TogetherAI API key from environment."""
    return os.getenv('TOGETHER_API_KEY', '').strip() or None


# ===========================================
# PROMPT BUILDING (unchanged from original)
# ===========================================

# Category keywords for prompt styling
CATEGORY_PROMPTS = {
    'politics': {
        'keywords': ['president', 'government', 'election', 'minister', 'parliament',
                     'congress', 'senate', 'politician', 'vote', 'democracy', 'biden',
                     'modi', 'putin', 'prime minister'],
        'template': "photorealistic news photograph of government buildings or political meeting, "
                   "professional journalism photography, serious tone, {topic}, "
                   "formal setting, dignified composition"
    },
    'conflict': {
        'keywords': ['war', 'military', 'attack', 'conflict', 'troops', 'army', 'defense',
                     'weapon', 'soldier', 'combat', 'battle', 'strike', 'missile'],
        'template': "photorealistic news photograph showing aftermath of conflict, "
                   "military equipment, serious journalistic documentation, {topic}, "
                   "impactful but tasteful composition"
    },
    'economy': {
        'keywords': ['economy', 'market', 'stock', 'business', 'gdp', 'trade', 'inflation',
                     'finance', 'bank', 'investment', 'growth', 'recession', 'currency'],
        'template': "photorealistic business photography, modern financial district, "
                   "stock market visualization, economic growth concept, {topic}, "
                   "professional corporate style"
    },
    'technology': {
        'keywords': ['tech', 'ai', 'digital', 'cyber', 'internet', 'software', 'computer',
                     'robot', 'innovation', 'startup', 'silicon valley', 'app', 'data'],
        'template': "modern technology scene, futuristic digital visualization, "
                   "high-tech environment, {topic}, clean professional photography, "
                   "innovation concept"
    },
    'climate': {
        'keywords': ['climate', 'environment', 'pollution', 'carbon', 'green', 'sustainable',
                     'renewable', 'solar', 'wind', 'emission', 'global warming'],
        'template': "environmental photography, nature and climate concept, "
                   "{topic}, documentary style, impactful environmental visualization, "
                   "professional nature photography"
    },
    'disaster': {
        'keywords': ['storm', 'flood', 'earthquake', 'disaster', 'weather', 'hurricane',
                     'tornado', 'tsunami', 'wildfire', 'emergency', 'rescue'],
        'template': "dramatic weather or disaster aftermath scene, {topic}, "
                   "photojournalism style, emergency response, impactful documentary photo"
    },
    'health': {
        'keywords': ['health', 'medical', 'hospital', 'doctor', 'vaccine', 'disease',
                     'covid', 'pandemic', 'treatment', 'research', 'medicine'],
        'template': "professional medical photography, healthcare setting, {topic}, "
                   "clean clinical environment, health concept visualization"
    },
    'sports': {
        'keywords': ['sports', 'game', 'match', 'championship', 'player', 'team',
                     'football', 'cricket', 'olympics', 'tournament', 'athlete'],
        'template': "dynamic sports photography, athletic action shot, {topic}, "
                   "professional sports journalism, stadium atmosphere"
    },
}


def detect_category(heading: str, story: str = "") -> str:
    """
    Detect article category based on content.

    Args:
        heading: Article headline.
        story: Article body text.

    Returns:
        Category name string.
    """
    text = (heading + " " + story[:200]).lower()

    for category, config in CATEGORY_PROMPTS.items():
        for keyword in config['keywords']:
            if keyword in text:
                return category

    return 'general'


def build_image_prompt(article: Dict) -> str:
    """
    Create a FLUX.1-optimised prompt from article content.

    Uses smart category detection, extracts location/country,
    and builds contextually relevant prompts for news-appropriate images.

    Args:
        article: Article dictionary with heading, story, location/dateline.

    Returns:
        Optimized prompt string with context.
    """
    heading = article.get('heading', 'News Event')
    story = article.get('story', '')
    topic = article.get('topic', heading)
    location = article.get('location', article.get('dateline', ''))

    # Combine heading and first part of story for analysis
    content = (heading + " " + story[:500]).lower()

    # Extract location/country context
    location_context = ""
    if location:
        location_clean = location.replace("*", "").strip().title()
        location_visuals = {
            'dubai': 'Dubai skyline, modern architecture',
            'india': 'India, Indian flag colors',
            'bangladesh': 'Bangladesh cricket venue, green and red colors',
            'london': 'London landmarks',
            'paris': 'Paris landmarks',
            'new york': 'New York cityscape',
            'washington': 'Washington DC government buildings',
        }

        location_lower = location.lower()
        for city, visual in location_visuals.items():
            if city in location_lower:
                location_context = f"in {visual}, "
                break

        if not location_context and location_clean:
            location_context = f"in {location_clean}, "

    # PRIORITY 1: Sports (especially cricket)
    if any(word in content for word in ['cricket', 'icc', 't20', 'test match', 'odi', 'world cup',
                                          'batsman', 'bowler', 'wicket', 'stadium', 'tournament']):
        prompt = (
            f"professional sports photography of cricket match, cricket stadium with players, "
            f"{location_context}"
            f"cricket action shot, international cricket tournament, "
            f"cricket ball and bat visible, sports journalism style, "
            f"dynamic athletic composition, dramatic stadium lighting"
        )

    # PRIORITY 2: Other sports
    elif any(word in content for word in ['football', 'soccer', 'match', 'championship',
                                           'olympics', 'athlete', 'game', 'player', 'team']):
        sport_type = 'cricket' if 'world cup' in content else 'football'
        prompt = (
            f"dynamic sports photography, {sport_type} action shot, {location_context}"
            f"professional sports journalism, stadium atmosphere, "
            f"athletic competition, sports venue"
        )

    # PRIORITY 3: Political/Government
    elif any(word in content for word in ['government', 'president', 'minister', 'parliament',
                                           'election', 'politics', 'congress', 'senate']):
        prompt = (
            f"government building or political setting, {location_context}"
            f"official government architecture, political press conference atmosphere, "
            f"professional political photography, news journalism style, "
            f"formal institutional setting"
        )

    # PRIORITY 4: Conflict/Military
    elif any(word in content for word in ['war', 'military', 'conflict', 'attack', 'strike',
                                           'troops', 'defense', 'weapon']):
        prompt = (
            f"news photograph showing conflict aftermath or military activity, "
            f"{location_context}"
            f"serious journalistic documentation, impactful but tasteful composition, "
            f"photojournalism style, documentary photography"
        )

    # PRIORITY 5: Economy/Business
    elif any(word in content for word in ['economy', 'market', 'business', 'stock', 'finance',
                                           'trade', 'investment', 'gdp', 'growth']):
        prompt = (
            f"modern business and finance concept, {location_context}"
            f"stock market visualization, financial district skyline, "
            f"professional business photography, economic news imagery, "
            f"corporate setting"
        )

    # PRIORITY 6: Technology
    elif any(word in content for word in ['technology', 'tech', 'ai', 'digital', 'cyber',
                                           'software', 'internet', 'computer', 'innovation']):
        prompt = (
            f"modern technology and innovation concept, {location_context}"
            f"futuristic digital visualization, high-tech environment, "
            f"professional tech photography, innovation and digital transformation"
        )

    # PRIORITY 7: Health/Medical
    elif any(word in content for word in ['health', 'medical', 'hospital', 'doctor', 'vaccine',
                                           'disease', 'covid', 'pandemic', 'treatment']):
        prompt = (
            f"professional medical and healthcare setting, {location_context}"
            f"healthcare concept, clinical environment, "
            f"health and medicine visualization, professional medical photography"
        )

    # PRIORITY 8: Climate/Environment
    elif any(word in content for word in ['climate', 'environment', 'pollution', 'green',
                                           'emission', 'renewable', 'sustainable']):
        prompt = (
            f"environmental and climate concept photography, {location_context}"
            f"nature and sustainability visualization, environmental awareness, "
            f"climate change imagery, documentary environmental photography"
        )

    # PRIORITY 9: Disaster/Emergency
    elif any(word in content for word in ['storm', 'flood', 'earthquake', 'disaster',
                                           'emergency', 'rescue', 'hurricane']):
        prompt = (
            f"dramatic weather or natural disaster scene, {location_context}"
            f"emergency response, photojournalism style, "
            f"impactful disaster documentation, news photography"
        )

    # FALLBACK: Generic news based on heading
    else:
        category = detect_category(heading, story)

        if category in CATEGORY_PROMPTS:
            template = CATEGORY_PROMPTS[category]['template']
            prompt = template.format(topic=topic[:150])
            if location_context:
                prompt = prompt.replace(', ', f', {location_context}', 1)
        else:
            prompt = (
                f"professional news photography illustrating: {heading[:100]}, "
                f"{location_context}"
                f"editorial quality, photojournalism style, news publication imagery, "
                f"clear visual storytelling"
            )

    # FLUX.1-specific quality suffix (no 'negative_prompt' needed for FLUX)
    quality_suffix = (
        ", high resolution, sharp focus, professional lighting, "
        "photorealistic, 4K, editorial photography, news agency quality"
    )

    prompt += quality_suffix

    logger.debug(f"Generated FLUX prompt: {prompt[:150]}...")

    return prompt


# ===========================================
# TOGETHERAI FLUX.1 SCHNELL GENERATION
# ===========================================

def generate_with_together_ai(
    prompt: str,
    width: int = 1024,
    height: int = 768,
    steps: int = 4,  # FLUX.1 Schnell is optimised for 4 steps
) -> Optional[bytes]:
    """
    Generate an image using TogetherAI FLUX.1 Schnell API.

    FLUX.1 Schnell requires only 4 inference steps (vs 30 for SD)
    making it ~8x faster while producing superior quality.

    Args:
        prompt: Text description of the image to generate.
        width: Image width in pixels (must be multiple of 8).
        height: Image height in pixels (must be multiple of 8).
        steps: Number of inference steps (4 is optimal for Schnell).

    Returns:
        Raw image bytes (PNG), or None if generation failed.
    """
    api_key = get_together_api_key()

    if not api_key:
        logger.error("TOGETHER_API_KEY not set in .env")
        return None

    # Ensure dimensions are valid multiples of 8
    width = max(256, (width // 8) * 8)
    height = max(256, (height // 8) * 8)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": TOGETHER_MODEL,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "n": 1,
        "response_format": "b64_json",  # Get base64 encoded image
    }

    try:
        logger.info(f"🖼️  Calling TogetherAI FLUX.1 Schnell (steps={steps}, {width}x{height})...")

        response = requests.post(
            TOGETHER_API_URL,
            json=payload,
            headers=headers,
            timeout=120  # FLUX is fast but give enough time
        )

        if response.status_code == 402:
            logger.warning("TogetherAI quota exceeded, retrying with Free tier model...")
            payload["model"] = TOGETHER_MODEL_FREE
            response = requests.post(TOGETHER_API_URL, json=payload, headers=headers, timeout=120)

        response.raise_for_status()

        result = response.json()

        # Extract base64 image data
        image_data = result.get("data", [{}])[0].get("b64_json")

        if not image_data:
            logger.error(f"No image data in TogetherAI response: {result}")
            return None

        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)
        logger.success(f"✅ TogetherAI FLUX.1 image generated ({len(image_bytes) / 1024:.1f} KB)")
        return image_bytes

    except requests.exceptions.Timeout:
        logger.error("TogetherAI API request timed out after 120s")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"TogetherAI API HTTP error {e.response.status_code}: {e.response.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"TogetherAI API unexpected error: {e}")
        return None


# ===========================================
# MAIN IMAGE GENERATION ENTRYPOINTS
# ===========================================

def generate_article_image(
    article: Dict,
    output_dir: str = "output/images",
    width: int = None,
    height: int = None,
    num_steps: int = 4,          # Optimal for FLUX.1 Schnell
    guidance_scale: float = 7.5  # Kept for API compatibility, not used by FLUX
) -> Optional[str]:
    """
    Generate an AI image for an article using TogetherAI FLUX.1 Schnell.

    Args:
        article: Article dictionary with heading and story.
        output_dir: Directory to save generated images.
        width: Image width (default from env or 1024).
        height: Image height (default from env or 768).
        num_steps: Inference steps (4 is optimal for FLUX.1 Schnell).
        guidance_scale: Ignored for FLUX.1 (kept for backwards compatibility).

    Returns:
        Path to generated image file, or None if generation failed.

    Example:
        >>> image_path = generate_article_image(article_data)
        >>> if image_path:
        ...     print(f"Image saved: {image_path}")
    """
    # Check if enabled
    if not is_image_generation_enabled():
        logger.debug("Image generation disabled, skipping")
        return None

    # Get dimensions from env if not specified
    if width is None:
        width = int(os.getenv('IMAGE_WIDTH', 1024))
    if height is None:
        height = int(os.getenv('IMAGE_HEIGHT', 768))

    # Check API key is available
    api_key = get_together_api_key()
    if not api_key:
        logger.warning("TOGETHER_API_KEY not set — falling back to placeholder image")
        return create_placeholder_image(article, output_dir)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build prompt
    prompt = build_image_prompt(article)

    # Call TogetherAI
    image_bytes = generate_with_together_ai(prompt, width=width, height=height, steps=num_steps)

    if not image_bytes:
        logger.warning("TogetherAI generation failed — falling back to placeholder")
        return create_placeholder_image(article, output_dir)

    # Save image
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(article.get('heading', '').encode()).hexdigest()[:8]
        filename = f"flux_{timestamp}_{title_hash}.png"
        filepath = output_path / filename

        image.save(str(filepath), format="PNG")
        logger.success(f"✅ FLUX.1 image saved: {filepath}")
        return str(filepath)

    except Exception as e:
        # If PIL is unavailable, save raw bytes directly
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(article.get('heading', '').encode()).hexdigest()[:8]
        filename = f"flux_{timestamp}_{title_hash}.png"
        filepath = output_path / filename

        filepath.write_bytes(image_bytes)
        logger.success(f"✅ FLUX.1 image saved (raw): {filepath}")
        return str(filepath)


def generate_images_for_articles(
    articles: List[Dict],
    output_dir: str = "output/images"
) -> List[Optional[str]]:
    """
    Generate images for multiple articles.

    Args:
        articles: List of article dictionaries.
        output_dir: Directory to save images.

    Returns:
        List of image paths (None for failed generations).
    """
    if not is_image_generation_enabled():
        logger.info("Image generation disabled")
        return [None] * len(articles)

    paths = []
    for i, article in enumerate(articles):
        logger.info(f"Generating image {i + 1}/{len(articles)}...")
        path = generate_article_image(article, output_dir)
        paths.append(path)

    successful = sum(1 for p in paths if p is not None)
    logger.info(f"Generated {successful}/{len(articles)} images via FLUX.1 Schnell")

    return paths


# ===========================================
# PLACEHOLDER IMAGE (fallback)
# ===========================================

def create_placeholder_image(
    article: Dict,
    output_dir: str = "output/images"
) -> Optional[str]:
    """
    Create a simple placeholder image when the API is unavailable.

    Args:
        article: Article dictionary.
        output_dir: Output directory.

    Returns:
        Path to placeholder image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        width = int(os.getenv('IMAGE_WIDTH', 1024))
        height = int(os.getenv('IMAGE_HEIGHT', 768))

        img = Image.new('RGB', (width, height), color=(30, 30, 46))
        draw = ImageDraw.Draw(img)

        heading = article.get('heading', 'News Article')[:60]

        try:
            font = ImageFont.truetype("arial.ttf", 36)
            small_font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        # Watermark
        draw.text((20, 20), "OSI News Automation", fill=(80, 80, 100), font=small_font)

        # Centered heading
        text = f"📰 {heading}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = max(20, (width - text_width) // 2)
        y = (height - (bbox[3] - bbox[1])) // 2

        draw.text((x, y), text, fill=(200, 200, 220), font=font)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(heading.encode()).hexdigest()[:8]
        filename = f"placeholder_{timestamp}_{title_hash}.png"
        filepath = output_path / filename

        img.save(str(filepath))

        logger.info(f"Created placeholder image: {filepath}")
        return str(filepath)

    except Exception as e:
        logger.error(f"Failed to create placeholder: {e}")
        return None


# Backwards compatibility — keep old SD init functions as no-ops
def initialize_sd_pipeline(*args, **kwargs) -> bool:
    """Deprecated: SD pipeline replaced by TogetherAI FLUX.1. Returns True as no-op."""
    logger.info("Stable Diffusion pipeline replaced by TogetherAI FLUX.1 Schnell API")
    return is_image_generation_enabled()


def cleanup_pipeline():
    """Deprecated: No local pipeline to clean up with TogetherAI backend."""
    pass


def get_device() -> str:
    """Deprecated: No local device needed with TogetherAI cloud API."""
    return "cloud"


# ===========================================
# TESTING
# ===========================================

def test_image_generator():
    """Test TogetherAI FLUX.1 Schnell image generation."""
    print("\n" + "="*60)
    print("🧪 TogetherAI FLUX.1 Schnell Image Generator Test")
    print("="*60)

    enabled = is_image_generation_enabled()
    print(f"\n📌 Image generation enabled: {enabled}")

    api_key = get_together_api_key()
    print(f"📌 TogetherAI API key set: {'Yes (' + api_key[:12] + '...)' if api_key else 'No'}")
    print(f"📌 Model: {TOGETHER_MODEL}")

    if not enabled:
        print("\n⚠️ Set ENABLE_IMAGE_GENERATION=true in .env to enable")
        return None

    if not api_key:
        print("\n⚠️ Set TOGETHER_API_KEY in .env")
        return None

    test_article = {
        "heading": "Global Leaders Discuss Climate Change Solutions at COP Summit",
        "story": "World leaders gathered to discuss new approaches to climate change and carbon emissions.",
        "topic": "Climate Summit",
        "location": "Paris"
    }

    print(f"\n📰 Test article: {test_article['heading']}")
    print(f"📍 Location: {test_article['location']}")
    print("\n🚀 Generating via FLUX.1 Schnell (should take 3-8 seconds)...")

    path = generate_article_image(test_article)

    if path:
        print(f"\n✅ Image generated successfully!")
        print(f"   Path: {path}")
    else:
        print("\n❌ Image generation failed — check API key and logs")

    print("\n" + "="*60 + "\n")
    return path


if __name__ == "__main__":
    test_image_generator()
