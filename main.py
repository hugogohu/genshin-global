"""
Genshin Impact Global Community Weekly Digest
Fetches posts from Reddit, VK, and HoYoLAB, generates a static HTML page.
"""

import os
import json
import datetime
import requests
from pathlib import Path

# ─── Reddit ───────────────────────────────────────────────────────────────────

def fetch_reddit(limit=15):
    import praw
    reddit = praw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent='genshin-global-digest/1.0 by hugogohu',
    )
    subreddits = ['Genshin_Impact', 'GenshinImpactTips', 'Genshin_Lore']
    posts = []
    for sub in subreddits:
        try:
            for post in reddit.subreddit(sub).hot(limit=limit):
                if post.stickied:
                    continue
                thumb = post.thumbnail if post.thumbnail.startswith('http') else None
                posts.append({
                    'title': post.title,
                    'url': f'https://reddit.com{post.permalink}',
                    'score': post.score,
                    'comments': post.num_comments,
                    'source': f'r/{sub}',
                    'platform': 'Reddit',
                    'thumb': thumb,
                })
        except Exception as e:
            print(f'Reddit error ({sub}): {e}')
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:20]


# ─── VK ───────────────────────────────────────────────────────────────────────

def fetch_vk(limit=15):
    token = os.environ.get('VK_SERVICE_TOKEN', '')
    if not token:
        print('VK token not set, skipping.')
        return []
    # Popular Russian Genshin VK communities
    groups = ['genshin_impact_ru', 'genshin.impact.official']
    posts = []
    for group in groups:
        try:
            resp = requests.get('https://api.vk.com/method/wall.get', params={
                'domain': group,
                'count': limit,
                'access_token': token,
                'v': '5.131',
                'filter': 'owner',
            }, timeout=10)
            data = resp.json()
            if 'response' not in data:
                print(f'VK error ({group}): {data}')
                continue
            for item in data['response']['items']:
                text = item.get('text', '').strip()
                if not text:
                    continue
                # Get photo if available
                thumb = None
                attachments = item.get('attachments', [])
                for att in attachments:
                    if att.get('type') == 'photo':
                        sizes = att['photo'].get('sizes', [])
                        if sizes:
                            thumb = sizes[-1]['url']
                        break
                posts.append({
                    'title': text[:200] + ('…' if len(text) > 200 else ''),
                    'url': f'https://vk.com/wall{item["owner_id"]}_{item["id"]}',
                    'score': item.get('likes', {}).get('count', 0),
                    'comments': item.get('comments', {}).get('count', 0),
                    'source': group,
                    'platform': 'VK',
                    'thumb': thumb,
                })
        except Exception as e:
            print(f'VK error ({group}): {e}')
    posts.sort(key=lambda x: x['score'], reverse=True)
    return posts[:10]


# ─── HoYoLAB ──────────────────────────────────────────────────────────────────

def fetch_hoyolab(limit=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'x-rpc-client_type': '4',
        'x-rpc-app_version': '1.5.0',
        'x-rpc-language': 'en-us',
        'Origin': 'https://www.hoyolab.com',
        'Referer': 'https://www.hoyolab.com/',
    }
    posts = []
    # Hot posts in Genshin forum (forum_id=29, gids=2)
    try:
        resp = requests.get(
            'https://bbs-api-os.hoyolab.com/community/post/wapi/getForumPostList',
            params={'forum_id': 29, 'is_good': 'false', 'is_hot': 'true',
                    'page_size': limit, 'gids': 2},
            headers=headers, timeout=10
        )
        data = resp.json()
        items = (data.get('data') or {}).get('list') or []
        for item in items:
            post = item.get('post', {})
            stat = item.get('stat', {})
            # cover image
            cover = None
            image_list = item.get('image_list', [])
            if image_list:
                cover = image_list[0].get('url')
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


# ─── HTML Generation ──────────────────────────────────────────────────────────

PLATFORM_COLORS = {
    'Reddit': '#FF4500',
    'VK': '#0077FF',
    'HoYoLAB': '#1A9DD9',
}

def card(post):
    color = PLATFORM_COLORS.get(post['platform'], '#888')
    thumb_html = ''
    if post.get('thumb'):
        thumb_html = f'<img src="{post["thumb"]}" alt="" loading="lazy">'
    return f'''
<a class="card" href="{post["url"]}" target="_blank" rel="noopener">
  {thumb_html}
  <div class="card-body">
    <span class="badge" style="background:{color}">{post["platform"]} · {post["source"]}</span>
    <p class="card-title">{post["title"]}</p>
    <div class="card-meta">
      <span>👍 {post["score"]:,}</span>
      <span>💬 {post["comments"]:,}</span>
    </div>
  </div>
</a>'''


def section(title, posts, icon):
    if not posts:
        return f'<section><h2>{icon} {title}</h2><p class="empty">No data this week.</p></section>'
    cards = '\n'.join(card(p) for p in posts)
    return f'<section><h2>{icon} {title}</h2><div class="grid">{cards}</div></section>'


def generate_html(reddit_posts, vk_posts, hoyolab_posts):
    now = datetime.datetime.utcnow()
    week = now.strftime('Week of %B %d, %Y')
    updated = now.strftime('%Y-%m-%d %H:%M UTC')

    body = '\n'.join([
        section('Reddit Highlights', reddit_posts, '🟠'),
        section('HoYoLAB Hot Posts', hoyolab_posts, '🌟'),
        section('VK Community (Russia)', vk_posts, '🔵'),
    ])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Genshin Global Digest — {week}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0f0f1a; color: #e8e8f0; min-height: 100vh; }}
  header {{ background: linear-gradient(135deg, #1a1040 0%, #2d1b69 100%);
            padding: 2rem 1.5rem; text-align: center; border-bottom: 1px solid #3d2d80; }}
  header h1 {{ font-size: 2rem; color: #c8a8ff; letter-spacing: 0.05em; }}
  header p {{ color: #a090c0; margin-top: 0.4rem; font-size: 0.9rem; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }}
  section {{ margin-bottom: 3rem; }}
  section h2 {{ font-size: 1.3rem; color: #d0b0ff; margin-bottom: 1rem;
               border-left: 3px solid #7c5cbf; padding-left: 0.75rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
  .card {{ background: #1a1a2e; border: 1px solid #2d2d4e; border-radius: 10px;
           overflow: hidden; text-decoration: none; color: inherit;
           transition: transform 0.15s, border-color 0.15s; display: flex; flex-direction: column; }}
  .card:hover {{ transform: translateY(-3px); border-color: #7c5cbf; }}
  .card img {{ width: 100%; height: 160px; object-fit: cover; display: block; }}
  .card-body {{ padding: 0.9rem; flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }}
  .badge {{ font-size: 0.72rem; font-weight: 600; color: #fff;
            padding: 0.2rem 0.5rem; border-radius: 4px; display: inline-block; width: fit-content; }}
  .card-title {{ font-size: 0.92rem; line-height: 1.45; flex: 1;
                 display: -webkit-box; -webkit-line-clamp: 3;
                 -webkit-box-orient: vertical; overflow: hidden; }}
  .card-meta {{ font-size: 0.8rem; color: #8080a0; display: flex; gap: 1rem; }}
  .empty {{ color: #606080; font-style: italic; }}
  footer {{ text-align: center; padding: 2rem; color: #5050708; font-size: 0.8rem; border-top: 1px solid #2d2d4e; }}
</style>
</head>
<body>
<header>
  <h1>🌙 Genshin Global Digest</h1>
  <p>{week} · Updated {updated}</p>
</header>
<main>
{body}
</main>
<footer>Auto-generated weekly digest · Data from Reddit, HoYoLAB, VK · Personal use only</footer>
</body>
</html>'''


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('Fetching Reddit...')
    reddit_posts = fetch_reddit()
    print(f'  Got {len(reddit_posts)} posts')

    print('Fetching HoYoLAB...')
    hoyolab_posts = fetch_hoyolab()
    print(f'  Got {len(hoyolab_posts)} posts')

    print('Fetching VK...')
    vk_posts = fetch_vk()
    print(f'  Got {len(vk_posts)} posts')

    html = generate_html(reddit_posts, vk_posts, hoyolab_posts)

    out = Path('docs')
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(html, encoding='utf-8')
    print('Generated docs/index.html')

    # Save raw data for debugging
    data = {'reddit': reddit_posts, 'vk': vk_posts, 'hoyolab': hoyolab_posts,
            'generated_at': datetime.datetime.utcnow().isoformat()}
    (out / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Done.')


if __name__ == '__main__':
    main()
