"""
build.py
--------
posts/*.md 파일들을 읽어서 docs/ 폴더에 정적 HTML 사이트를 생성한다.
GitHub Pages가 docs/ 폴더를 서빙하도록 설정하면 그대로 배포된다.
"""

import re
import html
import shutil
import datetime
from pathlib import Path

import markdown as md

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "posts"
DOCS_DIR = ROOT / "docs"
POSTS_OUT_DIR = DOCS_DIR / "posts"

SITE_TITLE = "시그널"
SITE_TAGLINE = "지금 사람들이 얘기하는 것들"


def parse_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"프론트매터를 찾을 수 없습니다: {path}")
    fm_block, body = match.groups()

    fm = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"')

    fm["body_html"] = md.markdown(body, extensions=["extra"])
    fm["slug"] = path.stem
    return fm


def load_posts() -> list[dict]:
    posts = [parse_post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


BASE_CSS = """
:root {
  --bg: #12141c;
  --bg-elevated: #1a1d28;
  --text: #f2f0ea;
  --muted: #8891a4;
  --accent: #e8a33d;
  --live: #e1483a;
  --rule: rgba(242, 240, 234, 0.12);
  --serif: "Source Serif 4", Georgia, serif;
  --display: "Space Grotesk", sans-serif;
  --mono: "JetBrains Mono", monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--serif);
  line-height: 1.65;
}

a { color: inherit; }

.wrap {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px;
}

header.masthead {
  border-bottom: 1px solid var(--rule);
  padding: 48px 0 28px;
}

.masthead .eyebrow {
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--live);
  box-shadow: 0 0 0 rgba(225, 72, 58, 0.6);
  animation: pulse 1.8s infinite;
}

@media (prefers-reduced-motion: reduce) {
  .pulse { animation: none; }
}

@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(225, 72, 58, 0.55); }
  70%  { box-shadow: 0 0 0 8px rgba(225, 72, 58, 0); }
  100% { box-shadow: 0 0 0 0 rgba(225, 72, 58, 0); }
}

.masthead h1 {
  font-family: var(--display);
  font-size: 44px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: -0.01em;
}

.masthead p.tagline {
  font-family: var(--mono);
  color: var(--muted);
  font-size: 13px;
  margin: 0;
}

main { padding: 8px 0 80px; }

.dispatch {
  display: block;
  padding: 28px 0;
  border-bottom: 1px solid var(--rule);
  text-decoration: none;
  color: inherit;
}

.dispatch:hover .headline { color: var(--accent); }

.dispatch .meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}

.tag-pill {
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 2px 8px;
  color: var(--accent);
  text-transform: uppercase;
}

.dispatch .headline {
  font-family: var(--display);
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
  transition: color 0.15s ease;
}

.dispatch .summary {
  color: var(--muted);
  font-size: 16px;
  margin: 0;
}

article.post {
  padding: 40px 0 100px;
}

.post .meta {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 0.04em;
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.post h1 {
  font-family: var(--display);
  font-size: 36px;
  line-height: 1.15;
  margin: 0 0 24px;
}

.post h2 {
  font-family: var(--display);
  font-size: 21px;
  margin: 36px 0 12px;
  color: var(--accent);
}

.post p { font-size: 18px; margin: 0 0 18px; }

.back-link {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 32px;
}
.back-link:hover { color: var(--accent); }

footer {
  border-top: 1px solid var(--rule);
  padding: 24px 0 60px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

@media (max-width: 600px) {
  .masthead h1 { font-size: 32px; }
  .post h1 { font-size: 27px; }
  .dispatch .headline { font-size: 20px; }
}
"""

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&'
    'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@400;500'
    '&display=swap" rel="stylesheet">'
)


def page_shell(title: str, body: str, description: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
{FONT_LINKS}
<style>{BASE_CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def render_index(posts: list[dict]) -> str:
    items = []
    for i, p in enumerate(posts):
        pulse = '<span class="pulse"></span>' if i == 0 else ""
        items.append(f"""
        <a class="dispatch" href="posts/{p['slug']}.html">
          <div class="meta">{pulse}<span>{p.get('date','')}</span>
            <span class="tag-pill">{html.escape(p.get('tag',''))}</span></div>
          <h2 class="headline">{html.escape(p.get('title',''))}</h2>
          <p class="summary">{html.escape(p.get('summary',''))}</p>
        </a>""")

    body = f"""
    <div class="wrap">
      <header class="masthead">
        <div class="eyebrow"><span class="pulse"></span> LIVE FEED</div>
        <h1>{SITE_TITLE}</h1>
        <p class="tagline">{SITE_TAGLINE}</p>
      </header>
      <main>{''.join(items) if items else '<p style="color:var(--muted);padding:40px 0;">아직 발행된 글이 없습니다.</p>'}</main>
      <footer>&copy; {datetime.date.today().year} {SITE_TITLE} · 매일 자동으로 업데이트됩니다</footer>
    </div>"""
    return page_shell(SITE_TITLE, body, SITE_TAGLINE)


def render_post(p: dict) -> str:
    body = f"""
    <div class="wrap">
      <article class="post">
        <a class="back-link" href="../index.html">&larr; 전체 글 보기</a>
        <div class="meta"><span>{p.get('date','')}</span>
          <span class="tag-pill">{html.escape(p.get('tag',''))}</span></div>
        <h1>{html.escape(p.get('title',''))}</h1>
        {p['body_html']}
      </article>
    </div>"""
    return page_shell(p.get("title", SITE_TITLE), body, p.get("summary", ""))


def build():
    DOCS_DIR.mkdir(exist_ok=True)
    POSTS_OUT_DIR.mkdir(exist_ok=True)

    posts = load_posts()

    (DOCS_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    for p in posts:
        out = POSTS_OUT_DIR / f"{p['slug']}.html"
        out.write_text(render_post(p), encoding="utf-8")

    print(f"빌드 완료: 글 {len(posts)}개 -> {DOCS_DIR}")


if __name__ == "__main__":
    build()
