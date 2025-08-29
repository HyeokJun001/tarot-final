# rename_tarot_minors.py
import os, re, unicodedata
from typing import Optional

FOLDER = "cards"
EXTS = (".jpg", ".jpeg", ".png", ".webp")

# ---- 스펙: 파일명 목표 규칙 ----
# <SUIT>_<RANK>.<ext>
# SUIT ∈ {PENTACLES, SWORDS, CUPS, WANDS}
# RANK ∈ {01..10, Ace, Page, Knight, Queen, King}

# 순서: 펜타클 → 소드 → 컵 → 완드 (매칭 우선순위용, 실제 리네임엔 영향 없음)
SUITS = [
    ("PENTACLES", ["펜타클", "동전", "코인", "pentacle", "pentacles", "pent", "coin"]),
    ("SWORDS",    ["소드", "검", "칼", "sword", "swords"]),
    ("CUPS",      ["컵", "잔", "chalice", "cup", "cups"]),
    ("WANDS",     ["완드", "지팡이", "봉", "막대", "wand", "wands"]),
]

# 랭크(법정카드) 한국어/영어 변형
COURT_ALIASES = {
    "Page":   ["페이지", "侍從", "시종", "소년", "page", "pager"],  # 일부 잘못 추출 대비
    "Knight": ["기사", "나이트", "knight"],
    "Queen":  ["여왕", "퀸", "queen"],
    "King":   ["왕", "킹", "king"],
}

def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.strip()
    # 앞번호/점/대시 제거: "10. " / "10 - " / "10_" 등
    s = re.sub(r"^\s*\d+\s*[.\-_]?\s*", "", s)
    # 확장자 제거
    s = re.sub(r"\.(jpg|jpeg|png|webp)$", "", s, flags=re.I)
    # 뒤 "카드" 제거
    s = re.sub(r"\s*카드$", "", s)
    # 괄호/구분자 제거(검색 용)
    s = re.sub(r"[\[\]\(\)·•]+", " ", s)
    return s

def find_ext(path_wo_ext: str) -> Optional[str]:
    for ext in EXTS:
        p = path_wo_ext + ext
        if os.path.exists(p):
            return ext
    return None

def detect_suit(name: str) -> Optional[str]:
    n = name.lower().replace(" ", "")
    for suit, aliases in SUITS:
        for a in aliases:
            if a.lower().replace(" ", "") in n:
                return suit
    return None

def detect_rank(name: str) -> Optional[str]:
    n = name.lower()
    # 1) 에이스
    if re.search(r"(?:^|[^a-z가-힣])(?:ace|에이스|a)(?:$|[^a-z가-힣])", n):
        return "Ace"

    # 2) 숫자(1~10) - 어디에 붙어 있어도 추출
    #   예: '소드10', '완드2', 'cup10', '10컵' 모두 매칭
    nums = re.findall(r"\d{1,2}", n)
    for tok in nums:
        try:
            num = int(tok)
            if 1 <= num <= 10:
                return f"{num:02d}"
        except:
            pass

    # 3) 법정 카드
    for rk, aliases in COURT_ALIASES.items():
        for a in aliases:
            if re.search(rf"(?:^|[^a-z가-힣]){re.escape(a)}(?:$|[^a-z가-힣])", n):
                return rk

    # 4) 로마숫자(II~X)
    roman_map = {
        "i": "01", "ii": "02", "iii": "03", "iv": "04", "v": "05",
        "vi": "06", "vii": "07", "viii": "08", "ix": "09", "x": "10"
    }
    m2 = re.search(r"(?:^|[^a-z])(?P<r>i|ii|iii|iv|v|vi|vii|viii|ix|x)(?:$|[^a-z])", n)
    if m2:
        return roman_map[m2.group("r")]
    return None

def main(dry_run=True):
    files = [f for f in os.listdir(FOLDER) if f.lower().endswith(EXTS)]
    renamed, skipped, unsure = [], [], []

    for f in files:
        # --- 추가: 메이저는 건너뛰기 ---
        if f.startswith("MAJOR_"):
            continue

        raw = os.path.splitext(f)[0]   # 확장자 뺀 원본 이름
        base = normalize(f)
        suit = detect_suit(base)
        # --- 숫자는 base / raw 둘 다에서 감지 ---
        rank = detect_rank(base) or detect_rank(raw)

        # ↓ 여기서부터는 원래 코드 이어서...
        if not suit or not rank:
            unsure.append((f, suit, rank))
            continue

        new_name = f"{suit}_{rank}{os.path.splitext(f)[1].lower()}"
        if f == new_name:
            continue
        if dry_run:
            print(f"[DRY] {f} -> {new_name}")
        else:
            os.rename(os.path.join(FOLDER, f), os.path.join(FOLDER, new_name))
            print(f"Renamed: {f} -> {new_name}")
            renamed.append((f, new_name))

    # 결과 요약 출력 부분 계속...


    print("\n=== 결과 요약 ===")
    print(f"총 파일: {len(files)}")
    if dry_run:
        print("※ DRY RUN 모드입니다. 실제 변경 없음. 문제 없으면 dry_run=False로 실행하세요.")
    print(f"리네임 완료(또는 예정): {len(renamed)}")
    print(f"스킵(메이저 추정): {len(skipped)}")
    print(f"판단 불가(수동 확인 필요): {len(unsure)}")
    if unsure:
        for f, s, r in unsure[:20]:
            print(f" - 미매칭: {f} / suit={s} / rank={r}")

if __name__ == "__main__":
    # 1) 먼저 미리보기
    main(dry_run=True)
    # 2) 이상 없으면 아래 주석 풀고 실행
    main(dry_run=False)
