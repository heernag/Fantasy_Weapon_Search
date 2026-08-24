"""한국어 질의의 치명적 오역만 우회하기 위한 도메인 용어 사전.

한국어 질의는 검색 서비스가 `Helsinki-NLP/opus-mt-ko-en`으로 번역한 뒤 검색한다.
그 번역기가 무기 용어 일부를 **다른 뜻으로** 바꿔 버려서 검색이 통째로 빗나간다.
실측한 오역은 다음과 같다(측정 기록: `docs/TEST_KEYWORDS_KO.md`).

    창 -> "Windows"        석궁 -> "The Labyrinth"    낫 -> "Better."
    표창 -> "Tablebar"      수리검 -> "The Remedy"      철퇴 -> "Retreat"
    곤봉 -> "Gobong"        장궁 -> "A Memorandum"      수정 -> "Modify"
    나무 -> "Tree"

번역 품질 전반을 손보려는 것이 아니다. 어색한 문장이나 미묘한 뉘앙스 차이는
그대로 둔다. 뜻이 아예 다른 물건으로 바뀌는 경우만 막는다.

## 방식

질의를 통째로 영어로 바꿀 수 있을 때만 바꾸고, 그렇지 않으면 손대지 않는다.
부분 치환은 실측 결과 오히려 더 나빴다. 한글이 조금이라도 남으면 번역기가 섞여
있는 영어 단어까지 망가뜨리기 때문이다.

    "불타는 greatsword" -> "Glosswords on fire"
    "창 spear"          -> "window space"

그래서 아래 세 조건을 모두 만족할 때만 영어 질의를 만든다.

1. 모든 토큰이 이 사전에 있다. (하나라도 모르면 원문 그대로 번역기에 맡긴다)
2. 오역이 확인된 용어가 최소 하나 들어 있다. (아니면 굳이 우회할 이유가 없다)
3. 결과가 완전한 영어다. -> 검색 서비스가 번역 단계를 건너뛴다.

## 사전에 없는 것

- `대검`은 "Dagger"로 오역되지만 **일부러 넣지 않았다.** 실측에서 치환이 결과를
  더 나쁘게 만들었다(`얼음 대검` 5/5 -> `ice greatsword` 2/5). 수식어가 검색을
  이끌기 때문에 한국어 원문이 이미 잘 동작한다.
- 조사가 붙은 형태(`창을`, `나무로`)는 토큰이 사전에 없으므로 규칙 1에서 걸러져
  원문 그대로 처리된다. 의도된 동작이다.

## 고치는 방법

용어를 추가하려면 아래 두 사전에 넣으면 된다. 새 항목을 넣기 전에
`docs/TEST_KEYWORDS_KO.md`의 측정 방식대로 치환 전후 적중률을 비교해서, 실제로
좋아지는지 확인할 것. 오역이라는 이유만으로 넣으면 위 `대검`처럼 역효과가 난다.
"""

# 번역기가 다른 뜻으로 바꿔 버리는 것이 확인된 용어. 이 중 하나라도 질의에
# 들어 있어야 재작성을 시도한다.
MISTRANSLATED_TERMS = {
    "창": "spear",
    "석궁": "crossbow",
    "장궁": "longbow",
    "낫": "scythe",
    "표창": "shuriken",
    "수리검": "shuriken",
    "철퇴": "mace",
    "곤봉": "club",
    "수정": "crystal",
    "나무": "wood",
}

# 위 용어와 함께 쓰이는 기본 수식어. 이 단어들 자체는 번역이 멀쩡하지만, 질의를
# 통째로 영어로 만들려면 함께 필요하다. 값은 실제 메타데이터 어휘에 맞췄다.
SUPPORTING_TERMS = {
    # 무기 종류
    "검": "sword", "장검": "longsword", "단검": "dagger", "소검": "shortsword",
    "방패": "shield", "도끼": "axe", "활": "bow", "화살": "arrow",
    "지팡이": "staff", "망치": "hammer", "총": "gun",
    # 색상
    "빨간": "red", "붉은": "red", "빨강": "red",
    "파란": "blue", "푸른": "blue", "파랑": "blue",
    "초록": "green", "녹색": "green", "초록색": "green",
    "노란": "yellow", "노랑": "yellow", "노란색": "yellow",
    "검은": "black", "검정": "black", "검은색": "black",
    "흰": "white", "하얀": "white", "흰색": "white",
    "금색": "gold", "황금": "gold", "금빛": "gold",
    "은색": "silver", "회색": "gray", "갈색": "brown",
    "보라": "purple", "보라색": "purple", "주황": "orange", "주황색": "orange",
    "청록": "cyan", "청동": "bronze", "분홍": "pink",
    # 속성
    "불": "fire", "화염": "fire", "불타는": "flaming",
    "얼음": "ice", "번개": "lightning", "어둠": "dark", "어두운": "dark",
    "신성한": "holy", "독": "poison", "자연": "nature", "물": "water", "바람": "wind",
    # 재질
    "강철": "steel", "가죽": "leather", "뼈": "bone",
    "흑요석": "obsidian", "돌": "stone", "천": "cloth",
    # 형태·등급·양식
    "양손": "two handed", "한손": "one handed",
    "전설": "legendary", "중세": "medieval", "동양": "eastern",
}

TERMS = {**SUPPORTING_TERMS, **MISTRANSLATED_TERMS}


def rewrite_korean_query(text: str) -> str | None:
    """질의를 통째로 영어로 바꿀 수 있으면 영어 질의를, 아니면 None을 돌려준다.

    None이면 호출한 쪽은 원문을 그대로 검색 서비스에 넘겨야 한다.
    """
    tokens = text.split()
    if not tokens:
        return None

    rewritten = []
    has_mistranslated = False
    for token in tokens:
        replacement = TERMS.get(token)
        if replacement is None:
            return None
        if token in MISTRANSLATED_TERMS:
            has_mistranslated = True
        rewritten.append(replacement)

    if not has_mistranslated:
        return None
    return " ".join(rewritten)
