"""Package the classroom review as a static site for an access-restricted host (Cloudflare Pages behind Cloudflare Access).
Same file allowlist and headers as serve.py; nothing outside the allowlist is copied. Output dir is regenerated from scratch.
Usage: build_static.py --config PRIVATE_CONFIG.json --out DIR [--guide review|public] [--profile current|minimal] [--reviewer EMAIL ...]"""
import argparse
import json
import shutil
from pathlib import Path

WEB = Path(__file__).resolve().parent
REPO = WEB.parents[1]
FILES = {
    'navigation.js': REPO / 'assets/navigation.js',
    'index.html': WEB / 'index.html', 'app.js': WEB / 'dist/app.js', 'app.js.LEGAL.txt': WEB / 'dist/app.js.LEGAL.txt',
    'brand.css': REPO / 'assets/site.css', 'tokens.css': REPO / 'assets/tokens.css', 'fonts-display.css': REPO / 'assets/fonts-display.css',
    'trial.css': REPO / 'classroom/trial.css', 'member.css': WEB / 'member.css', 'guide.css': WEB / 'guide.css',
    'assets/brand.css': REPO / 'assets/brand.css', 'assets/somnium_wordmark_on_paper.svg': REPO / 'assets/somnium_wordmark_on_paper.svg',
    'assets/SomniumDisplay.woff2': REPO / 'assets/SomniumDisplay.woff2',
    'SomniumDisplay.woff2': REPO / 'assets/SomniumDisplay.woff2',  # brand.css / site.css resolve ./SomniumDisplay.woff2 from the site root
}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' https://i.ytimg.com; font-src 'self'; "
       "connect-src 'self' https://jdfrottxrdhglxtqvtyx.supabase.co; frame-src https://www.youtube-nocookie.com https://player.vimeo.com; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
HEADERS = f"""/*
  Cache-Control: no-store
  X-Robots-Tag: noindex, nofollow, noarchive
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Cross-Origin-Resource-Policy: same-origin
  Content-Security-Policy: {CSP}
"""


def build(config_path, out, guide='review', profile='minimal', reviewers=(), public=False):
    private = json.loads(Path(config_path).read_text())
    if private.get('url') != 'https://jdfrottxrdhglxtqvtyx.supabase.co' or not private.get('publishableKey', '').startswith('sb_publishable_'):
        raise ValueError('Expected Somnium test project and publishable client key')
    guide_html = WEB / 'dist' / f'guide-{guide}.html'
    if not guide_html.is_file():
        raise FileNotFoundError(f'{guide_html} missing; run npm run build:all first')
    if out.exists():
        shutil.rmtree(out)
    for rel, src in {**FILES, 'guide/index.html': guide_html}.items():
        if not src.is_file():
            if rel.endswith('.LEGAL.txt'):
                continue
            raise FileNotFoundError(src)
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / rel)
    for font in (REPO / 'assets/fonts').glob('*.woff2'):
        for base in ('fonts', 'assets/fonts'):
            (out / base).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(font, out / base / font.name)
    for font in (REPO / 'assets/fonts/display').glob('*.woff2'):  # fonts-display.css loads ./fonts/display/*
        (out / 'fonts/display').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(font, out / 'fonts/display' / font.name)
    config = {k: private[k] for k in ('url', 'publishableKey')}
    # UI review restriction only; real access control is the host's Access policy plus Auth/RLS.
    config['testEmails'] = sorted({'agit.somnium@gmail.com', *reviewers})
    if public:
        config['openSignup'] = True  # public site: any e-mail may sign up; membership still needs a supporter confirmation or a series code
    config['profileMode'] = profile
    (out / 'runtime-config.json').write_text(json.dumps(config))
    (out / '_headers').write_text(HEADERS)
    return sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_file())


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--guide', choices=['review', 'public'], default='review')
    ap.add_argument('--profile', choices=['current', 'minimal'], default='minimal')
    ap.add_argument('--reviewer', action='append', default=[])
    ap.add_argument('--public', action='store_true', help='open sign-up to any e-mail (production host); requires --guide public')
    a = ap.parse_args()
    if a.public and a.guide != 'public':
        ap.error('--public requires --guide public')
    for name in build(a.config, a.out, a.guide, a.profile, a.reviewer, a.public):
        print(name)
