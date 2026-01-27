"""
Test the formatting function with real article data to debug bold text issue.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.api_integrations.hocalwire_uploader import format_article_for_cms

# Test with sample that mimics the real article structure
test_story = """DUBAI, January 23 –

The International Cricket Council (ICC) has removed Bangladesh from the upcoming T20 World Cup, replacing them with Scotland, due to a longstanding dispute over security concerns related to Bangladesh's scheduled matches in India. The decision comes after weeks of deliberation and dialogue between the ICC and the Bangladesh Cricket Board (BCB), which had requested to relocate its games from India. The ICC's refusal to change the venues has led to Bangladesh's ouster from the tournament, sparking a significant shift in the competition's landscape.

## Background of the Dispute

The dispute between the ICC and the BCB began when Bangladesh was drawn into Group C of the T20 World Cup, with its matches scheduled to take place in India. However, the BCB expressed concerns about the safety and security of its players and staff in India, citing potential risks and threats. The BCB had requested the ICC to relocate its matches to a neutral venue, but the governing body refused, citing the complexity and logistical challenges of making such a change.

## ICC's Decision and Its Implications

The ICC's decision to remove Bangladesh from the tournament is a significant development, with far-reaching implications for the competition and the teams involved. The ICC has stated that the decision was made after careful consideration and consultation with all parties involved, but the BCB has expressed disappointment and frustration with the outcome. The replacement of Bangladesh with Scotland has also raised questions about the fairness and integrity of the competition, with some arguing that Scotland's inclusion could give them an unfair advantage."""

formatted = format_article_for_cms(test_story)

print("="*80)
print("FORMATTED OUTPUT ANALYSIS")
print("="*80)
print()
print("Input story length:", len(test_story))
print("Output HTML length:", len(formatted))
print()
print("Checking for bold markers in output:")
print("  '**' found:", '**' in formatted)
print("  '<b>' found:", '<b>' in formatted)
print("  '<strong>' in body paragraphs:", formatted.count('<strong>') - formatted.count('## '))
print()
print("="*80)
print("FORMATTED HTML:")
print("="*80)
print(formatted)
print()
print("="*80)
