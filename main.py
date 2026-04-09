import os, json, datetime, requests, xml.etree.ElementTree as ET, subprocess, sys, re
from pathlib import Path


def fetch_reddit(limit=20):
    subreddits = ['Genshin_Impact', 'GenshinImpactTips', 'Genshin_Lore']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml',
    }
    posts = []
    ns = 'http://www.w3.org/2005/Atom'
    media_ns = 'http://search.yahoo.com/mrss/'
    per_sub = max(limit, 25)
    for sub in subreddits:
        try:
            resp = requests.get(
                'https://www.reddit.com/r/' + sub + '/hot.rss?limit=' + str(per_sub),
                headers=headers, timeout=15)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            entries = root.findall('{' + ns + '}entry')
            for entry in entries:
                title_el = entry.find('{' + ns + '}title')
                link_el = entry.find('{' + ns + '}link')
                if title_el is None or link_el is None:
                    continue
                thumb = None
                thumb_el = entry.find('{' + media_ns + '}thumbnail')
                if thumb_el is not None:
                    thumb = thumb_el.get('url')
                posts.append({
                    'title': title_el.text or '',
                    'url': link_el.get('href', ''),
                    'score': 0, 'comments': 0,
                    'source': 'r/' + sub, 'platform': 'Reddit', 'thumb': thumb,
                })
        except Exception as e:
            print('Reddit error (' + sub + '): ' + str(e))
    seen, deduped = set(), []
    for p in posts:
        if p['url'] not in seen:
            seen.add(p['url'])
            deduped.append(p)
    return deduped[:limit]


def fetch_hoyolab(limit=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
        'Accept': 'application/json',
        'x-rpc-client_type': '4', 'x-rpc-app_version': '1.5.0',
        'x-rpc-language': 'en-us',
        'Origin': 'https://www.hoyolab.com', 'Referer': 'https://www.hoyolab.com/',
    }
    posts = []
    last_id = ''
    while len(posts) < limit:
        try:
            resp = requests.get(
                'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList',
                params={'gids': 2, 'last_id': last_id, 'page_size': min(limit, 20), 'type': 3},
                headers=headers, timeout=15)
            data = resp.json()
            if data.get('retcode') != 0:
                break
            raw_list = (data.get('data') or {}).get('list') or []
            if not raw_list:
                break
            for item in raw_list:
                post = item.get('post', {})
                stat = item.get('stat', {})
                image_list = item.get('image_list') or []
                cover = image_list[0].get('url') if image_list else (post.get('cover') or None)
                posts.append({
                    'title': post.get('subject', '(no title)'),
                    'url': 'https://www.hoyolab.com/article/' + str(post.get('post_id')),
                    'score': stat.get('like_num', 0), 'comments': stat.get('reply_num', 0),
                    'source': 'HoYoLAB', 'platform': 'HoYoLAB', 'thumb': cover,
                })
            if (data.get('data') or {}).get('is_last', True):
                break
            last_id = (data.get('data') or {}).get('last_id', '')
        except Exception as e:
            print('HoYoLAB error: ' + str(e))
            break
    posts.sort(key=lambda x: x['score'], reverse=True)
    print('HoYoLAB list length: ' + str(len(posts[:limit])))
    return posts[:limit]


def fetch_youtube(limit=20):
    posts = []
    try:
        fetch_count = limit * 3
        result = subprocess.run(
            [sys.executable, '-m', 'yt_dlp',
             '--dump-json', '--flat-playlist', '--no-download',
             '--playlist-end', str(fetch_count),
             '--default-search', 'ytsearch' + str(fetch_count),
             'genshin impact'],
            capture_output=True, text=True, timeout=120)
        items = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                item = json.loads(line)
                thumbnails = item.get('thumbnails') or []
                thumb = thumbnails[-1].get('url') if thumbnails else item.get('thumbnail')
                items.append({
                    'title': item.get('title', '(no title)'),
                    'url': 'https://www.youtube.com/watch?v=' + item.get('id', ''),
                    'score': item.get('view_count') or 0, 'comments': 0,
                    'source': item.get('channel') or item.get('uploader') or 'YouTube',
                    'platform': 'YouTube', 'thumb': thumb,
                })
            except Exception:
                continue
        items.sort(key=lambda x: x['score'], reverse=True)
        posts = items[:limit]
        print('YouTube list length: ' + str(len(posts)))
    except Exception as e:
        print('YouTube error: ' + str(e))
    return posts


def fetch_bilibili(limit=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com',
        'Cookie': 'buvid3=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee12345infoc',
    }
    posts = []
    try:
        resp = requests.get(
            'https://api.bilibili.com/x/web-interface/search/type',
            params={'search_type': 'video', 'keyword': '原神', 'order': 'click',
                    'page': 1, 'page_size': limit},
            headers=headers, timeout=15)
        data = resp.json()
        print('Bilibili code: ' + str(data.get('code')))
        results = (data.get('data') or {}).get('result') or []
        print('Bilibili list length: ' + str(len(results)))
        for item in results:
            # Strip HTML tags from title
            title = re.sub(r'<[^>]+>', '', item.get('title', '(no title)'))
            bvid = item.get('bvid', '')
            aid = item.get('aid', '')
            url = ('https://www.bilibili.com/video/' + bvid) if bvid else ('https://www.bilibili.com/video/av' + str(aid))
            thumb = item.get('pic', '')
            if thumb and thumb.startswith('//'):
                thumb = 'https:' + thumb
            play = item.get('play', 0)
            if isinstance(play, str):
                play = int(play.replace(',', '')) if play.replace(',', '').isdigit() else 0
            posts.append({
                'title': title,
                'url': url,
                'score': play,
                'comments': item.get('review', 0),
                'source': item.get('author', 'Bilibili'),
                'platform': 'Bilibili',
                'thumb': thumb,
            })
    except Exception as e:
        print('Bilibili error: ' + str(e))
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:limit]


COLORS = {'Reddit': '#FF4500', 'HoYoLAB': '#1A9DD9', 'YouTube': '#FF0000', 'Bilibili': '#00A1D6'}


def fmt_score(p):
    score = p['score']
    platform = p['platform']
    if platform in ('YouTube', 'Bilibili') and score:
        if score >= 1000000:
            return str(round(score / 1000000, 1)) + 'M'
        elif score >= 1000:
            return str(round(score / 1000, 1)) + 'K'
        return str(score)
    return str(score) if score else '-'


def card(p):
    c = COLORS.get(p['platform'], '#888')
    img = '<img src="' + p['thumb'] + '" alt="" loading="lazy">' if p.get('thumb') else ''
    title = p['title'].replace('<', '&lt;').replace('>', '&gt;')
    icon = '▶️ ' if p['platform'] in ('YouTube', 'Bilibili') else '👍 '
    meta = '<span>' + icon + fmt_score(p) + '</span>'
    if p['platform'] not in ('YouTube', 'Bilibili') and p['comments']:
        meta += '<span>💬 ' + str(p['comments']) + '</span>'
    return (
        '<a class="card" href="' + p['url'] + '" target="_blank">' +
        img + '<div class="card-body">' +
        '<span class="badge" style="background:' + c + '">' + p['platform'] + ' &middot; ' + p['source'] + '</span>' +
        '<p class="card-title">' + title + '</p>' +
        '<div class="card-meta">' + meta + '</div>' +
        '</div></a>'
    )


def section(title, posts, icon):
    if not posts:
        return '<section><h2>' + icon + ' ' + title + '</h2><p class="empty">No data this week.</p></section>'
    cards = '\n'.join(card(p) for p in posts)
    return '<section><h2>' + icon + ' ' + title + '</h2><div class="grid">' + cards + '</div></section>'


def generate_html(reddit, hoyolab, youtube, bilibili):
    now = datetime.datetime.utcnow()
    week = now.strftime('%B %d, %Y')
    updated = now.strftime('%Y-%m-%d %H:%M UTC')
    body = '\n'.join([
        section('Reddit Highlights', reddit, '🟠'),
        section('HoYoLAB Hot Posts', hoyolab, '🌟'),
        section('YouTube Trending', youtube, '▶️'),
        section('Bilibili 热门', bilibili, '🔵'),
    ])
    css = (
        '*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }'
        'body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f0f1a; color: #e8e8f0; }'
        'header { background: linear-gradient(135deg, #1a1040, #2d1b69); padding: 2rem; text-align: center; border-bottom: 1px solid #3d2d80; }'
        'header h1 { font-size: 2rem; color: #c8a8ff; }'
        'header p { color: #a090c0; margin-top: .4rem; font-size: .9rem; }'
        'main { max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }'
        'section { margin-bottom: 3rem; }'
        'section h2 { font-size: 1.3rem; color: #d0b0ff; margin-bottom: 1rem; border-left: 3px solid #7c5cbf; padding-left: .75rem; }'
        '.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }'
        '.card { background: #1a1a2e; border: 1px solid #2d2d4e; border-radius: 10px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .15s, border-color .15s; display: flex; flex-direction: column; }'
        '.card:hover { transform: translateY(-3px); border-color: #7c5cbf; }'
        '.card img { width: 100%; height: 160px; object-fit: cover; display: block; }'
        '.card-body { padding: .9rem; flex: 1; display: flex; flex-direction: column; gap: .5rem; }'
        '.badge { font-size: .72rem; font-weight: 600; color: #fff; padding: .2rem .5rem; border-radius: 4px; display: inline-block; }'
        '.card-title { font-size: .92rem; line-height: 1.45; flex: 1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }'
        '.card-meta { font-size: .8rem; color: #8080a0; display: flex; gap: 1rem; }'
        '.empty { color: #606080; font-style: italic; }'
        'footer { text-align: center; padding: 2rem; color: #505070; font-size: .8rem; border-top: 1px solid #2d2d4e; }'
    )
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Genshin Global Digest</title>'
        '<style>' + css + '</style></head><body>'
        '<header><h1>🌙 Genshin Global Digest</h1>'
        '<p>Week of ' + week + ' &middot; Updated ' + updated + '</p></header>'
        '<main>' + body + '</main>'
        '<footer>Auto-generated weekly digest &middot; Reddit &middot; HoYoLAB &middot; YouTube &middot; Bilibili &middot; Personal use only</footer>'
        '</body></html>'
    )


def main():
    print('Fetching Reddit...')
    reddit = fetch_reddit(20)
    print('  ' + str(len(reddit)) + ' posts')

    print('Fetching HoYoLAB...')
    hoyolab = fetch_hoyolab(20)
    print('  ' + str(len(hoyolab)) + ' posts')

    print('Fetching YouTube...')
    youtube = fetch_youtube(20)
    print('  ' + str(len(youtube)) + ' videos')

    print('Fetching Bilibili...')
    bilibili = fetch_bilibili(20)
    print('  ' + str(len(bilibili)) + ' videos')

    html = generate_html(reddit, hoyolab, youtube, bilibili)
    out = Path('docs')
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'data.json').write_text(
        json.dumps({
            'reddit': reddit, 'hoyolab': hoyolab,
            'youtube': youtube, 'bilibili': bilibili,
            'generated_at': datetime.datetime.utcnow().isoformat(),
        }, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print('Done -> docs/index.html')


if __name__ == '__main__':
    main()
