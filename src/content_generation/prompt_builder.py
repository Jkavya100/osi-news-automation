"""
OSI News Automation – Prompt Builder
=====================================
Builds editorially-structured prompts for Groq / LLaMA article synthesis.

Provides:
    build_synthesis_prompt   – returns (system_msg, user_prompt, dateline, story_type)
    detect_story_type        – classifies source articles into a StoryType
    resolve_dateline         – picks the most-common source location + current date
    extract_source_digest    – token-budgeted source digest
    extract_newsworthiness_signals – info-quality tier guidance
    parse_generated_article  – splits LLM output into heading / sub_heading / story
    SYSTEM_MESSAGE           – journalist persona (system role constant)
"""

import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ───────────────────────────────────────
# Story-type classification
# ───────────────────────────────────────

@dataclass
class StoryType:
    """Represents a detected story category with matching section structure."""
    name: str
    sections: List[str] = field(default_factory=list)


# Pre-defined story types with recommended article sections
_STORY_TYPES = {
    "scientific": StoryType(
        name="scientific",
        sections=[
            "The Discovery",
            "Scientific Context",
            "Methodology & Reliability",
            "Expert Reception",
            "Path Forward",
        ],
    ),
    "economic": StoryType(
        name="economic",
        sections=[
            "The Economic Event",
            "Market Response",
            "Transmission & Impact",
            "Policy & Intervention",
            "Historical Context",
        ],
    ),
    "social": StoryType(
        name="social",
        sections=[
            "The Shift",
            "Who's Leading, Who's Resisting",
            "Institutional Response",
            "Speed & Scale",
            "Substance Assessment",
        ],
    ),
    "political": StoryType(
        name="political",
        sections=[
            "The Development",
            "Political Landscape",
            "Stakeholder Positions",
            "Public Reaction",
            "What Comes Next",
        ],
    ),
    "general": StoryType(
        name="general",
        sections=[
            "What Happened",
            "Key Details",
            "Background & Context",
            "Reactions",
            "Looking Ahead",
        ],
    ),
}

_KEYWORD_MAP = {
    "scientific": [
        "study", "research", "findings", "scientist", "discovery",
        "breakthrough", "published", "journal", "peer-reviewed",
        "experiment", "data", "clinical", "medical",
    ],
    "economic": [
        "economy", "market", "gdp", "inflation", "stock", "trade",
        "financial", "investment", "currency", "recession", "growth",
        "employment", "industry", "revenue", "profit",
    ],
    "social": [
        "trend", "social", "cultural", "generation", "adoption",
        "behavior", "demographic", "movement", "community", "society",
        "lifestyle", "millennials", "gen z", "viral",
    ],
    "political": [
        "election", "government", "president", "parliament", "minister",
        "political", "legislation", "vote", "policy", "opposition",
        "coalition", "reform", "diplomat", "sanctions",
    ],
}

_THRESHOLD = 3  # minimum keyword hits to trigger a category


def detect_story_type(articles: List[Dict], topic: str) -> StoryType:
    """
    Classify a set of source articles into a StoryType.

    Scans topic + first 5 articles for category keywords.
    Returns the best-matching StoryType, or *general* if no category
    meets the threshold.
    """
    combined = topic.lower() + " "
    for article in articles[:5]:
        combined += article.get("heading", "").lower() + " "
        combined += article.get("story", "")[:300].lower() + " "

    scores = {
        cat: sum(1 for kw in keywords if kw in combined)
        for cat, keywords in _KEYWORD_MAP.items()
    }

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] >= _THRESHOLD:
        return _STORY_TYPES[best_cat]
    return _STORY_TYPES["general"]


# ───────────────────────────────────────
# Dateline resolution
# ───────────────────────────────────────

def resolve_dateline(articles: List[Dict]) -> str:
    """
    Return an uppercase dateline string like ``NEW DELHI, March 21``.

    Picks the most-common *location* field across source articles,
    appends the current date.  Falls back to ``NEW DELHI`` when no
    locations are available.
    """
    locations = [
        a.get("location", "").strip()
        for a in articles
        if a.get("location", "").strip() and a.get("location", "").strip().lower() != "unknown"
    ]

    if locations:
        city = Counter(locations).most_common(1)[0][0].upper()
    else:
        city = "NEW DELHI"

    now = datetime.now()
    return f"{city}, {now.strftime('%B')} {now.day}"


# ───────────────────────────────────────
# Source digest with dynamic token budget
# ───────────────────────────────────────

def extract_source_digest(
    articles: List[Dict],
    token_budget: int = 4000,
) -> str:
    """
    Build a source-material digest within *token_budget* characters.

    Divides the budget evenly across sources (max 10), so longer
    article lists get shorter per-source slices instead of the old
    hard-coded 500-char limit.
    """
    usable = articles[:10]
    if not usable:
        return "(no source material)"

    per_source = max(200, token_budget // len(usable))
    parts: List[str] = []

    for i, article in enumerate(usable, 1):
        source_name = article.get("source_name", "Unknown Source")
        heading = article.get("heading", "No headline")
        story = article.get("story", "")[:per_source]
        location = article.get("location", "Unknown")

        parts.append(
            f"Source {i} ({source_name}, {location}):\n"
            f"Headline: {heading}\n"
            f"Content: {story}..."
        )

    return "\n\n".join(parts)


# ───────────────────────────────────────
# Newsworthiness / quality signals
# ───────────────────────────────────────

def extract_newsworthiness_signals(articles: List[Dict]) -> str:
    """
    Return an information-quality tier guide to embed in the prompt.
    """
    return (
        "INFORMATION QUALITY TIERS (Apply This Filter):\n"
        "✅ TIER 1 – MUST INCLUDE: Verified by 3+ sources, high impact, core to story\n"
        "✅ TIER 2 – SHOULD INCLUDE: 2 sources or credible expert analysis, moderate impact\n"
        "⚠️ TIER 3 – COULD INCLUDE: Single credible source, clearly label as preliminary\n"
        "❌ TIER 4 – EXCLUDE: Unverified rumors, promotional content, irrelevant details"
    )


# ───────────────────────────────────────
# System message (persona)
# ───────────────────────────────────────

SYSTEM_MESSAGE: str = (
    "You are a senior wire-service journalist writing for a major international "
    "news agency.  You write comprehensive, balanced, factual news articles by "
    "synthesising multiple sources.  Follow AP Style.  "
    "Each article MUST focus on ONE SINGLE TOPIC.  If sources cover unrelated "
    "topics, identify the main topic and write EXCLUSIVELY about it.  "
    "NEVER attribute information to specific media outlets (❌ 'BBC reported…').  "
    "You MAY attribute to institutional actors (✅ 'The WHO confirmed…').  "
    "Do NOT fabricate facts.  Do NOT include opinions."
)


# ───────────────────────────────────────
# Prompt builder (main entry point)
# ───────────────────────────────────────

def build_synthesis_prompt(
    articles: List[Dict],
    topic: str,
    target_words: int = 800,
    include_subheadings: bool = True,
) -> Tuple[str, str, str, StoryType]:
    """
    Build a full editorial prompt for article synthesis.

    Returns
    -------
    system_msg : str
        Persona / system-role message.
    user_prompt : str
        Task-specific user message with all source material.
    dateline : str
        Resolved dateline string (e.g. ``NEW DELHI, March 21``).
    story_type : StoryType
        Detected story category with matching section list.
    """
    story_type = detect_story_type(articles, topic)
    dateline = resolve_dateline(articles)
    source_digest = extract_source_digest(articles)
    quality_tiers = extract_newsworthiness_signals(articles)

    # Section structure for this story type
    section_block = ""
    if include_subheadings and story_type.sections:
        section_list = "\n".join(f"## {s}" for s in story_type.sections)
        section_block = (
            f"\nRECOMMENDED SECTIONS for {story_type.name.upper()} stories:\n"
            f"{section_list}\n"
        )

    subheading_count = int(os.getenv("SUBHEADING_COUNT", 5))
    subheading_instruction = ""
    if include_subheadings:
        subheading_instruction = (
            f"\n3. Include {subheading_count} descriptive subheadings "
            f"(use ## markdown format)"
        )

    user_prompt = f"""Write a comprehensive news article about: {topic}

STORY TYPE: {story_type.name.upper()}

═══════════════════════════════════════
PART 1 – SOURCE MATERIALS
═══════════════════════════════════════
{source_digest}

═══════════════════════════════════════
PART 2 – INFORMATION QUALITY FILTER
═══════════════════════════════════════
{quality_tiers}

═══════════════════════════════════════
PART 3 – SCOPE CONSTRAINT
═══════════════════════════════════════
The MAIN TOPIC is: "{topic}"
• Write EXCLUSIVELY about this topic.
• If sources contain unrelated stories, IGNORE them completely.
• Every paragraph must pass the test: "Is this about {topic}?" → YES.
• DO NOT mix unrelated events (e.g., Gaza conflict + Australian Open).

═══════════════════════════════════════
PART 4 – ATTRIBUTION RULES
═══════════════════════════════════════
BANNED – outlet attribution:
  ❌ "According to BBC News…"
  ❌ "Reuters reported…"
  ❌ "Sources say…"
ALLOWED – institutional attribution:
  ✅ "The World Health Organization confirmed…"
  ✅ "India's Finance Ministry stated…"
  ✅ "Police said…"

═══════════════════════════════════════
PART 5 – ARTICLE STRUCTURE
═══════════════════════════════════════
1. Headline (# markdown, 10-15 words) — about "{topic}" ONLY
2. Subheading (### markdown, MAXIMUM 150 characters) — concise event summary{subheading_instruction}
4. Dateline: {dateline} –
5. Strong lead paragraph: who, what, when, where, why
6. Organised body with subheadings (follow section guide below if applicable)
7. Closing paragraph with implications or future outlook
{section_block}
═══════════════════════════════════════
PART 6 – LENGTH & STYLE
═══════════════════════════════════════
• Minimum {target_words} words
• AP Style, objective, factual tone
• No opinions, no speculation, no fabricated facts
• No Tier 4 information

═══════════════════════════════════════
PART 7 – OUTPUT FORMAT
═══════════════════════════════════════
# [Headline]

### [Subheading – max 150 chars]

{dateline} –

[Lead paragraph]

## [Section 1]
[Content]

## [Section 2]
[Content]

...

═══════════════════════════════════════
PART 8 – SELF-CHECK BEFORE SUBMITTING
═══════════════════════════════════════
Before you finish, verify:
☑ Every paragraph is about "{topic}"
☑ No outlet names appear in the text
☑ Dateline is present and correct
☑ Word count ≥ {target_words}
☑ Subheading ≤ 150 characters

Write the article NOW:"""

    return SYSTEM_MESSAGE, user_prompt, dateline, story_type


# ───────────────────────────────────────
# Article parser
# ───────────────────────────────────────

def parse_generated_article(generated_text: str) -> Dict:
    """
    Parse LLM-generated text into a structured article dict.

    Returns
    -------
    dict with keys ``heading``, ``sub_heading``, ``story``.
    """
    if not generated_text:
        return {"heading": "", "sub_heading": "", "story": ""}

    lines = generated_text.strip().split("\n")

    # ── Extract headline (first line starting with # or ##) ──
    heading = ""
    headline_index = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") or stripped.startswith("## "):
            heading = stripped.lstrip("# ").strip()
            headline_index = i
            break

    # ── Extract subheading (first ### after headline) ──
    sub_heading = ""
    subheading_index = -1

    if headline_index >= 0:
        for i in range(headline_index + 1, min(headline_index + 10, len(lines))):
            stripped = lines[i].strip()
            if stripped.startswith("### "):
                sub_heading = stripped.replace("### ", "", 1).strip()
                if len(sub_heading) > 150:
                    sub_heading = sub_heading[:147] + "..."
                subheading_index = i
                break

    # ── Fallback: use first non-empty, non-heading line ──
    if not heading:
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith("#"):
                heading = line.strip()
                headline_index = i
                break

    # ── Extract body ──
    body_start = max(headline_index, subheading_index)
    body_lines = lines[body_start + 1:] if body_start >= 0 else lines[1:]

    story = "\n".join(body_lines).strip()
    story = re.sub(r"^[\s\n]+", "", story)
    story = re.sub(r"[\s\n]+$", "", story)

    return {
        "heading": heading,
        "sub_heading": sub_heading,
        "story": story,
    }
