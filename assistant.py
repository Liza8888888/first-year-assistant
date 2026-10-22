"""Помощник по дисциплинам 1 курса ОП «Информатика и вычислительная техника» (НИУ ВШЭ, МИЭМ), 2026/27.

Конвейер: вопрос -> распознавание дисциплины -> распознавание намерения -> поиск (BM25) по фрагментам
-> краткий ответ строго из найденного текста -> список источников (URL страниц hse.ru).
LLM необязателен: при заданном ANTHROPIC_API_KEY и флаге --llm ответ пересобирается моделью по тем же фрагментам.
"""
import json, math, os, re, sys, collections
import snowballstemmer

HERE = os.path.dirname(os.path.abspath(__file__))
STEM = snowballstemmer.stemmer('russian')
ESTEM = snowballstemmer.stemmer('english')

# ---------- данные ----------
COURSES = json.load(open(os.path.join(HERE, 'courses.json'), encoding='utf-8'))
BY_ID = {c['id']: c for c in COURSES}

TOK = re.compile(r'[a-zа-яё0-9+#]+', re.I)
STOP = set('и в во на не что как это для по из к с о об от до за или а но же ли бы есть какой какая какие каков какова сколько ли у ее его их мне вы можно нужно ли про при курс курсе дисциплина дисциплине дисциплины предмет предмете'.split())


def toks(text):
    out = []
    for w in TOK.findall(text.lower().replace('ё', 'е')):
        if w in STOP:
            continue
        out.append(STEM.stemWord(w) if re.search('[а-я]', w) else ESTEM.stemWord(w))
    return out


# ---------- нормализация названий дисциплин ----------
ABBR = [  # (регэксп по запросу, id дисциплины-основы или название-подстрока)
    (r'\bматан\w*|мат\.? ?анализ', 'Математический анализ'),
    (r'\bалгем\w*|\bалгебр\w*(?! булев)', 'Алгебра и геометрия'),
    (r'\bдискрет\w*|дискр\.? ?мат', 'Дискретная математика'),
    (r'\bаип\b|алгоритмизаци|программировани', 'Алгоритмизация и программирование'),
    (r'\bинфа\b|\bинформатик', 'Информатика'),
    (r'\bфизр\w*|физическ\w+ культур|физкультур', 'Физическая культура'),
    (r'\bбжд\b|безопасност\w+ жизнедеятельност', 'Безопасность жизнедеятельности'),
    (r'\bорг\b|российской государственност|основ\w* государственност', 'Основы российской государственности'),
    (r'истори\w+ росси', 'История России'),
    (r'ии-грамотност|грамотност\w+ ии|цифровой грамотност|независим\w+ экзамен', 'Независимый экзамен по ИИ-грамотности'),
    (r'integrative exam|интегративн\w+ экзамен|экзамен по английск', 'English Language Integrative Exam'),
    (r'инженерн\w+ график', 'Компьютерный практикум по инженерной графике'),
    (r'введени\w+ в специальност', 'Введение в специальность'),
    (r'python в науке|науке о данных', 'Проектный семинар "Python в науке о данных"'),
    (r'управлени\w+ продукт|продуктами и проектами', 'Проектный семинар "Управление продуктами и проектами"'),
    (r'\bфизик\w*', 'Физика'),
]
QUALIF = [('углубленн', 'углубленный курс'), ('индустриальн', 'индустриальный профиль')]


def base_title(t):
    return re.sub(r'\s*\((углубленный курс|индустриальный профиль)\)', '', t).strip()


def find_courses(q):
    """Возвращает список id курсов, упомянутых в вопросе (с учётом углубленного/индустриального варианта)."""
    ql = q.lower().replace('ё', 'е')
    wanted = []
    for rx, name in ABBR:
        if re.search(rx, ql):
            wanted.append(name)
    # длинные точные названия перекрывают общие («Python в науке…» не должен тянуть «Информатику»)
    if len(wanted) > 1:
        wanted = [w for w in wanted if not any(w != o and (w in o) for o in wanted)] or wanted
    # дополнительно — совпадение основ всех слов названия (склонения: «Математического анализа»)
    qs = set(toks(q))
    for c in COURSES:
        bt = base_title(c['title'])
        ts = set(toks(bt))
        if ts and ts <= qs and bt not in wanted:
            wanted.append(bt)
    qual = None
    for k, v in QUALIF:
        if k in ql:
            qual = v
    ids = []
    for w in wanted:
        variants = [c for c in COURSES if base_title(c['title']) == w]
        if not variants:
            continue
        if qual:
            sel = [c for c in variants if qual in c['title']] or variants
        else:
            sel = [c for c in variants if base_title(c['title']) == c['title']] or variants[:1]
        ids += [c['id'] for c in sel]
    return ids, (qual is None and wanted)


# ---------- фрагменты и индекс ----------
SEC_NAME = {'annotation': 'Аннотация', 'goal': 'Цель освоения', 'results': 'Планируемые результаты',
            'content': 'Содержание дисциплины', 'controls': 'Элементы контроля', 'formula': 'Формула оценивания',
            'literature': 'Список литературы', 'authors': 'Авторы', 'card': 'Паспорт дисциплины'}


def card_text(c):
    return (f"{c['title']}. Кредиты (ECTS): {c['credits'] or 'не указаны на странице'}. Язык: {c['lang']}. "
            f"Кто читает: {c['dept']}. Статус: {c['status']}. Когда читается: {c['when']}. "
            f"Преподаватели: {', '.join(c['teachers']) or 'не указаны'}.")


def build_chunks():
    chunks = []
    for c in COURSES:
        chunks.append(dict(cid=c['id'], sec='card', text=card_text(c)))
        for sec, lines in c['sections'].items():
            buf = ''
            for ln in lines:
                if len(buf) + len(ln) > 900 and buf:
                    chunks.append(dict(cid=c['id'], sec=sec, text=buf)); buf = ''
                buf += ln + '\n'
            if buf:
                chunks.append(dict(cid=c['id'], sec=sec, text=buf))
    for ch in chunks:
        ch['tok'] = toks(base_title(BY_ID[ch['cid']]['title']) + ' ' + SEC_NAME[ch['sec']] + ' ' + ch['text'])
    return chunks


CHUNKS = build_chunks()
DF = collections.Counter(t for ch in CHUNKS for t in set(ch['tok']))
AVG = sum(len(ch['tok']) for ch in CHUNKS) / len(CHUNKS)


def bm25(qt, ch, k1=1.4, b=0.75):
    tf = collections.Counter(ch['tok'])
    s = 0.0
    for t in set(qt):
        if t in tf:
            idf = math.log(1 + (len(CHUNKS) - DF[t] + .5) / (DF[t] + .5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(ch['tok']) / AVG))
    return s


def retrieve(q, course_ids=None, k=4, secs=None):
    qt = toks(q)
    cand = [ch for ch in CHUNKS if (not course_ids or ch['cid'] in course_ids) and (not secs or ch['sec'] in secs)]
    scored = sorted(((bm25(qt, ch), ch) for ch in cand), key=lambda x: -x[0])
    return [(s, ch) for s, ch in scored[:k] if s > 0]


# ---------- намерения ----------
INTENTS = [
    ('formula', r'формул|оценива|оценк|накопленн|вес |веса|итогов\w+ оценк|как считается|из чего складывается|процент|коэффициент'),
    ('literature', r'литератур|учебник|книг|пособи|читать|библиограф'),
    ('relations', r'(?:пре|пост)?реквизит|связ|предшеств|после|перед |основ\w+ для|нужн\w+ для|необходим\w* для|пригодится|зависит|использу\w+ (?:в дальнейшем|знани)|для каких дисциплин'),
    ('teachers', r'преподавател|лектор|кто (читает|ведет|ведёт|преподает|преподаёт)|ведет|ведёт'),
    ('authors', r'автор'),
    ('credits', r'кредит|зачетн\w+ единиц|ects|трудоемкост|трудоёмкост'),
    ('when', r'когда|модул|семестр|в каком|сколько длится|длительност'),
    ('language', r'язык|english|англ'),
    ('status', r'обязательн|по выбору|статус'),
    ('dept', r'департамент|кафедр|кто читает|подразделени|школа'),
    ('controls', r'элемент\w* контроля|контрольн|блокирующ|экзамен|коллоквиум|форма контроля|как сдавать|формат|тест'),
    ('goal', r'цел[ьи]|зачем|для чего'),
    ('results', r'результат|чему научу|что буду уметь|умени|навык|компетенц'),
    ('content', r'содержани|тем[ыа]|разделы|программа курса|о ч[её]м|что изуч|что проходят|что входит'),
    ('annotation', r'аннотац|описани|расскажи|что такое'),
]


def intent_of(q):
    ql = q.lower().replace('ё', 'е')
    hits = [n for n, rx in INTENTS if re.search('(?<![а-я])(?:' + rx.replace('ё', 'е') + ')', ql)]
    if 'when' in hits and 'formula' in hits:
        hits.remove('when')
    # приоритет формулы над экзаменом, а «кто читает» над подразделением
    if 'formula' in hits and 'controls' in hits and not re.search(r'блокирующ|формат|как сдавать', ql):
        hits.remove('controls')
    if 'teachers' in hits and 'dept' in hits and re.search(r'кто читает|кто ведет', ql):
        hits.remove('dept')
    return hits


# ---------- разбор данных ----------
def parse_formula(c):
    L = c['sections'].get('formula', [])
    out = []
    i = 0
    while i < len(L) - 1:
        if re.match(r'\d{4}/\d{4}', L[i]):
            out.append((L[i], L[i + 1])); i += 2
        else:
            i += 1
    return out


def fmt_formula(expr):
    parts = [p.strip() for p in expr.split(' + ')]
    res = []
    for p in parts:
        m = re.match(r'([\d.]+)\s*\*\s*(.+)', p)
        res.append(f"{round(float(m.group(1)) * 100, 1):g}% — {m.group(2)}" if m else p)
    return res


def parse_controls(c):
    L = c['sections'].get('controls', [])
    out = []
    for ln in L:
        if ln in ('блокирующий', 'неблокирующий', 'non-blocking', 'blocking'):
            out.append([ln, None, []])
        elif out:
            if out[-1][1] is None:
                out[-1][1] = ln
            else:
                out[-1][2].append(ln)
    return out


def parse_lit(c):
    L = c['sections'].get('literature', [])
    d, cur = {}, None
    for ln in L:
        if ln.startswith(('Рекомендуемая', 'Recommended')):
            cur = 'основная' if ('основная' in ln or 'Core' in ln) else 'дополнительная'
            d[cur] = []
        elif cur:
            d[cur].append(ln)
    return d


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[А-ЯA-Z«])', text.replace('\n', ' ')) if len(s.strip()) > 20]


def short(s, n=300):
    s = re.sub(r'\s+', ' ', s)
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'


def src(c, sec):
    return (c['url'], f"{c['title']} — {SEC_NAME[sec]}")


# ---------- ответы по намерениям ----------
def answer_for_course(c, intents, q, ql):
    """Возвращает (текст, [(url, подпись)])  или None, если встроенного обработчика нет."""
    T, S = [], []
    for it in intents:
        if it == 'formula':
            fs = parse_formula(c)
            if not fs:
                continue
            want = None
            m = re.search(r'([1-4])\s*(?:-?й|-?го)?\s*модул', ql)
            if m:
                want = {'1': '1st', '2': '2nd', '3': '3rd', '4': '4th'}[m.group(1)]
            yr = re.search(r'(20\d\d)\s*[/-]\s*(20\d\d)', ql)
            ykey = f'{yr.group(1)}/{yr.group(2)}' if yr else '2026/2027'
            fs = [(p, e) for p, e in fs if p.startswith(ykey)]
            if not fs:
                T.append(f"На странице «{c['title']}» нет формулы оценивания за {ykey} учебный год.")
                S.append(src(c, 'formula'))
                continue
            shown = [(p, e) for p, e in fs if not want or want in p] or fs
            T.append(f"Формула оценивания «{c['title']}» (оценка за период → состав, по данным страницы):")
            for p, e in shown:
                T.append(f"• {p}: " + '; '.join(fmt_formula(e)))
            T.append("Примечание: в формуле 4-го модуля может участвовать результат предыдущего модуля (как указано на странице).")
            S.append(src(c, 'formula'))
        elif it == 'literature':
            lit = parse_lit(c)
            if not lit:
                continue
            kinds = [k for k in lit if k in ql] or list(lit)
            for k in kinds:
                T.append(f"Литература ({k}), «{c['title']}»:")
                T += ['• ' + short(x, 200) for x in lit[k][:6]]
                if len(lit[k]) > 6:
                    T.append(f"  … и ещё {len(lit[k]) - 6} (см. страницу).")
            S.append(src(c, 'literature'))
        elif it == 'teachers':
            T.append(f"Преподаватели «{c['title']}»: {', '.join(c['teachers']) or 'на странице не указаны'}.")
            S.append(src(c, 'card'))
        elif it == 'authors':
            a = c['sections'].get('authors', [])
            T.append(f"Авторы программы «{c['title']}»: {', '.join(a) or 'не указаны'}.")
            S.append(src(c, 'authors'))
        elif it == 'credits':
            T.append(f"«{c['title']}»: {'кредитов — ' + c['credits'] if c['credits'] else 'число кредитов на странице не указано'}.")
            S.append(src(c, 'card'))
        elif it == 'when':
            T.append(f"«{c['title']}» читается: {c['when']}.")
            S.append(src(c, 'card'))
        elif it == 'language':
            T.append(f"«{c['title']}»: язык обучения — {'русский' if c['lang'] == 'RUS' else 'английский'}.")
            S.append(src(c, 'card'))
        elif it == 'status':
            T.append(f"«{c['title']}»: {c['status'].lower()}.")
            S.append(src(c, 'card'))
        elif it == 'dept':
            T.append(f"«{c['title']}» читает: {c['dept']}.")
            S.append(src(c, 'card'))
        elif it == 'controls':
            cs = parse_controls(c)
            if not cs:
                continue
            T.append(f"Элементы контроля «{c['title']}»:")
            seen = set()
            only_block = re.search(r'(?<!не)блокирующ', ql) and not re.search(r'неблокирующ', ql)
            for fl, name, desc in cs:
                if only_block and fl.startswith(('не', 'non')):
                    continue
                key = (fl, name)
                if key in seen:
                    continue
                seen.add(key)
                T.append(f"• {name} ({fl})" + (f": {short(' '.join(desc), 160)}" if desc else ''))
            S.append(src(c, 'controls'))
        elif it in ('goal', 'results', 'content'):
            L = c['sections'].get(it, [])
            if not L:
                continue
            T.append(f"{SEC_NAME[it]} «{c['title']}»:")
            T += ['• ' + short(x, 220) for x in L[:6]]
            if len(L) > 6:
                T.append(f"  … ещё {len(L) - 6} пункт(ов) на странице.")
            S.append(src(c, it))
        elif it == 'annotation':
            a = ' '.join(c['sections'].get('annotation', []))
            T.append(short(a, 600))
            S.append(src(c, 'annotation'))
        elif it == 'relations':
            if re.search(r'(?<![а-я])(?:перед|пререквизит|предшеств|до изучени|нужно знать|что нужно)', ql):
                d = 'pre'
            elif re.search(r'постреквизит|после|дальше|основа для|нужн\w+ для|для каких', ql):
                d = 'post'
            else:
                d = None
            r, sr = relations(c, d)
            if r:
                T += r; S += sr
        if len(T) > 0 and len(intents) > 3:
            break
    return T, S


REL_RX = re.compile(r'реквизит|использован\w+ при изучении|быть использованы в дальнейшем|могут быть использованы|базируется на|последующего изучения|последующего освоения|для освоения курсов', re.I)


def relations(c, direction=None):
    """Связи: предложения про пре-/постреквизиты из аннотации и обратные ссылки из других дисциплин."""
    T, S = [], []
    rx_dir = {'pre': re.compile(r'ререквизит|базируется на'),
              'post': re.compile(r'остреквизит|использован|последующего|для освоения курсов')}.get(direction)
    ann = ' '.join(c['sections'].get('annotation', []))
    sel = [s for s in sentences(ann + ' ' + ' '.join(c['sections'].get('goal', [])))
           if REL_RX.search(s) and (not rx_dir or rx_dir.search(s))]
    if sel:
        T.append(f"Связи «{c['title']}» с другими дисциплинами (из аннотации):")
        T += ['• ' + short(s, 420) for s in sel[:3]]
        S.append(src(c, 'annotation'))
    else:
        for o in COURSES:
            if o['id'] != c['id'] and base_title(o['title']) == base_title(c['title']):
                oa = ' '.join(o['sections'].get('annotation', []))
                osel = [s for s in sentences(oa) if REL_RX.search(s) and (not rx_dir or rx_dir.search(s))]
                if osel:
                    T.append(f"На странице «{c['title']}» связи не описаны; у варианта «{o['title']}» указано:")
                    T += ['• ' + short(s, 420) for s in osel[:2]]
                    S.append(src(o, 'annotation'))
                    break
    if direction == 'pre':
        if not T:
            T.append(f"На страницах «{base_title(c['title'])}» пререквизиты не указаны.")
            S.append(src(c, 'annotation'))
        return T, S
    bt = base_title(c['title'])
    back = []
    for o in COURSES:
        if base_title(o['title']) == bt:
            continue
        text = ' '.join(o['sections'].get('annotation', []) + o['sections'].get('goal', []))
        if f'«{bt}»' in text or f'"{bt}"' in text:
            back.append(base_title(o['title']))
    back = sorted(set(back))
    if back:
        T.append(f"Другие дисциплины 1 курса, в описании которых упоминается «{bt}»: " + '; '.join(back) + '.')
        S += [(BY_ID[o['id']]['url'], f"{o['title']} — Аннотация/Цель") for o in COURSES
              if base_title(o['title']) in back and base_title(o['title']) != bt][:4]
    return T, S


# ---------- сводные вопросы по всем дисциплинам ----------
def aggregate(q, ql):
    S = [(c['url'], c['title']) for c in COURSES]
    if re.search(r'больше всего кредит|максимальн\w+ (число )?кредит|самы\w+ (трудоемк|больш)', ql):
        cs = [c for c in COURSES if c['credits']]
        m = max(int(c['credits']) for c in cs)
        top = sorted({base_title(c['title']) for c in cs if int(c['credits']) == m})
        return [f"Больше всего кредитов — {m}: " + ', '.join(top) + '.'], [(c['url'], c['title']) for c in cs if int(c['credits']) == m]
    mod = re.search(r'(?:в|во) ([1-4])\s*(?:-?м|-?й)?\s*модул', ql)
    if mod and re.search(r'какие|список|что читается|перечисл', ql):
        n = mod.group(1)
        cs = [c for c in COURSES if re.search(r'(?<!\d)' + n + r'(?!\d)', c['when'].split(',', 1)[1] if ',' in c['when'] else c['when'])
              or re.search(rf'1-4|1-3|1, 2' if n in '12' else r'3, 4', c['when']) and False]
        # аккуратно: разворачиваем диапазоны
        def mods(w):
            w = w.split(',', 1)[1]
            s = set()
            for a, b in re.findall(r'(\d)-(\d)', w):
                s |= set(range(int(a), int(b) + 1))
            s |= {int(x) for x in re.findall(r'(?<![\d-])(\d)(?![\d-])', w)}
            return s
        cs = [c for c in COURSES if int(n) in mods(c['when'])]
        return [f"В {n} модуле читаются ({len(cs)}): " + '; '.join(c['title'] for c in cs) + '.'], [(c['url'], c['title']) for c in cs][:8]
    if re.search(r'сколько (всего )?(дисциплин|курсов)|список дисциплин|какие дисциплин', ql) and not re.search(r'связ|реквизит', ql):
        return [f"Для 1 курса в 2026/27 найдено {len(COURSES)} страниц дисциплин (включая углублённые и индустриальные варианты): "
                + '; '.join(c['title'] for c in COURSES) + '.'], S[:6]
    if re.search(r'сумм\w+ кредит|всего кредит|общее (число|количество) кредит', ql):
        t = sum(int(c['credits']) for c in COURSES if c['credits'] and base_title(c['title']) == c['title'])
        return [f"Сумма кредитов базовых (не углублённых) дисциплин с указанным числом кредитов: {t}. "
                f"У части дисциплин (физкультура, ИИ-грамотность, English Integrative Exam) число кредитов на странице не указано, "
                f"поэтому это нижняя оценка, а не официальный итог."], S[:4]
    return None


# ---------- основной вход ----------
NO_ANS = "В найденных материалах (страницы дисциплин 1 курса ОП ИВТ, 2026/27) ответа на этот вопрос нет."


def answer(q, use_llm=False):
    ql = q.lower().replace('ё', 'е')
    ids, defaulted = find_courses(q)
    intents = intent_of(q)
    note = ''
    if not ids:
        agg = aggregate(q, ql)
        if agg:
            return fmt(agg[0], agg[1])
    texts, sources = [], []
    if ids:
        for cid in ids:
            c = BY_ID[cid]
            if intents:
                t, s = answer_for_course(c, intents, q, ql)
            else:
                t, s = [], []
            if t:
                texts += t; sources += s
        if defaulted and len({base_title(BY_ID[i]['title']) for i in ids}) == len(ids):
            alts = [c for c in COURSES if base_title(c['title']) in [base_title(BY_ID[i]['title']) for i in ids] and c['id'] not in ids]
            if alts:
                note = "Есть также вариант: " + '; '.join(a['title'] for a in alts) + " — уточните, если нужен он."
    if not texts:  # свободный поиск
        hits = retrieve(q, ids or None, k=3)
        if not hits or hits[0][0] < (4.0 if not ids else 2.5):
            return fmt([NO_ANS], [])
        qt = set(toks(q))
        for sc, ch in hits[:2]:
            c = BY_ID[ch['cid']]
            ss = sorted(sentences(ch['text']) or [ch['text']], key=lambda s: -len(qt & set(toks(s))))
            texts.append(f"{c['title']} ({SEC_NAME[ch['sec']]}): " + short(' '.join(ss[:2]), 380))
            sources.append(src(c, ch['sec']))
        texts.insert(0, "Прямого ответа не найдено; ближайшие по смыслу фрагменты:")
    if note:
        texts.append(note)
    if use_llm:
        texts = llm_rewrite(q, texts) or texts
    return fmt(texts, sources)


def fmt(texts, sources):
    seen, srcs = set(), []
    for u, t in sources:
        if u not in seen:
            seen.add(u); srcs.append((u, t))
    return dict(text='\n'.join(texts), sources=srcs)


def llm_rewrite(q, texts):
    """Необязательный шаг: сжатие/перефразирование найденного текста внешней LLM (Anthropic API). Только по найденному."""
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return None
    import requests
    body = dict(model='claude-haiku-5-5', max_tokens=500,
                system='Отвечай кратко по-русски ТОЛЬКО на основе переданных фрагментов. Если ответа во фрагментах нет — скажи об этом.',
                messages=[dict(role='user', content='Фрагменты:\n' + '\n'.join(texts) + f'\n\nВопрос: {q}')])
    r = requests.post('https://api.anthropic.com/v1/messages', json=body, timeout=60,
                      headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
    return [r.json()['content'][0]['text']] if r.ok else None


def render(res):
    out = res['text']
    if res['sources']:
        out += '\n\nИсточники:\n' + '\n'.join(f'  [{i}] {t} — {u}' for i, (u, t) in enumerate(res['sources'], 1))
    return out


if __name__ == '__main__':
    use_llm = '--llm' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--llm']
    if args:
        print(render(answer(' '.join(args), use_llm)))
    else:
        print('Помощник по дисциплинам 1 курса ОП ИВТ. Пустая строка — выход.')
        while True:
            q = input('\nВопрос> ').strip()
            if not q:
                break
            print(render(answer(q, use_llm)))
