# rename_tarot_majors.py  (PyCharm 터미널에서 실행)
import os, re
from itertools import product

FOLDER = "cards"  # 카드 이미지 폴더

# 확장자 후보
EXTS = [".jpg", ".jpeg", ".png", ".webp"]

# 한글 이름 → 표준 ID (RWS 번호)
std_ids = {
    0:  "MAJOR_00_TheFool",
    1:  "MAJOR_01_TheMagician",
    2:  "MAJOR_02_TheHighPriestess",
    3:  "MAJOR_03_TheEmpress",
    4:  "MAJOR_04_TheEmperor",
    5:  "MAJOR_05_TheHierophant",
    6:  "MAJOR_06_TheLovers",
    7:  "MAJOR_07_TheChariot",
    8:  "MAJOR_08_Strength",
    9:  "MAJOR_09_TheHermit",
    10: "MAJOR_10_WheelOfFortune",
    11: "MAJOR_11_Justice",
    12: "MAJOR_12_TheHangedMan",
    13: "MAJOR_13_Death",
    14: "MAJOR_14_Temperance",
    15: "MAJOR_15_TheDevil",
    16: "MAJOR_16_TheTower",
    17: "MAJOR_17_TheStar",
    18: "MAJOR_18_TheMoon",
    19: "MAJOR_19_TheSun",
    20: "MAJOR_20_Judgement",
    21: "MAJOR_21_TheWorld",
}

# 흔한 한글 표기(여러 변형 포함)
kr_variants = {
    0:  ["바보", "광대", "바보 카드", "광대 카드"],
    1:  ["마법사", "마술사", "마법사 카드", "마술사 카드"],
    2:  ["여사제", "여사제 카드", "여여사제"],  # 오타 대비
    3:  ["여황제", "여황제 카드", "황후", "황후 카드"],
    4:  ["황제", "황제 카드"],
    5:  ["교황", "법황", "교황 카드", "법황 카드", "히에로펀트"],
    6:  ["연인", "연인 카드", "러버스"],
    7:  ["전차", "전차 카드"],
    8:  ["힘", "힘 카드", "스트렝스"],
    9:  ["은둔자", "은둔자 카드", "허밋"],
    10: ["운명의 수레바퀴", "운명의바퀴", "운명의 수레바퀴 카드", "운명 수레바퀴"],
    11: ["정의", "정의 카드", "저스티스"],
    12: ["매달린 남자", "교수형 남자", "교수형", "매달린 남자 카드", "행맨"],
    13: ["죽음", "사신", "죽음 카드"],
    14: ["절제", "절제 카드", "템퍼런스"],
    15: ["악마", "악마 카드", "데빌"],
    16: ["탑", "타워", "탑 카드", "타워 카드"],
    17: ["별", "별 카드", "스타"],
    18: ["달", "달 카드", "문"],
    19: ["태양", "태양 카드", "선"],
    20: ["심판", "심판 카드", "저지먼트"],
    21: ["세계", "월드", "세계 카드", "월드 카드"],
}

def find_existing(path_wo_ext: str):
    """확장자 여러 개 중 실제 존재하는 파일 경로 반환"""
    for ext in EXTS:
        p = path_wo_ext + ext
        if os.path.exists(p):
            return p
    return None

def main(dry_run: bool = False):
    renamed, missing = [], []
    for num, variants in kr_variants.items():
        std = std_ids[num]
        # 후보 파일명 만들기(공백/카드 유무가 이미 포함되어 있지만 추가 변형도 시도)
        candidates = set(variants)
        more = []
        for v in variants:
            v2 = re.sub(r"\s*카드$", "", v)  # 뒤 '카드' 제거
            more.extend([v2, v2.replace(" ", ""), v.replace(" ", "")])
        candidates.update(more)

        found = None
        for name in candidates:
            path = find_existing(os.path.join(FOLDER, name))
            if path:
                found = path
                break

        if not found:
            missing.append((num, variants[0]))
            continue

        new_path = os.path.join(FOLDER, std + os.path.splitext(found)[1].lower())
        if os.path.abspath(found) == os.path.abspath(new_path):
            continue  # 이미 표준명
        if dry_run:
            print(f"[DRY] {found}  ->  {new_path}")
        else:
            os.rename(found, new_path)
            print(f"Renamed: {found}  ->  {new_path}")
            renamed.append((found, new_path))

    print("\n=== 요약 ===")
    print(f"리네임 완료: {len(renamed)}개")
    if missing:
        print(f"미발견: {len(missing)}개")
        for num, ex in missing:
            print(f" - {num:02d} ({std_ids[num]}): 예) '{ex}.jpg'")

if __name__ == "__main__":
    # 먼저 드라이런으로 확인
    # main(dry_run=True)
    # 확인 후 실제 변경
    main(dry_run=False)
