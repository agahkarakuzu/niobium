import os
import json
import base64
import anthropic
from rich.console import Console

console = Console()

DEFAULT_SMART_PROMPT = """You are helping medical and science students create effective Anki flashcards from educational images using image occlusion.

You will receive an image alongside OCR-detected text regions. You can SEE the image — use your visual understanding to:
1. Understand what the image depicts (anatomy, histology, pathology, pharmacology, biochemistry, etc.)
2. Determine which text regions are educationally valuable to quiz on
3. Correct any OCR misreadings by comparing the OCR text against what you actually see in the image
4. Generate genuinely useful study hints that go beyond simple definitions

RESPONSE FORMAT — respond with ONLY this JSON:
{
  "context": "Brief description of what this image shows (1 sentence)",
  "decisions": [
    {
      "index": 0,
      "action": "occlude",
      "corrected_text": "Corrected version if OCR misread it, otherwise omit this field",
      "hint": "Clinically relevant context, function, or study aid"
    },
    {
      "index": 1,
      "action": "skip",
      "reason": "Brief reason"
    }
  ]
}

WHAT TO OCCLUDE (test-worthy content):
- Anatomical structures, organs, tissue layers, cell types
- Disease names, pathological findings, diagnostic criteria
- Drug names, drug classes, mechanisms of action, side effects
- Key numerical values (lab reference ranges, dosages, percentages)
- Biochemical pathways, enzymes, substrates, products
- Microorganisms, vectors, transmission routes
- Any specific term a professor would ask about on an exam

WHAT TO SKIP (not test-worthy):
- Figure labels and panel identifiers (A, B, C, Fig. 1, Panel 2)
- Publisher names, journal names, copyright notices, years
- Page numbers, watermarks, URLs, DOIs
- Generic headings that provide context but are not themselves testable ("Overview", "Summary")
- OCR noise and artifacts (random characters from image noise)
- Arrow markers or generic pointers that are not terms

HINTS — make them genuinely useful for learning:
- Clinical correlations: "Commonly injured in shoulder dislocations"
- Functional notes: "Produces bile and detoxifies blood"
- Alternative/Latin names: "Also called epinephrine"
- Distinguishing features: "Unlike skeletal muscle, contracts involuntarily"
- Pathology links: "Inflammation here causes peritonitis"
- Mnemonic aids when obvious: "Afferent = Arrives, Efferent = Exits"
- Keep under 20 words. Only add a hint when it genuinely aids recall.

OCR CORRECTION:
- Compare each OCR text against what you see in the image
- Medical terms are often misread (e.g., "Glcmerulus" → "Glomerulus")
- Only include "corrected_text" when the OCR text is actually wrong
- If the OCR is correct, omit the "corrected_text" field entirely

WHEN IN DOUBT: Occlude. It is better to quiz on something than to miss it.
"""

# Module-level client cache to avoid recreating per image in batch mode
_client_cache = {}


def _get_client(api_key):
    """Reuse Anthropic client across calls within the same session."""
    if api_key not in _client_cache:
        _client_cache[api_key] = anthropic.Anthropic(api_key=api_key)
    return _client_cache[api_key]


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
        console.print("[yellow]No API key found. Set ANTHROPIC_API_KEY or add api_key to llm config.[/yellow]")
        console.print("[yellow]Falling back to rule-based filtering.[/yellow]")
        from anki_niobium.io import niobium
        return niobium.filter_results(results, config)

    if not results:
        return ([], "")

    model = llm_config.get("model", "claude-sonnet-4-6-20250514")
    max_tokens = llm_config.get("max_tokens", 1024)
    temperature = llm_config.get("temperature", 0.2)

    instructions = llm_config.get("instructions")
    if instructions:
        system_prompt = DEFAULT_SMART_PROMPT + f"\nADDITIONAL INSTRUCTIONS FROM USER:\n{instructions}\n"
    else:
        system_prompt = DEFAULT_SMART_PROMPT

    # Build indexed text list for Claude
    text_list = []
    for i, (bbox, text, prob) in enumerate(results):
        text_list.append({"index": i, "text": text, "confidence": round(prob, 2)})

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
            "text": f"Here are the OCR-detected text regions:\n\n{json.dumps(text_list, indent=2)}\n\nAnalyze this image and classify each region.",
        },
    ]

    try:
        client = _get_client(api_key)
        console.print(f"[cyan]Sending image to Claude ({model}) for smart filtering...[/cyan]")
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

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
        decisions = {d["index"]: d for d in data["decisions"]}

        # Use image context as a header in Back Extra
        context = data.get("context", "")
        extra = ""
        if context:
            extra = f'<div style="text-align:left;color:#555;font-style:italic;margin-bottom:8px;">{context}</div>'
            console.print(f"[cyan]  Context: {context}[/cyan]")

        filtered_results = []
        hints_html = ""
        corrections = 0
        for i, (bbox, text, prob) in enumerate(results):
            decision = decisions.get(i)
            if decision is None or decision.get("action") == "occlude":
                # Apply OCR correction if Claude detected a misread
                corrected = decision.get("corrected_text") if decision else None
                if corrected and corrected != text:
                    console.print(f"[cyan]  OCR fix: '{text}' → '{corrected}'[/cyan]")
                    text = corrected
                    corrections += 1

                filtered_results.append((bbox, text, prob))
                hint = decision.get("hint", "") if decision else ""
                if hint:
                    hints_html += f"<b>{text}</b>: {hint}<br>"
                    console.print(f"[cyan]  Hint for '{text}': {hint}[/cyan]")
            else:
                reason = decision.get("reason", "")
                console.print(f"[dim]  Skipping '{text}'{f' ({reason})' if reason else ''}[/dim]")

        if hints_html:
            extra += hints_html

        kept = len(filtered_results)
        skipped = len(results) - kept
        summary = f"Smart filter: {kept} kept, {skipped} skipped"
        if corrections:
            summary += f", {corrections} OCR corrections"
        console.print(f"[green]{summary}[/green]")
        return (filtered_results, extra)

    except Exception as e:
        console.print(f"[bold red]Claude API error: {e}[/bold red]")
        console.print("[yellow]Falling back to rule-based filtering.[/yellow]")
        from anki_niobium.io import niobium
        return niobium.filter_results(results, config)
