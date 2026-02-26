import json
from django.conf import settings
import anthropic


def suggest_program(student):
    """
    Call Claude API to suggest a workout program for the given student.
    Returns a list of dicts: [{day_name, exercises: [{name, sets, reps, reason}]}]
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    profile = f"""
Student name: {student.name}
Age: {student.age or 'Unknown'}
Goals: {student.goals or 'Not specified'}
Health issues / contraindications: {student.health_issues or 'None reported'}
Additional notes: {student.notes or 'None'}
"""

    prompt = f"""You are an expert personal trainer. Based on the student profile below,
suggest a weekly workout program (3-4 days). For each day, list 4-6 exercises.

Student profile:
{profile}

Respond ONLY with valid JSON in this exact format (no extra text):
{{
  "program_name": "...",
  "description": "...",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Day 1 — ...",
      "exercises": [
        {{
          "name": "Exercise Name (must match common gym exercises)",
          "sets": 3,
          "reps": "10-12",
          "reason": "Why this exercise for this client"
        }}
      ]
    }}
  ]
}}

Important rules:
- If client has health issues, avoid exercises that could aggravate them
- Use exercise names that match standard gym equipment (barbells, dumbbells, cables, machines)
- Keep difficulty appropriate to client level
- Focus on the client's goals
"""

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}],
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)
