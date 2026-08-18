import re


def extract_ratio_from_text(text: str):
    """
    법령 문장에서 용도지역의 비율 정보를 추출한다.

    예:
    제3종일반주거지역 : 50퍼센트 이하
    → 50.0

    제3종일반주거지역 : 100퍼센트 이상 300퍼센트 이하
    → 300.0
    """

    if not text:
        return None

    match = re.search(
        r"제3종일반주거지역\s*:\s*"
        r"(?:\d+(?:\.\d+)?퍼센트\s*이상\s*)?"
        r"(\d+(?:\.\d+)?)퍼센트\s*이하",
        text
    )

    if match:
        return float(match.group(1))

    return None


def find_article_ratio(articles, article_number: str):
    """
    특정 조문에서 제3종일반주거지역의 비율을 찾는다.
    """

    for article in articles:

        if str(article.get("조문번호", "")) != article_number:
            continue

        # 항 검색
        paragraphs = article.get("항", [])

        for paragraph in paragraphs:

            # 항 자체의 내용도 확인
            paragraph_text = paragraph.get("항내용", "")

            ratio = extract_ratio_from_text(paragraph_text)

            if ratio is not None:
                return ratio

            # 호 검색
            items = paragraph.get("호", [])

            for item in items:

                item_text = item.get("호내용", "")

                ratio = extract_ratio_from_text(item_text)

                if ratio is not None:
                    return ratio

    return None