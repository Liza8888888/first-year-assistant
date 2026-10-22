"""Прогон тестов и генерация файла QA.md с вопросами, ответами, источниками и автоматической проверкой."""
import sys, tests
from assistant import answer

USE_LLM = '--llm' in sys.argv


def run(q):
    r = answer(q, USE_LLM)
    ids = [u.rsplit('/', 1)[-1][:-5] for u, _ in r['sources']]
    return r, ids


def block(i, q, r, verdict, note):
    s = [f"### {i}. {q}", '', f"**Проверка:** {verdict}  ", f"*{note}*", '', '**Ответ помощника:**', '']
    s += ['> ' + ln if ln else '>' for ln in r['text'].split('\n')]
    s += ['', '**Источники:**'] + ([f"- [{t}]({u})" for u, t in r['sources']] or ['- (нет)']) + ['']
    return '\n'.join(s)


out = ['# Тестовые вопросы к помощнику по дисциплинам 1 курса ОП «Информатика и вычислительная техника» (2026/27)', '',
       'Ответы получены запуском `assistant.py` (режим без LLM — извлекающий ответ из страниц hse.ru). '
       'Колонка «Проверка» — автоматическая: для рабочих вопросов ожидаемые подстроки найдены в ответе и среди источников есть нужная страница; '
       'для проблемных — подтверждено, что корректного ответа в выдаче **нет**.', '']
ok = 0
out += ['## Часть 1. Вопросы, демонстрирующие работоспособность', '']
parts = []
for i, (q, must, cid, note) in enumerate(tests.WORK, 1):
    r, ids = run(q)
    good = all(m in r['text'] for m in must) and (cid is None or tests.ID[cid] in ids)
    ok += good
    parts.append(block(i, q, r, '✅ пройдена' if good else '❌ НЕ пройдена', 'Что проверяет: ' + note))
out += [f'Пройдено автоматическую проверку: **{ok} из {len(tests.WORK)}**.', ''] + parts
confirmed = 0
parts = []
for i, (q, corr, mode, cat, why) in enumerate(tests.FAIL, 1):
    r, ids = run(q)
    correct = all(c in ids for c in corr) if mode == 'src' else all(c in r['text'] for c in corr)
    confirmed += (not correct)
    parts.append(block(i, q, r, '⚠️ ошибка подтверждена' if not correct else '✅ (ошибки не возникло)', f'Категория: {cat}. Почему: {why}'))
out += ['', '## Часть 2. Вопросы, демонстрирующие недостатки решения', '',
        f'Ошибка подтверждена на **{confirmed} из {len(tests.FAIL)}** вопросов.', ''] + parts
open('QA.md', 'w', encoding='utf-8').write('\n'.join(out))
print('work ok', ok, '/', len(tests.WORK), '| fail confirmed', confirmed, '/', len(tests.FAIL))
for i, (q, corr, mode, cat, why) in enumerate(tests.FAIL, 1):
    r, ids = run(q)
    correct = all(c in ids for c in corr) if mode == 'src' else all(c in r['text'] for c in corr)
    if correct:
        print('NOT FAILING:', q)
for q, must, cid, note in tests.WORK:
    r, ids = run(q)
    if not (all(m in r['text'] for m in must) and (cid is None or tests.ID[cid] in ids)):
        print('WORK FAILED:', q, '\n', r['text'][:300])
