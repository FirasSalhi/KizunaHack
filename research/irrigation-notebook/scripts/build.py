t=open('template.html',encoding='utf-8').read()
d=open('data.json',encoding='utf-8').read().replace('</','<\/')
r=open('ref_cases.json',encoding='utf-8').read().replace('</','<\/')
open('farmlink_banc_essai.html','w',encoding='utf-8').write(t.replace('__DATA__',d).replace('__REF__',r)); print('built')
