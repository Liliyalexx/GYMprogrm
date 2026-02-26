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


def suggest_program(student, training_days=3):
    """
    Call Claude API to suggest a workout program + nutrition plan.
    Reads uploaded blood test (PDF or image) if present.
    Applies special hormone-awareness logic for women aged 40+.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Unknown'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    profile = f"""
Student name: {student.name}
Gender: {gender}
Age: {age if age else 'Unknown'}
Training days per week: {training_days}
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
            pass

    # Hormone instructions for women 40+
    hormone_instructions = ''
    if is_woman_40_plus:
        hormone_instructions = """
SPECIAL INSTRUCTIONS — Woman aged 40+:
- Check hormone levels in blood test: estrogen, progesterone, FSH, LH, testosterone, DHEA
- Check thyroid: TSH, free T3, free T4
- Check bone markers: calcium, vitamin D (25-OH), ALP
- Identify signs of perimenopause or menopause
- Include weight-bearing exercises for bone density
- Adjust recovery time accordingly (48h+ between same muscle groups)
- In nutrition: consider phytoestrogens, calcium-rich foods, magnesium for hormonal support
- Fasting: assess carefully — prolonged fasting may worsen hormonal imbalance for some women 40+
"""

    # Blood test analysis instructions
    if blood_test_attached:
        blood_test_instructions = """
Blood test attached above. Analyse it for:
- Anaemia (haemoglobin, ferritin, iron) — affects training intensity
- Inflammation (CRP, ESR) — may require lower intensity and anti-inflammatory diet
- Blood sugar / insulin resistance (glucose, HbA1c) — affects fasting recommendation and carb intake
- Liver / kidney markers — contraindications for heavy loading or high protein
- Hormonal imbalances (see above if applicable)
- Vitamin/mineral deficiencies (vitamin D, B12, iron, magnesium) — impact recovery and nutrition
- Lipid panel (cholesterol, triglycerides) — affects dietary fat recommendations
Mention key findings in the description and reflect them in the nutrition plan.
"""
    else:
        blood_test_instructions = "No blood test uploaded — base all recommendations on profile only."

    prompt = f"""You are an expert personal trainer and sports nutritionist.
Based on the student profile{' and blood test results' if blood_test_attached else ''} below, create:
1. A personalised workout program for exactly {training_days} training days per week
2. A detailed daily nutrition plan with meal-by-meal food list
3. A fasting recommendation based on the client's health data

STUDENT PROFILE:
{profile}
{hormone_instructions}
{blood_test_instructions}

Respond ONLY with valid JSON in this exact format (no extra text, no markdown fences):
{{
  "program_name": "...",
  "description": "2-3 sentence personalised summary. Mention blood test findings if available.",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Day 1 — Push / Upper Body",
      "exercises": [
        {{
          "name": "Exercise Name",
          "sets": 3,
          "reps": "10-12",
          "reason": "Why this exercise for this specific client"
        }}
      ]
    }}
  ],
  "nutrition": {{
    "daily_calories": 2000,
    "macros": {{
      "protein_g": 150,
      "carbs_g": 200,
      "fat_g": 65
    }},
    "meals": [
      {{
        "meal": "Breakfast",
        "time": "7:00–8:00",
        "foods": ["Oatmeal with berries and chia seeds", "2 boiled eggs", "Green tea"],
        "notes": "High protein start, slow carbs for sustained energy"
      }},
      {{
        "meal": "Lunch",
        "time": "12:00–13:00",
        "foods": ["Grilled chicken breast 150g", "Brown rice 100g", "Steamed broccoli", "Olive oil dressing"],
        "notes": "Main meal, balanced macros"
      }},
      {{
        "meal": "Pre-workout snack",
        "time": "15:30–16:00",
        "foods": ["Banana", "Rice cake with almond butter"],
        "notes": "Fast carbs 30-60 min before training"
      }},
      {{
        "meal": "Post-workout",
        "time": "18:30–19:00",
        "foods": ["Protein shake with milk", "Rice cakes"],
        "notes": "Protein within 30 min after training"
      }},
      {{
        "meal": "Dinner",
        "time": "20:00–20:30",
        "foods": ["Salmon fillet 150g", "Sweet potato 150g", "Mixed salad with olive oil"],
        "notes": "Omega-3 rich, light on digestion"
      }}
    ],
    "fasting": {{
      "recommended": true,
      "type": "16:8 intermittent fasting",
      "eating_window": "12:00–20:00",
      "reasoning": "Based on blood glucose and goals, intermittent fasting supports fat loss and insulin sensitivity. Adjust if training is in the morning.",
      "cautions": "Skip fasting on heavy training days if energy is low."
    }},
    "supplements": ["Vitamin D 2000 IU", "Omega-3 1g", "Magnesium glycinate 300mg"],
    "notes": "Drink 2–2.5L water daily. Adjust portions on rest days (reduce carbs by ~20%)."
  }}
}}

Rules:
- Exactly {training_days} workout days in "days" array
- 4–6 exercises per day, avoid exercises that aggravate health issues
- Use standard gym exercise names (barbell, dumbbell, cable, machine)
- Nutrition must be specific to this client's goals and blood test findings
- Fasting recommendation must consider gender, age, blood sugar, hormones
- All food items should be specific (e.g. "Grilled salmon 150g" not just "protein")
"""

    content.append({'type': 'text', 'text': prompt})

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=4000,
        messages=[{'role': 'user', 'content': content}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
