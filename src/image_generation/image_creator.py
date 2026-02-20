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
    Build a photojournalism-quality prompt for FLUX.1-schnell.

    Leads with 'A Reuters/AP news photograph of...' to force photorealism.
    Covers 15+ news categories including religion, Palestine, protests, royals.
    """
    heading = article.get('heading', 'News Event')
    story = article.get('story', '')
    location = article.get('location', article.get('dateline', ''))

    content = (heading + " " + story[:600]).lower()

    # -------------------------------------------------------
    # LOCATION → specific visual scene description
    # -------------------------------------------------------
    loc_scene = ""
    location_map = {
        'palestine': 'in Jerusalem, Palestine, Arabic architecture, stone buildings',
        'gaza': 'in Gaza, Palestinians in street, concrete buildings',
        'israel': 'in Jerusalem, Israel, old city walls, stone buildings',
        'jerusalem': 'in Jerusalem old city, stone walls, religious buildings',
        'west bank': 'in the West Bank, Palestinian town, Israeli checkpoint',
        'india': 'in India, colorful street scene, Indian flag visible',
        'pakistan': 'in Pakistan, Pakistani city street',
        'bangladesh': 'in Dhaka Bangladesh, green and red flag visible',
        'ukraine': 'in Ukraine, war-damaged buildings, Ukrainian flag',
        'russia': 'in Moscow Russia, Red Square architecture',
        'china': 'in Beijing China, Chinese architecture',
        'iran': 'in Tehran Iran, Islamic architecture, Persian city',
        'afghanistan': 'in Kabul Afghanistan, mountainous skyline',
        'dubai': 'in Dubai, glass skyscrapers, modern Arabian architecture',
        'london': 'in London UK, Big Ben or Parliament in background',
        'paris': 'in Paris France, Eiffel Tower visible',
        'washington': 'in Washington DC, Capitol building or White House',
        'new york': 'in New York City, Manhattan skyline',
        'united states': 'in the United States, American street scene',
        'europe': 'in Europe, European city architecture',
        'middle east': 'in the Middle East, Islamic architecture, dusty streets',
        'africa': 'in Africa, African cityscape or landscape',
    }
    loc_lower = (location + " " + content).lower()
    for keyword, visual in location_map.items():
        if keyword in loc_lower:
            loc_scene = visual + ", "
            break
    if not loc_scene and location:
        loc_clean = location.replace("*", "").strip()
        if loc_clean:
            loc_scene = f"in {loc_clean}, "

    # -------------------------------------------------------
    # TOPIC DETECTION → specific photojournalism scene
    # Priority: most specific first
    # -------------------------------------------------------

    # RELIGION — mosque, prayers, Ramadan, pilgrimage
    if any(w in content for w in ['mosque', 'ramadan', 'prayer', 'prayers', 'friday prayer',
                                    'imam', 'mecca', 'pilgrim', 'hajj', 'eid', 'islamic',
                                    'church', 'cathedral', 'temple', 'religious', 'worship',
                                    'buddhist', 'hindu', 'sikh', 'jewish', 'synagogue']):
        if any(w in content for w in ['mosque', 'ramadan', 'prayer', 'imam', 'mecca', 'hajj', 'eid', 'islamic', 'muslim']):
            prompt = (f"A Reuters news photograph of Muslim worshippers gathered outside a mosque for Friday prayers, "
                      f"{loc_scene}crowd of men in traditional Islamic dress, "
                      f"ornate mosque architecture with minarets visible, serene atmosphere, "
                      f"documentary photojournalism")
        elif any(w in content for w in ['church', 'cathedral', 'christian']):
            prompt = (f"A Reuters news photograph of people at a church or cathedral, "
                      f"{loc_scene}religious gathering, stone architecture, "
                      f"documentary photojournalism style")
        else:
            prompt = (f"A Reuters news photograph of a religious gathering at a place of worship, "
                      f"{loc_scene}people in traditional religious dress, "
                      f"documentary photojournalism")

    # PROTEST / DEMONSTRATION
    elif any(w in content for w in ['protest', 'demonstration', 'rally', 'march', 'demonstrators',
                                     'protesters', 'riot', 'clashes', 'crowd gathered', 'activists']):
        prompt = (f"An AP news photograph of a large protest demonstration {loc_scene}"
                  f"crowd of protesters holding signs and banners in street, "
                  f"tense atmosphere, photojournalism style, wide angle shot, "
                  f"documentary street photography")

    # ARREST / CRIME / COURT
    elif any(w in content for w in ['arrested', 'arrest', 'court', 'trial', 'convicted', 'charged',
                                     'police', 'crime', 'criminal', 'detained', 'custody', 'prison',
                                     'sentence', 'verdict']):
        prompt = (f"A Reuters news photograph showing law enforcement activity {loc_scene}"
                  f"police officers in uniform, courthouse exterior or police station, "
                  f"serious news event, documentary journalism photography, "
                  f"professional press photo")

    # PALESTINE / ISRAEL / MIDDLE EAST CONFLICT
    elif any(w in content for w in ['palestine', 'palestinian', 'gaza', 'west bank', 'hamas',
                                     'israel', 'israeli', 'occupation', 'ceasefire', 'airstrike',
                                     'refugee camp', 'settlement']):
        prompt = (f"An AP documentary photograph {loc_scene}"
                  f"Palestinian people in street, stone buildings, separation barrier visible, "
                  f"humanitarian crisis scene, gritty photojournalism, "
                  f"serious documentary news photography")

    # ROYAL FAMILY / MONARCHY
    elif any(w in content for w in ['royal', 'king', 'queen', 'prince', 'princess', 'monarch',
                                     'palace', 'coronation', 'windsor', 'mountbatten', 'buckingham']):
        prompt = (f"A Reuters news photograph of a royal or official state occasion {loc_scene}"
                  f"formal government ceremony, elegant official setting, "
                  f"guards in uniform, ornate architecture, "
                  f"professional press photography, dignified composition")

    # CRICKET / SPORTS
    elif any(w in content for w in ['cricket', 'icc', 't20', 'test match', 'odi',
                                     'batsman', 'bowler', 'wicket']):
        prompt = (f"A Getty Images sports photograph of a cricket match {loc_scene}"
                  f"batsman hitting ball in international cricket stadium, "
                  f"packed crowd in stands, action shot, "
                  f"professional sports photography, motion blur on ball")

    elif any(w in content for w in ['football', 'soccer', 'championship', 'world cup',
                                     'olympics', 'athlete', 'tournament', 'league']):
        sport = 'football' if 'football' in content or 'soccer' in content else 'sport'
        prompt = (f"A Getty Images sports photograph of a {sport} match {loc_scene}"
                  f"athletes competing on the field, stadium crowd, "
                  f"dynamic action shot, professional sports photography")

    # MILITARY / WAR / CONFLICT (non-Palestine)
    elif any(w in content for w in ['war', 'military', 'troops', 'soldier', 'army', 'navy',
                                     'airstrike', 'bombing', 'drone', 'missile', 'combat',
                                     'battalion', 'armed forces', 'defense']):
        prompt = (f"A Reuters documentary photograph of military activity {loc_scene}"
                  f"soldiers in military uniform and gear, military vehicles, "
                  f"serious conflict journalism, photojournalism style, "
                  f"dramatic natural lighting")

    # POLITICS / GOVERNMENT / ELECTIONS
    elif any(w in content for w in ['government', 'president', 'prime minister', 'minister',
                                     'parliament', 'election', 'vote', 'senator', 'congress',
                                     'summit', 'diplomatic', 'treaty', 'policy', 'legislation']):
        prompt = (f"A Reuters press photograph of a political event or press conference {loc_scene}"
                  f"officials at podium addressing media, flags in background, "
                  f"formal government setting, "
                  f"professional political photojournalism")

    # ECONOMY / FINANCE / MARKETS
    elif any(w in content for w in ['economy', 'market', 'stock market', 'recession', 'inflation',
                                     'gdp', 'bank', 'trade', 'investment', 'finance', 'currency']):
        prompt = (f"A Reuters business photograph {loc_scene}"
                  f"stock exchange trading floor with traders and digital price boards, "
                  f"financial district glass towers, "
                  f"professional business journalism photography")

    # TECHNOLOGY
    elif any(w in content for w in ['artificial intelligence', 'ai', 'technology', 'cybersecurity',
                                     'startup', 'silicon valley', 'robot', 'chip', 'smartphone']):
        prompt = (f"A professional technology photograph {loc_scene}"
                  f"scientists or engineers working with technology equipment, "
                  f"clean modern research lab or tech office, "
                  f"documentary science photography")

    # HEALTH / MEDICAL
    elif any(w in content for w in ['hospital', 'doctor', 'vaccine', 'disease', 'pandemic',
                                     'health', 'medical', 'surgery', 'patient', 'treatment',
                                     'epidemic', 'virus']):
        prompt = (f"A Reuters health photograph {loc_scene}"
                  f"doctors and nurses in hospital treating patients, "
                  f"medical equipment visible, white clinical environment, "
                  f"documentary medical photography")

    # ENVIRONMENT / CLIMATE
    elif any(w in content for w in ['climate', 'global warming', 'flood', 'wildfire', 'drought',
                                     'pollution', 'renewable', 'solar', 'carbon', 'deforestation']):
        prompt = (f"A documentary environmental photograph {loc_scene}"
                  f"striking natural landscape showing climate or environmental impact, "
                  f"dramatic sky, powerful nature photography, "
                  f"National Geographic style")

    # DISASTER / EMERGENCY
    elif any(w in content for w in ['earthquake', 'hurricane', 'tsunami', 'disaster', 'explosion',
                                     'fire', 'rescue', 'emergency', 'evacuation', 'casualties']):
        prompt = (f"An AP emergency and disaster news photograph {loc_scene}"
                  f"rescue workers and emergency responders at disaster site, "
                  f"dramatic scene, photojournalism documentation, "
                  f"gritty realistic documentary photography")

    # IMMIGRATION / REFUGEES
    elif any(w in content for w in ['refugee', 'migrant', 'immigration', 'asylum', 'border',
                                     'displaced', 'humanitarian', 'camp']):
        prompt = (f"A UNHCR documentary photograph {loc_scene}"
                  f"refugees or migrants at border crossing or humanitarian camp, "
                  f"tents and temporary shelters visible, "
                  f"powerful humanitarian photojournalism")

    # FALLBACK — derive from heading directly
    else:
        # Use the article heading as direct scene description
        clean_heading = heading[:120].strip()
        prompt = (f"A Reuters news photograph illustrating: {clean_heading}, "
                  f"{loc_scene}"
                  f"documentary photojournalism style, real-world scene")

    # -------------------------------------------------------
    # FLUX.1 photorealism suffix
    # -------------------------------------------------------
    prompt += (
        ", Canon EOS 5D Mark IV DSLR photograph, 35mm lens, "
        "natural available lighting, photorealistic, "
        "ultra-detailed, sharp focus, news agency quality"
    )

    logger.debug(f"Prompt: {prompt[:160]}...")
    return prompt


def build_negative_prompt() -> str:
    """Strong negative prompt to prevent AI-looking, CGI, or generic imagery."""
    return (
        "CGI, 3D render, digital art, illustration, painting, cartoon, anime, "
        "sketch, watercolor, unrealistic, artificial lighting, studio lighting, "
        "text, watermark, signature, logo, "
        "blurry, low quality, overexposed, underexposed, "
        "distorted, deformed, ugly, duplicate, "
        "generic office building, glass skyscraper, corporate stock photo, "
        "futuristic, fantasy, sci-fi"
    )


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
