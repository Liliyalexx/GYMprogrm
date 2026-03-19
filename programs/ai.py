import base64
import json
import mimetypes
import os

from django.conf import settings
import anthropic
import openai as _openai_mod

LANG_INSTRUCTION = {
    'en': 'Respond in English.',
    'ru': 'Отвечай на русском языке.',
    'es': 'Responde en español.',
    'fr': 'Réponds en français.',
    'de': 'Antworte auf Deutsch.',
    'it': 'Rispondi in italiano.',
    'pt': 'Responda em português.',
    'zh-hans': '用中文回答。',
    'ar': 'أجب باللغة العربية.',
    'ja': '日本語で答えてください。',
}


def _lang_suffix(language):
    """Return a language instruction string to append to prompts."""
    lang = (language or 'en').split('-')[0] if language else 'en'
    # Try exact match first, then prefix match
    instruction = LANG_INSTRUCTION.get(language or 'en') or LANG_INSTRUCTION.get(lang) or LANG_INSTRUCTION['en']
    return f'\n\nIMPORTANT: {instruction}'


def translate_program_section(program, section):
    """
    Translate one section of a program to English and save it.
    section: 'analysis' | 'nutrition'
    Returns True on success.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    if section == 'analysis' and program.description and not program.description_en:
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2000,
            messages=[{
                'role': 'user',
                'content': (
                    'Translate each bullet point of this gym training analysis from Russian to English. '
                    'Keep the medical/fitness terminology precise. '
                    'Return only the translated text, same structure, one bullet per line. No explanation.\n\n'
                    + program.description
                ),
            }],
        )
        program.description_en = msg.content[0].text.strip()
        program.save(update_fields=['description_en'])
        return True

    if section == 'nutrition' and program.nutrition_plan and not program.nutrition_plan_en:
        plan_str = json.dumps(program.nutrition_plan, ensure_ascii=False)
        msg = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=8000,
            messages=[{
                'role': 'user',
                'content': (
                    'Translate this nutrition plan JSON from Russian to English. '
                    'Keep ALL keys exactly the same. Only translate string values (meal names, food items, notes, recommendations). '
                    'Keep all numbers, times, and units unchanged. '
                    'Return ONLY valid JSON, no markdown, no explanation.\n\n'
                    + plan_str
                ),
            }],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        program.nutrition_plan_en = json.loads(raw)
        program.save(update_fields=['nutrition_plan_en'])
        return True

    return False


def backfill_english_names(program):
    """
    For an existing program: translate all empty name_en fields (program + days)
    and clean Russian text out of exercise reps. Uses Claude Haiku (fast, cheap).
    Returns (programs_fixed, days_fixed, reps_fixed) counts.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Collect items that need translation
    items_to_translate = []
    if not program.name_en and program.name:
        items_to_translate.append({'type': 'program', 'id': program.pk, 'text': program.name})

    days = list(program.days.all())
    for day in days:
        if not day.name_en and day.name:
            items_to_translate.append({'type': 'day', 'id': day.pk, 'text': day.name})

    # Also collect reps that contain Cyrillic
    import re as _re
    exercises_with_ru_reps = []
    for day in days:
        for pe in day.exercises.all():
            if pe.reps and _re.search(r'[а-яёА-ЯЁ]', pe.reps):
                exercises_with_ru_reps.append(pe)

    programs_fixed = 0
    days_fixed = 0
    reps_fixed = 0

    # Translate names in one batch call
    if items_to_translate:
        texts_json = json.dumps([i['text'] for i in items_to_translate], ensure_ascii=False)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            messages=[{
                'role': 'user',
                'content': (
                    f'Translate each gym workout name from Russian to English. '
                    f'Keep the same structure (Day N — Muscle Group). '
                    f'Return ONLY a JSON array of translated strings, same order, same count. '
                    f'No explanation, no markdown.\n\nInput: {texts_json}'
                ),
            }],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        try:
            translations = json.loads(raw)
        except Exception:
            translations = []

        if len(translations) == len(items_to_translate):
            for item, eng in zip(items_to_translate, translations):
                if item['type'] == 'program':
                    from .models import WorkoutProgram
                    WorkoutProgram.objects.filter(pk=item['id']).update(name_en=eng)
                    programs_fixed += 1
                else:
                    from .models import ProgramDay
                    ProgramDay.objects.filter(pk=item['id']).update(name_en=eng)
                    days_fixed += 1

    # Clean Russian text from reps (e.g. "10-12 на каждую ногу" → "10-12 each leg")
    RU_REPS_MAP = {
        r'на каждую ногу': 'each leg',
        r'на каждую сторону': 'each side',
        r'на каждую руку': 'each arm',
        r'на сторону': 'each side',
        r'на ногу': 'each leg',
        r'на руку': 'each arm',
        r'каждая сторона': 'each side',
        r'каждая нога': 'each leg',
        r'секунд': 'sec',
        r'сек': 'sec',
        r'минут': 'min',
        r'мин': 'min',
    }
    for pe in exercises_with_ru_reps:
        cleaned = pe.reps
        for ru_pat, en_repl in RU_REPS_MAP.items():
            cleaned = _re.sub(ru_pat, en_repl, cleaned, flags=_re.IGNORECASE)
        # Remove any remaining Cyrillic words
        cleaned = _re.sub(r'\s+[а-яёА-ЯЁ][а-яёА-ЯЁ\s]*', ' ', cleaned).strip()
        if cleaned != pe.reps:
            pe.reps = cleaned
            pe.save(update_fields=['reps'])
            reps_fixed += 1

    return programs_fixed, days_fixed, reps_fixed


def generate_exercise_illustration(exercise_name, muscle_group, description=''):
    """
    Generate TWO cartoon female exercise illustrations using DALL-E 3:
      image 1 — starting position
      image 2 — peak / mid-movement position
    Also returns posture tips generated by Claude Haiku.
    Returns dict: {image_url, image_url_2, posture_tips}
    Two images at $0.04 each = $0.08 per exercise. Cheaper and faster than a GIF.
    """
    client_oai = _openai_mod.OpenAI(api_key=settings.OPENAI_API_KEY)
    client_ant = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    base_style = (
        f"Flat-design cartoon illustration of a fit woman. "
        f"Style: clean vector art, soft pastel colours, white background, similar to 30 Day Fitness app. "
        f"Show full body, correct exercise form. "
        f"Highlight the {muscle_group} muscles with a warm accent colour. "
        f"No text, no labels. Friendly, motivational look."
    )

    prompt_start = (
        f"STARTING POSITION of '{exercise_name}'. "
        f"Show the athlete at the very beginning of the movement, body fully extended or at rest position. "
        + base_style
    )
    prompt_peak = (
        f"PEAK / MID-MOVEMENT POSITION of '{exercise_name}'. "
        f"Show the athlete at the top of the contraction or halfway through the movement, muscles visibly engaged. "
        + base_style
    )

    resp1 = client_oai.images.generate(model='dall-e-3', prompt=prompt_start, size='1024x1024', quality='standard', n=1)
    resp2 = client_oai.images.generate(model='dall-e-3', prompt=prompt_peak,  size='1024x1024', quality='standard', n=1)

    # Generate posture tips with Claude Haiku
    tips_msg = client_ant.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=300,
        messages=[{
            'role': 'user',
            'content': (
                f"Give 3 concise posture & technique tips for '{exercise_name}' "
                f"(targets: {muscle_group}). Each tip max 12 words. "
                f"Format: numbered list 1. 2. 3. No intro text."
            ),
        }],
    )
    posture_tips = tips_msg.content[0].text.strip()

    return {
        'image_url': resp1.data[0].url,
        'image_url_2': resp2.data[0].url,
        'posture_tips': posture_tips,
    }


def suggest_warmup_stretch_exercises():
    """
    Ask Claude to suggest 2–3 warm-up (dynamic activation) and 2–3 stretch (static cool-down)
    exercises for every muscle group. Returns a list of dicts:
      {name, description, muscle_group, exercise_type, difficulty}
    All descriptions written for teenage girls and adult women — gentle, PT-approved.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    muscle_groups = [
        'glutes', 'legs', 'back', 'chest', 'shoulders', 'arms', 'core', 'cardio', 'full_body'
    ]

    prompt = """You are a Stanford-trained physical therapist and personal trainer specializing in teenage girls, kids, and adult women. You work with posture correction, injury prevention, and safe strength training.

Create a JSON array of warm-up and stretch exercises for a fitness app. For EACH of these muscle groups: glutes, legs, back, chest, shoulders, arms, core, cardio, full_body — provide:
- 2 warm-up exercises (dynamic activation, done BEFORE training)
- 2 stretch exercises (static holds, done AFTER training / cool-down)

Rules:
- All exercises must be safe for teenage girls (13+) and adult women
- Warm-up = dynamic movement (leg swings, hip circles, arm circles, cat-cow, etc.)
- Stretch = static hold (pigeon pose, child's pose, doorway chest stretch, etc.)
- Descriptions: 1–2 sentences explaining HOW to do it and WHAT it helps
- Names: use standard English exercise names
- Difficulty: always "beginner"

Return ONLY a valid JSON array, no markdown, no explanation:
[
  {
    "name": "Hip Circles",
    "description": "Stand with feet shoulder-width apart and rotate your hips in large circles. Loosens hip flexors and activates the glutes before loading.",
    "muscle_group": "glutes",
    "exercise_type": "warmup",
    "difficulty": "beginner"
  },
  ...
]"""

    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=4000,
        messages=[{'role': 'user', 'content': prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    exercises = json.loads(text)
    return exercises


def _format_goals(text):
    """Split numbered/bulleted goals into one-per-line format for the AI prompt."""
    import re
    if not text:
        return text
    # Split on patterns like "1." "2." "•" at word boundaries
    parts = re.split(r'\s*(?=(?:\d+\.|•)\s)', text)
    lines = [p.strip() for p in parts if p.strip()]
    return '\n'.join(lines) if len(lines) > 1 else text


def _encode_file(path):
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(path, 'rb') as f:
        data = base64.standard_b64encode(f.read()).decode('utf-8')
    return data, mime_type


def _photo_block(student):
    """Return (content_block_list, attached_bool) for the student's sport photo."""
    blocks = []
    if not student.photo:
        return blocks, False

    # Try local path first
    try:
        path = student.photo.path
        if os.path.exists(path):
            data, mime_type = _encode_file(path)
            if mime_type.startswith('image/'):
                blocks.append({'type': 'image',
                               'source': {'type': 'base64', 'media_type': mime_type, 'data': data}})
                return blocks, True
    except Exception:
        pass

    # Fall back to remote URL (Cloudinary)
    try:
        import httpx
        url = student.photo.url
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '').split(';')[0].strip()
            if not content_type.startswith('image/'):
                content_type = 'image/jpeg'
            data = base64.standard_b64encode(resp.content).decode('utf-8')
            blocks.append({'type': 'image',
                           'source': {'type': 'base64', 'media_type': content_type, 'data': data}})
            return blocks, True
    except Exception:
        pass

    return blocks, False


def _analyze_photo(client, student, photo_blocks):
    """Use Claude Vision to analyse the client's sport photo for body composition and posture."""
    if not photo_blocks:
        return ''

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'не указан'
    goals = student.goals or 'не указаны'

    prompt = (
        f'Ты — персональный тренер. Внимательно посмотри на фото клиента в спортивной одежде.\n'
        f'Клиент: {gender}, возраст {age}, цели: {goals}\n\n'
        f'Дай краткое профессиональное описание (3–5 предложений) по следующим пунктам:\n'
        f'1. Видимые мышечные группы и их развитие (что хорошо развито, что требует внимания)\n'
        f'2. Осанка и положение тела (есть ли сутулость, перекосы, дисбаланс)\n'
        f'3. Тип телосложения и примерный процент жира\n'
        f'4. Рекомендации по приоритетным зонам с учётом целей клиента\n\n'
        f'Отвечай ТОЛЬКО фактами, без предисловий. Максимум 5 предложений.'
    )

    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=512,
        messages=[{'role': 'user', 'content': photo_blocks + [{'type': 'text', 'text': prompt}]}],
    )
    return msg.content[0].text.strip()


def _blood_test_block(student):
    """Return (content_blocks, attached_bool) for the blood test file.
    Handles both local storage and Cloudinary remote storage."""
    blocks = []
    if not student.blood_test_file:
        return blocks, False

    # Try local path first (development / local storage)
    try:
        path = student.blood_test_file.path
        if os.path.exists(path):
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

    # Fall back to remote URL (Cloudinary or any other remote storage)
    try:
        import httpx

        base_url = student.blood_test_file.url
        # Build candidate URLs to try: prefer raw/upload for non-image files
        urls_to_try = [base_url]
        if base_url and 'cloudinary.com' in base_url:
            if '/image/upload/' in base_url:
                urls_to_try.insert(0, base_url.replace('/image/upload/', '/raw/upload/'))
            elif '/raw/upload/' in base_url:
                urls_to_try.append(base_url.replace('/raw/upload/', '/image/upload/'))

        resp = None
        for url in urls_to_try:
            try:
                r = httpx.get(url, timeout=60, follow_redirects=True)
                if r.status_code == 200:
                    resp = r
                    break
            except Exception:
                continue

        if resp is None:
            return blocks, False

        content_type = resp.headers.get('content-type', '').split(';')[0].strip()
        if not content_type or content_type == 'application/octet-stream':
            ct, _ = mimetypes.guess_type(str(student.blood_test_file.name))
            content_type = ct or 'application/octet-stream'
        data = base64.standard_b64encode(resp.content).decode('utf-8')
        if content_type == 'application/pdf':
            blocks.append({'type': 'document',
                           'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data}})
            return blocks, True
        elif content_type.startswith('image/'):
            blocks.append({'type': 'image',
                           'source': {'type': 'base64', 'media_type': content_type, 'data': data}})
            return blocks, True
    except Exception:
        pass

    return blocks, False


def _close_truncated_json(raw):
    """Close any open string and unclosed braces/brackets in a truncated JSON string."""
    in_string = False
    escaped = False
    stack = []  # track opening delimiters in order
    for c in raw:
        if escaped:
            escaped = False
            continue
        if c == '\\' and in_string:
            escaped = True
            continue
        if c == '"':
            in_string = not in_string
        elif not in_string:
            if c in ('{', '['):
                stack.append(c)
            elif c == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif c == ']' and stack and stack[-1] == '[':
                stack.pop()
    if in_string:
        raw += '"'
    # Close in reverse order
    for opener in reversed(stack):
        raw += '}' if opener == '{' else ']'
    return raw


def _parse_json(raw, msg=None):
    """Parse JSON from AI response. Handles truncation and model quirks."""
    if msg is not None and getattr(msg, 'stop_reason', None) == 'max_tokens':
        raise ValueError(
            'AI response was cut off (too many blood markers or too large a document). '
            'Try uploading a shorter extract of the blood test.'
        )
    raw = raw.strip()
    if raw.startswith('```'):
        parts = raw.split('```')
        raw = parts[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        fixed = re.sub(r'\bNone\b', 'null', raw)
        fixed = re.sub(r'\bTrue\b', 'true', fixed)
        fixed = re.sub(r'\bFalse\b', 'false', fixed)
        # Close truncated structure then try standard parse
        closed = _close_truncated_json(fixed)
        try:
            return json.loads(closed)
        except json.JSONDecodeError:
            # Final fallback: json-repair returns a Python object directly
            from json_repair import repair_json
            return repair_json(closed, return_objects=True)


def correct_text(text, field):
    """Rewrite health issues or goals in professional language."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    if field == 'health_issues':
        instruction = (
            'Ты — спортивный врач. Перепиши следующие жалобы/противопоказания клиента '
            'используя точную медицинскую и клиническую терминологию. '
            'Сохрани все факты дословно, только замени бытовые описания на профессиональные термины. '
            'Каждую жалобу/противопоказание выводи с новой строки в формате "• жалоба". '
            'Верни ТОЛЬКО список, без заголовков, без пояснений и без вступлений.'
        )
    else:
        instruction = (
            'Ты — профессиональный персональный тренер. Перепиши следующие пожелания клиента '
            'используя профессиональный язык спортивной науки и фитнеса. '
            'Сохрани суть пожеланий, сформулируй их как конкретные тренировочные цели. '
            'Каждую цель выводи с новой строки в формате "• цель" (через маркер •). '
            'Верни ТОЛЬКО список целей, без заголовков, без пояснений и без вступлений.'
        )
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=512,
        messages=[{'role': 'user', 'content': instruction + '\n\n' + text}],
    )
    return msg.content[0].text.strip()


def _normalize_health_issues(client, raw_text):
    """Rewrite health issues in professional medical/clinical language."""
    if not raw_text or not raw_text.strip():
        return raw_text
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=512,
        messages=[{
            'role': 'user',
            'content': (
                'Перепиши следующие жалобы/противопоказания клиента используя '
                'корректную медицинскую и клиническую терминологию. '
                'Сохрани все факты, добавь медицинские термины там, где это уместно. '
                'Верни ТОЛЬКО переписанный текст, без пояснений.\n\n'
                + raw_text
            ),
        }],
    )
    return msg.content[0].text.strip()


def suggest_nutrition(student, findings_summary='', language='ru'):
    """Re-run only Call 2 (nutrition plan) for an existing program."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Не указан'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    health_issues = _normalize_health_issues(client, student.health_issues) or 'Не выявлено'

    profile = f"""Имя: {student.name}
Пол: {gender}
Возраст: {age if age else 'Не указан'}
Рост: {f'{student.height_cm} см' if student.height_cm else 'Не указан'}
Вес: {f'{student.weight_kg} кг' if student.weight_kg else 'Не указан'}
Цели:\n{_format_goals(student.goals) or 'Не указано'}
Проблемы со здоровьем / противопоказания: {health_issues}
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
        "Анализ крови прикреплён — учти данные при составлении плана питания."
        if blood_attached else
        "Анализ крови не загружен — рекомендации по профилю клиента."
    )

    prompt = f"""Ты — спортивный диетолог. Составь краткий план питания.

ПРОФИЛЬ:
{profile}
{hormone_note}
{blood_note}

ВЫВОДЫ: {findings_summary}

Верни ТОЛЬКО валидный JSON (без markdown):
{{
  "daily_calories": 2000,
  "macros": {{"protein_g": 150, "carbs_g": 200, "fat_g": 65}},
  "meals": [
    {{
      "meal": "Завтрак",
      "time": "7:00–8:00",
      "calories": 420,
      "foods": ["Овсянка 80г", "Яйца 2шт", "Банан 1шт"],
      "notes": ["Краткий совет макс 10 слов"]
    }}
  ],
  "fasting": {{
    "recommended": true,
    "type": "16:8",
    "eating_window": "12:00–20:00",
    "reasoning": ["Причина 1", "Причина 2"],
    "cautions": "Краткое предупреждение или пустая строка"
  }},
  "supplements": ["Витамин D 2000 МЕ", "Омега-3 1г"],
  "notes": [
    {{"title": "ГИДРАТАЦИЯ", "text": "Краткая рекомендация"}},
    {{"title": "ДЕФИЦИТ КАЛОРИЙ", "text": "Краткий расчёт"}}
  ]
}}

Правила (СТРОГО):
- Ровно 4 приёма пищи
- foods: 3–4 продукта с граммовкой
- notes каждого приёма: ровно 1 строка (массив из 1 элемента)
- fasting.reasoning: ровно 2 строки
- notes верхнего уровня: ровно 2 объекта
- Все строки — краткие (макс 15 слов)
{_lang_suffix(language)}"""

    content = blood_blocks + [{'type': 'text', 'text': prompt}]
    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content}],
    )
    return _parse_json(msg.content[0].text, msg)


def _build_exercise_menu(training_location):
    """Return a formatted string listing available exercises grouped by muscle group."""
    from programs.models import ExerciseLibrary
    if training_location == 'home':
        return """Место тренировки: ДОМА.
Используй ТОЛЬКО упражнения с собственным весом, гантелями или резиновыми лентами.
Примеры: Squat, Lunge, Glute Bridge, Hip Thrust (с гантелью), Push-up, Tricep Dip,
Dumbbell Row, Dumbbell Curl, Plank, Dead Bug, Mountain Climber, Jumping Jack,
Step-Up, Donkey Kick, Fire Hydrant, Romanian Deadlift (гантели), Lateral Raise (гантели).
Для поля "name" используй стандартные английские названия упражнений.
Также верни поле "muscle_group" для каждого упражнения (значения: glutes, legs, back, chest, shoulders, arms, core, cardio)."""

    # Gym — pull from actual library
    from collections import defaultdict
    groups = defaultdict(list)
    for ex in ExerciseLibrary.objects.all().order_by('muscle_group', 'name'):
        groups[ex.get_muscle_group_display()].append(ex.name)

    lines = ['Место тренировки: СПОРТЗАЛ.', 'Используй ТОЛЬКО упражнения из списка ниже (точные названия для поля "name"):']
    for group, names in sorted(groups.items()):
        lines.append(f'{group}: {", ".join(names)}')
    return '\n'.join(lines)


def suggest_program(student, training_days=3, training_location='gym', language='ru'):
    """
    Two separate Claude calls to avoid hitting the output token limit:
      Call 1 → key_findings + workout days (exercises)
      Call 2 → nutrition plan
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Не указан'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    health_issues = _normalize_health_issues(client, student.health_issues) or 'Не выявлено'

    profile = f"""Имя: {student.name}
Пол: {gender}
Возраст: {age if age else 'Не указан'}
Рост: {f'{student.height_cm} см' if student.height_cm else 'Не указан'}
Вес: {f'{student.weight_kg} кг' if student.weight_kg else 'Не указан'}
Дней тренировок в неделю: {training_days}
Цели:\n{_format_goals(student.goals) or 'Не указано'}
Проблемы со здоровьем / противопоказания: {health_issues}
Дополнительные заметки: {student.notes or 'Нет'}"""

    blood_blocks, blood_attached = _blood_test_block(student)
    photo_blocks, photo_attached = _photo_block(student)

    # Analyse photo before building the main prompt
    photo_analysis = ''
    if photo_attached:
        try:
            photo_analysis = _analyze_photo(client, student, photo_blocks)
        except Exception:
            photo_analysis = ''

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

    photo_note = (
        f'Анализ фото клиента:\n{photo_analysis}'
        if photo_analysis else
        'Фото клиента не загружено.'
    )

    exercise_menu = _build_exercise_menu(training_location)

    home_muscle_group_field = (
        ',\n          "muscle_group": "glutes"'
        if training_location == 'home' else ''
    )

    # ── CALL 1: workout program + key findings ──────────────────────────────
    prompt1 = f"""Ты — профессиональный персональный тренер.
На основе профиля клиента{' и анализа крови' if blood_attached else ''}{' и анализа фото' if photo_analysis else ''} создай программу тренировок.

ПРОФИЛЬ:
{profile}
{hormone_note}
{blood_note}

{photo_note}

ДОСТУПНЫЕ УПРАЖНЕНИЯ:
{exercise_menu}

═══════════════════════════════════════════
ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА — НАРУШЕНИЕ НЕДОПУСТИМО:

1. АНАЛИЗ ЦЕЛЕЙ — ПЕРВЫЙ ШАГ:
   Внимательно прочитай цели клиента. Определи ПРИОРИТЕТНЫЕ мышечные группы.
   Пример: "похудеть ноги + увеличить ягодицы" → из {training_days} дней минимум 2 дня на ягодицы/ноги.
   Пример: "укрепить спину + рельеф рук" → приоритет спина и руки.

2. СТРОГОЕ СООТВЕТСТВИЕ ДНЯ И УПРАЖНЕНИЙ:
   Каждый день имеет ОДНУ тему (мышечную группу или комбинацию).
   Упражнения 1–5 должны тренировать ТОЛЬКО указанные в названии дня мышцы.
   Упражнение 6 (финишёр) — ВСЕГДА упражнение на пресс/кор (планка, скручивания, подъём ног и т.д.).
   ЗАПРЕЩЕНО: добавлять упражнения на плечи в день ног, руки в день спины и т.д. (кроме финишёра на пресс).

3. ВОЗРАСТ И ЗДОРОВЬЕ:
   Возраст {age} лет — адаптируй нагрузку и выбор упражнений.
   Противопоказания: {health_issues} — исключи упражнения, создающие нагрузку на указанные области.

4. ТОЛЬКО УПРАЖНЕНИЯ ИЗ СПИСКА (для зала):
   Поле "name" должно совпадать с названиями из списка выше ТОЧНО.

5. НЕТ ДУБЛИКАТОВ:
   Одно упражнение может встречаться ТОЛЬКО ОДИН РАЗ во всей программе.
   НЕЛЬЗЯ повторять одно и то же упражнение в разных днях.

6. КОЛИЧЕСТВО УПРАЖНЕНИЙ:
   В каждом дне РОВНО 6 упражнений. Не 5, не 4 — ровно 6.
   Упражнения 1–5: основные мышечные группы дня.
   Упражнение 6: финишёр на пресс/кор (Plank, Crunch, Leg Raise, Russian Twist и т.д.).
═══════════════════════════════════════════

Отвечай ТОЛЬКО валидным JSON (без markdown, без пояснений):
{{
  "program_name": "Название программы на русском",
  "program_name_en": "Program name in English",
  "key_findings": [
    "Одно предложение — главная цель клиента и фокус программы",
    "Одно предложение — почему выбрано такое распределение дней под цели клиента",
    "Одно предложение — возрастные/физические адаптации в программе",
    "Одно предложение — ключевая находка из анализа крови (если есть, иначе про здоровье клиента)",
    "Одно предложение — наблюдение по фото: тип телосложения, осанка или приоритетные зоны (если фото загружено)",
    "Одно предложение — рекомендация по восстановлению и прогрессии"
  ],
  "days": [
    {{
      "day_number": 1,
      "day_name": "День 1 — Ягодицы и ноги",
      "day_name_en": "Day 1 — Glutes & Legs",
      "warmup": [
        {{"name": "Hip Circles", "duration": "1 min", "description": "Slow circular hip rotations to activate the hip joint and glutes"}},
        {{"name": "Glute Bridge Hold", "duration": "45 sec", "description": "Static hold at top to activate glutes before loading"}},
        {{"name": "Bodyweight Squat", "duration": "1 min", "description": "Slow controlled squats to warm up quads, glutes and knees"}}
      ],
      "exercises": [
        {{
          "name": "Barbell Hip Thrust",
          "name_ru": "Тяга бедра со штангой",
          "sets": 3,
          "reps": "10-12",
          "reason_ru": "Почему это упражнение важно для ДАННОГО клиента"{home_muscle_group_field}
        }}
      ],
      "cooldown": [
        {{"name": "Pigeon Pose", "duration": "1 min each side", "description": "Deep stretch for glutes and hip flexors worked today"}},
        {{"name": "Standing Quad Stretch", "duration": "45 sec each leg", "description": "Lengthen the quadriceps after squatting movements"}},
        {{"name": "Seated Hamstring Stretch", "duration": "1 min", "description": "Elongate hamstrings after leg press and deadlift patterns"}}
      ]
    }}
  ]
}}

Правила:
- Ровно {training_days} дней в "days"
- РОВНО 6 упражнений в каждом дне (5 основных + 1 финишёр на пресс/кор)
- "warmup": РОВНО 3 упражнения — динамические активационные движения для мышц ДАННОГО дня, ~5 минут суммарно
- "cooldown": РОВНО 3 растяжки — статические стрейчи для мышц ДАННОГО дня, ~5 минут суммарно
- Warm-up и cooldown: поля "name" (название на английском), "duration" (время), "description" (1 предложение на английском)
- "name" — английское название из списка доступных упражнений
- "reps" — ТОЛЬКО цифры/диапазон на английском: "10-12", "8", "30 sec", "12 each leg". НИКАКОГО русского текста в reps!
- "name_ru" — русское название
- "program_name_en" — английское название программы (ALWAYS in English)
- "day_name_en" — английское название дня (ALWAYS in English, e.g. "Day 1 — Glutes & Legs")
- key_findings — каждый элемент это ОДНО предложение
- Если анализ крови загружен — включи реальные числовые значения в findings
{_lang_suffix(language)}"""

    content1 = blood_blocks + [{'type': 'text', 'text': prompt1}]
    msg1 = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content1}],
    )
    result = _parse_json(msg1.content[0].text, msg1)

    # ── CALL 2: nutrition plan ───────────────────────────────────────────────
    findings_summary = ' '.join(result.get('key_findings', []))
    prompt2 = f"""Ты — спортивный диетолог. Составь краткий план питания.

ПРОФИЛЬ:
{profile}
{hormone_note}
{blood_note}

ВЫВОДЫ: {findings_summary}

Верни ТОЛЬКО валидный JSON (без markdown):
{{
  "daily_calories": 2000,
  "macros": {{"protein_g": 150, "carbs_g": 200, "fat_g": 65}},
  "meals": [
    {{
      "meal": "Завтрак",
      "time": "7:00–8:00",
      "calories": 420,
      "foods": ["Овсянка 80г", "Яйца 2шт", "Банан 1шт"],
      "notes": ["Краткий совет макс 10 слов"]
    }}
  ],
  "fasting": {{
    "recommended": true,
    "type": "16:8",
    "eating_window": "12:00–20:00",
    "reasoning": ["Причина 1", "Причина 2"],
    "cautions": "Краткое предупреждение или пустая строка"
  }},
  "supplements": ["Витамин D 2000 МЕ", "Омега-3 1г"],
  "notes": [
    {{"title": "ГИДРАТАЦИЯ", "text": "Краткая рекомендация"}},
    {{"title": "ДЕФИЦИТ КАЛОРИЙ", "text": "Краткий расчёт"}}
  ]
}}

Правила (СТРОГО):
- Ровно 4 приёма пищи
- foods: 3–4 продукта с граммовкой
- notes каждого приёма: ровно 1 строка (массив из 1 элемента)
- fasting.reasoning: ровно 2 строки
- notes верхнего уровня: ровно 2 объекта
- Все строки — краткие (макс 15 слов)
{_lang_suffix(language)}"""

    content2 = blood_blocks + [{'type': 'text', 'text': prompt2}]
    msg2 = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content2}],
    )
    nutrition = _parse_json(msg2.content[0].text, msg2)
    result['nutrition'] = nutrition

    return result


def generate_student_recommendations(student, language='ru'):
    """Generate personalized food, exercise, and lifestyle recommendations."""
    client = anthropic.Anthropic()

    age = student.age or 'unknown'
    gender = student.get_gender_display() if student.gender else 'not specified'
    goals = student.goals or 'not specified'
    health_issues = student.health_issues or 'none'
    height = str(student.height_cm) if student.height_cm else 'unknown'
    weight = str(student.weight_kg) if student.weight_kg else 'unknown'

    blood_info = ''
    if student.blood_analysis and not student.blood_analysis.get('_processing') and not student.blood_analysis.get('_error'):
        deficiencies = student.blood_analysis.get('deficiencies', [])
        markers = [m for m in student.blood_analysis.get('markers', [])
                   if m.get('status') in ('low', 'high', 'critical_low', 'critical_high')]
        if deficiencies:
            blood_info += 'Deficiencies: ' + ', '.join(
                [f"{d['nutrient']} ({d.get('severity', '')})" for d in deficiencies])
        if markers:
            blood_info += '\nAbnormal markers: ' + ', '.join(
                [f"{m['name']} ({m['status']})" for m in markers[:6]])

    photo_info = (student.photo_analysis or '').strip()
    if photo_info.startswith('_'):
        photo_info = ''

    lang_note = _lang_suffix(language)

    prompt = (
        f'You are an expert personal trainer and sports nutritionist. '
        f'Analyze this client and provide detailed personalized recommendations.\n\n'
        f'CLIENT DATA:\n'
        f'- Age: {age}, Gender: {gender}\n'
        f'- Height: {height} cm, Weight: {weight} kg\n'
        f'- Goals: {goals}\n'
        f'- Health issues: {health_issues}\n'
        + (f'- Blood test: {blood_info}\n' if blood_info else '')
        + (f'- Body assessment: {photo_info}\n' if photo_info else '')
        + '\nReturn ONLY valid JSON in this exact structure:\n'
        '{\n'
        '  "nutrition": {\n'
        '    "summary": "2-3 sentence overview tailored to goals and blood work",\n'
        '    "recommendations": ["tip 1", "tip 2", "tip 3", "tip 4", "tip 5"],\n'
        '    "focus_foods": ["🥩 food 1", "🥦 food 2", "🐟 food 3", "🥚 food 4", "🫐 food 5"],\n'
        '    "limit_foods": ["🍞 food 1", "🍭 food 2", "🧂 food 3"]\n'
        '  },\n'
        '  "exercise": {\n'
        '    "summary": "2-3 sentence exercise strategy",\n'
        '    "priority_areas": ["💪 area 1", "🦵 area 2", "🏋️ area 3"],\n'
        '    "recommendations": ["tip 1", "tip 2", "tip 3", "tip 4"]\n'
        '  },\n'
        '  "lifestyle": {\n'
        '    "fasting": "specific fasting protocol recommendation",\n'
        '    "hydration": "daily water intake recommendation",\n'
        '    "sleep": "sleep recommendation",\n'
        '    "supplements": ["💊 supplement + reason 1", "supplement 2", "supplement 3"]\n'
        '  }\n'
        '}'
        + lang_note
    )

    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}],
    )

    text = msg.content[0].text.strip()
    if '```' in text:
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def analyze_blood_test(student, language='ru'):
    """
    Deep standalone analysis of a blood test file.
    Returns structured JSON with every marker, deficiencies, and exercise/nutrition recommendations.
    Returns None if no blood test file is attached or the file cannot be read.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=240.0)

    blood_blocks, blood_attached = _blood_test_block(student)
    if not blood_attached:
        return None

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Не указан'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    profile = f"""Имя: {student.name}
Пол: {gender}
Возраст: {age if age else 'Не указан'}
Рост: {f'{student.height_cm} см' if student.height_cm else 'Не указан'}
Вес: {f'{student.weight_kg} кг' if student.weight_kg else 'Не указан'}
Цели: {student.goals or 'Не указано'}
Проблемы со здоровьем / противопоказания: {student.health_issues or 'Не указано'}"""

    hormone_note = ''
    if is_woman_40_plus:
        hormone_note = """
ВАЖНО — Женщина 40+: особое внимание уделить гормональному статусу.
Проверить: эстроген, прогестерон, ФСГ, ЛГ, тестостерон, ДГЭА, ТТГ, Т3, Т4.
Костные маркеры: кальций, витамин D, щелочная фосфатаза.
"""

    prompt = f"""Ты — спортивный врач. Проанализируй анализ крови клиента.

ПРОФИЛЬ: {profile}
{hormone_note}

Верни ТОЛЬКО валидный JSON (без markdown):
{{
  "summary": "2 предложения — ключевые выводы",
  "markers": [
    {{
      "name": "Гемоглобин",
      "value": "115 г/л",
      "reference": "120–160 г/л",
      "status": "low",
      "interpretation": "Лёгкая анемия — снижает выносливость"
    }}
  ],
  "deficiencies": [
    {{
      "nutrient": "Железо",
      "severity": "moderate",
      "impact_on_training": "Утомляемость, медленное восстановление",
      "food_sources": ["Говядина 150г", "Шпинат 100г"],
      "supplement": "Феррум Лек 100 мг/день, 3 месяца"
    }}
  ],
  "exercise_recommendations": ["рекомендация 1", "рекомендация 2", "рекомендация 3"],
  "nutrition_recommendations": ["рекомендация 1", "рекомендация 2", "рекомендация 3"],
  "urgent_attention": [],
  "positive_findings": ["вывод 1", "вывод 2"]
}}

СТРОГИЕ ПРАВИЛА:
- markers: ТОЛЬКО аномальные показатели (status = low/high/critical_low/critical_high)
  Нормальные показатели НЕ включай в массив markers
- status: "normal"|"low"|"high"|"critical_low"|"critical_high"
- Учитывай нормы для пола и возраст {age} лет
- deficiencies: максимум 5, только реальные дефициты
- food_sources: максимум 3 продукта
- exercise_recommendations: ровно 3 строки, макс 12 слов каждая
- nutrition_recommendations: ровно 3 строки, макс 12 слов каждая
- urgent_attention: пустой массив если нет критических значений
- positive_findings: ровно 2 строки — группы показателей в норме
{_lang_suffix(language)}"""

    content = blood_blocks + [{'type': 'text', 'text': prompt}]
    msg = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=8096,
        messages=[{'role': 'user', 'content': content}],
    )
    return _parse_json(msg.content[0].text, msg)


def suggest_exercises_from_photo(student, exercise_names: list) -> list:
    """Given a student's photo analysis and the full exercise library names,
    return a list of suggested exercises (matching library names) with sets/reps/reason.

    Returns a list of dicts:
      [{"name": "...", "sets": 3, "reps": "10-12", "reason": "..."}, ...]
    """
    client = anthropic.Anthropic()

    analysis = student.photo_analysis or ''
    goals = student.goals or 'not specified'
    health = student.health_issues or 'none'
    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'unknown'

    library_list = '\n'.join(f'- {n}' for n in sorted(exercise_names))

    prompt = f"""You are an expert personal trainer. Based on the following body composition analysis and client profile, select 4–6 exercises from the exercise library below that would be most beneficial.

CLIENT PROFILE:
- Gender: {gender}, Age: {age}
- Goals: {goals}
- Health issues / contraindications: {health}

BODY COMPOSITION ANALYSIS:
{analysis}

EXERCISE LIBRARY (you MUST only use exercises from this list, using the exact name):
{library_list}

Return a JSON array only — no extra text. Each item:
{{"name": "<exact name from library>", "sets": <integer 3-5>, "reps": "<e.g. 10-12 or 30 sec>", "reason": "<1 sentence why this exercise for this client>"}}

Rules:
- Pick exercises that address the weak points or goals identified in the analysis
- Use EXACT exercise names from the library list
- No duplicates
- Return only the JSON array"""

    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    result = _parse_json(msg.content[0].text, msg)
    if isinstance(result, list):
        return result
    return []
