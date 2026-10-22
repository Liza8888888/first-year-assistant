from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

NAVY, BLUE, LIGHT, INK, GREY = RGBColor(0x0F, 0x2A, 0x5C), RGBColor(0x1A, 0x5F, 0xD6), RGBColor(0xEA, 0xF0, 0xFB), RGBColor(0x1F, 0x29, 0x37), RGBColor(0x6B, 0x72, 0x80)
GREEN, RED = RGBColor(0x15, 0x80, 0x3D), RGBColor(0xB9, 0x1C, 0x1C)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, lines, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    if isinstance(lines, str):
        lines = [lines]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(ln, tuple):
            ln, kw = ln
        else:
            kw = {}
        r = p.add_run(); r.text = ln
        r.font.size = Pt(kw.get('size', size)); r.font.bold = kw.get('bold', bold)
        r.font.color.rgb = kw.get('color', color); r.font.name = 'Calibri'
        p.alignment = align; p.space_after = Pt(kw.get('after', 6))
    return tb


def box(slide, x, y, w, h, fill=LIGHT, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line: s.line.color.rgb = line; s.line.width = Pt(1.25)
    else: s.line.fill.background()
    s.shadow.inherit = False
    return s


def slide(title, sub=None):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12)); bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    text(s, 0.6, 0.35, 12.1, 0.9, title, size=32, color=NAVY, bold=True)
    if sub: text(s, 0.6, 1.1, 12.1, 0.5, sub, size=16, color=GREY)
    return s


# 1. титул
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
text(s, 0.8, 2.1, 11.5, 1.6, 'Помощник по дисциплинам 1 курса', size=44, color=RGBColor(255, 255, 255), bold=True)
text(s, 0.8, 3.4, 11.5, 1.2, ['ОП «Информатика и вычислительная техника», НИУ ВШЭ (МИЭМ), 2026/27',
                              'Отвечает на вопросы по страницам hse.ru и показывает источники'], size=20, color=RGBColor(0xC7, 0xD7, 0xF5))
text(s, 0.8, 6.3, 11.5, 0.5, '25 страниц дисциплин · 30 + 14 тестовых вопросов', size=16, color=RGBColor(0x9F, 0xB6, 0xE6))

# 2. что делает
s = slide('Что делает решение', 'Вопрос на русском → краткий ответ из страниц курсов + ссылки на источники')
cards = [('Данные', '25 страниц дисциплин 1 курса за 2026/27 (включая «углублённые» и «индустриальные» варианты) скачаны и разобраны в JSON: паспорт, аннотация, цель, результаты, содержание, элементы контроля, формулы, литература, авторы.'),
         ('Вопросы', 'Формула оценивания, преподаватели, кредиты, модули, литература, содержание, цели, статус и язык, связи между дисциплинами (пре-/постреквизиты), сводные вопросы («что в 1 модуле», «где больше всего кредитов»).'),
         ('Ответ', 'Короткий текст, собранный только из найденных фрагментов, и пронумерованный список источников — ссылки на страницы hse.ru. Если ответа нет — явный отказ, а не выдумка.')]
for i, (h, b) in enumerate(cards):
    x = 0.6 + i * 4.1
    box(s, x, 1.9, 3.9, 4.6)
    text(s, x + 0.2, 2.05, 3.5, 0.6, h, size=22, color=BLUE, bold=True)
    text(s, x + 0.2, 2.75, 3.5, 3.7, b, size=17)

# 3. как
s = slide('Как это работает', 'Детерминированный конвейер; LLM — необязательный последний шаг')
steps = ['Вопрос', 'Нормализация:\nсленг, склонения,\nвариант курса', 'Поиск курса\nи намерения\n(формула, литература…)', 'Структурный\nответ из полей\nстраницы', 'BM25 по фрагментам\n(если шаблона нет)', 'Ответ +\nисточники']
for i, t in enumerate(steps):
    x = 0.45 + i * 2.1
    box(s, x, 2.0, 1.85, 1.7, fill=NAVY if i in (0, 5) else LIGHT)
    text(s, x + 0.05, 2.0, 1.75, 1.7, t, size=15, color=RGBColor(255, 255, 255) if i in (0, 5) else INK, bold=i in (0, 5), align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if i < 5: text(s, x + 1.8, 2.5, 0.35, 0.6, '›', size=28, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
text(s, 0.6, 4.1, 12.1, 2.9, [
    ('• Страницы разобраны по полям, поэтому формулы оценивания превращаются в проценты («50% — Экзамен…»), а блокирующие элементы фильтруются точно, без «творчества» модели.', {}),
    ('• Связи между дисциплинами: предложения про пре-/постреквизиты из аннотаций + обратный поиск «какие страницы упоминают этот курс».', {}),
    ('• Свободный поиск: BM25 со стеммингом (Snowball, русский) по фрагментам ≤ 900 символов; порог релевантности отсекает вопросы вне темы.', {}),
    ('• Внешняя LLM (Claude Haiku) подключается флагом --llm для пересказа найденных фрагментов; в тестах не использовалась — ключа в среде не было, результаты получены без неё.', {'color': GREY})], size=17)

# 4. почему
s = slide('Почему такой подход')
rows = [('Точность важнее красноречия', 'Вопросы про формулы, кредиты и литературу требуют дословных цифр. Прямое чтение полей страницы не искажает числа — LLM-пересказ может.'),
        ('Проверяемость', 'Каждый ответ ссылается на страницу; каждый шаблон проверяется автотестом (30/30 и 14/14 подтверждённых ошибок).'),
        ('Мало данных — не нужна векторная БД', '25 страниц ≈ 500 фрагментов: BM25 + разбор по полям быстрее и прозрачнее, чем эмбеддинги; нет зависимости от API и стоимости.'),
        ('Честные отказы', 'Если подходящего фрагмента нет, помощник говорит «в материалах ответа нет», а не додумывает.')]
for i, (h, b) in enumerate(rows):
    y = 1.5 + i * 1.35
    box(s, 0.6, y, 12.1, 1.2)
    text(s, 0.8, y + 0.08, 3.9, 1.0, h, size=19, color=BLUE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 4.8, y + 0.08, 7.8, 1.05, b, size=16, anchor=MSO_ANCHOR.MIDDLE)

# 5. результаты
s = slide('Результаты тестов', 'Файл QA.md: вопросы, ответы, источники и автоматическая проверка')
box(s, 0.6, 1.8, 5.9, 2.2, fill=RGBColor(0xE8, 0xF5, 0xEC))
text(s, 0.8, 1.9, 5.5, 1.0, '30 из 30', size=48, color=GREEN, bold=True)
text(s, 0.8, 3.0, 5.5, 1.0, 'вопросов отвечены верно: формулы, кредиты, литература, связи, сводные вопросы, корректные отказы', size=16)
box(s, 6.8, 1.8, 5.9, 2.2, fill=RGBColor(0xFD, 0xEC, 0xEC))
text(s, 7.0, 1.9, 5.5, 1.0, '14 из 14', size=48, color=RED, bold=True)
text(s, 7.0, 3.0, 5.5, 1.0, 'проблемных вопросов дают неверный или неполный ответ — и это подтверждено проверкой', size=16)
text(s, 0.6, 4.35, 12.1, 2.7, [
    ('Важно: наборы подобраны нами и автор системы знал её устройство — 30/30 показывает работоспособность шаблонов, а не точность на произвольных вопросах реальных студентов.', {'bold': True, 'color': NAVY}),
    ('Живой пример из тестов: «Как считается оценка по матану за 2 модуль?» → 5% аудиторная работа, 15% коллоквиум, 15% контрольная, 50% экзамен — ссылка на страницу «Математический анализ».', {}),
], size=17)

# 6. ошибки
s = slide('Где решение ошибается', 'Реальные классы ошибок из части 2 файла QA.md')
errs = [('Сленг, опечатки, английский', '«матеша», «препадаёт», “Calculus” — нет словаря синонимов и исправления опечаток'),
        ('Нет данных — но ответ «шумит»', '«В какой аудитории лекции?», «можно ли пересдать?» — выводятся близкие по словам фрагменты'),
        ('Сравнение и вычисления', 'Разница обычного/углублённого курса; итоговый вес экзамена с учётом вложенных формул (60%)'),
        ('Гранулярность и роли', 'Темы по модулям, лекторы vs семинаристы — на страницах этого деления нет, система об этом не предупреждает'),
        ('Связи и агрегаты', 'Обратные пререквизиты только по названиям в «», сводные вопросы — только по нескольким шаблонам'),
        ('Контекст и пробелы источника', 'Нет памяти диалога; у физкультуры на странице не указаны кредиты')]
for i, (h, b) in enumerate(errs):
    c, r = i % 2, i // 2
    x, y = 0.6 + c * 6.15, 1.8 + r * 1.75
    box(s, x, y, 5.95, 1.6)
    text(s, x + 0.15, y + 0.08, 5.65, 0.5, h, size=18, color=RED, bold=True)
    text(s, x + 0.15, y + 0.62, 5.65, 0.95, b, size=15)

# 7. улучшения
s = slide('Что улучшили бы за ещё два дня')
plan = [('День 1 — понимание вопроса', ['Эмбеддинги (e5/bge-m3) + BM25 и реранкер вместо ручных регулярных выражений', 'Словарь синонимов из реальных вопросов студентов, исправление опечаток, английские запросы', 'Память диалога для уточнений («а у углублённого?»)']),
        ('День 2 — надёжность ответов', ['LLM-генерация по найденным фрагментам с проверкой «каждое утверждение подтверждено цитатой»', 'Разворачивание вложенных формул и автоматический расчёт весов', 'Оценка на 100+ вопросах от студентов, метрики recall@k / faithfulness, ежедневное обновление страниц'])]
for i, (h, bl) in enumerate(plan):
    x = 0.6 + i * 6.15
    box(s, x, 1.5, 5.95, 5.3)
    text(s, x + 0.2, 1.65, 5.55, 0.6, h, size=22, color=BLUE, bold=True)
    text(s, x + 0.2, 2.4, 5.55, 4.3, ['• ' + b for b in bl], size=17)

prs.save('Presentation.pptx')
print('saved')
