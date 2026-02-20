"""
OSI News Automation System - Image Generator
=============================================
Generates AI images for articles using Hugging Face Inference API.
Model: Stable Diffusion 3.5 Large (stabilityai/stable-diffusion-3.5-large)

API: https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large
Auth: Authorization: Bearer <HF_ACCESS_TOKEN>
"""

import os
import sys
import io
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

# FLUX.1-schnell via HuggingFace Serverless Inference (free, no license required)
HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
HF_MODEL_NAME = "black-forest-labs/FLUX.1-schnell"


def is_image_generation_enabled() -> bool:
    """Check if image generation is enabled in config."""
    return os.getenv('ENABLE_IMAGE_GENERATION', 'false').lower() == 'true'


def get_hf_token() -> Optional[str]:
    """Get HuggingFace access token from environment."""
    return os.getenv('HF_ACCESS_TOKEN', '').strip() or None


# ===========================================
# PROMPT BUILDING  (unchanged)
# ===========================================

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
    """Detect article category based on content."""
    text = (heading + " " + story[:200]).lower()
    for category, config in CATEGORY_PROMPTS.items():
        for keyword in config['keywords']:
            if keyword in text:
                return category
    return 'general'


def build_image_prompt(article: Dict) -> str:
    """
    Create an SD 3.5-optimised prompt from article content.

    Args:
        article: Article dictionary with heading, story, location/dateline.
    Returns:
        Optimized prompt string.
    """
    heading = article.get('heading', 'News Event')
    story = article.get('story', '')
    topic = article.get('topic', heading)
    location = article.get('location', article.get('dateline', ''))

    content = (heading + " " + story[:500]).lower()

    # Extract location context
    location_context = ""
    if location:
        location_clean = location.replace("*", "").strip().title()
        location_visuals = {
            'dubai': 'Dubai skyline, modern architecture',
            'india': 'India, Indian flag colors',
            'bangladesh': 'Bangladesh, green and red colors',
            'london': 'London landmarks',
            'paris': 'Paris landmarks',
            'new york': 'New York cityscape',
            'washington': 'Washington DC government buildings',
        }
        for city, visual in location_visuals.items():
            if city in location.lower():
                location_context = f"in {visual}, "
                break
        if not location_context and location_clean:
            location_context = f"in {location_clean}, "

    # Category-based prompt selection (priority order)
    if any(w in content for w in ['cricket', 'icc', 't20', 'test match', 'odi', 'world cup',
                                    'batsman', 'bowler', 'wicket', 'stadium', 'tournament']):
        prompt = (f"professional sports photography of cricket match, cricket stadium with players, "
                  f"{location_context}cricket action shot, international cricket tournament, "
                  f"cricket ball and bat visible, sports journalism style, dynamic athletic composition")

    elif any(w in content for w in ['football', 'soccer', 'match', 'championship',
                                     'olympics', 'athlete', 'game', 'player', 'team']):
        sport = 'cricket' if 'world cup' in content else 'football'
        prompt = (f"dynamic {sport} sports photography, {location_context}professional sports journalism, "
                  f"stadium atmosphere, athletic competition")

    elif any(w in content for w in ['government', 'president', 'minister', 'parliament',
                                     'election', 'politics', 'congress', 'senate']):
        prompt = (f"government building or political setting, {location_context}"
                  f"official government architecture, political press conference atmosphere, "
                  f"professional political photography, formal institutional setting")

    elif any(w in content for w in ['war', 'military', 'conflict', 'attack', 'strike',
                                     'troops', 'defense', 'weapon']):
        prompt = (f"news photograph showing conflict aftermath or military activity, {location_context}"
                  f"serious journalistic documentation, photojournalism style, documentary photography")

    elif any(w in content for w in ['economy', 'market', 'business', 'stock', 'finance',
                                     'trade', 'investment', 'gdp', 'growth']):
        prompt = (f"modern business and finance concept, {location_context}"
                  f"stock market visualization, financial district skyline, professional business photography")

    elif any(w in content for w in ['technology', 'tech', 'ai', 'digital', 'cyber',
                                     'software', 'internet', 'computer', 'innovation']):
        prompt = (f"modern technology and innovation concept, {location_context}"
                  f"futuristic digital visualization, high-tech environment, professional tech photography")

    elif any(w in content for w in ['health', 'medical', 'hospital', 'doctor', 'vaccine',
                                     'disease', 'covid', 'pandemic', 'treatment']):
        prompt = (f"professional medical and healthcare setting, {location_context}"
                  f"healthcare concept, clinical environment, health and medicine visualization")

    elif any(w in content for w in ['climate', 'environment', 'pollution', 'green',
                                     'emission', 'renewable', 'sustainable']):
        prompt = (f"environmental and climate concept photography, {location_context}"
                  f"nature and sustainability visualization, documentary environmental photography")

    elif any(w in content for w in ['storm', 'flood', 'earthquake', 'disaster',
                                     'emergency', 'rescue', 'hurricane']):
        prompt = (f"dramatic weather or natural disaster scene, {location_context}"
                  f"emergency response, photojournalism style, impactful disaster documentation")

    else:
        category = detect_category(heading, story)
        if category in CATEGORY_PROMPTS:
            tmpl = CATEGORY_PROMPTS[category]['template']
            prompt = tmpl.format(topic=topic[:150])
            if location_context:
                prompt = prompt.replace(', ', f', {location_context}', 1)
        else:
            prompt = (f"professional news photography illustrating: {heading[:100]}, {location_context}"
                      f"editorial quality, photojournalism style, news publication imagery")

    # SD 3.5 quality suffix
    prompt += (", high resolution, sharp focus, professional lighting, "
               "photorealistic, 4K, editorial photography, news agency quality")

    logger.debug(f"Generated SD 3.5 prompt: {prompt[:150]}...")
    return prompt


def build_negative_prompt() -> str:
    """Negative prompt to steer away from common artifacts."""
    return ("text, watermark, signature, logo, blurry, low quality, "
            "distorted, deformed, ugly, bad anatomy, cartoon, anime, "
            "illustration, painting, sketch, oversaturated, underexposed")


# ===========================================
# HUGGINGFACE INFERENCE API CALL
# ===========================================

def generate_with_huggingface(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
) -> Optional[bytes]:
    """
    Call the HuggingFace router for Stable Diffusion 3.5 Large.

    Uses the OpenAI-compatible /v1/images/generations endpoint via
    router.huggingface.co.  Returns raw PNG bytes.

    Args:
        prompt: Positive text prompt.
        negative_prompt: Negative text prompt (passed inside prompt as suffix).
        width: Image width (recommended: 1024).
        height: Image height (recommended: 1024).
        num_inference_steps: Quality steps (30 is ideal for SD 3.5 Large).
        guidance_scale: Prompt adherence strength (7-8 recommended).

    Returns:
        Raw image bytes (PNG), or None if generation failed.
    """
    import base64, time

    token = get_hf_token()
    if not token:
        logger.error("HF_ACCESS_TOKEN not set in .env")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # HF image models use the `inputs` format (same API as the old inference endpoint)
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        },
        "options": {
            "wait_for_model": True,
            "use_cache": False,
        }
    }

    try:
        logger.info(f"\U0001f5bc\ufe0f  Calling HuggingFace SD 3.5 Large via router ({width}x{height}, steps={num_inference_steps})...")

        response = requests.post(
            HF_API_URL,
            json=payload,
            headers=headers,
            timeout=180,
        )

        if response.status_code == 503:
            logger.info("Model loading on HuggingFace, waiting 20s and retrying...")
            time.sleep(20)
            response = requests.post(HF_API_URL, json=payload, headers=headers, timeout=180)

        response.raise_for_status()

        # Image models return raw PNG/JPEG bytes
        content_type = response.headers.get("Content-Type", "")
        if "image" in content_type or len(response.content) > 1000:
            logger.success(f"\u2705 HuggingFace SD 3.5 image generated ({len(response.content) / 1024:.1f} KB)")
            return response.content

        # Attempt JSON parse for error detail
        try:
            err = response.json()
            logger.error(f"HuggingFace returned JSON instead of image: {err}")
        except Exception:
            logger.error(f"Unexpected HuggingFace response ({len(response.content)} bytes): {response.text[:200]}")
        return None

    except requests.exceptions.Timeout:
        logger.error("HuggingFace API timed out after 180s — model may be warming up, try again")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HuggingFace API HTTP {e.response.status_code}: {e.response.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"HuggingFace API unexpected error: {e}")
        return None


# ===========================================
# MAIN IMAGE GENERATION ENTRYPOINTS
# ===========================================

def generate_article_image(
    article: Dict,
    output_dir: str = "output/images",
    width: int = None,
    height: int = None,
    num_steps: int = 30,
    guidance_scale: float = 7.5
) -> Optional[str]:
    """
    Generate an AI image for an article using HuggingFace SD 3.5 Large.

    Args:
        article: Article dictionary with heading and story.
        output_dir: Directory to save generated images.
        width: Image width (default 1024).
        height: Image height (default 1024).
        num_steps: Inference steps (30 = good quality/speed balance).
        guidance_scale: Prompt adherence (7.5 recommended).

    Returns:
        Path to generated image file, or None if generation failed.
    """
    if not is_image_generation_enabled():
        logger.debug("Image generation disabled, skipping")
        return None

    # Dimensions — SD 3.5 works best at 1024x1024
    if width is None:
        width = int(os.getenv('IMAGE_WIDTH', 1024))
    if height is None:
        height = int(os.getenv('IMAGE_HEIGHT', 1024))

    # Snap to valid multiples of 8
    width = max(512, (width // 8) * 8)
    height = max(512, (height // 8) * 8)

    token = get_hf_token()
    if not token:
        logger.warning("HF_ACCESS_TOKEN not set — falling back to placeholder image")
        return create_placeholder_image(article, output_dir)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build prompts
    prompt = build_image_prompt(article)
    negative_prompt = build_negative_prompt()

    # Call HuggingFace
    image_bytes = generate_with_huggingface(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        num_inference_steps=num_steps,
        guidance_scale=guidance_scale,
    )

    if not image_bytes:
        logger.warning("HuggingFace SD 3.5 generation failed — falling back to placeholder")
        return create_placeholder_image(article, output_dir)

    # Save image
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(article.get('heading', '').encode()).hexdigest()[:8]
        filename = f"sd35_{timestamp}_{title_hash}.png"
        filepath = output_path / filename

        image.save(str(filepath), format="PNG")
        logger.success(f"✅ SD 3.5 image saved: {filepath}")
        return str(filepath)

    except Exception:
        # PIL unavailable — save raw bytes
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(article.get('heading', '').encode()).hexdigest()[:8]
        filename = f"sd35_{timestamp}_{title_hash}.png"
        filepath = output_path / filename
        filepath.write_bytes(image_bytes)
        logger.success(f"✅ SD 3.5 image saved (raw): {filepath}")
        return str(filepath)


def generate_images_for_articles(
    articles: List[Dict],
    output_dir: str = "output/images"
) -> List[Optional[str]]:
    """Generate images for a list of articles."""
    if not is_image_generation_enabled():
        logger.info("Image generation disabled")
        return [None] * len(articles)

    paths = []
    for i, article in enumerate(articles):
        logger.info(f"Generating image {i + 1}/{len(articles)}...")
        paths.append(generate_article_image(article, output_dir))

    successful = sum(1 for p in paths if p is not None)
    logger.info(f"Generated {successful}/{len(articles)} images via SD 3.5 Large")
    return paths


# ===========================================
# PLACEHOLDER IMAGE (fallback)
# ===========================================

def create_placeholder_image(
    article: Dict,
    output_dir: str = "output/images"
) -> Optional[str]:
    """Create a simple placeholder image when the API is unavailable."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        width = int(os.getenv('IMAGE_WIDTH', 1024))
        height = int(os.getenv('IMAGE_HEIGHT', 1024))

        img = Image.new('RGB', (width, height), color=(30, 30, 46))
        draw = ImageDraw.Draw(img)

        heading = article.get('heading', 'News Article')[:60]

        try:
            font = ImageFont.truetype("arial.ttf", 36)
            small_font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        draw.text((20, 20), "OSI News Automation", fill=(80, 80, 100), font=small_font)

        text = f"📰 {heading}"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = max(20, (width - (bbox[2] - bbox[0])) // 2)
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


# ===========================================
# BACKWARDS COMPATIBILITY STUBS
# ===========================================

def initialize_sd_pipeline(*args, **kwargs) -> bool:
    """Deprecated: SD 3.5 is now called via HuggingFace Inference API (no local init needed)."""
    logger.info("Using HuggingFace Inference API for SD 3.5 Large — no local init required")
    return is_image_generation_enabled()


def cleanup_pipeline():
    """Deprecated: No local pipeline to clean up with cloud API backend."""
    pass


def get_device() -> str:
    """Deprecated: No local device needed with HuggingFace cloud API."""
    return "cloud"


# ===========================================
# TESTING
# ===========================================

def test_image_generator():
    """Test HuggingFace SD 3.5 Large image generation."""
    print("\n" + "="*60)
    print("🧪 HuggingFace Stable Diffusion 3.5 Large Test")
    print("="*60)

    enabled = is_image_generation_enabled()
    token = get_hf_token()

    print(f"\n📌 Image generation enabled: {enabled}")
    print(f"📌 HF token set: {'Yes (' + token[:15] + '...)' if token else 'No'}")
    print(f"📌 Model: {HF_MODEL_NAME}")
    print(f"📌 Endpoint: {HF_API_URL}")

    if not enabled:
        print("\n⚠️ Set ENABLE_IMAGE_GENERATION=true in .env to enable")
        return None

    if not token:
        print("\n⚠️ Set HF_ACCESS_TOKEN in .env")
        return None

    test_article = {
        "heading": "Global Leaders Discuss Climate Change Solutions at COP Summit",
        "story": "World leaders gathered to discuss new approaches to climate change and carbon emissions.",
        "topic": "Climate Summit",
        "location": "Paris"
    }

    print(f"\n📰 Test article: {test_article['heading']}")
    print("\n🚀 Generating via SD 3.5 Large (may take 30-120s on cold start)...")

    path = generate_article_image(test_article)

    if path:
        print(f"\n✅ Image generated: {path}")
    else:
        print("\n❌ Generation failed — check token and logs")

    print("\n" + "="*60 + "\n")
    return path


if __name__ == "__main__":
    test_image_generator()
