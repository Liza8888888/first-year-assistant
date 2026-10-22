import glob, json, os
from bs4 import BeautifulSoup
ALIAS = {'Аннотация':'annotation','Abstract':'annotation',
 'Цель освоения дисциплины':'goal','Learning Objectives':'goal',
 'Планируемые результаты обучения':'results','Expected Learning Outcomes':'results',
 'Содержание учебной дисциплины':'content','Course Contents':'content',
 'Элементы контроля':'controls','Assessment Elements':'controls',
 'Промежуточная аттестация':'formula','Interim Assessment':'formula',
 'Список литературы':'literature','Bibliography':'literature',
 'Авторы':'authors','Authors':'authors'}
SKIP = {'Программа дисциплины','Дополнительные материалы в LMS','Задать вопрос','Course Syllabus','Full Syllabus','Ask Question'}
courses=[]
for f in sorted(glob.glob('raw/1*.html')):
    cid=os.path.basename(f)[:-5]
    s=BeautifulSoup(open(f,encoding='utf-8').read(),'lxml')
    L=[x.strip() for x in s.get_text('\n',strip=True).split('\n') if x.strip()]
    i=next(k for k,x in enumerate(L) if x=='2026/2027' and L[k+1]=='Учебный год')
    title=L[i-1]
    e=next(k for k in range(i,len(L)) if L[k].startswith('Национальный исследовательский университет «Высшая') and k>i)
    body=L[i:e]
    def after(key):
        return body[body.index(key)+1]
    meta=dict(lang=body[2], credits=(body[body.index('Кредиты')-1] if 'Кредиты' in body else None))
    meta['dept']=after('Кто читает:'); meta['status']=after('Статус:'); meta['when']=after('Когда читается:')
    k0=next((k for k,x in enumerate(body) if x in ('Преподаватели','Преподаватель','Course Syllabus')),None)
    if k0 is None: k0=next(k for k,x in enumerate(body) if x=='Программа дисциплины')
    first=next(k for k,x in enumerate(body) if x in ALIAS)
    teachers=[x for x in body[k0+1:first] if x not in SKIP and x not in ALIAS]
    if body[k0] in ('Course Syllabus','Программа дисциплины'): teachers=[]
    pos=[];seen=set()
    for k,x in enumerate(body):
        if x in ALIAS and ALIAS[x] not in seen and k>=k0:
            seen.add(ALIAS[x]); pos.append((k,ALIAS[x]))
    secs={}
    for n,(k,name) in enumerate(pos):
        en=pos[n+1][0] if n+1<len(pos) else len(body)
        secs[name]=body[k+1:en]
    # drop Russian-site boilerplate "Авторы" for English; keep
    courses.append(dict(id=cid,url=f'https://www.hse.ru/ba/isct/courses/{cid}.html',title=title,teachers=teachers,**meta,sections=secs))
json.dump(courses,open('courses.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for c in courses: print(c['id'],c['title'],'|',c['credits'],'|',c['when'],'|',c['status'],'|',c['lang'],'|',len(c['teachers']),'|',','.join(c['sections']))
