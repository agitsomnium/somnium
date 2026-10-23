import argparse, hashlib, html.parser, json, os, re, subprocess, sys
from urllib.parse import urljoin, urlparse, urldefrag

SKIP={'script','style','header','nav','noscript','template'}

def fetch(url):
    r=subprocess.run(['curl','-fLsS','--retry','2','--max-time','45',url],capture_output=True,check=True)
    return r.stdout

class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0; self.text=[]; self.links=[]; self.images=[]; self.title=''; self._t=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in SKIP: self.skip+=1
        if tag=='title': self._t=True
        if tag=='a' and a.get('href'): self.links.append(a['href'])
        if tag=='img':
            if a.get('src'): self.images.append(a['src'])
            if a.get('srcset'):
                for part in a['srcset'].split(','):
                    u=part.strip().split(' ')[0]
                    if u: self.images.append(u)
        st=a.get('style','')
        for m in re.finditer(r'url\(([^)]+)\)',st):
            self.images.append(m.group(1).strip('\'" '))
    def handle_endtag(self,tag):
        if tag in SKIP and self.skip>0: self.skip-=1
        if tag=='title': self._t=False
    def handle_data(self,d):
        if self._t: self.title+=d
        if self.skip==0:
            s=d.strip()
            if s: self.text.append(s)


def parse_page(raw,url):
    txt=raw.decode('utf-8','replace')
    p=P(); p.feed(txt)
    links=[urljoin(url,urldefrag(l)[0]) for l in p.links]
    imgs=[urljoin(url,i) for i in p.images]
    ext=[]
    m=re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',txt,re.S)
    if m:
        try: walk_json(json.loads(m.group(1)),imgs,ext)
        except Exception: pass
    return {'title':p.title.strip(),'text':'\n'.join(p.text),'links':links,'images':imgs,'external':ext}

def walk_json(o, imgs, ext):
    if isinstance(o, dict):
        for v in o.values():
            walk_json(v, imgs, ext)
    elif isinstance(o, list):
        for v in o:
            walk_json(v, imgs, ext)
    elif isinstance(o, str):
        s = o
        if not (s.startswith('https://') or s.startswith('http://')):
            return
        low = s.lower()
        path = urlparse(s).path.lower()
        is_img = bool(re.search(r'\.(png|jpe?g|gif|webp|svg|bmp|ico|avif|tiff?)(\?|$)', path))
        if not is_img and '/image' in path and 'oopy.lazyrockets' in low:
            is_img = True
        if is_img:
            imgs.append(s)
        else:
            ext.append(s)


def crawl(root, outdir):
    os.makedirs(outdir, exist_ok=True)
    assets_dir = os.path.join(outdir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    pages_dir = os.path.join(outdir, 'pages')
    os.makedirs(pages_dir, exist_ok=True)
    next_dir = os.path.join(outdir, 'next')
    os.makedirs(next_dir, exist_ok=True)

    root_host = urlparse(root).netloc

    def canon(u):
        u, _ = urldefrag(u)
        p = urlparse(u)
        path = p.path or '/'
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        return p._replace(path=path, fragment='').geturl()

    def same_host(u):
        return urlparse(u).netloc == root_host

    manifest = {'pages': [], 'assets': [], 'errors': [], 'external_links': [], 'discovered': []}
    seen_pages = set()
    seen_assets = set()
    queue = [canon(root)]
    seen_pages.add(canon(root))
    page_count = 0
    MAX_PAGES = 200

    def save_manifest():
        with open(os.path.join(outdir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)

    def download_asset(u):
        if u in seen_assets:
            return
        seen_assets.add(u)
        try:
            data = fetch(u)
        except Exception as e:
            manifest['errors'].append({'url': u, 'error': str(e)})
            return
        ext = 'bin'
        m = re.search(r'\.([a-zA-Z0-9]{1,8})(?:\?|$)', urlparse(u).path)
        if m:
            ext = m.group(1).lower()
        name = hashlib.sha256(u.encode()).hexdigest()[:16] + '.' + ext
        with open(os.path.join(assets_dir, name), 'wb') as f:
            f.write(data)
        manifest['assets'].append({'url': u, 'file': name, 'size': len(data)})

    while queue and page_count < MAX_PAGES:
        url = queue.pop(0)
        try:
            raw = fetch(url)
        except Exception as e:
            manifest['errors'].append({'url': url, 'error': str(e)})
            save_manifest()
            continue
        try:
            page = parse_page(raw, url)
        except Exception as e:
            manifest['errors'].append({'url': url, 'error': 'parse: ' + str(e)})
            save_manifest()
            continue
        page_count += 1
        title = page.get('title', '')
        text = page.get('text', '')
        links = page.get('links', [])
        images = page.get('images', [])
        external = page.get('external', [])

        next_data = None
        m = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', raw.decode('utf-8', 'replace'), re.S)
        if m:
            try:
                next_data = json.loads(m.group(1))
            except Exception:
                next_data = None

        if next_data:
            nid = hashlib.sha256(url.encode()).hexdigest()[:16]
            with open(os.path.join(next_dir, nid + '.json'), 'w') as f:
                json.dump(next_data, f)
            try:
                blocks = next_data['props']['pageProps']['recordMap']['block']
                for bid, bv in blocks.items():
                    val = bv.get('value', {}) if isinstance(bv, dict) else {}
                    if val.get('type') == 'page' and val.get('parent_id') and val.get('parent_table') == 'block':
                        child = urlparse(url)._replace(path='/' + bid, query='', fragment='').geturl()
                        if same_host(child) and canon(child) not in seen_pages:
                            seen_pages.add(canon(child))
                            queue.append(canon(child))
                            manifest['discovered'].append(child)
            except Exception:
                pass

        for l in links:
            if not l.startswith('http'):
                l = urljoin(url, l)
            if same_host(l):
                c = canon(l)
                if c not in seen_pages:
                    seen_pages.add(c)
                    queue.append(c)
                    manifest['discovered'].append(c)
            else:
                if l not in manifest['external_links']:
                    manifest['external_links'].append(l)

        for img in images:
            download_asset(img)

        pid = hashlib.sha256(url.encode()).hexdigest()[:16]
        with open(os.path.join(pages_dir, pid + '.html'), 'wb') as f:
            f.write(raw)
        with open(os.path.join(pages_dir, pid + '.txt'), 'w') as f:
            f.write(text)

        manifest['pages'].append({
            'url': url, 'title': title, 'sha256': hashlib.sha256(raw).hexdigest(),
            'size': len(raw), 'links': links, 'image_urls': images,
            'text_file': pid + '.txt', 'html_file': pid + '.html'
        })
        save_manifest()
        print(title, 'links=%d images=%d' % (len(links), len(images)), flush=True)

    save_manifest()
    print('pages=%d assets=%d errors=%d external=%d' % (
        len(manifest['pages']), len(manifest['assets']),
        len(manifest['errors']), len(manifest['external_links'])), flush=True)
    return manifest


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='https://somnium.oopy.io/')
    ap.add_argument('--output',required=True)
    a=ap.parse_args()
    crawl(a.root,a.output)

if __name__=='__main__': main()
