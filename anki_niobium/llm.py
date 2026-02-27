import os
import json
import base64
import anthropic
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from anki_niobium.cache import content_hash_bytes, get_cached_claude_response, set_cached_claude_response
from anki_niobium.theme import S

console = Console()

DEFAULT_SMART_PROMPT = """You are an expert at creating effective Anki flashcards using image occlusion.

You will receive an image alongside OCR-detected text regions. You can SEE the image — use your visual understanding to:
1. Understand what the image depicts
2. Determine which text regions are educationally valuable to quiz on
3. Correct any OCR misreadings by comparing the OCR text against what you actually see
4. Generate genuinely useful study hints

RESPONSE FORMAT — respond with ONLY this JSON:
{
  "context": "Brief description of what this image shows (1 sentence)",
  "decisions": [
    {
      "index": 0,
      "action": "occlude",
      "corrected_text": "Corrected version if OCR misread it, otherwise omit this field",
      "hint": "Relevant context or study aid"
    },
    {
      "index": 1,
      "action": "skip",
      "reason": "Brief reason"
    }
  ]
}

WHAT TO OCCLUDE (test-worthy content):
- Key terms, definitions, named concepts
- Labels on diagrams, charts, maps, figures
- Formulas, equations, numerical values
- Names, dates, classifications, categories
- Technical vocabulary and domain-specific terms
- Any specific term that would be tested in an exam

WHAT TO SKIP (not test-worthy):
- Figure labels and panel identifiers (A, B, C, Fig. 1, Panel 2)
- Publisher names, journal names, copyright notices, years
- Page numbers, watermarks, URLs, DOIs
- Generic headings that provide context but are not themselves testable ("Overview", "Summary")
- OCR noise and artifacts (random characters from image noise)
- Arrow markers or generic pointers that are not terms

HINTS — make them genuinely useful for learning:
- Functional notes: "Controls blood sugar levels"
- Relationships: "Opposite of inflation"
- Distinguishing features: "Unlike X, this does Y"
- Mnemonic aids when obvious: "Afferent = Arrives, Efferent = Exits"
- Keep under 20 words. Only add a hint when it genuinely aids recall.

OCR CORRECTION:
- Compare each OCR text against what you see in the image
- Technical terms are often misread by OCR — correct them
- Only include "corrected_text" when the OCR text is actually wrong
- If the OCR is correct, omit the "corrected_text" field entirely

WHEN IN DOUBT: Occlude. It is better to quiz on something than to miss it.

PRIORITY INSTRUCTIONS HANDLING:
When the user provides instructions below, they are ABSOLUTE — override ALL defaults above.
- Interpret instructions LITERALLY. If the user says "only from key facts", look for
  visually distinct elements labeled "KEY FACT" (boxes, callouts, sidebars) and only
  occlude text found within those elements. Skip everything else.
- When instructions say "only" or "exclusively", skip ALL content that does not match,
  even if it would normally be occluded. Return fewer decisions rather than violating
  the user's constraint.
"""

# Module-level client cache to avoid recreating per image in batch mode
_client_cache = {}


def _get_client(api_key):
    """Reuse Anthropic client across calls within the same session."""
    if api_key not in _client_cache:
        _client_cache[api_key] = anthropic.Anthropic(api_key=api_key)
    return _client_cache[api_key]


# Pricing per million tokens (USD) — updated as of 2025
_PRICING = {
    "claude-sonnet-4-6":  {"input": 3.00, "output": 15.00},
    "claude-opus-4-6":    {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5":   {"input": 0.80, "output": 4.00},
}
_DEFAULT_PRICING = {"input": 3.00, "output": 15.00}

# Running session totals
_session_totals = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0, "calls": 0}


def _log_usage(response, model):
    """Log token usage and estimated cost from an API response."""
    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    prices = _PRICING.get(model, _DEFAULT_PRICING)
    cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000

    _session_totals["input_tokens"] += input_tokens
    _session_totals["output_tokens"] += output_tokens
    _session_totals["cost"] += cost
    _session_totals["calls"] += 1

    console.print(
        f"[{S.muted}]  tokens: {input_tokens:,} in / {output_tokens:,} out "
        f"| cost: ${cost:.4f} "
        f"| session: ${_session_totals['cost']:.4f} ({_session_totals['calls']} calls)[/{S.muted}]"
    )


def smart_filter_results(results, image_bytes, config):
    """
    Use Claude Vision to semantically filter OCR results.

    Args:
        results: list of (bbox, text, prob) tuples from OCR/merge
        image_bytes: PNG image as bytes
        config: the loaded config dict

    Returns:
        (filtered_results, extra) — same shape as filter_results()
    """
    llm_config = config.get("llm", {})

    # API key: config takes priority, then env var
    api_key = llm_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(f"[{S.accent2}]No API key found. Set ANTHROPIC_API_KEY or add api_key to llm config.[/{S.accent2}]")
        console.print(f"[{S.accent2}]Falling back to rule-based filtering.[/{S.accent2}]")
        from anki_niobium.io import niobium
        return niobium.filter_results(results, config)

    if not results:
        return ([], "")

    model = llm_config.get("model", "claude-sonnet-4-6")
    max_tokens = llm_config.get("max_tokens", 1024)
    temperature = llm_config.get("temperature", 0.2)

    instructions = llm_config.get("instructions")
    if instructions:
        system_prompt = DEFAULT_SMART_PROMPT + f"\nPRIORITY INSTRUCTIONS (override defaults above):\n{instructions}\n"
    else:
        system_prompt = DEFAULT_SMART_PROMPT

    # Build indexed text list for Claude
    text_list = []
    for i, (bbox, text, prob) in enumerate(results):
        text_list.append({"index": i, "text": text, "confidence": round(prob, 2)})

    text_list_json = json.dumps(text_list, indent=2)
    image_bytes_hash = content_hash_bytes(image_bytes)
    no_cache = config.get("_no_cache", False)

    # Check Claude response cache
    cached = None
    if not no_cache:
        cached = get_cached_claude_response(image_bytes_hash, text_list_json, model, instructions)

    if cached is not None:
        data = cached
        from_cache = True
    else:
        # Live API call
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            },
            {
                "type": "text",
                "text": f"Here are the OCR-detected text regions:\n\n{text_list_json}\n\nAnalyze this image and classify each region.",
            },
        ]

        try:
            client = _get_client(api_key)
            console.print(f"[{S.accent}]Sending image to Claude ({model}) for smart filtering...[/{S.accent}]")
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            _log_usage(response, model)

            response_text = response.content[0].text

            # Strip markdown code fences if present
            if "```" in response_text:
                parts = response_text.split("```")
                for part in parts[1:]:
                    cleaned = part.strip()
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                    cleaned = cleaned.strip()
                    if cleaned.startswith("{"):
                        response_text = cleaned
                        break

            data = json.loads(response_text.strip())
            set_cached_claude_response(image_bytes_hash, text_list_json, model, instructions, data)
            from_cache = False

        except Exception as e:
            console.print(f"[{S.error}]Claude API error: {e}[/{S.error}]")
            console.print(f"[{S.accent2}]Falling back to rule-based filtering.[/{S.accent2}]")
            from anki_niobium.io import niobium
            return niobium.filter_results(results, config)

    # Process response (same path for cached and live)
    decisions = {d["index"]: d for d in data["decisions"]}

    context = data.get("context", "")
    extra = ""
    if context:
        extra = f'<div style="text-align:left;color:#555;font-style:italic;margin-bottom:8px;">{context}</div>'

    table = Table(show_header=True, header_style="bold", pad_edge=False, box=None)
    table.add_column("", width=2)
    table.add_column("Text", style="white", no_wrap=True, max_width=30)
    table.add_column("Detail", style=S.muted)

    filtered_results = []
    hints_html = ""
    corrections = 0
    for i, (bbox, text, prob) in enumerate(results):
        decision = decisions.get(i)
        if decision is None or decision.get("action") == "occlude":
            corrected = decision.get("corrected_text") if decision else None
            display_text = text
            if corrected and corrected != text:
                display_text = f"{corrected} [{S.muted}](was: {text})[/{S.muted}]"
                text = corrected
                corrections += 1

            filtered_results.append((bbox, text, prob))
            hint = decision.get("hint", "") if decision else ""
            if hint:
                hints_html += f"<b>{text}</b>: {hint}<br>"
            table.add_row(f"[{S.success}]+[/{S.success}]", display_text, hint if hint else f"[{S.muted}]-[/{S.muted}]")
        else:
            reason = decision.get("reason", "")
            table.add_row(f"[{S.error}]-[/{S.error}]", f"[{S.muted}]{text}[/{S.muted}]", f"[{S.muted}]{reason}[/{S.muted}]")

    if hints_html:
        extra += hints_html

    kept = len(filtered_results)
    skipped = len(results) - kept
    subtitle_parts = [f"[{S.success}]{kept} kept[/{S.success}]", f"[{S.error}]{skipped} skipped[/{S.error}]"]
    if corrections:
        subtitle_parts.append(f"[{S.accent}]{corrections} OCR fixes[/{S.accent}]")
    if from_cache:
        subtitle_parts.append(f"[{S.muted}]cached[/{S.muted}]")
    subtitle = " | ".join(subtitle_parts)

    renderables = []
    if context:
        renderables.append(Text.from_markup(f"[italic]{context}[/italic]\n"))
    renderables.append(table)

    panel = Panel(
        Group(*renderables),
        title=f"[bold]Smart Filter[/bold] [{S.muted}]({model})[/{S.muted}]",
        subtitle=subtitle,
        border_style=S.accent,
        padding=(1, 1),
    )
    console.print(panel)

    return (filtered_results, extra)


SMART_GENERATE_PROMPT = """You are an expert flashcard creator. You analyze educational content and produce effective Anki flashcards that follow evidence-based study principles.

You will receive content from a PDF page — either as an image, extracted text, or both. Analyze the content and create the best flashcards possible.

For each card, choose the most appropriate type:

1. **image_occlusion**: ONLY when the image contains labeled regions, annotated diagrams, or text overlaid on a figure where hiding a label and asking the learner to recall it makes sense. The image must have identifiable text or symbols to occlude. Do NOT create image_occlusion for:
   - Photos or illustrations with no labels/annotations
   - Charts where all information is better captured as text
   - Decorative images that add no educational value
   Provide rectangular coordinates as fractions of image width/height (0.0 to 1.0).

2. **cloze**: When there are important facts, definitions, formulas, or concepts that work well as fill-in-the-blank. Use Anki cloze syntax: {{c1::answer}}. Multiple cloze deletions per card are fine (c1, c2, c3...). When extracted text is provided, quote it accurately for cloze cards.

3. **basic**: When the content is best tested as a question/answer pair. Also use this for visual content that isn't suited for occlusion — e.g., "What does [structure/process] look like?" with a description as the answer.

RESPONSE FORMAT — respond with ONLY this JSON:
{
  "page_summary": "Brief description of what this page covers (1 sentence)",
  "cards": [
    {
      "type": "image_occlusion",
      "occlusions": [
        {"left": 0.12, "top": 0.23, "width": 0.05, "height": 0.03, "label": "What is hidden here"}
      ],
      "hint": "Optional context"
    },
    {
      "type": "cloze",
      "text": "The {{c1::mitochondria}} is the powerhouse of the {{c2::cell}}.",
      "hint": "Optional extra info"
    },
    {
      "type": "basic",
      "front": "Clear, specific question?",
      "back": "Concise answer",
      "hint": "Optional context"
    }
  ]
}

CARD QUALITY PRINCIPLES:
- Each card tests ONE concept (atomic cards)
- Cloze deletions should test recall, not recognition — hide the hard part
- Basic card questions must be specific and unambiguous
- Hints should aid understanding, not give away the answer
- Skip metadata: page numbers, headers/footers, copyright, watermarks
- Prefer cloze for factual/definitional content, basic for conceptual "why/how" questions
- Only use image_occlusion when the image has labeled regions worth hiding
- If an image has no text/labels to occlude, describe it in a basic card or skip it
- When both image and text are provided, use the text for accurate cloze quotes and the image for spatial/visual understanding
- Generate as many cards as the content warrants (typically 1-10 per page) — never pad to fill a quota

PRIORITY INSTRUCTIONS HANDLING:
When the user provides instructions below, they are ABSOLUTE — override ALL defaults.
- Interpret instructions LITERALLY. If the user says "only from key facts", look for
  visually distinct elements on the page labeled "KEY FACT" (boxes, callouts, sidebars,
  highlighted sections) and create cards ONLY from those. Ignore all surrounding body text.
- If the instruction references a specific visual element (e.g., "key facts", "tables",
  "diagrams", "highlighted boxes", "mnemonics"), scan the page for those elements and
  restrict card generation to content found within them.
- When instructions say "only" or "exclusively", generate ZERO cards from content that
  does not match. Return fewer cards or even an empty cards list rather than violating
  the user's constraint.
"""


def smart_generate_cards(page_index, page_image_bytes, config, max_cards=None, card_type=None, page_text=None, page_label=None):
    """
    Use Claude to analyze page content and generate cards of multiple types.

    Three sending modes based on available content:
      - text:        markdown only (no figures on page)
      - image + text: full page render + markdown (page has figures)
      - image:       image only (standalone image input, no PDF text)

    page_label is the user-visible page number (from PDF labels); falls back to
    page_index + 1 when not provided.
    """
    display_page = page_label or str(page_index + 1)
    has_image = page_image_bytes is not None
    has_text = page_text is not None and len(page_text.strip()) > 0
    llm_config = config.get("llm", {})

    api_key = llm_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(f"[{S.error}]No API key found. --smart requires ANTHROPIC_API_KEY.[/{S.error}]")
        raise ValueError("API key required for smart generation")

    model = llm_config.get("model", "claude-sonnet-4-6")
    max_tokens = llm_config.get("max_tokens_generate", 4096)
    temperature = llm_config.get("temperature", 0.2)

    instructions = llm_config.get("instructions")
    if instructions:
        system_prompt = SMART_GENERATE_PROMPT + f"\nPRIORITY INSTRUCTIONS (override defaults above):\n{instructions}\n"
    else:
        system_prompt = SMART_GENERATE_PROMPT

    constraints = []
    if not has_image:
        constraints.append("No image is provided. Do NOT generate image_occlusion cards. Only generate 'cloze' and/or 'basic' cards.")
    if max_cards:
        constraints.append(f"Generate no more than {max_cards} cards for this page. This is a CEILING, not a target — if the content only warrants fewer cards, generate fewer. Never pad to reach this number.")
    if card_type:
        constraints.append(f"ONLY generate cards of type '{card_type}'. Do not use any other card type.")
    if constraints:
        system_prompt += "\nCONSTRAINTS:\n" + "\n".join(f"- {c}" for c in constraints) + "\n"

    # Cache key accounts for the sending mode
    if has_image:
        content_hash = content_hash_bytes(page_image_bytes)
    else:
        content_hash = content_hash_bytes(page_text.encode("utf-8"))
    mode_tag = "img_text" if (has_image and has_text) else ("text" if has_text else "img")
    cache_text_key = f"smart_generate_page_{page_index}_max{max_cards}_type{card_type}_mode{mode_tag}"
    no_cache = config.get("_no_cache", False)

    cached = None
    if not no_cache:
        cached = get_cached_claude_response(content_hash, cache_text_key, model, instructions)

    if cached is not None:
        data = cached
        from_cache = True
    else:
        # Build user message based on available content
        if has_image and has_text:
            mode_label = "image + text"
            image_b64 = base64.b64encode(page_image_bytes).decode("utf-8")
            user_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"This is page {display_page} of a PDF. The image shows the full page render. "
                        f"Below is the structured text extracted from this page:\n\n"
                        f"---\n{page_text}\n---\n\n"
                        f"Use BOTH the image (for visual content, diagrams, spatial layout) "
                        f"and the extracted text (for accurate quotes in cloze cards) to generate flashcards."
                    ),
                },
            ]
        elif has_image:
            mode_label = "image"
            image_b64 = base64.b64encode(page_image_bytes).decode("utf-8")
            user_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": f"Analyze this image and generate flashcards.",
                },
            ]
        else:
            mode_label = "text"
            user_content = [
                {
                    "type": "text",
                    "text": (
                        f"This is the text content of page {display_page} of a PDF. "
                        f"There are no diagrams or figures on this page.\n\n"
                        f"---\n{page_text}\n---\n\n"
                        f"Analyze this text and generate flashcards."
                    ),
                },
            ]

        try:
            client = _get_client(api_key)
            console.print(f"[{S.accent}]Sending page {display_page} ({mode_label}) to Claude ({model})...[/{S.accent}]")
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            _log_usage(response, model)

            response_text = response.content[0].text

            if "```" in response_text:
                parts = response_text.split("```")
                for part in parts[1:]:
                    cleaned = part.strip()
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                    cleaned = cleaned.strip()
                    if cleaned.startswith("{"):
                        response_text = cleaned
                        break

            data = json.loads(response_text.strip())
            set_cached_claude_response(content_hash, cache_text_key, model, instructions, data)
            from_cache = False

        except Exception as e:
            console.print(f"[{S.error}]Claude API error for page {display_page}: {e}[/{S.error}]")
            raise

    _display_generated_cards(data, display_page, model, from_cache)
    return data


def _display_generated_cards(data, display_page, model, from_cache):
    table = Table(show_header=True, header_style="bold", pad_edge=False, box=None)
    table.add_column("#", width=3)
    table.add_column("Type", style=S.accent, width=16)
    table.add_column("Content", style="white", no_wrap=False)

    for i, card in enumerate(data.get("cards", []), 1):
        card_type = card["type"]
        if card_type == "image_occlusion":
            n = len(card.get("occlusions", []))
            content = f"{n} occlusion region(s)"
        elif card_type == "cloze":
            content = card.get("text", "")
        elif card_type == "basic":
            content = f"Q: {card.get('front', '')}\nA: {card.get('back', '')}"
        else:
            content = "unknown type"
        table.add_row(str(i), card_type, content)

    subtitle_parts = [f"[{S.success}]{len(data.get('cards', []))} cards[/{S.success}]"]
    if from_cache:
        subtitle_parts.append(f"[{S.muted}]cached[/{S.muted}]")
    subtitle = " | ".join(subtitle_parts)

    renderables = []
    summary = data.get("page_summary", "")
    if summary:
        renderables.append(Text.from_markup(f"[italic]{summary}[/italic]\n"))
    renderables.append(table)

    panel = Panel(
        Group(*renderables),
        title=f"[bold]Smart Generate[/bold] — Page {display_page} [{S.muted}]({model})[/{S.muted}]",
        subtitle=subtitle,
        border_style=S.accent2,
        padding=(1, 1),
    )
    console.print(panel)
