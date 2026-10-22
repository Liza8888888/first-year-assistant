import requests, re, os, time
urls = """1197128571 1197128589 1197128565 1197128597 1163619150 1197128541 1197128645 1163619144 1197128559 1197128613 1197128577 1197128605 1163619176 1197128535 1197128637 1197128651 1163619130 1163619170 1197128547 1197128621 1197128553 1197128629 1197128657 1197128896 1163619156""".split()
H={'User-Agent':'Mozilla/5.0'}
for i in urls:
    r=requests.get(f'https://www.hse.ru/ba/isct/courses/{i}.html',headers=H,timeout=30)
    open(f'raw/{i}.html','w',encoding='utf-8').write(r.text)
    t=re.search(r'<title>(.*?)</title>',r.text,re.S)
    print(i,r.status_code,len(r.text),t.group(1).strip()[:90] if t else '')
    time.sleep(0.5)
r=requests.get('https://www.hse.ru/ba/isct/courses?course=1.1.1.4&page=1&year=2026',headers=H,timeout=30)
open('raw/list.html','w',encoding='utf-8').write(r.text); print('list',r.status_code,len(r.text))
