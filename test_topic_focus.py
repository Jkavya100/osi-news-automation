"""
Test script to validate topic focus detection
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from content_generation.article_generator import validate_topic_focus

# Test case 1: Gaza article with Australian Open content (SHOULD FAIL)
test_article_1 = {
    "heading": "Palestinians Face Ongoing Conflict and Humanitarian Crisis",
    "story": """DUBAI, January 23 –

A recent military operation in Gaza has highlighted the stark contrast in treatment between Israeli and Palestinian lives, with a massive effort to recover a single Israeli body resulting in the deaths of four Palestinian civilians and the destruction of a neighborhood. 

Meanwhile, in a separate development, Australian tennis fans were treated to a thrilling match at the Australian Open, where Carlos Alcaraz defeated Alex de Minaur to reach the semifinals.

The situation in Gaza remains dire, with thousands of Palestinians living in poverty and facing limited access to basic necessities."""
}

topic_1 = "Palestinians Face Ongoing Conflict and Humanitarian Crisis"

# Test case 2: Pure Gaza article (SHOULD PASS)
test_article_2 = {
    "heading": "Palestinians Face Ongoing Conflict and Humanitarian Crisis",
    "story": """DUBAI, January 23 –

A recent military operation in Gaza has highlighted the stark contrast in treatment between Israeli and Palestinian lives. The Israeli military mobilized a significant force to retrieve a body, leaving a trail of devastation.

The situation in Gaza remains dire, with thousands of Palestinians living in poverty and facing limited access to basic necessities."""
}

topic_2 = "Palestinians Face Ongoing Conflict and Humanitarian Crisis"

print("="*60)
print("Testing Topic Focus Validation")
print("="*60)

print("\n--- Test 1: Gaza article with sports content (should detect mixing) ---")
validation_1 = validate_topic_focus(test_article_1, topic_1, [])
print(f"Is Focused: {validation_1['is_focused']}")
print(f"Warnings: {validation_1['warnings']}")
print(f"Detected Categories: {validation_1['detected_categories']}")

print("\n--- Test 2: Pure Gaza article (should be focused) ---")
validation_2 = validate_topic_focus(test_article_2, topic_2, [])
print(f"Is Focused: {validation_2['is_focused']}")
print(f"Warnings: {validation_2['warnings']}")
print(f"Detected Categories: {validation_2['detected_categories']}")

print("\n" + "="*60)
print("✅ Test Complete!")
print("="*60)
