import os, json, datetime, requests, subprocess, xml.etree.ElementTree as ET
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
    for sub in subreddits:
        try:
            resp = requests.get(
                'https://www.reddit.com/r/' + sub + '/hot.rss?limit=' + str(limit),
                headers=headers, timeout=15)
            if resp.status_code != 200:
                print('Reddit ' + sub + ' status: ' + str(resp.status_code))
                continue
            root = ET.fromstring(resp.content)
            entries = root.findall('{' + ns + '}entry')
            for entry in entries:
                title_el = entry.find('{' + ns + '}title')
                link_el = entry.find('{' + ns + '}link')
                if title_el is None or link_el is None:
                    continue
                title = title_el.text or ''
                url = link_el.get('href', '')
                # try to get thumbnail from media:thumbnail
                thumb = None
                thumb_el = entry.find('{' + media_ns + '}thumbnail')
                if thumb_el is not None:
                    thumb = thumb_el.get('url')
                posts.append({
                    'title': title,
                    'url': url,
                    'score': 0,
                    'comments': 0,
                    'source': 'r/' + sub,
                    'platform': 'Reddit',
                    'thumb': thumb,
                })
        except Exception as e:
            print('Reddit error (' + sub + '): ' + str(e))
    return posts[:20]


def fetch_hoyolab(limit=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
        'Accept': 'application/json',
        'x-rpc-client_type': '4',
        'x-rpc-app_version': '1.5.0',
        'x-rpc-language': 'en-us',
        'Origin': 'https://www.hoyolab.com',
        'Referer': 'https://www.hoyolab.com/',
    }
    posts = []
    try:
        resp = requests.get(
            'https://bbs-api-os.hoyolab.com/community/post/wapi/getForumPostList',
            params={'forum_id': 29, 'is_good': 'false', 'is_hot': 'true',
                    'page_size': limit, 'gids': 2},
            headers=headers, timeout=15)
        print('HoYoLAB status: ' + str(resp.status_code))
        data = resp.json()
        print('HoYoLAB retcode: ' + str(data.get('retcode')))
        raw_list = (data.get('data') or {}).get('posts') or []
        print('HoYoLAB list length: ' + str(len(raw_list)))
        for item in raw_list:
            post = item.get('post', {})
            stat = item.get('stat', {})
            image_list = item.get('image_list') or []
            cover = image_list[0].get('url') if image_list else None
            posts.append({
                'title': post.get('subject', '(no title)'),
                'url': 'https://www.hoyolab.com/article/' + str(post.get('post_id')),
                'score': stat.get('like_num', 0),
                'comments': stat.get('reply_num', 0),
                'source': 'HoYoLAB',
                'platform': 'HoYoLAB',
                'thumb': cover,
            })
    except Exception as e:
        print('HoYoLAB error: ' + str(e))
    return posts


def fetch_youtube(limit=10):
    # Fetch full metadata (no --flat-playlist) so upload_date is available,
    # use --dateafter to let yt-dlp natively filter out old videos.
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=14)).strftime('%Y%m%d')
    try:
        result = subprocess.run(
            ['yt-dlp', '--dump-json', '--no-warnings',
             '--dateafter', cutoff,
             '--playlist-end', '20',
             'ytsearch20:genshin impact'],
            capture_output=True, text=True, timeout=120)
        videos = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                v = json.loads(line)
                vid_id = v.get('id', '')
                thumb = v.get('thumbnail') or (
                    'https://i.ytimg.com/vi/' + vid_id + '/hqdefault.jpg' if vid_id else None)
                videos.append({
                    'title': v.get('title', '(no title)'),
                    'url': 'https://www.youtube.com/watch?v=' + vid_id,
                    'score': v.get('view_count') or 0,
                    'comments': 0,
                    'source': v.get('channel', 'YouTube'),
                    'platform': 'YouTube',
                    'thumb': thumb,
                })
            except Exception:
                continue
        videos.sort(key=lambda x: x['score'], reverse=True)
        print('YouTube: ' + str(len(videos)) + ' videos within 14 days')
        return videos[:limit]
    except Exception as e:
        print('YouTube error: ' + str(e))
        return []


def fetch_vk(limit=15):
    token = os.environ.get('VK_SERVICE_TOKEN', '')
    if not token:
        return []
    groups = ['genshin_impact_ru', 'genshin.impact.official']
    posts = []
    for group in groups:
        try:
            resp = requests.get('https://api.vk.com/method/wall.get', params={
                'domain': group, 'count': limit, 'access_token': token,
                'v': '5.131', 'filter': 'owner'}, timeout=10)
            data = resp.json()
            if 'response' not in data:
                continue
            for item in data['response']['items']:
                text = item.get('text', '').strip()
                if not text:
                    continue
                thumb = None
                for att in item.get('attachments', []):
                    if att.get('type') == 'photo':
                        sizes = att['photo'].get('sizes', [])
                        if sizes:
                            thumb = sizes[-1]['url']
                        break
                posts.append({
                    'title': text[:200] + ('...' if len(text) > 200 else ''),
                    'url': 'https://vk.com/wall' + str(item['owner_id']) + '_' + str(item['id']),
                    'score': item.get('likes', {}).get('count', 0),
                    'comments': item.get('comments', {}).get('count', 0),
                    'source': group,
                    'platform': 'VK',
                    'thumb': thumb,
                })
        except Exception as e:
            print('VK error: ' + str(e))
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:10]


COLORS = {'Reddit': '#FF4500', 'VK': '#0077FF', 'HoYoLAB': '#1A9DD9', 'YouTube': '#FF0000'}


def card(p):
    c = COLORS.get(p['platform'], '#888')
    img = '<img src="' + p['thumb'] + '" alt="" loading="lazy">' if p.get('thumb') else ''
    title = p['title'].replace('<', '&lt;').replace('>', '&gt;')
    score_str = str(p['score']) if p['score'] else '-'
    comments_str = str(p['comments']) if p['comments'] else '-'
    return (
        '<a class="card" href="' + p['url'] + '" target="_blank">' +
        img + '<div class="card-body">' +
        '<span class="badge" style="background:' + c + '">' + p['platform'] + ' &middot; ' + p['source'] + '</span>' +
        '<p class="card-title">' + title + '</p>' +
        '<div class="card-meta"><span>👍 ' + score_str + '</span>' +
        '<span>💬 ' + comments_str + '</span></div>' +
        '</div></a>'
    )


def section(title, posts, icon):
    if not posts:
        return '<section><h2>' + icon + ' ' + title + '</h2><p class="empty">No data this week.</p></section>'
    cards = '\n'.join(card(p) for p in posts)
    return '<section><h2>' + icon + ' ' + title + '</h2><div class="grid">' + cards + '</div></section>'


def generate_html(reddit, vk, hoyolab, youtube):
    now = datetime.datetime.utcnow()
    week = now.strftime('%B %d, %Y')
    updated = now.strftime('%Y-%m-%d %H:%M UTC')
    body = '\n'.join([
        section('Reddit Highlights', reddit, '🟠'),
        section('HoYoLAB Hot Posts', hoyolab, '🌟'),
        section('YouTube Hot Videos (Past 2 Weeks)', youtube, '▶️'),
        section('VK Community (Russia)', vk, '🔵'),
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
        '<footer>Auto-generated weekly digest &middot; Reddit &middot; HoYoLAB &middot; YouTube &middot; VK &middot; Personal use only</footer>'
        '</body></html>'
    )


def main():
    print('Fetching Reddit...')
    reddit = fetch_reddit()
    print('  ' + str(len(reddit)) + ' posts')

    print('Fetching HoYoLAB...')
    hoyolab = fetch_hoyolab()
    print('  ' + str(len(hoyolab)) + ' posts')

    print('Fetching YouTube...')
    youtube = fetch_youtube()
    print('  ' + str(len(youtube)) + ' videos')

    print('Fetching VK...')
    vk = fetch_vk()
    print('  ' + str(len(vk)) + ' posts')

    html = generate_html(reddit, vk, hoyolab, youtube)
    out = Path('docs')
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'data.json').write_text(
        json.dumps({
            'reddit': reddit,
            'vk': vk,
            'hoyolab': hoyolab,
            'youtube': youtube,
            'generated_at': datetime.datetime.utcnow().isoformat(),
        }, ensure_ascii=False, indent=2),
        encoding='utf-8')
    print('Done -> docs/index.html')


if __name__ == '__main__':
    main()
