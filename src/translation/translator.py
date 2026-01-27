"""
OSI News Automation System - Translation Service
=================================================
Translates generated articles into multiple languages using deep-translator.
Uses Google Translate (free, no API costs) via the deep-translator library.
"""

import os
import sys
import time
import re
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()


# ===========================================
# LANGUAGE CONFIGURATION
# ===========================================

# Supported languages with their full names
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'ar': 'Arabic',
    'zh-cn': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'de': 'German',
    'ja': 'Japanese',
    'ko': 'Korean',
    'it': 'Italian',
    'nl': 'Dutch',
    'tr': 'Turkish',
    'pl': 'Polish',
    'uk': 'Ukrainian',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
}


def is_translation_enabled() -> bool:
    """Check if translation is enabled in config."""
    return os.getenv('TRANSLATION_ENABLED', 'false').lower() == 'true'


def get_target_languages() -> List[str]:
    """Get list of target languages from config."""
    languages_str = os.getenv('TARGET_LANGUAGES', 'hi,es,fr,ar')
    return [lang.strip() for lang in languages_str.split(',') if lang.strip()]


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return SUPPORTED_LANGUAGES.get(code, code)


# ===========================================
# TEXT CHUNKING
# ===========================================

def chunk_text(text: str, max_length: int = 4500) -> List[str]:
    """
    Split text into chunks for translation.
    
    Google Translate has a character limit (~5000), so we split
    longer texts at sentence boundaries.
    
    Args:
        text: Text to split.
        max_length: Maximum characters per chunk.
        
    Returns:
        List of text chunks.
    """
    if not text:
        return []
    
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    
    # Split by paragraphs first (preserve markdown structure)
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If single paragraph is too long, split by sentences
        if len(paragraph) > max_length:
            # Save current chunk if any
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            # Split paragraph by sentences
            sentences = re.split(r'(?<=[.!?।])\s+', paragraph)
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= max_length:
                    current_chunk += sentence + ' '
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + ' '
        
        # Normal paragraph - try to add to current chunk
        elif len(current_chunk) + len(paragraph) + 2 <= max_length:
            current_chunk += paragraph + '\n\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n\n'
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def preserve_markdown(text: str) -> tuple:
    """
    Extract markdown elements that shouldn't be translated.
    
    Args:
        text: Original text with markdown.
        
    Returns:
        Tuple of (cleaned text, placeholder map).
    """
    placeholders = {}
    
    # Preserve markdown headings
    heading_pattern = r'^(#{1,6}\s+)(.+)$'
    
    lines = text.split('\n')
    preserved_lines = []
    
    for line in lines:
        if line.startswith('#'):
            # Keep the heading markers
            match = re.match(heading_pattern, line)
            if match:
                marker = match.group(1)
                content = match.group(2)
                preserved_lines.append(f"{marker}{content}")
            else:
                preserved_lines.append(line)
        else:
            preserved_lines.append(line)
    
    return '\n'.join(preserved_lines), placeholders


# ===========================================
# TRANSLATION FUNCTIONS
# ===========================================

def translate_text(
    text: str,
    source_lang: str = 'en',
    target_lang: str = 'hi',
    max_retries: int = 3
) -> Optional[str]:
    """
    Translate text from source to target language.
    
    Args:
        text: Text to translate.
        source_lang: Source language code.
        target_lang: Target language code.
        max_retries: Maximum retry attempts.
        
    Returns:
        Translated text or None if failed.
    """
    if not text or not text.strip():
        return text
    
    try:
        from deep_translator import GoogleTranslator
        
        # Handle long text by chunking
        chunks = chunk_text(text)
        translated_chunks = []
        
        for i, chunk in enumerate(chunks):
            for attempt in range(max_retries):
                try:
                    translator = GoogleTranslator(source=source_lang, target=target_lang)
                    translated = translator.translate(chunk)
                    translated_chunks.append(translated)
                    
                    # Small delay between chunks to avoid rate limiting
                    if i < len(chunks) - 1:
                        time.sleep(0.5)
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Translation attempt {attempt + 1} failed, retrying...")
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        raise e
        
        # Rejoin chunks
        if len(chunks) == 1:
            return translated_chunks[0] if translated_chunks else None
        else:
            # Preserve paragraph structure
            return '\n\n'.join(translated_chunks)
            
    except ImportError:
        logger.error("deep-translator not installed. Run: pip install deep-translator")
        return None
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return None


def translate_article(
    article: Dict,
    target_languages: List[str] = None,
    include_metadata: bool = True
) -> Dict[str, Dict]:
    """
    Translate an article to multiple languages.
    
    Args:
        article: Article dictionary with 'heading' and 'story'.
        target_languages: List of language codes (e.g., ['hi', 'es', 'fr']).
                         If None, uses config TARGET_LANGUAGES.
        include_metadata: Whether to include translation metadata.
        
    Returns:
        Dictionary mapping language codes to translated articles.
        
    Example:
        >>> translations = translate_article(article, ['hi', 'es'])
        >>> print(translations['hi']['heading'])  # Hindi headline
    """
    # Check if enabled
    if not is_translation_enabled():
        logger.info("Translation is disabled in config")
        return {}
    
    # Get target languages
    if target_languages is None:
        target_languages = get_target_languages()
    
    if not target_languages:
        logger.warning("No target languages specified")
        return {}
    
    # Get source language
    source_lang = article.get('language', 'en')
    
    # Validate article
    heading = article.get('heading', '')
    story = article.get('story', '')
    
    if not heading and not story:
        logger.warning("Article has no content to translate")
        return {}
    
    logger.info(f"Translating article to {len(target_languages)} languages...")
    translations = {}
    
    for lang in target_languages:
        # Skip source language
        if lang == source_lang:
            logger.debug(f"Skipping {lang} (same as source)")
            continue
        
        # Validate language code
        if lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {lang}")
            continue
        
        try:
            logger.info(f"📝 Translating to {get_language_name(lang)} ({lang})...")
            
            # Translate heading
            translated_heading = translate_text(heading, source_lang, lang)
            
            if not translated_heading:
                logger.warning(f"Failed to translate heading to {lang}")
                continue
            
            # Translate story
            translated_story = translate_text(story, source_lang, lang)
            
            if not translated_story:
                logger.warning(f"Failed to translate story to {lang}")
                continue
            
            # Build translated article
            translated_article = {
                'heading': translated_heading,
                'story': translated_story,
                'language': lang,
                'language_name': get_language_name(lang),
            }
            
            # Add metadata if requested
            if include_metadata:
                translated_article.update({
                    'original_language': source_lang,
                    'translated_at': datetime.utcnow().isoformat(),
                    'source_heading': heading,
                    'word_count': len(translated_story.split()),
                })
            
            translations[lang] = translated_article
            logger.success(f"✅ Translated to {get_language_name(lang)}")
            
            # Small delay between languages
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Translation to {lang} failed: {e}")
            continue
    
    logger.info(f"Completed {len(translations)}/{len(target_languages)} translations")
    return translations


def translate_articles_batch(
    articles: List[Dict],
    target_languages: List[str] = None
) -> List[Dict[str, Dict]]:
    """
    Translate multiple articles to multiple languages.
    
    Args:
        articles: List of article dictionaries.
        target_languages: Target language codes.
        
    Returns:
        List of translation dictionaries (one per article).
    """
    if not is_translation_enabled():
        logger.info("Translation is disabled")
        return [{} for _ in articles]
    
    results = []
    
    for i, article in enumerate(articles):
        logger.info(f"Translating article {i + 1}/{len(articles)}...")
        translations = translate_article(article, target_languages)
        results.append(translations)
    
    return results


# ===========================================
# TESTING
# ===========================================

def test_translation():
    """Test translation functionality."""
    print("\n" + "="*60)
    print("🧪 Translation Service Test")
    print("="*60)
    
    # Check if enabled
    enabled = is_translation_enabled()
    print(f"\n📌 Translation enabled: {enabled}")
    
    if not enabled:
        print("\n⚠️ Translation is disabled in .env")
        print("   Set TRANSLATION_ENABLED=true to enable")
        print("="*60 + "\n")
        return None
    
    # Test article
    test_article = {
        "heading": "India's Economy Shows Strong Growth in Q4",
        "story": "India's GDP grew by 7.2% this quarter, exceeding analyst expectations. "
                "The growth was driven by strong performance in the services sector "
                "and increased consumer spending. Government officials attribute the "
                "success to recent policy reforms and infrastructure investments.",
        "language": "en"
    }
    
    print(f"\n📰 Test article: {test_article['heading']}")
    print("-" * 40)
    
    # Test with Hindi
    target_langs = ['hi']
    print(f"\n🌐 Translating to: {', '.join([get_language_name(l) for l in target_langs])}")
    
    try:
        from deep_translator import GoogleTranslator
        
        translations = translate_article(test_article, target_langs)
        
        if translations:
            for lang, translated in translations.items():
                print(f"\n✅ {get_language_name(lang)} Translation:")
                print(f"   📝 {translated['heading']}")
                print(f"   📊 Words: {translated.get('word_count', 'N/A')}")
        else:
            print("\n⚠️ No translations produced")
            
    except ImportError:
        print("\n❌ deep-translator not installed")
        print("   Run: pip install deep-translator")
    except Exception as e:
        print(f"\n❌ Translation failed: {e}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_translation()
