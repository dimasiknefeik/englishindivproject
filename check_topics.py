"""
Проверка файла data/topics.json перед запуском программы.

Запусти этот файл в Thonny (F5) после того, как добавил или изменил темы.
Он найдёт типичные ошибки и объяснит, где именно они находятся.
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, "data", "topics.json")

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_str_list(topic_name, field, value):
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        err(f"[{topic_name}] поле «{field}» должно быть списком строк: [\"...\", \"...\"]")


def check_topic(i, t):
    name = t.get("title") or t.get("id") or f"тема №{i}"

    if not isinstance(t, dict):
        err(f"Тема №{i}: должна быть блоком в фигурных скобках {{ }}")
        return

    for field in ("id", "title", "rule"):
        if not isinstance(t.get(field), str) or not t[field].strip():
            err(f"[{name}] нет обязательного поля «{field}» (или оно пустое)")

    if not isinstance(t.get("category"), str) or not t["category"].strip():
        warn(f"[{name}] нет «category» — тема попадёт в группу «Другое»")

    for field in ("examples", "markers", "notes"):
        if field in t:
            check_str_list(name, field, t[field])

    if "formula" in t and not isinstance(t["formula"], str):
        err(f"[{name}] поле «formula» должно быть текстом в кавычках")

    exercises = t.get("exercises", [])
    if not isinstance(exercises, list):
        err(f"[{name}] поле «exercises» должно быть списком [ ... ]")
        return
    if not exercises:
        warn(f"[{name}] нет упражнений — тренажёр для этой темы будет пустым")

    for j, ex in enumerate(exercises, start=1):
        where = f"[{name}] упражнение №{j}"
        if not isinstance(ex, dict):
            err(f"{where}: должно быть блоком в фигурных скобках {{ }}")
            continue
        if not isinstance(ex.get("question"), str) or not ex["question"].strip():
            err(f"{where}: нет поля «question»")
        answers = ex.get("answers")
        if isinstance(answers, str):
            err(f"{where}: «answers» должно быть СПИСКОМ, например [\"goes\"], а не просто \"goes\"")
        elif not isinstance(answers, list) or not answers \
                or not all(isinstance(a, str) and a.strip() for a in answers):
            err(f"{where}: «answers» должно быть непустым списком строк")
        if "explanation" not in ex:
            warn(f"{where}: нет «explanation» — при ошибке не будет подсказки")


def main():
    if not os.path.exists(PATH):
        print(f"Не найден файл {PATH}")
        sys.exit(1)

    with open(PATH, "r", encoding="utf-8") as f:
        text = f.read()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        lines = text.splitlines()
        print("ОШИБКА В СИНТАКСИСЕ JSON")
        print(f"Строка {e.lineno}, позиция {e.colno}: {e.msg}")
        if 1 <= e.lineno <= len(lines):
            print("  >>", lines[e.lineno - 1])
        print("\nЧастые причины: забытая запятая между блоками, лишняя запятая")
        print("перед ] или }, незакрытая кавычка или скобка. Ищи ошибку в этой")
        print("строке или в строке чуть выше.")
        sys.exit(1)

    topics = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(topics, list):
        print("В файле должен быть ключ \"topics\" со списком тем.")
        sys.exit(1)

    seen = {}
    for i, t in enumerate(topics, start=1):
        check_topic(i, t)
        if isinstance(t, dict) and isinstance(t.get("id"), str):
            if t["id"] in seen:
                err(f"[{t.get('title', t['id'])}] id «{t['id']}» уже используется темой "
                    f"«{seen[t['id']]}» — id должны быть уникальными")
            else:
                seen[t["id"]] = t.get("title", t["id"])

    total_ex = sum(len(t.get("exercises", [])) for t in topics if isinstance(t, dict)
                   and isinstance(t.get("exercises"), list))
    print(f"Тем: {len(topics)}, упражнений: {total_ex}\n")

    for w in warnings:
        print("Предупреждение:", w)
    for e in errors:
        print("ОШИБКА:", e)

    if errors:
        print(f"\nНайдено ошибок: {len(errors)}. Исправь их до запуска main.py.")
        sys.exit(1)
    print("\nОшибок нет, файл в порядке." if not warnings
          else "\nОшибок нет, но есть предупреждения выше.")


if __name__ == "__main__":
    main()
