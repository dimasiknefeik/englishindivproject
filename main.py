"""
Тренажёр по грамматике английского языка
==========================================

Индивидуальный проект. Программа читает темы и правила из файла
data/topics.json и показывает их в трёх режимах:
  - "Теория"    — правило, формула, примеры, слова-маркеры;
  - "Тренажёр"  — упражнения на пропуски с проверкой ответа
                  и объяснением ошибки;
  - "Тест"      — 10-15 случайных вопросов по всем темам и итоговая оценка.

Темы в списке слева сгруппированы по полю "category" из topics.json.
Прогресс тренажёра сохраняется в data/progress.json,
результаты тестов — в data/test_results.json.

Как добавлять новые темы и вопросы — см. README.md рядом с этим файлом.
"""

import json
import os
import random
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk


# ---------------------------------------------------------------------------
# НАСТРОЙКИ (их можно менять)
# ---------------------------------------------------------------------------

# Сколько вопросов можно выбрать в тесте и сколько стоит по умолчанию
TEST_MIN_QUESTIONS = 10
TEST_MAX_QUESTIONS = 15
TEST_DEFAULT_QUESTIONS = 10

# Шкала оценок: (минимальный процент правильных ответов, оценка).
# Проверяется сверху вниз. Если процент ниже всех порогов — ставится GRADE_FAIL.
GRADE_SCALE = [(85, 5), (65, 4), (45, 3)]
GRADE_FAIL = 2

# В какую группу попадают темы, у которых не указана "category"
DEFAULT_CATEGORY = "Другое"


# ---------------------------------------------------------------------------
# Пути к файлам данных.
# resource_path() работает и при запуске из Thonny/VS Code, и после сборки
# в один .exe файл через PyInstaller (--onefile распаковывает данные во
# временную папку sys._MEIPASS).
# ---------------------------------------------------------------------------

def resource_path(*parts):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def app_dir():
    """Папка, где лежит сам .exe / .py — сюда пишем файлы результатов,
    чтобы они не терялись во временной папке PyInstaller."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_PATH = resource_path("data", "topics.json")
PROGRESS_PATH = os.path.join(app_dir(), "data", "progress.json")
TEST_RESULTS_PATH = os.path.join(app_dir(), "data", "test_results.json")


def load_topics():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["topics"]


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def normalize(text):
    """Приводит ответ к единому виду для сравнения: без регистра, без лишних
    пробелов, с одинаковыми апострофами (don't и don’t считаются одним и тем же)."""
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.lower().split())


def grade_for(percent):
    for min_percent, grade in GRADE_SCALE:
        if percent >= min_percent:
            return grade
    return GRADE_FAIL


def build_test(topics, n):
    """Выбирает n случайных вопросов так, чтобы в тест попали РАЗНЫЕ темы:
    берём по одному вопросу из каждой темы по кругу, пока не наберём n."""
    pools = []
    for t in topics:
        items = [(t, ex) for ex in t.get("exercises", [])]
        random.shuffle(items)
        if items:
            pools.append(items)
    random.shuffle(pools)

    picked = []
    while len(picked) < n and any(pools):
        for pool in pools:
            if pool and len(picked) < n:
                picked.append(pool.pop())
    random.shuffle(picked)
    return picked


# ---------------------------------------------------------------------------
# Главное окно приложения
# ---------------------------------------------------------------------------

class GrammarApp(tk.Tk):
    def __init__(self, topics=None):
        super().__init__()
        try:
            self.title("Тренажёр по грамматике английского языка")
            self.geometry("1100x700")
            self.minsize(860, 580)

            style = ttk.Style()
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
            style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))

            self.topics = topics if topics is not None else load_topics()
            self.progress = load_json(PROGRESS_PATH, {})
            self.test_results = load_json(TEST_RESULTS_PATH, [])

            self.current_topic = None
            self.current_exercise = None
            self.exercise_pool = []

            # состояние теста
            self.test_active = False
            self.test_items = []
            self.test_answers = []
            self.test_index = 0

            self._build_menu()
            self._build_layout()

            if self.topics:
                self.select_topic(0)
        except Exception:
            self.destroy()
            raise

    # ---------------- построение интерфейса ----------------

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Сбросить прогресс и результаты тестов", command=self.reset_progress)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.destroy)
        menubar.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.config(menu=menubar)

    def _show_about(self):
        messagebox.showinfo(
            "О программе",
            "Тренажёр по грамматике английского языка.\n"
            "Индивидуальный проект.\n\n"
            f"Загружено тем: {len(self.topics)}\n"
            f"Вопросов в базе: {self._total_exercises()}",
        )

    def _total_exercises(self):
        return sum(len(t.get("exercises", [])) for t in self.topics)

    def _build_layout(self):
        # --- левая панель: темы, сгруппированные по категориям ---
        left = ttk.Frame(self, width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        ttk.Label(left, text="Темы", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        # Колонка шире панели, чтобы длинные названия не обрезались: их видно
        # полностью, если прокрутить список вправо.
        self.tree.column("#0", width=430, minwidth=430, stretch=False)
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("category", font=("Segoe UI", 10, "bold"))
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._fill_tree()

        ttk.Label(
            left,
            text="[верно/всего] — статистика тренажёра.\nГруппу можно свернуть двойным щелчком.",
            font=("Segoe UI", 8),
            foreground="#666666",
            wraplength=290,
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # --- правая часть с вкладками ---
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.theory_frame = ttk.Frame(self.notebook)
        self.practice_frame = ttk.Frame(self.notebook)
        self.test_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.theory_frame, text="Теория")
        self.notebook.add(self.practice_frame, text="Тренажёр")
        self.notebook.add(self.test_frame, text="Тест")

        self._build_theory_tab()
        self._build_practice_tab()
        self._build_test_tab()

    # ---------------- дерево тем ----------------

    def _topic_label(self, topic):
        prog = self.progress.get(topic["id"], {})
        total = prog.get("total", 0)
        mark = f'  [{prog.get("correct", 0)}/{total}]' if total else ""
        return topic["title"] + mark

    def _fill_tree(self):
        """Строит дерево: категория -> темы. Категории идут в том порядке,
        в котором они впервые встречаются в topics.json."""
        self.tree.delete(*self.tree.get_children())

        groups = {}
        for i, t in enumerate(self.topics):
            category = (t.get("category") or "").strip() or DEFAULT_CATEGORY
            groups.setdefault(category, []).append(i)

        for n, (category, indices) in enumerate(groups.items()):
            cat_iid = f"c:{n}"
            self.tree.insert("", "end", iid=cat_iid, text=category, open=True, tags=("category",))
            for i in indices:
                self.tree.insert(cat_iid, "end", iid=f"t:{i}", text=self._topic_label(self.topics[i]))

    def _refresh_topic_labels(self):
        """Обновляет подписи [верно/всего], не сворачивая группы."""
        for i, t in enumerate(self.topics):
            self.tree.item(f"t:{i}", text=self._topic_label(t))

    def _highlight_topic(self, index):
        iid = f"t:{index}"
        self.tree.item(self.tree.parent(iid), open=True)
        self.tree.selection_set(iid)
        self.tree.see(iid)

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel or not sel[0].startswith("t:"):
            return  # щелчок по названию группы — ничего не выбираем
        index = int(sel[0][2:])
        if self.topics[index] is not self.current_topic:
            self.select_topic(index)
        # Если человек нажал на тему, находясь на вкладке «Тест», показываем теорию
        # (сам тест при этом не сбрасывается — к нему можно вернуться).
        if self.notebook.select() == str(self.test_frame):
            self.notebook.select(self.theory_frame)

    # ---------------- вкладка «Теория» ----------------

    def _build_theory_tab(self):
        self.theory_text = tk.Text(
            self.theory_frame, wrap="word", font=("Segoe UI", 11), padx=14, pady=12,
            borderwidth=0, highlightthickness=0,
        )
        self.theory_text.configure(state="disabled")
        scroll = ttk.Scrollbar(self.theory_frame, command=self.theory_text.yview)
        self.theory_text.configure(yscrollcommand=scroll.set)
        self.theory_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.theory_text.tag_configure("h1", font=("Segoe UI", 17, "bold"), spacing3=10)
        self.theory_text.tag_configure("h2", font=("Segoe UI", 12, "bold"), spacing1=12, spacing3=4,
                                        foreground="#2b4c7e")
        self.theory_text.tag_configure("body", font=("Segoe UI", 11), spacing3=2)
        self.theory_text.tag_configure("example", font=("Consolas", 10), foreground="#1a5d1a", spacing3=2)
        self.theory_text.tag_configure("note", font=("Segoe UI", 10), foreground="#444444", spacing3=2)
        self.theory_text.tag_configure("marker", font=("Segoe UI", 10, "italic"), foreground="#555555")

    def _render_theory(self):
        t = self.current_topic
        self.theory_text.configure(state="normal")
        self.theory_text.delete("1.0", "end")

        self.theory_text.insert("end", t["title"] + "\n", "h1")

        if t.get("formula"):
            self.theory_text.insert("end", "Формула\n", "h2")
            self.theory_text.insert("end", t["formula"] + "\n", "body")

        self.theory_text.insert("end", "Правило\n", "h2")
        self.theory_text.insert("end", t["rule"] + "\n", "body")

        if t.get("examples"):
            self.theory_text.insert("end", "Примеры\n", "h2")
            for ex in t["examples"]:
                self.theory_text.insert("end", "• " + ex + "\n", "example")

        if t.get("markers"):
            self.theory_text.insert("end", "Слова-маркеры\n", "h2")
            self.theory_text.insert("end", ", ".join(t["markers"]) + "\n", "marker")

        if t.get("notes"):
            self.theory_text.insert("end", "Дополнительно\n", "h2")
            for note in t["notes"]:
                self.theory_text.insert("end", "— " + note + "\n", "note")

        self.theory_text.configure(state="disabled")

    # ---------------- вкладка «Тренажёр» ----------------

    def _build_practice_tab(self):
        top = ttk.Frame(self.practice_frame)
        top.pack(fill="x", padx=10, pady=(14, 6))

        self.question_var = tk.StringVar(value="Выбери тему слева, чтобы начать тренировку.")
        ttk.Label(
            top, textvariable=self.question_var, font=("Segoe UI", 13), wraplength=680
        ).pack(anchor="w")

        entry_row = ttk.Frame(self.practice_frame)
        entry_row.pack(fill="x", padx=10, pady=6)
        self.answer_var = tk.StringVar()
        self.answer_entry = ttk.Entry(entry_row, textvariable=self.answer_var, font=("Segoe UI", 12))
        self.answer_entry.pack(side="left", fill="x", expand=True)
        self.answer_entry.bind("<Return>", lambda e: self.check_answer())

        ttk.Button(entry_row, text="Проверить", command=self.check_answer).pack(side="left", padx=6)

        self.feedback_var = tk.StringVar()
        ttk.Label(
            self.practice_frame, textvariable=self.feedback_var, font=("Segoe UI", 11), wraplength=680
        ).pack(anchor="w", padx=10, pady=6)

        btn_row = ttk.Frame(self.practice_frame)
        btn_row.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_row, text="Следующий вопрос", command=self.next_exercise).pack(side="left")
        ttk.Button(
            btn_row, text="Случайный вопрос (все темы)", command=self.random_from_all
        ).pack(side="left", padx=6)

        self.score_var = tk.StringVar(value="")
        ttk.Label(self.practice_frame, textvariable=self.score_var, font=("Segoe UI", 10)).pack(
            anchor="w", padx=10
        )

    def select_topic(self, index):
        self.current_topic = self.topics[index]
        self._highlight_topic(index)
        self._render_theory()
        self.exercise_pool = list(self.current_topic.get("exercises", []))
        random.shuffle(self.exercise_pool)
        self.next_exercise()

    def next_exercise(self):
        if not self.current_topic:
            return
        if not self.exercise_pool:
            self.exercise_pool = list(self.current_topic.get("exercises", []))
            random.shuffle(self.exercise_pool)
        if not self.exercise_pool:
            self.question_var.set("Для этой темы пока нет упражнений.")
            self.current_exercise = None
            self.feedback_var.set("")
            return
        self.current_exercise = self.exercise_pool.pop()
        self.question_var.set(self.current_exercise["question"])
        self.answer_var.set("")
        self.feedback_var.set("")
        self._update_score_label()
        self.answer_entry.focus_set()

    def random_from_all(self):
        all_pairs = [(t, ex) for t in self.topics for ex in t.get("exercises", [])]
        if not all_pairs:
            return
        topic, exercise = random.choice(all_pairs)

        self.current_topic = topic
        self.notebook.select(self.practice_frame)
        self._highlight_topic(self.topics.index(topic))
        self._render_theory()

        self.current_exercise = exercise
        self.question_var.set(exercise["question"])
        self.answer_var.set("")
        self.feedback_var.set("")
        self._update_score_label()
        self.answer_entry.focus_set()

    def check_answer(self):
        if not self.current_exercise:
            return
        user_answer = normalize(self.answer_var.get())
        accepted = [normalize(a) for a in self.current_exercise.get("answers", [])]

        topic_id = self.current_topic["id"]
        prog = self.progress.setdefault(topic_id, {"correct": 0, "total": 0})
        prog["total"] += 1

        explanation = self.current_exercise.get("explanation", "")
        if user_answer and user_answer in accepted:
            prog["correct"] += 1
            self.feedback_var.set("Верно! " + explanation)
        else:
            correct = self.current_exercise.get("answers", ["?"])[0]
            self.feedback_var.set(f"Неверно. Правильный ответ: {correct}. {explanation}")

        save_json(PROGRESS_PATH, self.progress)
        self._refresh_topic_labels()
        self._update_score_label()

    def _update_score_label(self):
        if not self.current_topic:
            return
        prog = self.progress.get(self.current_topic["id"], {"correct": 0, "total": 0})
        self.score_var.set(
            f'Результат по теме «{self.current_topic["title"]}»: {prog["correct"]} из {prog["total"]}'
        )

    # ---------------- вкладка «Тест» ----------------

    def _build_test_tab(self):
        # Три «экрана» внутри вкладки: стартовый, вопрос, результат.
        self.test_start = ttk.Frame(self.test_frame)
        self.test_question = ttk.Frame(self.test_frame)
        self.test_result = ttk.Frame(self.test_frame)

        # --- стартовый экран ---
        f = self.test_start
        ttk.Label(f, text="Итоговый тест", font=("Segoe UI", 17, "bold")).pack(
            anchor="w", padx=14, pady=(16, 4)
        )
        self.test_info_var = tk.StringVar()
        ttk.Label(
            f, textvariable=self.test_info_var, font=("Segoe UI", 11), wraplength=700, justify="left"
        ).pack(anchor="w", padx=14, pady=4)

        row = ttk.Frame(f)
        row.pack(anchor="w", padx=14, pady=12)
        ttk.Label(row, text="Количество вопросов:", font=("Segoe UI", 11)).pack(side="left")
        self.test_count_var = tk.IntVar(value=TEST_DEFAULT_QUESTIONS)
        ttk.Spinbox(
            row, from_=TEST_MIN_QUESTIONS, to=TEST_MAX_QUESTIONS,
            textvariable=self.test_count_var, width=5, state="readonly",
        ).pack(side="left", padx=8)

        ttk.Button(f, text="Начать тест", command=self.start_test).pack(anchor="w", padx=14, pady=6)

        self.test_history_var = tk.StringVar()
        ttk.Label(
            f, textvariable=self.test_history_var, font=("Segoe UI", 10),
            foreground="#444444", justify="left",
        ).pack(anchor="w", padx=14, pady=(18, 0))

        # --- экран вопроса ---
        f = self.test_question
        self.test_progress_var = tk.StringVar()
        ttk.Label(f, textvariable=self.test_progress_var, font=("Segoe UI", 10)).pack(
            anchor="w", padx=14, pady=(16, 2)
        )
        self.test_progressbar = ttk.Progressbar(f, maximum=100, mode="determinate")
        self.test_progressbar.pack(fill="x", padx=14, pady=4)

        self.test_q_var = tk.StringVar()
        ttk.Label(
            f, textvariable=self.test_q_var, font=("Segoe UI", 13), wraplength=700, justify="left"
        ).pack(anchor="w", padx=14, pady=(16, 8))

        row = ttk.Frame(f)
        row.pack(fill="x", padx=14, pady=6)
        self.test_answer_var = tk.StringVar()
        self.test_entry = ttk.Entry(row, textvariable=self.test_answer_var, font=("Segoe UI", 12))
        self.test_entry.pack(side="left", fill="x", expand=True)
        self.test_entry.bind("<Return>", lambda e: self.submit_test_answer())
        self.test_next_text = tk.StringVar(value="Далее")
        ttk.Button(row, textvariable=self.test_next_text, command=self.submit_test_answer).pack(
            side="left", padx=6
        )

        ttk.Label(
            f, text="Во время теста подсказок нет — результат покажем в конце.",
            font=("Segoe UI", 9), foreground="#666666",
        ).pack(anchor="w", padx=14, pady=(2, 0))
        ttk.Button(f, text="Прервать тест", command=self.abort_test).pack(anchor="w", padx=14, pady=14)

        # --- экран результата ---
        f = self.test_result
        self.test_grade_var = tk.StringVar()
        ttk.Label(f, textvariable=self.test_grade_var, font=("Segoe UI", 24, "bold")).pack(
            anchor="w", padx=14, pady=(14, 0)
        )
        self.test_score_var = tk.StringVar()
        ttk.Label(f, textvariable=self.test_score_var, font=("Segoe UI", 12)).pack(
            anchor="w", padx=14, pady=(2, 0)
        )
        self.test_weak_var = tk.StringVar()
        ttk.Label(
            f, textvariable=self.test_weak_var, font=("Segoe UI", 11), wraplength=700, justify="left"
        ).pack(anchor="w", padx=14, pady=(4, 8))

        btn_row = ttk.Frame(f)
        btn_row.pack(side="bottom", fill="x", padx=14, pady=10)
        ttk.Button(btn_row, text="Пройти ещё раз", command=self.back_to_test_start).pack(side="left")

        review_frame = ttk.Frame(f)
        review_frame.pack(fill="both", expand=True, padx=14)
        self.test_review_text = tk.Text(
            review_frame, wrap="word", font=("Segoe UI", 10), padx=8, pady=8,
            borderwidth=1, relief="solid", highlightthickness=0,
        )
        review_scroll = ttk.Scrollbar(review_frame, command=self.test_review_text.yview)
        self.test_review_text.configure(yscrollcommand=review_scroll.set, state="disabled")
        self.test_review_text.pack(side="left", fill="both", expand=True)
        review_scroll.pack(side="right", fill="y")
        self.test_review_text.tag_configure("q", font=("Segoe UI", 10, "bold"), spacing1=6)
        self.test_review_text.tag_configure("ok", foreground="#1a6b1a")
        self.test_review_text.tag_configure("bad", foreground="#b02020")
        self.test_review_text.tag_configure("hint", foreground="#555555", font=("Segoe UI", 9, "italic"))

        self._show_test_screen("start")

    def _show_test_screen(self, name):
        screens = {
            "start": self.test_start,
            "question": self.test_question,
            "result": self.test_result,
        }
        for frame in screens.values():
            frame.pack_forget()
        screens[name].pack(fill="both", expand=True)
        if name == "start":
            self._refresh_test_start()

    def _refresh_test_start(self):
        total = self._total_exercises()
        scale = ", ".join(f"{g} — от {p}%" for p, g in GRADE_SCALE) + f", иначе {GRADE_FAIL}"
        text = (
            f"Вопросы выбираются случайно из упражнений всех тем (сейчас в базе: {total}). "
            "Стараемся брать вопросы из разных тем. В конце программа считает "
            f"процент правильных ответов и ставит оценку.\n\nШкала оценок: {scale}."
        )
        if total < TEST_MIN_QUESTIONS:
            text += (
                f"\n\nВнимание: в базе всего {total} вопросов — тест получится короче "
                f"{TEST_MIN_QUESTIONS}. Добавь упражнения в topics.json."
            )
        self.test_info_var.set(text)

        if self.test_results:
            lines = ["Последние результаты:"]
            for r in reversed(self.test_results[-5:]):
                lines.append(
                    f'  {r["date"]} — {r["correct"]} из {r["total"]} ({r["percent"]}%), оценка {r["grade"]}'
                )
            self.test_history_var.set("\n".join(lines))
        else:
            self.test_history_var.set("Тест ещё не проходили.")

    def start_test(self):
        total = self._total_exercises()
        if total == 0:
            messagebox.showinfo("Тест", "В базе нет ни одного упражнения. Добавь их в topics.json.")
            return
        try:
            n = int(self.test_count_var.get())
        except (tk.TclError, ValueError):
            n = TEST_DEFAULT_QUESTIONS
        n = max(TEST_MIN_QUESTIONS, min(TEST_MAX_QUESTIONS, n))
        n = min(n, total)

        self.test_items = build_test(self.topics, n)
        self.test_answers = []
        self.test_index = 0
        self.test_active = True
        self._show_test_screen("question")
        self._show_test_question()

    def _show_test_question(self):
        n = len(self.test_items)
        _, exercise = self.test_items[self.test_index]
        self.test_progress_var.set(f"Вопрос {self.test_index + 1} из {n}")
        self.test_progressbar["value"] = self.test_index / n * 100
        self.test_q_var.set(exercise["question"])
        self.test_answer_var.set("")
        self.test_next_text.set("Завершить" if self.test_index == n - 1 else "Далее")
        self.test_entry.focus_set()

    def submit_test_answer(self):
        if not self.test_active:
            return
        self.test_answers.append(self.test_answer_var.get())
        self.test_index += 1
        if self.test_index >= len(self.test_items):
            self._finish_test()
        else:
            self._show_test_question()

    def abort_test(self):
        if messagebox.askyesno("Прервать тест", "Прервать тест? Результат не сохранится."):
            self.test_active = False
            self._show_test_screen("start")

    def back_to_test_start(self):
        self._show_test_screen("start")

    def _finish_test(self):
        self.test_active = False
        n = len(self.test_items)
        correct = 0
        review = []
        weak_topics = []

        for (topic, ex), given in zip(self.test_items, self.test_answers):
            accepted = [normalize(a) for a in ex.get("answers", [])]
            ok = bool(normalize(given)) and normalize(given) in accepted
            if ok:
                correct += 1
            elif topic["title"] not in weak_topics:
                weak_topics.append(topic["title"])
            review.append({
                "question": ex["question"],
                "topic": topic["title"],
                "given": given.strip(),
                "correct": ex.get("answers", ["?"])[0],
                "explanation": ex.get("explanation", ""),
                "ok": ok,
            })

        percent = correct * 100 // n  # округляем вниз, чтобы % и оценка не расходились
        grade = grade_for(percent)

        self.test_results.append({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "correct": correct,
            "total": n,
            "percent": percent,
            "grade": grade,
        })
        self.test_results = self.test_results[-30:]
        save_json(TEST_RESULTS_PATH, self.test_results)

        self.test_grade_var.set(f"Оценка: {grade}")
        self.test_score_var.set(f"Правильных ответов: {correct} из {n} ({percent}%)")
        if weak_topics:
            self.test_weak_var.set("Стоит повторить: " + "; ".join(weak_topics))
        else:
            self.test_weak_var.set("Ошибок нет — отличный результат!")
        self._render_review(review)
        self._show_test_screen("result")

    def _render_review(self, review):
        t = self.test_review_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        for i, item in enumerate(review, start=1):
            t.insert("end", f'{i}. {item["question"]}   ({item["topic"]})\n', "q")
            if item["ok"]:
                t.insert("end", f'    Верно: {item["given"]}\n', "ok")
            else:
                t.insert("end", f'    Твой ответ: {item["given"] or "(пусто)"}\n', "bad")
                t.insert("end", f'    Правильно: {item["correct"]}\n', "ok")
                if item["explanation"]:
                    t.insert("end", f'    {item["explanation"]}\n', "hint")
        t.configure(state="disabled")

    # ---------------- сброс ----------------

    def reset_progress(self):
        if messagebox.askyesno(
            "Сбросить прогресс",
            "Обнулить статистику тренажёра по всем темам и историю результатов тестов?",
        ):
            self.progress = {}
            self.test_results = []
            save_json(PROGRESS_PATH, self.progress)
            save_json(TEST_RESULTS_PATH, self.test_results)
            self._refresh_topic_labels()
            self._update_score_label()
            self._refresh_test_start()


def show_startup_error(error):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Не удалось запустить программу",
        "Не получилось загрузить темы из data/topics.json.\n\n"
        f"{type(error).__name__}: {error}\n\n"
        "Запусти check_topics.py — он покажет, в какой строке ошибка.",
        parent=root,
    )
    root.destroy()


def main():
    try:
        app = GrammarApp(load_topics())
    except Exception as e:
        show_startup_error(e)
        return
    app.mainloop()


if __name__ == "__main__":
    main()
