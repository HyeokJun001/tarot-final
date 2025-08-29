# rename_tarot_majors_v2.py
import os, re, unicodedata

FOLDER = "cards"
EXTS = (".jpg", ".jpeg", ".png", ".webp")

# 표준 ID (Rider–Waite 번호)
STD_IDS = {
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

# 한글 변형(자주 쓰는 표기)
KR_VARIANTS = {
    0:  ["바보", "광대"],
    1:  ["마법사", "마술사"],
    2:  ["여사제"],
    3:  ["여황제", "황후"],
    4:  ["황제"],
    5:  ["교황", "법황", "히에로펀트"],
    6:  ["연인", "러버스"],
    7:  ["전차"],
    8:  ["힘", "스트렝스"],
    9:  ["은둔자", "허밋"],
    10: ["운명의수레바퀴", "운명의 수레바퀴", "운명수레바퀴"],
    11: ["정의", "저스티스"],
    12: ["매달린남자", "매달린 남자", "교수형남자", "교수형", "행맨"],
    13: ["죽음", "사신"],
    14: ["절제", "템퍼런스"],
    15: ["악마", "데빌"],
    16: ["탑", "타워"],
    17: ["별", "스타"],
    18: ["달", "문"],
    19: ["태양", "선"],
    20: ["심판", "저지먼트"],
    21: ["세계", "월드"],
}

def normalize(s: str) -> str:
    """번호/점/공백/괄호/특수문자/‘카드’ 제거 후 소문자화"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"^\s*\d+\s*[._-]?\s*", "", s)   # 앞쪽 번호/점/대쉬 제거 (예: '10. ', '10 - ')
    s = re.sub(r"\.(jpg|jpeg|png|webp)$", "", s, flags=re.I)  # 확장자 제거
    s = re.sub(r"\s*카드$", "", s)              # 끝 '카드' 제거
    s = re.sub(r"[\s\[\]\(\)\-_/·•]+", "", s)   # 공백/구분자 제거
    return s.lower()

def scan_files(folder: str):
    files = []
    for name in os.listdir(folder):
        if name.lower().endswith(EXTS):
            files.append(name)
    return files

def main(dry_run=True):
    files = scan_files(FOLDER)
    norm_to_file = {}
    for f in files:
        base = normalize(f)
        norm_to_file.setdefault(base, []).append(f)

    # 각 번호별로 매칭 시도
    renamed, missing, conflicts = [], [], []
    for num, variants in KR_VARIANTS.items():
        targets = set()
        for v in variants:
            targets.add(normalize(v))
            targets.add(normalize(v + " 카드"))
        # 후보 중 존재하는 파일 찾기
        matches = []
        for t in targets:
            if t in norm_to_file:
                matches.extend(norm_to_file[t])

        matches = sorted(set(matches))
        if not matches:
            missing.append((num, variants[0]))
            continue
        if len(matches) > 1:
            conflicts.append((num, matches))
            continue

        found = matches[0]
        std = STD_IDS[num]
        new = std + os.path.splitext(found)[1].lower()
        if found == new:
            continue
        if dry_run:
            print(f"[DRY] {found} -> {new}")
        else:
            os.rename(os.path.join(FOLDER, found), os.path.join(FOLDER, new))
            print(f"Renamed: {found} -> {new}")
            renamed.append((found, new))

    print("\n=== 요약 ===")
    print(f"리네임 후보: {len(files)}개")
    if dry_run:
        print("※ 현재 DRY RUN 모드(미적용). 확인 후 dry_run=False로 바꿔 실행하세요.")

    if missing:
        print(f"미발견: {len(missing)}개")
        for num, ex in missing:
            print(f" - {num:02d} ({STD_IDS[num]}): 예시 '{ex}.jpg'")
    if conflicts:
        print(f"다중매칭(수동확인 필요): {len(conflicts)}개")
        for num, lst in conflicts:
            print(f" - {num:02d} ({STD_IDS[num]}): {lst}")

if __name__ == "__main__":
    # 1) 먼저 DRY RUN으로 무엇이 바뀌는지 확인
    main(dry_run=True)

    # 2) 이상 없으면 아래 줄 주석 풀어서 실제 변경 실행
    main(dry_run=False)

