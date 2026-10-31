"""Strict provider IDs. Private lecture URLs never enter the public site catalog."""
import re
from urllib.parse import urlsplit, parse_qs


def source(provider, url):
    if provider not in ('youtube','vimeo') or not isinstance(url,str):
        raise ValueError('영상 제공자 확인')
    p=urlsplit(url.strip())
    if p.scheme!='https' or p.username or p.password or p.port or p.fragment:
        raise ValueError('HTTPS 영상 주소만 등록해 주세요.')
    host=p.hostname
    if provider=='youtube':
        if host=='youtu.be': ident=p.path.lstrip('/')
        elif host in ('www.youtube.com','youtube.com') and p.path=='/watch': ident=parse_qs(p.query).get('v',[''])[0]
        else: raise ValueError('유튜브 영상 주소 확인')
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident): raise ValueError('유튜브 영상 ID 확인')
        return ident,''
    if host not in ('vimeo.com','www.vimeo.com','player.vimeo.com'): raise ValueError('Vimeo 주소 확인')
    m=re.fullmatch(r'/(?:video/)?([0-9]{6,12})(?:/([A-Za-z0-9]{6,32}))?/?',p.path)
    if not m: raise ValueError('Vimeo 영상 ID 확인')
    privacy=m[2] or parse_qs(p.query).get('h',[''])[0]
    if privacy and not re.fullmatch(r'[A-Za-z0-9]{6,32}',privacy): raise ValueError('Vimeo 비공개 주소 확인')
    return m[1],privacy


def embed(provider, ident, privacy=''):
    if provider=='youtube' and re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):
        return 'https://www.youtube-nocookie.com/embed/'+ident+'?rel=0'
    if provider=='vimeo' and re.fullmatch(r'[0-9]{6,12}',ident) and (not privacy or re.fullmatch(r'[A-Za-z0-9]{6,32}',privacy)):
        return 'https://player.vimeo.com/video/'+ident+('?h='+privacy if privacy else '')
    raise ValueError('등록 영상 식별자 확인')
