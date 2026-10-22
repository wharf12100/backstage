from __future__ import annotations
import os, re, shutil, html
from pathlib import Path
from datetime import datetime, date
from email.utils import format_datetime
from urllib.parse import quote
import yaml, mistune
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
SITE = yaml.safe_load((ROOT / 'site.yml').read_text(encoding='utf8'))
repo = os.getenv('GITHUB_REPOSITORY', 'demo/newsroom-github-starter')
owner, _, repo_name = repo.partition('/')
project = '' if repo_name.lower() == f'{owner.lower()}.github.io' else repo_name
BASE = f'/{project}/' if project else '/'
ORIGIN = os.getenv('SITE_URL', '').strip().rstrip('/')
if not ORIGIN:
    ORIGIN = f'https://{owner}.github.io' + (f'/{project}' if project else '')

def read_post(path):
    raw = path.read_text(encoding='utf8')
    if not raw.startswith('---\n'):
        raise ValueError(f'Missing YAML frontmatter: {path}')
    _, front, body = raw.split('---', 2)
    meta = yaml.safe_load(front) or {}
    if not meta.get('title'):
        raise ValueError(f'Missing title: {path}')
    v = meta.get('date', date.today())
    if isinstance(v, datetime): dt = v
    elif isinstance(v, date): dt = datetime(v.year, v.month, v.day)
    else: dt = datetime.fromisoformat(str(v).replace('Z','+00:00'))
    slug = path.stem
    cover = str(meta.get('cover') or '').strip()
    def url_for_media(url):
        if not url: return ''
        if url.startswith(('https://','http://','data:')): return url
        return url if url.startswith(BASE) else BASE + url.lstrip('/')
    rendered = mistune.create_markdown(plugins=['table', 'strikethrough', 'url'])(body)
    rendered = re.sub(r'(?P<attr>(?:src|href))="/(?P<path>(?!/)[^"]+)"', lambda m: f'{m.group("attr")}="{BASE}{m.group("path")}"' if not m.group('path').startswith(BASE.lstrip('/')) else m.group(0), rendered)
    return dict(title=str(meta['title']),subtitle=str(meta.get('subtitle') or ''),date=dt,date_label=f'{dt.year}.{dt.month:02d}.{dt.day:02d}',category=str(meta.get('category') or '其他'),author=str(meta.get('author') or '編輯部'),summary=str(meta.get('summary') or body[:110].replace('\n',' ')),cover=cover,cover_url=url_for_media(cover),cover_caption=str(meta.get('cover_caption') or ''),slug=slug,featured=meta.get('featured') is True,html=rendered)

def render(template, destination, **ctx):
    dest = DIST / destination
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(env.get_template(template).render(site=SITE,base=BASE,year=datetime.now().year,**ctx),encoding='utf8')

def main():
    global env
    if DIST.exists(): shutil.rmtree(DIST)
    shutil.copytree(ROOT / 'static', DIST)
    (DIST / '.nojekyll').touch()
    env = Environment(loader=FileSystemLoader(ROOT / 'src/templates'),autoescape=select_autoescape(['html']))
    all_posts = sorted((read_post(p) for p in (ROOT/'content/posts').glob('*.md')),key=lambda p:p['date'],reverse=True)
    posts = sorted(all_posts,key=lambda p:(p['featured'],p['date']),reverse=True)
    render('index.html','index.html',posts=posts,today=date.today().strftime('%Y / %m / %d'))
    for p in all_posts:
        canonical = ORIGIN + f'/posts/{quote(p["slug"])}/'
        p['canonical_cover'] = (ORIGIN.split('/',3)[0]+'//'+ORIGIN.split('/')[2]+p['cover_url']) if p['cover_url'].startswith('/') else p['cover_url']
        render('article.html',f'posts/{p["slug"]}/index.html',post=p,canonical=canonical)
    for c in SITE.get('categories',[]):
        render('category.html',f'category/{quote(c,safe="")}/index.html',category=c,posts=[p for p in all_posts if p['category']==c])
    proxy = os.getenv('CMS_OAUTH_BASE_URL','').strip().rstrip('/')
    backend = 'backend:\n  name: github\n  repo: '+repo+'\n  branch: main\n'
    if proxy: backend += '  base_url: '+proxy+'\n  auth_endpoint: /auth\n'
    config = backend + '''\nlocale: zh_Hant\nmedia_folder: static/assets/uploads\npublic_folder: "''' + BASE + '''assets/uploads"\npublish_mode: editorial_workflow\ncollections:\n  - name: posts\n    label: 新聞文章\n    label_singular: 文章\n    folder: content/posts\n    create: true\n    delete: true\n    extension: md\n    format: frontmatter\n    slug: "{{year}}-{{month}}-{{day}}-{{slug}}"\n    summary: "{{title}}｜{{category}}｜{{date}}"\n    sortable_fields: [date, title]\n    fields:\n      - { label: 標題, name: title, widget: string }\n      - { label: 副標題, name: subtitle, widget: string, required: false }\n      - { label: 發布時間, name: date, widget: datetime, format: 'YYYY-MM-DD HH:mm', date_format: 'YYYY-MM-DD', time_format: 'HH:mm' }\n      - label: 分類\n        name: category\n        widget: select\n        options: [社會, 政治, 國際, 文化, 深度報導]\n      - { label: 作者, name: author, widget: string, default: 編輯部 }\n      - { label: 摘要, name: summary, widget: text, hint: 顯示於首頁文章卡片與搜尋摘要 }\n      - { label: 封面圖片, name: cover, widget: image, required: false }\n      - { label: 封面圖說, name: cover_caption, widget: string, required: false }\n      - { label: 設為焦點, name: featured, widget: boolean, default: false, required: false }\n      - { label: 文章內文, name: body, widget: markdown }\n'''
    (DIST/'admin/config.yml').write_text(config,encoding='utf8')
    (DIST/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n',encoding='utf8')
    urls = [ORIGIN+'/', *(ORIGIN+f'/posts/{quote(p["slug"])}/' for p in all_posts),*(ORIGIN+'/category/'+quote(c,safe='')+'/' for c in SITE.get('categories',[]))]
    (DIST/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+html.escape(u)+'</loc></url>' for u in urls)+'</urlset>',encoding='utf8')
    items=[]
    for p in all_posts[:20]:
        link=ORIGIN+f'/posts/{quote(p["slug"])}/'
        items.append('<item><title>'+html.escape(p['title'])+'</title><link>'+html.escape(link)+'</link><guid>'+html.escape(link)+'</guid><description>'+html.escape(p['summary'])+'</description></item>')
    (DIST/'feed.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>'+html.escape(SITE['name'])+'</title><link>'+html.escape(ORIGIN)+'</link><description>'+html.escape(SITE['description'])+'</description>'+''.join(items)+'</channel></rss>',encoding='utf8')
    print(f'Generated {len(all_posts)} articles at {DIST}, base={BASE}, repo={repo}')
    if not proxy: print('NOTICE: CMS_OAUTH_BASE_URL is unset; configure OAuth proxy to enable admin login.')

if __name__ == '__main__': main()
