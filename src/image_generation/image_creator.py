"""
OSI News Automation System - Image Generator
=============================================
Generates AI images for articles using local Stable Diffusion.
Uses Hugging Face diffusers library for free, local image generation.
"""

import os
import sys
import hashlib
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
# GLOBAL STATE
# ===========================================

_pipeline = None
_device = None
_initialized = False
_initialization_failed = False


# ===========================================
# MODEL INITIALIZATION
# ===========================================

def is_image_generation_enabled() -> bool:
    """Check if image generation is enabled in config."""
    return os.getenv('ENABLE_IMAGE_GENERATION', 'false').lower() == 'true'


def get_device() -> str:
    """Determine best device for inference."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    except ImportError:
        return "cpu"


def initialize_sd_pipeline(model_id: str = None, force: bool = False) -> bool:
    """
    Initialize Stable Diffusion pipeline.
    
    Should be called once at startup. Model is loaded into memory
    and reused for all subsequent image generations.
    
    Args:
        model_id: Hugging Face model ID or local path.
        force: Force re-initialization even if already loaded.
        
    Returns:
        bool: True if initialization successful.
    """
    global _pipeline, _device, _initialized, _initialization_failed
    
    # Check if already initialized
    if _initialized and not force:
        return True
    
    # Check if previous initialization failed
    if _initialization_failed and not force:
        return False
    
    # Check if enabled
    if not is_image_generation_enabled():
        logger.info("Image generation is disabled in config")
        return False
    
    try:
        import torch
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        
        # Get model ID from env or use default (non-gated model)
        if model_id is None:
            model_id = os.getenv('IMAGE_MODEL_PATH', 'stabilityai/stable-diffusion-2-1-base')
        
        logger.info(f"Loading Stable Diffusion model: {model_id}")
        logger.info("This may take a few minutes on first run...")
        
        # Determine device
        _device = get_device()
        logger.info(f"Using device: {_device}")
        
        # Set dtype based on device
        if _device == "cuda":
            dtype = torch.float16
        else:
            dtype = torch.float32
        
        # Load pipeline
        _pipeline = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=dtype,
            safety_checker=None,  # Disable for speed (news content is safe)
            requires_safety_checker=False
        )
        
        # Use faster scheduler
        _pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            _pipeline.scheduler.config
        )
        
        # Move to device
        _pipeline = _pipeline.to(_device)
        
        # Enable memory optimizations
        if _device == "cuda":
            _pipeline.enable_attention_slicing()
            try:
                _pipeline.enable_xformers_memory_efficient_attention()
                logger.info("Enabled xformers memory efficient attention")
            except Exception:
                pass  # xformers not available
        
        _initialized = True
        _initialization_failed = False
        
        logger.success(f"✅ Stable Diffusion loaded successfully on {_device}")
        return True
        
    except ImportError as e:
        logger.error(f"Missing required packages: {e}")
        logger.error("Install with: pip install diffusers transformers accelerate")
        _initialization_failed = True
        return False
    
    except Exception as e:
        error_msg = str(e)
        if 'username' in error_msg.lower() or 'password' in error_msg.lower() or 'gated' in error_msg.lower():
            logger.error("Hugging Face authentication required for this model")
            logger.error("Run: huggingface-cli login")
            logger.error("Or set HF_TOKEN environment variable")
            logger.info("Alternatively, image generation will use placeholder images")
        else:
            logger.error(f"Failed to initialize Stable Diffusion: {e}")
        _initialization_failed = True
        return False


def cleanup_pipeline():
    """Release GPU memory by cleaning up the pipeline."""
    global _pipeline, _initialized
    
    if _pipeline is not None:
        del _pipeline
        _pipeline = None
        _initialized = False
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        
        logger.info("Pipeline cleaned up")


# ===========================================
# PROMPT BUILDING
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
    Create Stable Diffusion prompt from article content.
    
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
        # Common locations and their visual context
        location_visuals = {
            'dubai': 'Dubai skyline, modern architecture',
            'india': 'India cricket stadium, Indian flag colors',
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
        # Use category detection as backup
        category = detect_category(heading, story)
        
        if category in CATEGORY_PROMPTS:
            template = CATEGORY_PROMPTS[category]['template']
            prompt = template.format(topic=topic[:150])
            if location_context:
                prompt = prompt.replace(', ', f', {location_context}', 1)
        else:
            # Final fallback - extract key subject from heading
            prompt = (
                f"professional news photography illustrating: {heading[:100]}, "
                f"{location_context}"
                f"editorial quality, photojournalism style, news publication imagery, "
                f"clear visual storytelling"
            )
    
    # Add universal quality modifiers
    quality_suffix = (
        ", high resolution, sharp focus, professional lighting, "
        "photorealistic, 4k quality, editorial photography, news agency quality"
    )
    
    prompt += quality_suffix
    
    logger.debug(f"Generated prompt: {prompt[:150]}...")
    
    return prompt


def build_negative_prompt() -> str:
    """Create negative prompt to avoid common issues."""
    return (
        "text, watermark, signature, logo, blurry, low quality, "
        "distorted, deformed, ugly, bad anatomy, cartoon, anime, "
        "illustration, painting, drawing, art, sketch, "
        "oversaturated, underexposed, overexposed"
    )


# ===========================================
# IMAGE GENERATION
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
    Generate an AI image for an article using Stable Diffusion.
    
    Args:
        article: Article dictionary with heading and story.
        output_dir: Directory to save generated images.
        width: Image width (default from env or 1024).
        height: Image height (default from env or 768).
        num_steps: Number of inference steps (more = higher quality).
        guidance_scale: How closely to follow prompt (7-8 recommended).
        
    Returns:
        Path to generated image file, or None if generation failed.
        
    Example:
        >>> image_path = generate_article_image(article_data)
        >>> if image_path:
        ...     print(f"Image saved: {image_path}")
    """
    global _pipeline, _device
    
    # Check if enabled
    if not is_image_generation_enabled():
        logger.debug("Image generation disabled, skipping")
        return None
    
    # Initialize if needed
    if not _initialized:
        if not initialize_sd_pipeline():
            logger.warning("Stable Diffusion not available, creating placeholder image")
            return create_placeholder_image(article, output_dir)
    
    if _pipeline is None:
        logger.warning("Pipeline not loaded, using placeholder image")
        return create_placeholder_image(article, output_dir)
    
    try:
        import torch
        
        # Get dimensions from env if not specified
        if width is None:
            width = int(os.getenv('IMAGE_WIDTH', 1024))
        if height is None:
            height = int(os.getenv('IMAGE_HEIGHT', 768))
        
        # Ensure dimensions are multiples of 8
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Build prompts
        prompt = build_image_prompt(article)
        negative_prompt = build_negative_prompt()
        
        logger.info(f"🖼️ Generating image for: {article.get('heading', 'Article')[:50]}...")
        logger.debug(f"Prompt: {prompt[:100]}...")
        
        # Generate image
        with torch.inference_mode():
            result = _pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height
            )
        
        image = result.images[0]
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        title_hash = hashlib.md5(article.get('heading', '').encode()).hexdigest()[:8]
        filename = f"article_{timestamp}_{title_hash}.png"
        filepath = output_path / filename
        
        # Save image
        image.save(str(filepath), quality=95)
        
        logger.success(f"✅ Image generated: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None


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
    
    # Initialize once
    if not _initialized:
        if not initialize_sd_pipeline():
            return [None] * len(articles)
    
    paths = []
    for i, article in enumerate(articles):
        logger.info(f"Generating image {i + 1}/{len(articles)}...")
        path = generate_article_image(article, output_dir)
        paths.append(path)
    
    successful = sum(1 for p in paths if p is not None)
    logger.info(f"Generated {successful}/{len(articles)} images")
    
    return paths


# ===========================================
# PLACEHOLDER IMAGE
# ===========================================

def create_placeholder_image(
    article: Dict,
    output_dir: str = "output/images"
) -> Optional[str]:
    """
    Create a simple placeholder image when SD is unavailable.
    
    Args:
        article: Article dictionary.
        output_dir: Output directory.
        
    Returns:
        Path to placeholder image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create image
        width = int(os.getenv('IMAGE_WIDTH', 1024))
        height = int(os.getenv('IMAGE_HEIGHT', 768))
        
        img = Image.new('RGB', (width, height), color=(50, 50, 70))
        draw = ImageDraw.Draw(img)
        
        # Add text
        heading = article.get('heading', 'News Article')[:50]
        
        # Simple text (using default font)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        
        # Center text
        text = f"📰 {heading}..."
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(200, 200, 220), font=font)
        
        # Generate filename
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
# TESTING
# ===========================================

def test_image_generator():
    """Test image generation functionality."""
    print("\n" + "="*60)
    print("🧪 Image Generator Test")
    print("="*60)
    
    # Check if enabled
    enabled = is_image_generation_enabled()
    print(f"\n📌 Image generation enabled: {enabled}")
    
    if not enabled:
        print("\n⚠️ Image generation is disabled in .env")
        print("   Set ENABLE_IMAGE_GENERATION=true to enable")
        print("\n   Testing placeholder image instead...\n")
        
        test_article = {
            "heading": "Test Article for Placeholder",
            "story": "This is a test article.",
            "topic": "Testing"
        }
        
        path = create_placeholder_image(test_article)
        if path:
            print(f"✅ Placeholder created: {path}")
        
        print("\n" + "="*60 + "\n")
        return None
    
    # Test full initialization
    print("\n🔄 Initializing Stable Diffusion...")
    print("   (This may take several minutes on first run)")
    
    if not initialize_sd_pipeline():
        print("\n⚠️ Stable Diffusion not available")
        print("   Creating placeholder image instead...\n")
        
        test_article = {
            "heading": "Global Leaders Discuss Climate Change Solutions",
            "story": "World leaders gathered to discuss new approaches to climate change...",
            "topic": "Climate Summit"
        }
        
        path = create_placeholder_image(test_article)
        if path:
            print(f"✅ Placeholder created: {path}")
        else:
            print("❌ Placeholder creation failed")
        
        print("\n" + "="*60 + "\n")
        return path
    
    # Generate test image
    test_article = {
        "heading": "Global Leaders Discuss Climate Change Solutions",
        "story": "World leaders gathered to discuss new approaches to climate change...",
        "topic": "Climate Summit"
    }
    
    print(f"\n📰 Test article: {test_article['heading']}")
    print("-" * 40)
    
    path = generate_article_image(test_article)
    
    if path:
        print(f"\n✅ Image generated successfully!")
        print(f"   Path: {path}")
    else:
        print("\n❌ Image generation failed")
    
    print("\n" + "="*60 + "\n")
    
    return path


if __name__ == "__main__":
    test_image_generator()
