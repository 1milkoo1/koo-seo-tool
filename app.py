import streamlit as st
import pandas as pd
import re
import random
import io

# --- [중요] 1. 보안 설정 (이 부분이 맨 위에 있어야 합니다) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.set_page_config(page_title="🔒 보안 접속", layout="centered")
    st.title("🔒 KOO SEO 가공툴 접속")
    
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if password == "1234": # <--- 비밀번호를 바꾸려면 여기를 수정하세요!
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if not check_password():
    st.stop()

# --- 2. 가공 설정 및 로직 ---
FORBIDDEN_WORDS = ['돌돌이', '벨루아', '라떼', '이지라이프', '굿라이프', '슈슈앤', '플랜홈', '원마운트', '액티브원', '라테', '네추럴', '잔플라워', '그레타', '이지', '라이프홈']
CORE_ITEMS = ['정리함', '수납박스', '수납함', '스틱', '썬캡', '버킷햇', '거치대', '보관함', '트레이', '케이스', '머플러', '거울', '물주머니', '찜질팩', '안대', '마스크', '등산스틱']
COLORS = ['화이트', '블랙', '그레이', '아이보리', '베이지', '투명', '블루', '핑크', '그린', '레드', '옐로우', '네이비', '오렌지', '차콜', '스카이', '퍼플', '옐로', '브라운', '스노우']

def refine_final_naming(text, original_p):
    clean_text = re.sub(r'[^a-zA-Z0-9가-힣\s\(\)\[\]\-\_\/\&\,\.]', ' ', text)
    words = clean_text.split()
    if not words: return ""
    final_words = []
    for word in words:
        is_duplicate = False
        for checked in final_words:
            if word == checked or (len(word) >= 2 and len(checked) >= 2 and (word in checked or checked in word)):
                is_duplicate = True; break
        if not is_duplicate: final_words.append(word)
    found_core = next((item for item in CORE_ITEMS if item in original_p), "")
    if found_core and not any(found_core in w for w in final_words):
        final_words.insert(min(len(final_words), 2), found_core)
    return " ".join(final_words)

def advanced_refine_engine(row, p_col, k_col):
    try:
        raw_p = str(row[p_col]).strip() if pd.notna(row[p_col]) else ""
        raw_k = str(row[k_col]).strip() if pd.notna(row[k_col]) else ""
        if not raw_p: return ""
        temp_p = raw_p.replace('+', ' ')
        spec_pat = r'([0-9]+(?:\.[0-9]+)?(?:cm|mm|m|L|ml|kg|g|단|칸|종|구|p|개|세트|EA|set))'
        temp_p = re.sub(spec_pat, r' \1 ', temp_p)
        for c in COLORS: temp_p = re.sub(f"([^ ])({c})", r"\1 \2 ", temp_p)
        for core in CORE_ITEMS: 
            if core in temp_p: temp_p = temp_p.replace(core, f" {core} ")
        specs_in_p = re.findall(r'[0-9]+(?:\.[0-9]+)?(?:cm|mm|m|L|ml|kg|g|단|칸|종|구|p|개|세트|EA|set)', temp_p, re.IGNORECASE)
        k_list = [k.strip() for k in re.split(r'[,|/]+', raw_k) if len(k.strip()) >= 2]
        safe_keywords = [k for k in k_list if not any(fw in k for fw in FORBIDDEN_WORDS)]
        selected_k = random.choice(safe_keywords) if safe_keywords else ""
        front_specs = [s for s in specs_in_p if any(u in s for u in ['단', '칸', '종', '구'])]
        measure_specs = [s for s in specs_in_p if any(u in s.lower() for u in ['cm', 'mm', 'm', 'l', 'ml', 'kg', 'g'])]
        quantity = [s for s in specs_in_p if any(u in s.lower() for u in ['p', '개', 'ea'])]
        set_word = "세트" if any(x in temp_p.lower() for x in ["세트", "set"]) else ""
        combined_qty = quantity[0] if quantity else (set_word if set_word else "")
        clean_p = temp_p
        for s in specs_in_p + COLORS + FORBIDDEN_WORDS + ["세트", "set"]: clean_p = clean_p.replace(s, " ")
        p_words = [w for w in clean_p.split() if len(w) >= 2]
        core_name = p_words[-1] if p_words else ""
        color_vals = [c for c in COLORS if c in temp_p]
        color_str = " ".join(color_vals[:2])
        seo_list = [s for s in [selected_k, measure_specs[0] if measure_specs else None, front_specs[0] if front_specs else None, core_name, combined_qty, color_str] if s]
        return refine_final_naming(" ".join(seo_list), raw_p)
    except: return raw_p

# --- 3. 앱 화면 구성 ---
st.title("🧚 KOO전용 SEO 상품명 가공 마스터")
uploaded_file = st.file_uploader("가공할 엑셀 파일을 업로드하세요", type=["xlsx"])
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    row_count = len(df_raw)
    cols = df_raw.columns.tolist()
    p_col = next((c for c in cols if '상품명' in str(c) and '최종' not in str(c)), None)
    k_col = next((c for c in cols if '키워드' in str(c)), None)
    if p_col and k_col:
        col1, col2 = st.columns([1, 4])
        with col1: process_btn = st.button("✨ 조합 무한 가공 시작!")
        with col2: st.markdown(f"**<div style='padding-top: 10px;'>📂 현재 가공 대기 리스트: {row_count:,}개</div>**", unsafe_allow_html=True)
        if process_btn:
            with st.spinner(f'{row_count:,}개의 상품명을 SEO 최적화 중입니다...'):
                df_raw['최종_조합_상품명'] = df_raw.apply(lambda row: advanced_refine_engine(row, p_col, k_col), axis=1)
                st.success(f"✅ 총 {row_count:,}개 리스트 가공 완료!")
                st.dataframe(df_raw[[p_col, '최종_조합_상품명']], use_container_width=True)
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    df_raw.to_excel(writer, index=False)
                st.download_button("📥 가공 결과 다운로드", out.getvalue(), f"KOO_SEO_Result.xlsx")
