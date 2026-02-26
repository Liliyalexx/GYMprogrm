import base64
import json
import mimetypes
import os

from django.conf import settings
import anthropic


def _encode_file(path):
    """Return (base64_data, mime_type) for a file on disk."""
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    return data, mime_type


def suggest_program(student):
    """
    Call Claude API to suggest a workout program for the given student.
    Reads the uploaded blood test (PDF or image) if present.
    Applies special hormone-awareness logic for women aged 40+.
    Returns a list of dicts: [{day_name, exercises: [{name, sets, reps, reason}]}]
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Unknown'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    profile = f"""
Student name: {student.name}
Gender: {gender}
Age: {age if age else 'Unknown'}
Goals: {student.goals or 'Not specified'}
Health issues / contraindications: {student.health_issues or 'None reported'}
Additional notes: {student.notes or 'None'}
""".strip()

    # Build the message content blocks
    content = []

    # Attach blood test file if uploaded
    blood_test_attached = False
    if student.blood_test_file:
        try:
            file_path = student.blood_test_file.path
            if os.path.exists(file_path):
                data, mime_type = _encode_file(file_path)
                if mime_type == 'application/pdf':
                    content.append({
                        'type': 'document',
                        'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data},
                    })
                    blood_test_attached = True
                elif mime_type.startswith('image/'):
                    content.append({
                        'type': 'image',
                        'source': {'type': 'base64', 'media_type': mime_type, 'data': data},
                    })
                    blood_test_attached = True
        except Exception:
            pass  # If file unreadable, continue without it

    # Build hormone section
    hormone_instructions = ''
    if is_woman_40_plus:
        hormone_instructions = """
SPECIAL INSTRUCTIONS — Woman aged 40+:
- Check blood test for hormone levels: estrogen, progesterone, FSH, LH, testosterone, DHEA
- Check thyroid function: TSH, free T3, free T4
- Check bone health markers: calcium, vitamin D (25-OH), ALP
- Look for signs of perimenopause or menopause and adjust program accordingly
- Include weight-bearing exercises to support bone density
- Prioritize pelvic floor-friendly movements if needed
- Allow adequate recovery between sessions (at least 48h for same muscle groups)
- Note any hormonal imbalances found in the blood test in the program description
"""

    # Build blood test instructions
    blood_test_instructions = ''
    if blood_test_attached:
        blood_test_instructions = """
Blood test is attached above. Analyse it for:
- Anaemia (haemoglobin, ferritin, iron) — affects endurance capacity
- Inflammation markers (CRP, ESR) — may require lower intensity
- Blood sugar / insulin resistance (glucose, HbA1c) — affects nutrition and exercise type
- Liver / kidney markers — contraindications for heavy loading
- Hormonal imbalances (see above if applicable)
- Nutritional deficiencies (vitamin D, B12, magnesium) — impact recovery
Mention key findings in the program description.
"""
    else:
        blood_test_instructions = "No blood test uploaded — base recommendations on profile only."

    prompt = f"""You are an expert personal trainer and sports medicine specialist.
Based on the student profile{' and blood test results' if blood_test_attached else ''} below, create a personalised weekly workout program (3–4 days).

STUDENT PROFILE:
{profile}
{hormone_instructions}
{blood_test_instructions}

Respond ONLY with valid JSON in this exact format (no extra text, no markdown):
{{
  "program_name": "...",
  "description": "Personalised 2-3 sentence description. If blood test was provided, mention key findings and how they shaped the program.",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Day 1 — Push / Upper Body",
      "exercises": [
        {{
          "name": "Exercise Name (standard gym name)",
          "sets": 3,
          "reps": "10-12",
          "reason": "Why this exercise specifically for this client"
        }}
      ]
    }}
  ]
}}

Rules:
- Avoid exercises that aggravate stated health issues
- Use standard gym exercise names (barbell, dumbbell, cable, machine)
- 4–6 exercises per day
- Adjust intensity and volume based on blood test findings if available
- Focus strongly on the client's stated goals
"""

    content.append({'type': 'text', 'text': prompt})

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=3000,
        messages=[{'role': 'user', 'content': content}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if model wraps response
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
