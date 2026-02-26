import base64
import json
import mimetypes
import os

from django.conf import settings
import anthropic


def _encode_file(path):
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    return data, mime_type


def _blood_test_block(student):
    """Return (content_blocks, attached_bool) for the blood test file."""
    blocks = []
    if not student.blood_test_file:
        return blocks, False
    try:
        path = student.blood_test_file.path
        if not os.path.exists(path):
            return blocks, False
        data, mime_type = _encode_file(path)
        if mime_type == 'application/pdf':
            blocks.append({'type': 'document',
                           'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data}})
            return blocks, True
        elif mime_type.startswith('image/'):
            blocks.append({'type': 'image',
                           'source': {'type': 'base64', 'media_type': mime_type, 'data': data}})
            return blocks, True
    except Exception:
        pass
    return blocks, False


def _parse_json(raw):
    raw = raw.strip()
    if raw.startswith('```'):
        parts = raw.split('```')
        raw = parts[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def suggest_program(student, training_days=3):
    """
    Two separate Claude calls to avoid hitting the output token limit:
      Call 1 → key_findings + workout days (exercises)
      Call 2 → nutrition plan
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Не указан'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    profile = f"""Имя: {student.name}
Пол: {gender}
Возраст: {age if age else 'Не указан'}
Дней тренировок в неделю: {training_days}
Цели: {student.goals or 'Не указано'}
Проблемы со здоровьем / противопоказания: {student.health_issues or 'Не выявлено'}
Дополнительные заметки: {student.notes or 'Нет'}"""

    blood_blocks, blood_attached = _blood_test_block(student)

    hormone_note = ''
    if is_woman_40_plus:
        hormone_note = """
ОСОБЫЕ ИНСТРУКЦИИ — Женщина 40+:
- Проверить: эстроген, прогестерон, ФСГ, ЛГ, тестостерон, ДГЭА, ТТГ, Т3, Т4
- Костные маркеры: кальций, витамин D, ЩФ
- Включить силовые упражнения для укрепления костей
- Восстановление минимум 48ч между тренировками одних мышц
"""

    blood_note = (
        """Анализ крови прикреплён. Проанализировать:
- Анемия (Hb, ферритин, железо), воспаление (СРБ, СОЭ)
- Сахар/инсулинорезистентность (глюкоза, HbA1c)
- Печень/почки, гормоны, дефициты (D, B12, магний)
- Липиды (холестерин, триглицериды)"""
        if blood_attached else
        "Анализ крови не загружен — рекомендации по профилю клиента."
    )

    # ── CALL 1: workout program + key findings ──────────────────────────────
    prompt1 = f"""Ты — профессиональный персональный тренер.
На основе профиля клиента{' и анализа крови' if blood_attached else ''} создай программу тренировок.

ПРОФИЛЬ:
{profile}
{hormone_note}
{blood_note}

Отвечай ТОЛЬКО валидным JSON (без markdown, без пояснений):
{{
  "program_name": "Название программы на русском",
  "key_findings": [
    "Одно предложение — цель клиента и общий подход программы",
    "Одно предложение — ключевая находка из анализа крови №1 (конкретные значения)",
    "Одно предложение — ключевая находка из анализа крови №2",
    "Одно предложение — ключевая находка из анализа крови №3",
    "Одно предложение — гормональный статус и как он повлиял на программу",
    "Одно предложение — что поддерживает полноценные тренировки"
  ],
  "days": [
    {{
      "day_number": 1,
      "day_name": "День 1 — Ягодицы и ноги",
      "exercises": [
        {{
          "name": "Barbell Hip Thrust",
          "name_ru": "Тяга бедра со штангой",
          "sets": 3,
          "reps": "10-12",
          "reason_ru": "Почему это упражнение для данного клиента"
        }}
      ]
    }}
  ]
}}

Правила:
- Ровно {training_days} дней в "days"
- 4–6 упражнений в день
- "name" — английское название (для базы упражнений)
- "name_ru" — русское название
- key_findings — каждый элемент это ОДНО предложение, не абзац
- Если анализ крови загружен — включи реальные числовые значения в findings
"""

    content1 = blood_blocks + [{'type': 'text', 'text': prompt1}]
    msg1 = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content1}],
    )
    result = _parse_json(msg1.content[0].text)

    # ── CALL 2: nutrition plan ───────────────────────────────────────────────
    findings_summary = ' '.join(result.get('key_findings', []))
    prompt2 = f"""Ты — профессиональный спортивный диетолог.
На основе профиля клиента и выводов о здоровье составь детальный план питания.

ПРОФИЛЬ:
{profile}
{hormone_note}
{blood_note}

ВЫВОДЫ О ЗДОРОВЬЕ (из анализа крови):
{findings_summary}

Отвечай ТОЛЬКО валидным JSON (без markdown, без пояснений):
{{
  "daily_calories": 2000,
  "macros": {{
    "protein_g": 150,
    "carbs_g": 200,
    "fat_g": 65
  }},
  "meals": [
    {{
      "meal": "Завтрак",
      "time": "7:00–8:00",
      "foods": ["Конкретный продукт с граммовкой", "Ещё продукт 100г"],
      "notes": "Короткая заметка"
    }}
  ],
  "fasting": {{
    "recommended": true,
    "type": "Интервальное голодание 16:8",
    "eating_window": "12:00–20:00",
    "reasoning": "Обоснование на основе данных клиента",
    "cautions": "Предупреждения"
  }},
  "supplements": ["Витамин D 2000 МЕ", "Омега-3 1г"],
  "notes": "Общие рекомендации по гидратации и питанию в дни отдыха"
}}

Правила:
- 4–5 приёмов пищи с конкретными продуктами и граммовкой
- Учитывать все находки из анализа крови
- Если женщина 40+ — учитывать гормональный статус в питании
- Рекомендации по голоданию — на основе сахара крови, гормонов, целей
"""

    content2 = blood_blocks + [{'type': 'text', 'text': prompt2}]
    msg2 = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content2}],
    )
    nutrition = _parse_json(msg2.content[0].text)
    result['nutrition'] = nutrition

    return result
