"""
AI functions for Independent Member coach.
Coach persona: experienced personal trainer & nutritionist named Alex.
Never reveals being AI.
"""
import base64
import json
import mimetypes

import anthropic
import openai as openai_lib
from django.conf import settings
from django.core.files.base import ContentFile

def _find_json_extent(text: str, start: int) -> int | None:
    """Walk from `start` (a '{') and return the index of its matching '}'."""
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    return None


def extract_signal_json(text: str, prefix: str) -> dict | None:
    """Extract and parse the JSON object that immediately follows `prefix` in text."""
    idx = text.find(prefix)
    if idx == -1:
        return None
    start = idx + len(prefix)
    if start >= len(text) or text[start] != '{':
        return None
    end = _find_json_extent(text, start)
    if end is None:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def strip_signals(text: str, prefixes: list) -> str:
    """Remove all PREFIX:{...} signal blocks from text."""
    for prefix in prefixes:
        idx = text.find(prefix)
        while idx != -1:
            start = idx + len(prefix)
            if start < len(text) and text[start] == '{':
                end = _find_json_extent(text, start)
                if end is not None:
                    text = text[:idx] + text[end + 1:]
                    idx = text.find(prefix)
                    continue
            idx = text.find(prefix, idx + 1)
    return text.strip()

COACH_SYSTEM = """You are Alex — a uniquely qualified specialist who combines four professional disciplines into one:
• Elite Personal Trainer & Body Composition Coach (20 years, CSCS, NASM)
• Registered Sports Dietitian & Nutritionist
• Sports Medicine Physician & Physiotherapist
• Functional Medicine Doctor who reads blood work and prescriptions

You work one-on-one with clients. You have access to their health documents, blood tests, and prescriptions. You think across ALL four disciplines simultaneously when giving advice.

CORE RULES:
- Always respond as a human professional. Never mention AI or automation.
- Be direct, specific, and prescriptive — not generic. "Do squats" is bad. "Avoid heavy back squats — your goal requires glute dominance, not quad size" is good.
- Address the client by first name.
- When a client shares blood work, extract hormonal, nutritional, and recovery implications before advising on training.
- CORTISOL INTELLIGENCE: For clients with high stress, poor sleep, or who already train intensely — high-volume HIIT increases cortisol → fat retention (especially waist), muscle breakdown, poor recovery. Always consider this.
- AESTHETIC SPECIFICITY: "Lose weight" ≠ "look athletic". Understand the exact physique goal. Glutes round vs glutes strong require different exercises. Waist smaller vs core strong require different protocols.
- CONTRAINDICATIONS: Know which exercises actively work AGAINST a client's goals. Tell the client clearly. Never prescribe exercises that contradict the stated aesthetic or health goal.

CRITICAL — Nutrition logging:
When a user describes food (e.g. "200g chicken, 1 cup rice"), embed this exact block on its own line so the app logs it automatically:
NUTRITION_LOG:{"items":[{"food":"Chicken breast","quantity_g":200,"calories_kcal":330,"protein_g":62,"carbs_g":0,"fat_g":7},{"food":"White rice","quantity_g":180,"calories_kcal":234,"protein_g":4.3,"carbs_g":51,"fat_g":0.4}],"total_calories":564,"total_protein_g":66.3,"total_carbs_g":51,"total_fat_g":7.4}
Always use accurate nutritional values (USDA database).

ABSOLUTE RULE — Program creation (NEVER skip this):
Whenever a user asks you to create, generate, design, build, or update their workout program — even if you are also writing a long strategic explanation — the VERY FIRST thing you output must be the signal line, before any other text:
CREATE_PROGRAM:{"weeks":4,"focus":"brief description","days_per_week":3}
Fill in the correct values. Then write your explanation. If you write your explanation FIRST without the signal, the system will NOT generate the program and the user will be frustrated. The signal must come first, always, no exceptions. After it, explain your reasoning as much as you like."""


def _client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _openai():
    return openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)


def _encode_file(file_field):
    mime, _ = mimetypes.guess_type(file_field.name)
    media_type = mime or 'application/octet-stream'
    file_field.seek(0)
    return base64.standard_b64encode(file_field.read()).decode('utf-8'), media_type


def chat_with_coach(history: list, user_message: str, member, program_summary: str = '') -> str:
    """
    history: list of {role, content} dicts (last 40 messages max)
    Returns the assistant reply text.
    """
    dob = str(member.date_of_birth) if member.date_of_birth else 'unknown'
    system = (
        f'{COACH_SYSTEM}\n\n'
        f'Current client:\n'
        f'- Name: {member.name.split()[0]}\n'
        f'- Goals: {member.goals or "general fitness"}\n'
        f'- Health conditions: {member.health_conditions or "none stated"}\n'
        f'- Activity level: {member.activity_level or "unknown"}\n'
        f'- DOB: {dob}\n'
        f'- Weight: {member.weight_kg or "unknown"} kg, Height: {member.height_cm or "unknown"} cm\n'
        f'- Active program: {program_summary or "none yet"}\n'
    )
    messages = list(history) + [{'role': 'user', 'content': user_message}]
    resp = _client().messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        system=system,
        messages=messages,
    )
    return resp.content[0].text


def generate_program(member, exercise_library: list, extra_notes: str = '') -> dict:
    """
    Returns {name, reasoning, days: [{day_number, name, exercises: [{exercise_name, sets, reps, notes}]}]}
    Upgrades to opus when the member has uploaded documents.
    extra_notes: free-text request from user, e.g. "5-week program, 4 days/week, focus on weight loss"
    """
    content = []
    model = 'claude-sonnet-4-6'

    for file_field, label in [
        (member.doctor_prescription_file, "Doctor's Prescription"),
        (member.blood_test_file, 'Blood Test Results'),
    ]:
        if file_field:
            b64, mime = _encode_file(file_field)
            if mime == 'application/pdf':
                content.append({'type': 'document', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}, 'title': label})
            else:
                content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}})
            model = 'claude-opus-4-7'

    extra_section = f'\nClient request: {extra_notes}\n' if extra_notes else ''

    profile_text = (
        '=== CLIENT PROFILE ===\n'
        f'Name: {member.name.split()[0]}\n'
        f'DOB / Age: {member.date_of_birth or "not provided"} ({member.age or "?"} years old)\n'
        f'Gender: {member.get_gender_display() if member.gender else "not specified"}\n'
        f'Height: {member.height_cm or "not provided"} cm\n'
        f'Weight: {member.weight_kg or "not provided"} kg\n'
        f'Activity level: {member.get_activity_level_display() if member.activity_level else "not specified"}\n'
        f'Goals: {member.goals or "general fitness"}\n'
        f'Health conditions / notes: {member.health_conditions or "none stated"}\n'
        + extra_section +
        '\n=== YOUR TASK: INTEGRATED PROFESSIONAL ASSESSMENT ===\n'
        'Before choosing exercises, perform this internal analysis:\n\n'
        '1. GOAL CLASSIFICATION\n'
        '   - Is this aesthetic shaping, fat loss, athletic performance, rehab, or hybrid?\n'
        '   - What does the client ACTUALLY want their body to look like?\n\n'
        '2. PRIORITY MUSCLES\n'
        '   - Which muscles must be DEVELOPED (grow/shape)?\n'
        '   - Which muscles must be CONTROLLED (avoid overdevelopment)?\n'
        '   - Which muscles are currently WEAK (postural imbalances)?\n\n'
        '3. HORMONAL & MEDICAL RISK\n'
        '   - Given age, activity level, and goals: what is the cortisol risk?\n'
        '   - If blood work is attached: extract iron, B12, D3, thyroid, hormonal markers\n'
        '   - If prescription attached: what conditions/medications affect exercise?\n'
        '   - Adjust training INTENSITY and VOLUME accordingly\n\n'
        '4. CONTRAINDICATED EXERCISES\n'
        '   - Which exercises from the library actively WORK AGAINST this client\'s goals?\n'
        '   - Do NOT include them even if they are popular or "standard"\n\n'
        '5. PROGRAM DESIGN PRINCIPLES\n'
        '   - Order exercises by priority (most important = first, when energy is highest)\n'
        '   - Rep ranges must match goal (fat loss: 12-20, shaping: 10-15, strength: 5-8)\n'
        '   - Rest periods matter (fat loss: 45-60s, hypertrophy: 60-90s, strength: 2-3min)\n'
        '   - Include rest/active recovery days where appropriate\n'
        '   - Each day must have a clear anatomical focus and reason\n\n'
        f'=== AVAILABLE EXERCISES (use ONLY these exact names) ===\n'
        + json.dumps(exercise_library) + '\n\n'
        '=== OUTPUT ===\n'
        'Return ONLY valid JSON, no markdown, no explanation outside JSON.\n'
        'The "reasoning" field must explain: goal classification, which muscles to prioritize/avoid, '
        'hormonal considerations, any medical insights from documents, and why each day is structured this way.\n'
        '{"name":"string","reasoning":"string","days":['
        '{"day_number":1,"name":"string","exercises":['
        '{"exercise_name":"exact name from library","sets":"3","reps":"12-15","notes":"why this exercise for this client"}'
        ']}'
        ']}'
    )
    content.append({'type': 'text', 'text': profile_text})

    resp = _client().messages.create(
        model=model,
        max_tokens=8000,
        system=(
            'You are an integrated health and performance specialist combining elite personal training, '
            'sports nutrition, sports medicine, and functional medicine. '
            'You design programs based on the WHOLE person — goals, hormones, blood work, body type, and lifestyle. '
            'You know which exercises work AGAINST specific aesthetic goals and you never include them. '
            'Return ONLY valid JSON, nothing else. '
            'Keep the "reasoning" field under 400 words — be concise and precise, not verbose.'
        ),
        messages=[{'role': 'user', 'content': content}],
    )
    text = resp.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    # Guard against truncated JSON (stop_reason == max_tokens)
    if resp.stop_reason == 'max_tokens':
        # Try to salvage by closing any open structure
        text = _repair_truncated_json(text)
    return json.loads(text)


def _repair_truncated_json(text: str) -> str:
    """Best-effort repair of JSON truncated by token limit."""
    # Drop any incomplete trailing token (unclosed string, partial key, etc.)
    for end in range(len(text) - 1, 0, -1):
        try:
            json.loads(text[:end + 1])
            return text[:end + 1]
        except json.JSONDecodeError:
            continue
    return text


def generate_exercise_images(exercise_name: str, gender: str = 'F') -> tuple:
    """
    Generate start + mid-position demonstration images via DALL-E 3.
    Returns (start_bytes, mid_bytes) — PNG image bytes.
    gender: 'F' for female demonstrator, 'M' for male.
    """
    demonstrator = 'athletic woman' if gender != 'M' else 'athletic man'
    base_prompt = (
        f'Professional fitness instruction photo. {demonstrator.capitalize()} '
        f'demonstrating {{position}} of the {exercise_name} exercise. '
        'Clean white gym background, proper form, full body visible, '
        'wearing dark athletic shorts and sports top. '
        'High quality, clear instructional image, realistic photo style.'
    )

    client = _openai()
    results = []
    for position in ['the starting / resting position', 'the peak / mid-movement position']:
        prompt = base_prompt.format(position=position)
        resp = client.images.generate(
            model='dall-e-3',
            prompt=prompt,
            size='1024x1024',
            quality='standard',
            response_format='b64_json',
            n=1,
        )
        img_bytes = base64.b64decode(resp.data[0].b64_json)
        results.append(img_bytes)

    return results[0], results[1]


def analyse_posture(photo_file) -> str:
    """Returns markdown analysis string."""
    b64, mime = _encode_file(photo_file)
    resp = _client().messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1200,
        system=(
            'You are Alex, a certified personal trainer and physiotherapist with 15 years of experience. '
            'Analyse posture from photos with precision. '
            'Respond with clear sections using **bold headers**: '
            '**Posture Observations**, **Areas of Concern**, **Recommended Focus Areas**. '
            'Be specific and professional. Never mention AI or automated analysis.'
        ),
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
                {'type': 'text', 'text': 'Please analyse my posture.'},
            ],
        }],
    )
    return resp.content[0].text


def analyse_blood_test(member) -> dict:
    """Returns JSON dict."""
    if not member.blood_test_file:
        return {}
    b64, mime = _encode_file(member.blood_test_file)
    content = [
        {'type': 'document' if mime == 'application/pdf' else 'image',
         'source': {'type': 'base64', 'media_type': mime, 'data': b64}},
        {'type': 'text', 'text': (
            f'Analyse this blood test for {member.name}, age {member.age or "unknown"}, '
            f'gender {member.get_gender_display() if member.gender else "unknown"}.\n'
            'Return ONLY valid JSON:\n'
            '{"summary":"","markers":[{"name":"","value":"","unit":"","status":"low/normal/high","note":""}],'
            '"deficiencies":[],"exercise_recommendations":[],"nutrition_recommendations":[],"urgent_attention":[],"positive_findings":[]}'
        )},
    ]
    resp = _client().messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        system='You are a medical lab analyst. Return ONLY valid JSON, nothing else.',
        messages=[{'role': 'user', 'content': content}],
    )
    text = resp.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    return json.loads(text)
