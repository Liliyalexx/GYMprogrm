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
from json_repair import repair_json

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


def generate_program(member, exercise_library: list, extra_notes: str = '', posture_analysis: str = '') -> dict:
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
            try:
                b64, mime = _encode_file(file_field)
            except (FileNotFoundError, OSError):
                continue  # file was lost on server redeploy — skip silently
            if mime == 'application/pdf':
                content.append({'type': 'document', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}, 'title': label})
            else:
                content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime, 'data': b64}})
            model = 'claude-opus-4-7'

    posture_section = (
        f'\n=== POSTURE ANALYSIS (from photo assessment) ===\n{posture_analysis}\n'
        if posture_analysis else ''
    )
    extra_section = f'\n=== CLIENT REQUEST ===\n{extra_notes}\n' if extra_notes else ''

    profile_text = (
        '=== CLIENT PROFILE ===\n'
        f'Name: {member.name.split()[0]}\n'
        f'Age: {member.age or "unknown"} years old\n'
        f'Gender: {member.get_gender_display() if member.gender else "not specified"}\n'
        f'Height: {member.height_cm or "not provided"} cm\n'
        f'Weight: {member.weight_kg or "not provided"} kg\n'
        f'Activity level: {member.get_activity_level_display() if member.activity_level else "not specified"}\n'
        f'Goals: {member.goals or "general fitness"}\n'
        f'Health conditions / medical notes: {member.health_conditions or "none stated"}\n'
        + posture_section
        + extra_section +
        '\n=== YOUR ROLE ===\n'
        'You are simultaneously:\n'
        '• Family doctor — you read the full health picture: age, medications, blood markers, risk factors\n'
        '• Physiotherapist — you assess posture faults, movement compensation, injury risk, pain avoidance\n'
        '• Registered dietitian — you understand how nutrition status (iron, B12, thyroid, hormones) affects energy and recovery\n'
        '• Personal trainer — you select exercises, volume, intensity, and progression appropriate to THIS specific person\n\n'
        'NEVER design a generic program. Every decision must be justified by this client\'s specific data.\n\n'
        '=== MANDATORY CLINICAL ASSESSMENT (do this before touching the exercise list) ===\n\n'
        'STEP 1 — AGE-APPROPRIATE VOLUME\n'
        '  Under 30: standard volume OK\n'
        '  30–44: reduce volume 15–20% vs young adult baseline; prioritise recovery\n'
        '  45–54: reduce volume 25–30%; favour low-impact; hormonal sensitivity high\n'
        '  55+: 40% volume reduction; balance, functional movement, joint-friendly only\n'
        '  ➜ Apply this to the CLIENT\'S age right now. Do not skip.\n\n'
        'STEP 2 — ACTIVITY LEVEL → EXERCISE COUNT PER SESSION\n'
        '  Sedentary: max 3–4 exercises/day, 2 days/week\n'
        '  Lightly active: max 4–5 exercises/day, 2–3 days/week\n'
        '  Moderately active: max 5–6 exercises/day, 3–4 days/week\n'
        '  Very active: max 6–7 exercises/day, 4–5 days/week\n'
        '  ➜ Strictly obey these caps. A beginner or moderate person must NOT get an athlete\'s program.\n\n'
        'STEP 3 — GOAL → REP RANGES & REST\n'
        '  Fat loss / tone: 15–20 reps, 30–45s rest, compound + metabolic\n'
        '  Shaping / body recomposition: 12–15 reps, 60s rest, compound + isolation mix\n'
        '  Strength: 5–8 reps, 2–3 min rest, heavy compound\n'
        '  Rehab / pain management: 15–20 reps, 60–90s rest, pain-free ROM only, low load\n\n'
        'STEP 4 — PHYSIOTHERAPY CONTRAINDICATIONS FROM POSTURE\n'
        '  Anterior pelvic tilt → avoid hip flexor overload; add glute activation\n'
        '  Forward head / upper cross syndrome → avoid overhead pressing; add chin tucks, rows\n'
        '  Shoulder protraction → avoid push-dominant movements; add scapular retraction, rowing\n'
        '  Knee valgus → avoid deep loaded squats; add hip abduction, glute med exercises\n'
        '  Lower back pain / lordosis → no spinal compression; add core stability, bird-dog, dead bug\n'
        '  ➜ If posture analysis is provided above, extract findings and apply contraindications NOW.\n\n'
        'STEP 5 — MEDICAL & HORMONAL FACTORS\n'
        '  Women 35+: cortisol risk elevated — limit HIIT frequency, include 1–2 low-intensity days\n'
        '  Blood test provided → extract: iron/ferritin (low = reduce intensity), thyroid TSH (high = fatigue risk), '
        'vitamin D (low = bone stress risk), haemoglobin, B12\n'
        '  Prescription provided → identify contraindications: beta-blockers (HR cap), '
        'corticosteroids (bone density risk), NSAIDs (avoid high-impact)\n\n'
        'STEP 6 — SESSION LOADING BALANCE (critical — do not skip)\n'
        '  Never put more than 2 exercises targeting the same PRIMARY muscle in one session.\n'
        '  Example WRONG: Hip thrust + RDL + Sumo deadlift + Kickback in one day = posterior chain overload → fatigue, bad form, no glute activation.\n'
        '  Example RIGHT: Hip thrust + RDL + Kickback (3 exercises, posterior chain, well distributed).\n'
        '  Apply this rule across ALL muscle groups. If a day already has 2 glute exercises, the 3rd exercise must target something else.\n\n'
        'STEP 7 — AESTHETIC PROPORTIONS INTELLIGENCE\n'
        '  Smaller waist appearance = WIDER shoulders, not just smaller waist.\n'
        '  ➜ For any client wanting "smaller waist" or "sporty look": include lateral raises — this is NON-NEGOTIABLE visually.\n'
        '  Lower back aesthetics ("fitted lower back", "defined back"): back extensions are essential, not optional.\n'
        '  Quad dominance tendency (common in women): Bulgarian split squat is PARTIALLY QUAD DOMINANT even with forward lean.\n'
        '     ➜ Replace with: step-back lunge, hip thrust variation, or curtsy lunge instead.\n'
        '  Core goal = flat stomach + defined lines: dead bug + plank alone are NOT enough.\n'
        '     ➜ Add cable crunch or weighted crunch for visible ab development.\n'
        '  "Sporty arms": if client wants defined arms, add lateral raises (shoulder width) + 1–2 arm isolation exercises.\n\n'
        'STEP 8 — CONTRAINDICATED EXERCISES FOR THIS CLIENT\n'
        '  Based on all the above, list which exercises you are EXCLUDING and WHY.\n'
        '  Do not include any excluded exercises in the output.\n\n'
        f'=== AVAILABLE EXERCISES — use ONLY these exact names ===\n'
        + json.dumps(exercise_library) + '\n\n'
        '=== OUTPUT FORMAT ===\n'
        'Return ONLY valid JSON. No markdown. No text outside the JSON.\n'
        'The "reasoning" field: max 350 words. State age/activity calibration applied, posture findings used, '
        'medical factors considered, exercises excluded and why, and the logic for each training day.\n'
        '{"name":"string","reasoning":"string","days":['
        '{"day_number":1,"name":"string","exercises":['
        '{"exercise_name":"exact name from library","sets":"3","reps":"15-20","notes":"specific reason for THIS client"}'
        ']}'
        ']}'
    )
    content.append({'type': 'text', 'text': profile_text})

    resp = _client().messages.create(
        model=model,
        max_tokens=8000,
        system=(
            'You are simultaneously a family doctor, licensed physiotherapist, registered dietitian, and certified personal trainer. '
            'You think across ALL four disciplines at once. '
            'You never design generic programs — every choice is dictated by this specific client\'s '
            'age, health, posture, blood markers, medications, activity level, and exact aesthetic goal.\n'
            'HARD RULES you must never break:\n'
            '1. Never put more than 2 exercises targeting the same primary muscle group in one session (prevents overload and form breakdown).\n'
            '2. For women wanting a smaller waist: wider shoulders = smaller waist appearance → lateral raises are mandatory.\n'
            '3. Bulgarian split squat is partially quad-dominant even with forward lean — '
            'if client has quad dominance, replace with step-back lunge or hip thrust variation.\n'
            '4. "Fitted lower back" goal requires back extensions — indirect work (RDL, bird dog) alone is not enough.\n'
            '5. Core goal of flat stomach + visual definition requires cable crunch or weighted crunch — stability work alone is not sufficient.\n'
            '6. A 42-year-old moderately active woman gets a completely different program from a 25-year-old athlete.\n'
            '7. Strictly obey the volume caps and rep ranges from the assessment protocol.\n'
            'Return ONLY valid JSON, nothing else.'
        ),
        messages=[{'role': 'user', 'content': content}],
    )
    text = resp.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    # Guard against truncated JSON (stop_reason == max_tokens)
    if resp.stop_reason == 'max_tokens':
        text = _repair_truncated_json(text)
    return _parse_program_json(text)


def _parse_program_json(text: str) -> dict:
    """Parse program JSON — falls back to json_repair on any parse error."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict) and 'days' in repaired:
            return repaired
        # Last resort: try to extract JSON object from surrounding text
        start = text.find('{')
        if start != -1:
            end = _find_json_extent(text, start)
            if end is not None:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    repaired2 = repair_json(text[start:end + 1], return_objects=True)
                    if isinstance(repaired2, dict):
                        return repaired2
        raise


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
    try:
        b64, mime = _encode_file(member.blood_test_file)
    except (FileNotFoundError, OSError):
        return {}
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
