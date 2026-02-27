import re
from django import template

register = template.Library()


@register.filter
def split_goals(value):
    """Split a goals string into individual items, stripping leading numbers/bullets."""
    if not value:
        return []
    parts = re.split(r'\s*(?=(?:\d+\.|•)\s)', value.strip())
    cleaned = []
    for p in parts:
        p = p.strip()
        p = re.sub(r'^\d+\.\s*', '', p)   # remove "1. "
        p = re.sub(r'^•\s*', '', p)        # remove "• "
        if p:
            cleaned.append(p)
    return cleaned


@register.filter
def ensure_list(value):
    """Return value as a list. If it's already a list, return as-is.
    If it's a string, wrap in a list. Otherwise return empty list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


@register.filter
def split_numbered(value):
    """If value is already a list, return as-is.
    If it's a string, split on numbered points like 1), 2), 3) … into separate items."""
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value:
        return []
    parts = re.split(r'\s+(?=\d+\))', value)
    return [p.strip() for p in parts if p.strip()]


@register.filter
def as_sections(value):
    """Parse nutrition notes into a list of dicts with 'title' and 'text' keys.

    Handles three formats:
      - New AI format: list of {title, text} dicts → returned as-is
      - Old AI format: single string with ALLCAPS headers like "ГИДРАТАЦИЯ: ..."
      - List of plain strings → each becomes a section with no title
    """
    if not value:
        return []

    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append({'title': item.get('title') or '', 'text': item.get('text', '')})
            else:
                result.append({'title': '', 'text': str(item)})
        return result

    if isinstance(value, str):
        # Split on sentence boundary followed by an ALLCAPS header (2+ consecutive uppercase chars before colon)
        parts = re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z]{2}[А-ЯA-Z\s\-/()+0-9A-Z]*:)', value)
        result = []
        for part in parts:
            part = part.strip()
            m = re.match(r'^([А-ЯA-Z][А-ЯA-Z\s\-/()+0-9A-Z]*?):\s*(.*)', part, re.DOTALL)
            if m:
                result.append({'title': m.group(1).strip(), 'text': m.group(2).strip()})
            else:
                result.append({'title': '', 'text': part})
        return result or [{'title': '', 'text': value}]

    return []
