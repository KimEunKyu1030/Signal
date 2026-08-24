"""
generate_post.py
-----------------
오늘의 핫이슈를 웹에서 직접 찾아 블로그 글 초안을 자동으로 작성하고
posts/ 폴더에 마크다운 파일로 저장하는 스크립트.

동작 방식:
1. Claude API에 web_search 도구를 붙여서, 지금 가장 화제가 되고 있는
   주제를 스스로 검색하게 한다.
2. 찾은 정보를 바탕으로 사람이 읽기 좋은 블로그 글(제목/요약/태그/본문)을
   JSON 형식으로 작성하게 한다.
3. 결과를 posts/YYYY-MM-DD-slug.md 파일로 저장한다 (프론트매터 + 마크다운 본문).

주의:
- 원문을 그대로 베끼지 않고, 배경 설명 + 정리 + 코멘트 형태로 재구성하도록
  프롬프트에 명시했다. (저작권 문제 방지)
- 완전 자동 발행보다는, 이 스크립트가 만든 초안을 사람이 한 번 훑어보고
  발행하는 "반자동" 운영을 권장한다.
"""

import os
import re
import sys
import json
import datetime
import unicodedata
from pathlib import Path

import anthropic

POSTS_DIR = Path(__file__).parent / "posts"
POSTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """당신은 트렌드 정보를 정리해서 소개하는 블로그의 필자입니다.
반드시 아래 규칙을 지키세요.

1. 원문 기사를 그대로 베끼지 말고, 배경 설명 + 핵심 정리 + 당신만의 관점/코멘트로
   재구성해서 작성하세요. 직접 인용은 최소화하고, 인용하더라도 15단어(영문 기준) 이내로 짧게만 사용하세요.
2. 특정 인물을 비방하거나 명예훼손이 될 수 있는 표현, 미확인 루머를 사실처럼 쓰는 것은 금지합니다.
3. 정치적으로 민감한 주제는 한쪽 입장만 대변하지 말고 균형 있게 서술하세요.
4. 출력은 반드시 아래 JSON 스키마 하나만 반환하세요. 다른 설명, 코드블록 표시(```) 없이
   순수 JSON 텍스트만 출력하세요.

{
  "title": "글 제목 (한국어, 30자 이내, 클릭을 유도하되 과장/낚시성 금지)",
  "tag": "이 글의 카테고리 한 단어 (예: IT, 엔터, 경제, 스포츠, 사회 등)",
  "summary": "이 글을 한 문장으로 요약 (60자 이내)",
  "content_markdown": "본문 마크다운. 800~1200자 분량. 소제목(##)을 2~3개 사용해서 구조화."
}
"""

USER_PROMPT = """지금 이 시점에 한국 또는 전세계적으로 가장 화제가 되고 있는 주제를 하나
직접 웹에서 검색해서 찾아주세요. 분야는 상관없습니다 (IT, 경제, 연예, 스포츠, 사회 이슈 등 아무거나 좋습니다).
가장 최신이고 사람들이 지금 관심 가질 만한 주제를 고르세요.

그 주제에 대해 배경 지식이 없는 독자도 이해할 수 있도록 정리하고 소개하는 블로그 글을 써주세요.
"""


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text, flags=re.UNICODE)
    return text[:60].strip("-") or "post"


def extract_json(text: str) -> dict:
    """모델 응답에서 JSON 부분만 안전하게 추출한다."""
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("응답에서 JSON을 찾을 수 없습니다:\n" + text[:500])
    return json.loads(match.group(0))


def generate() -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("환경변수 ANTHROPIC_API_KEY 가 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    # web_search를 쓰면 여러 turn/블록이 섞여서 올 수 있으므로 text 블록만 모두 이어붙인다.
    full_text = "\n".join(
        block.text for block in response.content if block.type == "text"
    )

    data = extract_json(full_text)
    for key in ("title", "tag", "summary", "content_markdown"):
        if key not in data:
            raise ValueError(f"응답 JSON에 '{key}' 필드가 없습니다: {data}")
    return data


def save_post(data: dict) -> Path:
    today = datetime.date.today().isoformat()
    slug = slugify(data["title"])
    filepath = POSTS_DIR / f"{today}-{slug}.md"

    frontmatter = (
        "---\n"
        f"title: \"{data['title']}\"\n"
        f"date: \"{today}\"\n"
        f"tag: \"{data['tag']}\"\n"
        f"summary: \"{data['summary']}\"\n"
        "---\n\n"
    )
    filepath.write_text(frontmatter + data["content_markdown"], encoding="utf-8")
    return filepath


if __name__ == "__main__":
    result = generate()
    path = save_post(result)
    print(f"글이 생성되었습니다: {path}")
