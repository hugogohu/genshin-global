import os, json, datetime, requests
from pathlib import Path

def fetch_reddit(limit=20):
    subreddits = ['Genshin_Impact', 'GenshinImpactTips', 'Genshin_Lore']
    headers = {'User-Agent': 'genshin-global-digest/1.0'}
    posts = []
    for sub in subreddits:
        try:
            resp = requests.get(
                f'https://www.reddit.com/r/{sub}/hot.json?limit={limit}',
                headers=headers, timeout=10)
            data = resp.json()
            for item in data['data']['children']:
                p = item['data']
                if p.get('stickied'):
                    continue
                thumb = p.

get('thumbnail', '')
                posts.append({
                    'title': p['title'],
                    'url': f'https://reddit.com{p["permalink"]}',
                    'score': p['score'],
                    'comments': p['num_comments'],
                    'source': f'r/{sub}',
                    'platform': 'Reddit',
                    'thumb': thumb if thumb.startswith('http') else None,
                })
        except Exception as e:
            print(f'Reddit error ({sub}): {e}')
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:20]

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
                    'url': f'https://vk.com/wall{item["owner_id"]}_{item["id"]}',
                    'score': item.get('likes', {}).get('count', 0),
                    'comments': item.get('comments', {}).get('count', 0),
                    'source': group,
                    'platform': 'VK',
                    'thumb': thumb,
                })
        except Exception as e:
            print(f'VK error: {e}')
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:10]

def fetch_hoyolab(limit=10):
    headers = {
        'User-Agent': 'Mozilla/5.0',
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
            headers=headers, timeout=10)
        data = resp.json()
        for item in (data.get('data') or {}).get('list') or []:
            post = item.get('post', {})
            stat = item.get('stat', {})
            image_list = item.get('image_list') or []
            cover = image_list[0].get('url') if image_list else None
            posts.append({
                'title': post.get('subject', '(no title)'),
                'url': f'https://www.hoyolab.com/article/{post.get("post_id")}',

'score': stat.get('like_num', 0),
                'comments': stat.get('reply_num', 0),
                'source': 'HoYoLAB',
                'platform': 'HoYoLAB',
                'thumb': cover,
            })
    except Exception as e:
        print(f'HoYoLAB error: {e}')
    return posts

COLORS = {'Reddit': '#FF4500', 'VK': '#0077FF', 'HoYoLAB': '#1A9DD9'}

def card(p):
    c = COLORS.get(p['platform'], '#888')
    img = f'<img src="{p["thumb"]}" alt="" loading="lazy">' if p.get('thumb') else ''
    title = p['title'].replace('<', '&lt;').replace('>', '&gt;')
    return (f'<a class="card" href="{p["url"]}" target="_blank">'
            f'{img}<div class="card-body">'
            f'<span class="badge" style="background:{c}">{p["platform"]} · {p["source"]}</span>'

f'<p class="card-title">{title}</p>'
            f'<div class="card-meta"><span>👍 {p["score"]:,}</span>'
            f'<span>💬 {p["comments"]:,}</span></div>'
            f'</div></a>')

def section(title, posts, icon):
    if not posts:
        return f'<section><h2>{icon} {title}</h2><p class="empty">No data this week.</p></section>'
    cards = '\n'.join(card(p) for p in posts)
    return f'<section><h2>{icon} {title}</h2><div class="grid">{cards}</div></section>'

def generate_html(reddit, vk, hoyolab):
    now = datetime.datetime.utcnow()
    week = now.strftime('%B %d, %Y')
    updated = now.strftime('%Y-%m-%d %H:%M UTC')
    body = '\n'.join([
        section('Reddit Highlights', reddit, '🟠'),
        section('HoYoLAB Hot Posts', hoyolab, '🌟'),
        section('VK Community (Russia)', vk,

'🔵'),
    ])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Genshin Global Digest</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f0f1a; color: #e8e8f0; }}
header {{ background: linear-gradient(135deg, #1a1040, #2d1b69); padding: 2rem; text-align: center; border-bottom: 1px solid #3d2d80; }}
header h1 {{ font-size: 2rem; color: #c8a8ff; }}
header p {{ color: #a090c0; margin-top: .4rem; font-size: .9rem; }}
main {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }}
section {{ margin-bottom: 3rem; }}
section h2 {{ font-size: 1.3rem; color: #d0b0ff; margin-bottom:

1rem; border-left: 3px solid #7c5cbf; padding-left: .75rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
.card {{ background: #1a1a2e; border: 1px solid #2d2d4e; border-radius: 10px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .15s, border-color .15s; display: flex; flex-direction: column; }}
.card:hover {{ transform: translateY(-3px); border-color: #7c5cbf; }}
.card img {{ width: 100%; height: 160px; object-fit: cover; display: block; }}
.card-body {{ padding: .9rem; flex: 1; display: flex; flex-direction: column; gap: .5rem; }}
.badge {{ font-size: .72rem; font-weight: 600; color: #fff; padding: .2rem .5rem; border-radius: 4px; display: inline-block; }}
.card-title {{ font-size: .92rem; line-height:

1.45; flex: 1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
.card-meta {{ font-size: .8rem; color: #8080a0; display: flex; gap: 1rem; }}
.empty {{ color: #606080; font-style: italic; }}
footer {{ text-align: center; padding: 2rem; color: #505070; font-size: .8rem; border-top: 1px solid #2d2d4e; }}
</style>
</head>
<body>
<header>
  <h1>🌙 Genshin Global Digest</h1>
  <p>Week of {week} · Updated {updated}</p>
</header>
<main>
{body}
</main>
<footer>Auto-generated weekly digest · Reddit · HoYoLAB · VK · Personal use only</footer>
</body>
</html>"""

def main():
    print('Fetching Reddit...')
    reddit = fetch_reddit()
    print(f'  {len(reddit)} posts')
    print('Fetching HoYoLAB...')
    hoyolab = fetch_hoyolab()
    print(f'  {len(hoyolab)}

posts')
    print('Fetching VK...')
    vk = fetch_vk()
    print(f'  {len(vk)} posts')
    html = generate_html(reddit, vk, hoyolab)
    out = Path('docs')
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(html, encoding='utf-8')
    (out / 'data.json').write_text(
        json.dumps({'reddit': reddit, 'vk': vk, 'hoyolab': hoyolab,
                    'generated_at': datetime.datetime.utcnow().isoformat()},
                   ensure_ascii=False, indent=2),
        encoding='utf-8')
    print('Done -> docs/index.html')

if __name__ == '__main__':
    main()