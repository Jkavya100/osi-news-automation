"""
Test the updated formatting function to ensure consistent fonts on Hocalwire.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.api_integrations.hocalwire_uploader import format_article_for_cms

# Sample article with markdown formatting (like your generated articles)
sample_story = """India's parliament passed a landmark climate bill today, committing the nation to net-zero emissions by 2070.

## Key Provisions

The legislation includes mandatory renewable energy targets for all major industries and establishes a national carbon trading system.

## Political Response

Opposition parties praised the bipartisan effort, while environmental groups called for more aggressive timelines.

## Economic Impact

Economists predict the transition will create millions of green jobs while requiring significant infrastructure investment over the next decade.

The bill now awaits presidential approval before becoming law."""

# Test formatting
formatted_html = format_article_for_cms(sample_story)

print("="*80)
print("FORMATTED HTML OUTPUT FOR HOCALWIRE")
print("="*80)
print("\n" + formatted_html + "\n")
print("="*80)
print("\nKEY CHANGES:")
print("- Subheadings converted to <p><strong> (NOT <h2>)")
print("- All text uses same paragraph formatting")
print("- Consistent font styling on Hocalwire")
print("="*80)
