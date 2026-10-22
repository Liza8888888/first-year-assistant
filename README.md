# Помощник по дисциплинам 1 курса ОП ИВТ (НИУ ВШЭ, 2026/27)

    pip install requests beautifulsoup4 snowballstemmer python-pptx
    python fetch.py && python parse.py        # скачать страницы -> courses.json
    python assistant.py "Как считается оценка по матану?"   # один вопрос (без аргумента — диалог)
    python run_tests.py                       # перегенерировать QA.md
    python build_pptx.py                      # перегенерировать Presentation.pptx

Необязательно: `--llm` + переменная `ANTHROPIC_API_KEY` — пересказ найденных фрагментов моделью (в тестах не использовалось).
