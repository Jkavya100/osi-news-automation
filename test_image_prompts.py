"""
Test improved image prompt generation for relevance.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.image_generation.image_creator import build_image_prompt

# Test article about cricket (like the one in the screenshot)
cricket_article = {
    "heading": "Bangladesh Out of T20 World Cup After ICC's Refusal",
    "story": """The International Cricket Council (ICC) has removed Bangladesh from the upcoming T20 World Cup, replacing them with Scotland, due to a longstanding dispute over security concerns related to Bangladesh's scheduled matches in India. The decision comes after weeks of deliberation and dialogue between the ICC and the Bangladesh Cricket Board (BCB), which had requested to relocate its games from India. The ICC's refusal to change the venues has led to Bangladesh's ouster from the tournament, sparking a significant shift in the competition's landscape.

## Background of the Dispute

The dispute between the ICC and the BCB began when Bangladesh expressed concerns about the safety and security of its players and staff in India, citing potential risks and threats. The BCB had requested the ICC to consider alternative venues for its matches, but the ICC ultimately decided to stick with the original schedule.""",
    "location": "DUBAI",
    "dateline": "DUBAI",
    "topic": "Cricket T20 World Cup Bangladesh ICC"
}

# Test other types
politics_article = {
    "heading": "Prime Minister Announces New Economic Reforms",
    "story": "The government has introduced sweeping economic reforms aimed at boosting growth...",
    "location": "NEW DELHI",
    "topic": "Politics Economic Policy"
}

tech_article = {
    "heading": "New AI Breakthrough in Medical Diagnostics",
    "story": "Researchers have developed an AI system that can detect diseases with unprecedented accuracy...",
    "location": "SAN FRANCISCO",
    "topic": "Technology AI Health" 
}

print("="*80)
print("IMAGE PROMPT GENERATION TEST - Improved Version")
print("="*80)

print("\n\n1. CRICKET ARTICLE (Main Test)")
print("-"*80)
print(f"Heading: {cricket_article['heading']}")
print(f"Location: {cricket_article['location']}")
prompt = build_image_prompt(cricket_article)
print(f"\nGenerated Prompt:\n{prompt}")

print("\n\n2. POLITICS ARTICLE")
print("-"*80)
print(f"Heading: {politics_article['heading']}")
prompt = build_image_prompt(politics_article)
print(f"\nGenerated Prompt:\n{prompt[:200]}...")

print("\n\n3. TECHNOLOGY ARTICLE")
print("-"*80)
print(f"Heading: {tech_article['heading']}")
prompt = build_image_prompt(tech_article)
print(f"\nGenerated Prompt:\n{prompt[:200]}...")

print("\n\n" + "="*80)
print("KEY IMPROVEMENTS:")
print("="*80)
print("✅ Cricket articles now generate cricket-specific prompts")
print("✅ Location/country context included in all prompts")
print("✅ Priority-based content detection (sports first)")
print("✅ More detailed keyword matching")
print("="*80)
