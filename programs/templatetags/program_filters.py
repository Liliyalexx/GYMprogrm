import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# SVG illustrations per muscle group — simple clean figures on gradient backgrounds
_MUSCLE_SVG = {
    'cardio': (
        '#e0f2fe', '#0ea5e9',
        # person on bike
        '<ellipse cx="50" cy="28" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="36" x2="44" y2="55" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="44" y1="55" x2="35" y2="70" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="44" y1="55" x2="56" y2="70" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="62" y2="48" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="35" cy="72" r="10" fill="none" stroke="{c}" stroke-width="3"/>'
        '<circle cx="65" cy="72" r="10" fill="none" stroke="{c}" stroke-width="3"/>'
        '<line x1="35" y1="72" x2="65" y2="72" stroke="{c}" stroke-width="2.5"/>'
        '<line x1="62" y1="48" x2="68" y2="60" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="65" y1="62" x2="56" y2="70" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
    'glutes': (
        '#fdf4ff', '#a855f7',
        # squat figure
        '<ellipse cx="50" cy="20" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="28" x2="50" y2="50" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="38" x2="38" y2="30" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="38" x2="62" y2="30" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="50" x2="38" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="50" x2="62" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="38" y1="68" x2="30" y2="60" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="62" y1="68" x2="70" y2="60" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<ellipse cx="50" cy="52" rx="14" ry="7" fill="{c}" opacity="0.25"/>'
    ),
    'legs': (
        '#f0fdf4', '#16a34a',
        # lunge figure
        '<ellipse cx="50" cy="18" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="26" x2="50" y2="48" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="38" y2="28" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="62" y2="28" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="48" x2="36" y2="72" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="48" x2="64" y2="56" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="36" y1="72" x2="36" y2="80" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="64" y1="56" x2="72" y2="72" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
    'back': (
        '#fff7ed', '#ea580c',
        # bent-over row figure
        '<ellipse cx="38" cy="28" rx="8" ry="8" fill="{c}"/>'
        '<line x1="38" y1="36" x2="50" y2="55" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="55" x2="62" y2="55" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="44" y1="46" x2="34" y2="58" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="44" y1="46" x2="54" y2="40" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="55" x2="46" y2="75" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="55" x2="58" y2="73" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="34" y1="58" x2="30" y2="72" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>'
    ),
    'chest': (
        '#fef2f2', '#dc2626',
        # push-up figure
        '<ellipse cx="25" cy="45" rx="7" ry="7" fill="{c}"/>'
        '<line x1="25" y1="52" x2="60" y2="52" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="60" y1="52" x2="72" y2="62" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="38" y1="52" x2="32" y2="62" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="32" y1="62" x2="22" y2="62" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="72" y1="62" x2="78" y2="62" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="25" y1="42" x2="38" y2="35" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
    'shoulders': (
        '#fffbeb', '#d97706',
        # overhead press figure
        '<ellipse cx="50" cy="20" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="28" x2="50" y2="55" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="35" y2="28" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="65" y2="28" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="35" y1="28" x2="30" y2="18" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="65" y1="28" x2="70" y2="18" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="55" x2="42" y2="75" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="55" x2="58" y2="75" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
    'arms': (
        '#f0fdf4', '#059669',
        # bicep curl figure
        '<ellipse cx="50" cy="20" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="28" x2="50" y2="52" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="38" x2="36" y2="32" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="36" y1="32" x2="30" y2="48" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="30" y1="48" x2="26" y2="38" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="38" x2="64" y2="32" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="64" y1="32" x2="70" y2="48" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="70" y1="48" x2="74" y2="38" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="52" x2="42" y2="74" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="52" x2="58" y2="74" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
    'core': (
        '#fafaf9', '#78716c',
        # plank figure
        '<ellipse cx="22" cy="52" rx="7" ry="7" fill="{c}"/>'
        '<line x1="22" y1="59" x2="68" y2="59" stroke="{c}" stroke-width="3.5" stroke-linecap="round"/>'
        '<line x1="22" y1="55" x2="18" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="34" y1="59" x2="30" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="68" y1="59" x2="72" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="55" y1="59" x2="58" y2="68" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<ellipse cx="50" cy="57" rx="18" ry="5" fill="{c}" opacity="0.2"/>'
    ),
    'full_body': (
        '#f5f3ff', '#7c3aed',
        # standing figure arms wide
        '<ellipse cx="50" cy="18" rx="8" ry="8" fill="{c}"/>'
        '<line x1="50" y1="26" x2="50" y2="56" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="28" y2="50" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="36" x2="72" y2="50" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="56" x2="40" y2="78" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
        '<line x1="50" y1="56" x2="60" y2="78" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
    ),
}
_DEFAULT_SVG = _MUSCLE_SVG['full_body']


@register.filter
def exercise_illustration(muscle_group):
    """Return an inline SVG illustration for the given muscle group."""
    bg, color, shapes = _MUSCLE_SVG.get(muscle_group, _DEFAULT_SVG)
    svg = (
        f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;height:100%;">'
        f'<rect width="100" height="100" fill="{bg}"/>'
        + shapes.format(c=color) +
        f'</svg>'
    )
    return mark_safe(svg)


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
