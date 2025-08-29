# make_cards_json.py
import os, json, re
from pathlib import Path

BASE = Path(__file__).parent
CARDS_DIR = BASE / "cards"
DATA_DIR  = BASE / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
OUT = DATA_DIR / "cards.json"

# 1) 메이저 아르카나 한글 표기 (Rider–Waite 번호)
DISPLAY_KR_MAJOR = {
    "MAJOR_00_TheFool": "바보",
    "MAJOR_01_TheMagician": "마법사",
    "MAJOR_02_TheHighPriestess": "여사제",
    "MAJOR_03_TheEmpress": "여황제",
    "MAJOR_04_TheEmperor": "황제",
    "MAJOR_05_TheHierophant": "교황",
    "MAJOR_06_TheLovers": "연인",
    "MAJOR_07_TheChariot": "전차",
    "MAJOR_08_Strength": "힘",
    "MAJOR_09_TheHermit": "은둔자",
    "MAJOR_10_WheelOfFortune": "운명의 수레바퀴",
    "MAJOR_11_Justice": "정의",
    "MAJOR_12_TheHangedMan": "매달린 남자",
    "MAJOR_13_Death": "죽음",
    "MAJOR_14_Temperance": "절제",
    "MAJOR_15_TheDevil": "악마",
    "MAJOR_16_TheTower": "탑",
    "MAJOR_17_TheStar": "별",
    "MAJOR_18_TheMoon": "달",
    "MAJOR_19_TheSun": "태양",
    "MAJOR_20_Judgement": "심판",
    "MAJOR_21_TheWorld": "세계",
}

# 2) 마이너 아르카나 한글 표기 규칙
SUIT_KR = {
    "PENTACLES": "펜타클",
    "SWORDS":    "소드",
    "CUPS":      "컵",
    "WANDS":     "완드",
}
RANK_KR = {
    "Ace":   "에이스",
    "Page":  "페이지",
    "Knight":"나이트",
    "Queen": "퀸",
    "King":  "킹",
}
def rank_to_kr(rank: str) -> str:
    if re.fullmatch(r"\d{2}", rank):
        return str(int(rank))  # "01" -> "1"
    return RANK_KR.get(rank, rank)

def parse_card(fname: str):
    stem = os.path.splitext(fname)[0]  # e.g. MAJOR_08_Strength, WANDS_07, CUPS_Ace
    card_id = stem
    if stem.startswith("MAJOR_"):
        arcana = "major"
        suit = None
        m = re.match(r"MAJOR_(\d{2})_(.+)", stem)
        rank = m.group(1) if m else None
        en_name = m.group(2) if m else stem
        kr_name = DISPLAY_KR_MAJOR.get(stem, en_name)
    else:
        arcana = "minor"
        m = re.match(r"(PENTACLES|SWORDS|CUPS|WANDS)_(.+)", stem)
        suit = m.group(1).upper() if m else None
        rank = m.group(2) if m else None
        en_name = f"{suit.title()} {rank}"
        suit_kr = SUIT_KR.get(suit, suit or "")
        rank_kr = rank_to_kr(rank or "")
        kr_name = f"{suit_kr} {rank_kr}".strip()

    return {
        "id": card_id,
        "name_kr": kr_name,   # 한국어 이름
        "name_en": en_name,   # 영문 이름
        "arcana": arcana,
        "suit": (suit.lower() if suit else None),
        "rank": rank,
        "img": fname,
        "keywords": [],
        "upright":  {"general":"", "love":"", "career":"", "finance":"", "health":"", "advice":""},
        "reversed": {"general":"", "love":"", "career":"", "finance":"", "health":"", "advice":""}
    }

def main():
    entries = []
    for f in sorted(os.listdir(CARDS_DIR)):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            entries.append(parse_card(f))

    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(entries, fp, ensure_ascii=False, indent=2)
    print(f"작성 완료: {OUT} ({len(entries)}장, 한글/영문 이름 포함)")

if __name__ == "__main__":
    main()
