# app.py — Tarot Reader (78-card click-to-reveal)
# -------------------------------------------------
# - 78장 타로(메이저22 + 마이너56) 뒷면 그리드
# - 스프레드로 뽑을 장수 자동 결정
# - 선택 후 공개: 카드 이미지/명칭/정·역위/카테고리별 의미
# - 규칙형 종합 요약 + 한두 줄 자연어 요약
# - 데이터: ./data/cards.json, ./data/spreads.json, (선택) ./data/combos.json
# - 이미지: ./cards/{id}.jpg, 뒷면: ./assets/card_back.png
# -------------------------------------------------

import json
import random
from pathlib import Path
from typing import List, Dict, Any

from io import BytesIO
import math

import streamlit as st
from PIL import Image

# ========================= 설정 =========================
APP_TITLE = "클릭형 타로 리딩"
CARD_BACK_PATH = Path("assets/card_back.png")  # 뒷면 공용 이미지
CARDS_DIR = Path("cards")                      # 각 카드 앞면 이미지 폴더
DATA_DIR = Path("data")
CARDS_JSON = DATA_DIR / "cards.json"           # 카드 메타/의미 데이터
COMBOS_JSON = DATA_DIR / "combos.json"         # 조합 규칙 데이터(선택)

GRID_COLS = 13
DEFAULT_REVERSED_PROB = 0.5

# ========================= 캐시/로딩 =========================
@st.cache_data(show_spinner=False)
def load_cards() -> List[Dict[str, Any]]:
    with open(CARDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(show_spinner=False)
def load_combos() -> List[Dict[str, Any]]:
    if COMBOS_JSON.exists():
        with open(COMBOS_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_resource(show_spinner=False)
def get_back_image() -> Image.Image:
    return Image.open(CARD_BACK_PATH)
@st.cache_resource(show_spinner=False)
def get_back_thumb(width: int) -> Image.Image:
    """뒷면 이미지를 지정 너비로 1회만 리사이즈하여 캐시."""
    img = Image.open(CARD_BACK_PATH).convert("RGBA")
    w, h = img.size
    if w > width:  # 필요할 때만 축소
        ratio = width / float(w)
        img = img.resize((width, int(h * ratio)), Image.LANCZOS)
    return img

@st.cache_resource(show_spinner=False)
def get_back_thumb_bytes(width: int) -> bytes:
    """streamlit 렌더링 부담을 줄이기 위해 메모리 바이트로 캐시."""
    img = get_back_thumb(width)
    buf = BytesIO()
    # PNG 그대로 써도 되고, 더 가볍게 하려면 WebP:
    # img.save(buf, format="WEBP", quality=85, method=6)
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

@st.cache_resource(show_spinner=False)
def get_front_image(card_id: str) -> Image.Image:
    path = CARDS_DIR / f"{card_id}.jpg"
    return Image.open(path)

# ========================= 종합 해석 로직 =========================
# ========================= 종합 해석 로직 =========================
CATEGORY_KEYS = ["general", "love", "career", "finance", "health", "advice"]

def summarize_drawn(cards: List[Dict[str, Any]]) -> Dict[str, str]:
    """간단 규칙 기반 요약 + (있다면) 콤보 룰 적용"""
    if not cards:
        return {k: "" for k in CATEGORY_KEYS}

    majors = sum(1 for c in cards if c.get("arcana") == "major")
    reversed_cnt = sum(1 for c in cards if c.get("is_reversed"))
    suits = {"wands": 0, "cups": 0, "swords": 0, "pentacles": 0}
    for c in cards:
        s = c.get("suit")
        if s in suits:
            suits[s] += 1

    def cat_text(cat: str) -> str:
        lines = []
        for c in cards:
            blk = c["reversed" if c.get("is_reversed") else "upright"]
            txt = blk.get(cat, "")
            if txt:
                lines.append(txt)
        return " / ".join(lines[:3])

    combos = load_combos()
    combo_msgs = {k: [] for k in CATEGORY_KEYS}
    # 콤보 패턴 매칭은 name_en → 없으면 name_kr → 없으면 id
    names_in_order = [c.get("name_en") or c.get("name_kr") or c.get("id") for c in cards]

    for rule in combos:
        pattern: List[str] = rule.get("pattern", [])
        if not pattern:
            continue
        try:
            start = 0
            for token in pattern:
                idx = names_in_order.index(token, start)
                start = idx + 1
            # 순서대로 전부 발견 → 룰 트리거
            for cat in CATEGORY_KEYS:
                msg = rule.get(cat) or rule.get("general")
                if msg:
                    combo_msgs[cat].append(msg)
        except ValueError:
            continue

    header = (
        f"메이저:{majors} / 마이너:{len(cards)-majors}, "
        f"역위:{reversed_cnt}, "
        f"슈트(완드/컵/소드/펜타클): {suits['wands']}/{suits['cups']}/{suits['swords']}/{suits['pentacles']}"
    )

    summary = {k: cat_text(k) for k in CATEGORY_KEYS}
    for k in CATEGORY_KEYS:
        if combo_msgs[k]:
            summary[k] = (summary[k] + " | " if summary[k] else "") + " | ".join(combo_msgs[k][:2])
    summary["general"] = header + ("\n" + summary["general"] if summary["general"] else "")
    return summary


# ---- 여기를 전역(함수 밖)으로 꼭 둬야 함! ----
def _pick_text_from_card(card: Dict[str, Any], focus: str) -> str:
    """포커스(연애/직업/금전/건강/조언) 우선으로 카드 한 장에서 한 줄 선택"""
    blk = card["reversed" if card.get("is_reversed") else "upright"]
    order_map = {
        "love":   ["love", "advice", "general", "career", "finance", "health"],
        "career": ["career", "advice", "general", "finance", "love", "health"],
        "finance":["finance","advice","general","career","love","health"],
        "health": ["health","advice","general","career","finance","love"],
        "advice": ["advice","general","career","finance","health","love"],
    }
    order = order_map.get(focus, ["advice","general","career","finance","health","love"])
    for k in order:
        t = (blk.get(k) or "").strip()
        if t:
            return t
    return ""


def build_position_story(picked: List[Dict[str, Any]], current_spread: Dict[str, Any], focus: str) -> str:
    """
    positions 항목이
      - ["과거","현재","미래"] 같은 '문자열 리스트' 이거나
      - [{"title":"과거","role":"past"}, ...] 같은 '딕셔너리 리스트'
    둘 다 동작하도록 방어적으로 처리.
    """
    # 1) positions 추출 + 정규화
    raw_positions = (current_spread or {}).get("positions", []) or []
    pos_defs: List[Dict[str, Any]] = []
    for p in raw_positions:
        if isinstance(p, dict):
            pos_defs.append(p)
        elif isinstance(p, str):
            pos_defs.append({"title": p})
        else:
            pos_defs.append({"title": f"포지션 {len(pos_defs)+1}"})

    # 만약 포지션 개수가 카드보다 적으면 기본 타이틀로 채워줌
    if len(pos_defs) < len(picked):
        for i in range(len(pos_defs), len(picked)):
            pos_defs.append({"title": f"포지션 {i+1}"})

    # 2) 라인 작성
    lines = []
    for i, card in enumerate(picked):
        pos = pos_defs[i] if i < len(pos_defs) else {}
        title = pos.get("title") or f"포지션 {i+1}"
        role  = (pos.get("role") or "").lower()  # past/present/future/advice/obstacle/outcome...

        name_kr = card.get("name_kr")
        name_en = card.get("name_en") or card.get("name") or card.get("id")
        display = f"{name_kr} ({name_en})" if (name_kr and name_en and name_en != name_kr) else (name_kr or name_en)

        t = _pick_text_from_card(card, focus=focus)
        if not t:
            t = "지금은 균형과 조율이 필요한 흐름으로 보여요." if not card.get("is_reversed") else "먼저 방향을 가다듬고 정리하면 좋아 보여요."

        head = {
            "past":    "과거 흐름을 보면, ",
            "present": "현재 상황에서는, ",
            "future":  "앞으로의 흐름은, ",
            "advice":  "조언으로는, ",
            "obstacle":"장애/주의 포인트로는, ",
            "outcome": "결과적으로, ",
        }.get(role, "")

        tail = "" if t.endswith(("요.", "요!", "요?")) else " 같아요."
        ori = "역위" if card.get("is_reversed") else "정위"
        meta = f" (*{ori}*)"

        lines.append(f"**{i+1}. {title} — {display}**{meta}\n- {head}{t}{tail}")

    return "\n\n".join(lines)# ---- 여기까지가 전역 정의! ----


def compose_fluent_summary(cards: List[Dict[str, Any]], focus: str = "love") -> str:
    """정/역위·슈트·메이저 비율 기반으로 1~2문장 자연어 요약."""
    n = len(cards)
    majors = sum(1 for c in cards if c.get("arcana") == "major")
    reversed_cnt = sum(1 for c in cards if c.get("is_reversed"))
    suits = {"wands":0, "cups":0, "swords":0, "pentacles":0}
    for c in cards:
        s = c.get("suit")
        if s in suits:
            suits[s] += 1

    mood = []
    if majors >= max(1, n//2): mood.append("큰 전환점")
    if reversed_cnt >= max(1, n//3): mood.append("조정이 필요한 신호")
    if suits["wands"] >= 2: mood.append("열정과 실행력")
    if suits["cups"]  >= 2: mood.append("감정과 관계")
    if suits["swords"]>= 2: mood.append("사고와 판단")
    if suits["pentacles"]>=2: mood.append("현실과 안정")
    mood_txt = "와 ".join(mood) if mood else "균형"

    # 포커스 카테고리에서 상위 1~2개 문장만 뽑아 연결
    lines = []
    for c in cards:
        blk = c["reversed" if c.get("is_reversed") else "upright"]
        t = (blk.get(focus) or "").strip()
        if t:
            lines.append(t)
    lines = lines[:2]

    first = f"지금 흐름은 **{mood_txt}** 쪽으로 기울어 보입니다."
    second = " ".join(lines).replace("  ", " ").strip()
    return (first + (" " + second if second else "")).strip()

def compose_fluent_summary(cards: List[Dict[str, Any]], focus: str = "love") -> str:
    """정/역위·슈트·메이저 비율 기반으로 1~2문장 자연어 요약."""

    def _pick_text_from_card(card: Dict[str, Any], focus: str) -> str:
        """
        카드 1장의 텍스트를 포커스(연애/직업/금전/건강/조언) 우선으로 고르고,
        없으면 다른 카테고리로 유연하게 폴백.
        """
        blk = card["reversed" if card.get("is_reversed") else "upright"]
        order_map = {
            "love": ["love", "advice", "general", "career", "finance", "health"],
            "career": ["career", "advice", "general", "finance", "love", "health"],
            "finance": ["finance", "advice", "general", "career", "love", "health"],
            "health": ["health", "advice", "general", "career", "finance", "love"],
            "advice": ["advice", "general", "career", "finance", "health", "love"],
        }
        order = order_map.get(focus, ["advice", "general", "career", "finance", "health", "love"])
        for k in order:
            t = (blk.get(k) or "").strip()
            if t:
                return t
        return ""

    def build_position_story(picked: List[Dict[str, Any]], current_spread: Dict[str, Any], focus: str) -> str:
        """
        스프레드의 positions 순서대로 카드 해석을 1~2문장으로 생성.
        spreads.json 예시:
        {
          "three_cards_ppf": {
            "name": "3장 (과거-현재-미래)",
            "positions": [
              {"title":"과거","role":"past"},
              {"title":"현재","role":"present"},
              {"title":"미래","role":"future"}
            ]
          }
        }
        role이 없어도 title만으로 동작.
        """
        pos_defs = current_spread.get("positions", [])
        lines = []
        for i, card in enumerate(picked):
            pos = pos_defs[i] if i < len(pos_defs) else {}
            title = pos.get("title") or f"포지션 {i + 1}"
            role = (pos.get("role") or "").lower()  # past/present/future/advice/obstacle/outcome...

            # 카드 표시명
            name_kr = card.get("name_kr")
            name_en = card.get("name_en") or card.get("name") or card.get("id")
            display = f"{name_kr} ({name_en})" if (name_kr and name_en and name_en != name_kr) else (name_kr or name_en)

            # 포커스 기준 한 줄
            t = _pick_text_from_card(card, focus=focus)
            if not t:
                t = "지금은 균형과 조율이 필요한 흐름으로 보여요." if not card.get("is_reversed") else "먼저 방향을 가다듬고 정리하면 좋아 보여요."

            # role별 자연스러운 머리말
            head = {
                "past": "과거 흐름을 보면, ",
                "present": "현재 상황에서는, ",
                "future": "앞으로의 흐름은, ",
                "advice": "조언으로는, ",
                "obstacle": "장애/주의 포인트로는, ",
                "outcome": "결과적으로, ",
            }.get(role, "")

            tail = "" if t.endswith(("요.", "요!", "요?")) else " 같아요."
            ori = "역위" if card.get("is_reversed") else "정위"
            meta = f" (*{ori}*)"  # 정/역위 표기

            lines.append(f"**{i + 1}. {title} — {display}**{meta}\n- {head}{t}{tail}")

        return "\n\n".join(lines)

    n = len(cards)
    majors = sum(1 for c in cards if c.get("arcana") == "major")
    reversed_cnt = sum(1 for c in cards if c.get("is_reversed"))
    suits = {"wands": 0, "cups": 0, "swords": 0, "pentacles": 0}
    for c in cards:
        s = c.get("suit")
        if s in suits:
            suits[s] += 1

    mood = []
    if majors >= max(1, n // 2):
        mood.append("큰 전환점")
    if reversed_cnt >= max(1, n // 3):
        mood.append("조정이 필요한 신호")
    if suits["wands"] >= 2:
        mood.append("열정과 실행력")
    if suits["cups"] >= 2:
        mood.append("감정과 관계")
    if suits["swords"] >= 2:
        mood.append("사고와 판단")
    if suits["pentacles"] >= 2:
        mood.append("현실과 안정")

    mood_txt = "와 ".join(mood) if mood else "균형"

    # 포커스 카테고리에서 상위 1~2개 문장만 뽑아 연결
    lines = []
    for c in cards:
        blk = c["reversed" if c.get("is_reversed") else "upright"]
        t = (blk.get(focus) or "").strip()
        if t:
            lines.append(t)
    lines = lines[:2]
    first = f"지금 흐름은 **{mood_txt}** 쪽으로 기울어 보입니다."
    second = " ".join(lines).replace("  ", " ").strip()
    return (first + (" " + second if second else "")).strip()

# ========================= 앱 본문 =========================
st.set_page_config(page_title=APP_TITLE, page_icon="🔮", layout="wide")
st.title(APP_TITLE)

cards_master = load_cards()
back_img = get_back_image()

with open("data/spreads.json", "r", encoding="utf-8") as f:
    SPREADS = json.load(f)

# ===== 사이드바 =====
with st.sidebar:
    st.header("설정")

    # 스프레드 선택 → 장수 자동 결정
    spread_key = st.selectbox(
        "🔮 스프레드 선택",
        list(SPREADS.keys()),
        format_func=lambda k: SPREADS[k]["name"]
    )
    current_spread = SPREADS[spread_key]
    num_cards = len(current_spread["positions"])
    st.info(f"👉 이 스프레드는 **{num_cards}장**을 뽑습니다.")

    # 역위 옵션
    allow_reversed = st.checkbox("역위치 포함", value=True)
    reversed_prob = st.slider("역위치 확률", 0.0, 1.0, DEFAULT_REVERSED_PROB, 0.05, disabled=not allow_reversed)

    # 앞면 전용 이미지 크기
    front_img_size = st.slider("🖼️ 앞면 이미지 크기(px)", 100, 400, 200, 10)

    # 종합 요약 포커스(연애/직업/금전/건강/조언)
    focus = st.selectbox("요약 포커스", ["love", "career", "finance", "health", "advice"], index=0,
                         format_func=lambda k: {"love":"연애","career":"직업","finance":"금전","health":"건강","advice":"조언"}[k])
    back_thumb_width=st.slider("뒷면 썸네일 너비(px)", 120,220,160,10)

    st.divider()
    if st.button("새로 섞기 / 초기화", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 스프레드 변경 시 선택 초기화
if "last_spread" not in st.session_state:
    st.session_state.last_spread = spread_key
if st.session_state.last_spread != spread_key:
    st.session_state.selected_ids = []
    st.session_state.last_spread = spread_key

# 초기 덱/선택 상태
if "deck" not in st.session_state:
    deck = cards_master.copy()
    random.shuffle(deck)
    for c in deck:
        c["is_reversed"] = allow_reversed and (random.random() < reversed_prob)
    st.session_state.deck = deck

if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []

# ===== 78장 뒷면 그리드 =====
st.subheader("카드를 선택하세요 (뒷면 클릭)")
cols = st.columns(GRID_COLS)

for idx, card in enumerate(st.session_state.deck):
    col = cols[idx % GRID_COLS]
    with col:
        key = f"card_{card['id']}"
        selected = card["id"] in st.session_state.selected_ids

        st.image(get_back_thumb_bytes(back_thumb_width), caption=f"{idx+1}")
        if st.button("해제" if selected else "선택", key=key, use_container_width=True):
            if selected:
                st.session_state.selected_ids.remove(card["id"])
            else:
                if len(st.session_state.selected_ids) >= num_cards:
                    st.warning(f"이 스프레드는 최대 {num_cards}장까지 선택 가능합니다.")
                else:
                    st.session_state.selected_ids.append(card["id"])
            st.rerun()

st.caption(f"선택: {len(st.session_state.selected_ids)}/{num_cards}장")
picked = [c for c in st.session_state.deck if c['id'] in st.session_state.selected_ids]
st.info(f"선택: {len(picked)}/{num_cards}장")

# ===== 공개 섹션 =====
if len(picked) == num_cards:
    st.divider()
    st.subheader("🔓 공개된 카드")

    for i, c in enumerate(picked, start=1):
        img = get_front_image(c["id"])
        if c.get("is_reversed"):
            img = img.rotate(180)

        with st.container(border=True):
            name_kr = c.get("name_kr")
            name_en = c.get("name_en") or c.get("name") or c.get("id")
            display = f"{name_kr} ({name_en})" if (name_kr and name_en and name_en != name_kr) else (name_kr or name_en)

            st.markdown(f"**{i}. {display}**  —  {'역위' if c.get('is_reversed') else '정위'}")
            st.image(img, width=front_img_size)

            # 개요 탭 제거 → 5탭만 유지
            tabs = st.tabs(["연애", "직업", "금전", "건강", "조언"])
            blk = c["reversed" if c.get("is_reversed") else "upright"]
            with tabs[0]: st.write(blk.get("love", ""))
            with tabs[1]: st.write(blk.get("career", ""))
            with tabs[2]: st.write(blk.get("finance", ""))
            with tabs[3]: st.write(blk.get("health", ""))
            with tabs[4]: st.write(blk.get("advice", ""))

    # ===== 포지션별 스토리 =====
    st.divider()
    st.subheader("📜 포지션별 스토리")
    story_md = build_position_story(picked, current_spread, focus=focus)
    st.markdown(story_md)


    # ===== 종합 해석 =====
    st.divider()
    st.subheader("🧩 종합 해석")

    # 한두 줄 자연어 요약
    st.markdown("**요약(한두 줄)**")
    st.write(compose_fluent_summary(picked, focus=focus))

    # 상세 요약(기존)
    summary = summarize_drawn(picked)
    with st.expander("요약 보기", expanded=True):
        st.markdown(
            f"""
            **종합 개요**  
            {summary.get('general','')}

            **연애**: {summary.get('love','')}

            **직업**: {summary.get('career','')}

            **금전**: {summary.get('finance','')}

            **건강**: {summary.get('health','')}

            **조언**: {summary.get('advice','')}
            """
        )

# ========================= 푸터/도움말 =========================
    with st.expander("데이터/배포 가이드"):
        st.markdown(
        """
        **데이터 구조**
        - `data/cards.json`: 78장 메타/의미 (정위/역위, 카테고리별)
        - `data/spreads.json`: 스프레드 정의(포지션 타이틀/역할)
        - `data/combos.json`: 순서 의존 콤보 규칙(선택)
        - `cards/`: 각 카드 앞면 이미지(`{id}.jpg`)
        - `assets/card_back.png`: 공용 뒷면 이미지

        **배포 팁**
        - 이미지를 레포에 포함하면 Streamlit Community Cloud에서도 그대로 동작합니다.
        - 또는 절대 URL로 호스팅하고 `get_front_image`를 URL 로더로 바꿔도 됩니다.

        **저작권 주의**
        - 카드 일러스트 사용권 확인 필수. 의미 텍스트는 직접 작성/요약본 권장.
        - 모든 내용 작성 : 컴퓨터비전 B반 양혁준
        """
    )
