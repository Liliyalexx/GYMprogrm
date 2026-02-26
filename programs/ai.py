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


def suggest_program(student, training_days=3):
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    age = student.age or 0
    gender = student.get_gender_display() if student.gender else 'Не указан'
    is_woman_40_plus = student.gender == 'F' and age >= 40

    profile = f"""
Имя: {student.name}
Пол: {gender}
Возраст: {age if age else 'Не указан'}
Дней тренировок в неделю: {training_days}
Цели: {student.goals or 'Не указано'}
Проблемы со здоровьем / противопоказания: {student.health_issues or 'Не выявлено'}
Дополнительные заметки: {student.notes or 'Нет'}
""".strip()

    content = []

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

    hormone_instructions = ''
    if is_woman_40_plus:
        hormone_instructions = """
ОСОБЫЕ ИНСТРУКЦИИ — Женщина 40+:
- Проверить в анализе крови: эстроген, прогестерон, ФСГ, ЛГ, тестостерон, ДГЭА
- Щитовидная железа: ТТГ, свободный Т3, свободный Т4
- Костные маркеры: кальций, витамин D (25-OH), ЩФ
- Определить признаки перименопаузы или менопаузы
- Включить силовые упражнения для укрепления костей
- Восстановление: минимум 48ч между тренировками одних и тех же мышц
- В питании: фитоэстрогены, кальций, магний для гормональной поддержки
- Интервальное голодание: оценить осторожно — может усугубить гормональный дисбаланс
"""

    if blood_test_attached:
        blood_test_instructions = """
Анализ крови прикреплён выше. Необходимо проанализировать:
- Анемия: гемоглобин, ферритин, железо — влияет на интенсивность тренировок
- Воспаление: СРБ, СОЭ — при высоких значениях снизить интенсивность
- Сахар крови / инсулинорезистентность: глюкоза, HbA1c — влияет на рекомендации по голоданию и углеводам
- Печень / почки — противопоказания при высоких нагрузках и высоком белке
- Гормональный дисбаланс (см. выше при необходимости)
- Дефициты: витамин D, B12, железо, магний — влияют на восстановление и питание
- Липидный профиль: холестерин, триглицериды — влияет на жировые рекомендации
Ключевые находки отразить в блоке key_findings и в плане питания.
"""
    else:
        blood_test_instructions = "Анализ крови не загружен — рекомендации основаны только на профиле клиента."

    prompt = f"""Ты — профессиональный персональный тренер и спортивный диетолог.
На основе профиля клиента{' и результатов анализа крови' if blood_test_attached else ''} создай:
1. Персональную программу тренировок на {training_days} дней в неделю
2. Детальный план питания с конкретным списком продуктов на каждый приём пищи
3. Рекомендации по интервальному голоданию на основе данных клиента

ПРОФИЛЬ КЛИЕНТА:
{profile}
{hormone_instructions}
{blood_test_instructions}

Отвечай ТОЛЬКО валидным JSON в точно таком формате (без лишнего текста, без markdown):
{{
  "program_name": "Название программы на русском",
  "key_findings": [
    "Короткая находка или вывод 1 (одно предложение)",
    "Короткая находка или вывод 2",
    "Короткая находка или вывод 3",
    "Цели и как программа на них направлена"
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
          "reason_ru": "Почему именно это упражнение для данного клиента (на русском)"
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
        "meal": "Завтрак",
        "time": "7:00–8:00",
        "foods": ["Овсяная каша с ягодами и семенами чиа 200г", "2 варёных яйца", "Зелёный чай"],
        "notes": "Высокобелковый старт, медленные углеводы для длительной энергии"
      }},
      {{
        "meal": "Обед",
        "time": "12:00–13:00",
        "foods": ["Куриная грудка гриль 150г", "Бурый рис 100г", "Тушёная брокколи", "Заправка из оливкового масла"],
        "notes": "Основной приём пищи, сбалансированные макронутриенты"
      }},
      {{
        "meal": "Перекус перед тренировкой",
        "time": "15:30–16:00",
        "foods": ["Банан", "Рисовый хлебец с миндальным маслом"],
        "notes": "Быстрые углеводы за 30-60 мин до тренировки"
      }},
      {{
        "meal": "После тренировки",
        "time": "18:30–19:00",
        "foods": ["Протеиновый коктейль на молоке 250мл", "Рисовые хлебцы"],
        "notes": "Белок в течение 30 мин после тренировки"
      }},
      {{
        "meal": "Ужин",
        "time": "20:00–20:30",
        "foods": ["Филе лосося 150г", "Батат 150г", "Салат с оливковым маслом"],
        "notes": "Богато омега-3, лёгкое для пищеварения"
      }}
    ],
    "fasting": {{
      "recommended": true,
      "type": "Интервальное голодание 16:8",
      "eating_window": "12:00–20:00",
      "reasoning": "Обоснование на основе анализа крови и целей клиента",
      "cautions": "Предупреждения или противопоказания"
    }},
    "supplements": ["Витамин D 2000 МЕ", "Омега-3 1г", "Магний глицинат 300мг"],
    "notes": "Пить 2–2.5л воды в день. В дни отдыха сократить углеводы на ~20%."
  }}
}}

Правила:
- Ровно {training_days} тренировочных дней в массиве "days"
- 4–6 упражнений в день, избегать упражнений при проблемах со здоровьем
- В поле "name" — стандартное английское название упражнения (для сопоставления с базой)
- В поле "name_ru" — название упражнения на русском языке
- В поле "reason_ru" — обоснование выбора упражнения на русском
- Все остальные тексты — на русском языке
- Продукты питания — конкретные с граммовкой (например "Куриная грудка гриль 150г", не просто "белок")
- Рекомендации по голоданию должны учитывать пол, возраст, сахар крови, гормоны
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
