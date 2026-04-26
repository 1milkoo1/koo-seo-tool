import streamlit as st
import pandas as pd
import re
import random
import io

# 1. 매칭용 텍스트 정제
def clean_for_match(text):
    if not text: return ""
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(text))

# 2. SEO 최적화 및 글자수 제어 엔진
def seo_optimized_cleaner(keyword, mods_list, person_info, noun, count_info, unit_info, color_tail):
    # 인원 정보 (명사 앞 배치용)
    p_part = [str(person_info).strip()] if str(person_info).strip() and str(person_info).lower() != 'nan' else []
    
    # 키워드/수식어 그룹 정제 및 중복 제거
    check_group = []
    if keyword: check_group.append(keyword)
    check_group.extend(mods_list)
    check_group = [str(w).strip() for w in check_group if str(w).strip() and str(w).strip().lower() != 'nan']
    
    cleaned_front = []
    for i, word in enumerate(check_group):
        is_redundant = False
        for j, other in enumerate(check_group):
            if i == j: continue
            if word == other and i > j: is_redundant = True; break
            if len(word) < len(other) and word in other: is_redundant = True; break
        if not is_redundant: cleaned_front.append(word)
    
    # 명사 뒤 배치 정보 (개수, 단위, 색상)
    count_part = [str(count_info).strip()] if str(count_info).strip() and str(count_info).lower() != 'nan' else []
    unit_part = [str(unit_info).strip()] if str(unit_info).strip() and str(unit_info).lower() != 'nan' else []
    c_part = [str(c).strip() for c in color_tail if str(c).strip() and str(c).strip().lower() != 'nan']
    
    # [순서] 키워드/수식어 + 인원 + 명사 + 개수 + 단위 + 색상
    current_parts = cleaned_front + p_part + [noun] + count_part + unit_part + c_part
    
    # 35자 제한 로직 (글자수 초과 시 색상 -> 수식어 순 삭제)
    if len(" ".join(current_parts)) >= 35:
        if c_part: c_part = [] 
        while len(" ".join(cleaned_front + p_part + [noun] + count_part + unit_part + c_part)) >= 35 and len(cleaned_front) > 1:
            cleaned_front.pop() 
            
    return cleaned_front + p_part + [noun] + count_part + unit_part + c_part

# 3. 핵심 조립 엔진 V8.71
def v8_engine(idx, row, master_df, k_col, p_col, prev_keywords, run_seed):
    try:
        random.seed(run_seed + idx)
        
        # 전략적 색상 필터링 리스트
        TARGET_COLORS = [
            "블랙", "네이비", "챠콜", "검정", "다크그레이", "진네이비", "밤색", "먹색",
            "화이트", "아이보리", "베이지", "크림", "연베이지", "샌드", "오프화이트"
        ]
        
        raw_k = str(row.get(k_col, '')).strip()
        k_list = [k.strip() for k in re.split(r'[,|/]+', raw_k) if len(k.strip()) >= 2]
        
        orig_name = str(row.get(p_col, '')).strip()
        clean_orig = clean_for_match(orig_name)
        master_match = master_df[master_df.iloc[:, 0].apply(clean_for_match) == clean_orig]

        if not master_match.empty:
            m_data = master_match.iloc[0]
            noun = str(m_data.iloc[2]).strip()
            mods = [str(m_data.iloc[i]).strip() for i in range(3, 7) if str(m_data.iloc[i]).strip()]
            
            person_info = str(m_data.iloc[7]).strip() # H열 (인원)
            count_info = str(m_data.iloc[8]).strip()  # I열 (개수)
            unit_info = str(m_data.iloc[9]).strip()   # J열 (단위)
            raw_color = str(m_data.iloc[10]).strip()
            
            color_tail = []
            if raw_color and raw_color.lower() != 'nan':
                if any(tc in raw_color for tc in TARGET_COLORS):
                    color_tail = [raw_color]

            # --- [필터 조건] 숫자 감지 및 P/p 포함 여부 체크 ---
            has_quantity = any(re.search(r'\d', str(t)) for t in [person_info, count_info, unit_info])
            # 대소문자 구분 없이 p나 P가 포함되어 있는지 체크
            is_p_target = 'p' in (orig_name + person_info + count_info + unit_info).lower()
            
            random.shuffle(mods)
            selected_k = ""
            if k_list:
                shuffled_k_list = k_list.copy()
                random.shuffle(shuffled_k_list)
                for k in shuffled_k_list:
                    if (noun not in k) and (k not in prev_keywords[-3:]):
                        selected_k = k
                        break
                if not selected_k:
                    for k in shuffled_k_list:
                        if noun not in k: selected_k = k; break
                if not selected_k: selected_k = shuffled_k_list[0]

            prev_keywords.append(selected_k)

            # --- [세트 삭제 로직] P타입이고 수량이 감지될 때만 실행 ---
            # '4세트'처럼 p가 없는 경우는 이 로직을 타지 않아 '세트'가 유지됩니다.
            if has_quantity and is_p_target:
                selected_k = selected_k.replace("세트", "").strip()
                noun = noun.replace("세트", "").strip()
                person_info = person_info.replace("세트", "").strip()
                count_info = count_info.replace("세트", "").strip()
                unit_info = unit_info.replace("세트", "").strip()
                mods = [m.replace("세트", "").strip() for m in mods]

            final_parts = seo_optimized_cleaner(selected_k, mods, person_info, noun, count_info, unit_info, color_tail)
            final_str = " ".join(final_parts).strip()
            final_str = final_str.replace("/", " ").replace("<", " ")
            final_str = re.sub(r'\s+', ' ', final_str).strip()
            
            return final_str
        
        return f"[사전미등록] {orig_name}"
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- UI Layout ---
st.set_page_config(page_title="KOO전용 V8.71", layout="wide")
st.title("🧚 KOO전용 상품명 마스터 V8.71")

if 'run_count' not in st.session_state:
    st.session_state.run_count = 0

master_file = st.sidebar.file_uploader("1. 사전 업로드(xlsx)", type=["xlsx"])
target_file = st.file_uploader("2. 작업 대상 업로드(xlsx)", type=["xlsx"])

if master_file and target_file:
    # 사전 데이터 로드
    raw_m_df = pd.read_excel(master_file, header=None)
    header_row_idx = 0
    for i, r in raw_m_df.iterrows():
        if '명사' in r.values: 
            header_row_idx = i
            break
    m_df = pd.read_excel(master_file, skiprows=header_row_idx).fillna("")
    
    # 작업 대상 데이터 로드
    t_df = pd.read_excel(target_file).fillna("")
    t_df.columns = [str(c).strip() for c in t_df.columns]
    
    p_col = next((c for c in t_df.columns if '상품명' in str(c) and '최종' not in str(c)), t_df.columns[0])
    k_col = next((c for c in t_df.columns if '키워드' in str(c)), None)

    # --- 가공 대기 리스트 개수 표시 ---
    st.info(f"📂 현재 가공 대기 리스트: {len(t_df)}개 상품")

    if st.button("✨ 통합 최적화 가공 시작"):
        st.session_state.run_count += random.randint(1, 9999)
        prev_keywords = []
        results = []
        for i, row in t_df.iterrows():
            res = v8_engine(i, row, m_df, k_col, p_col, prev_keywords, st.session_state.run_count)
            results.append(res)
        
        t_df['최종_조합_상품명'] = results
        st.success("✅ 가공 완료!")
        st.dataframe(t_df[[p_col, '최종_조합_상품명']].head(500), use_container_width=True)
        
        # 엑셀 다운로드 파일 생성
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            t_df.to_excel(writer, index=False)
        st.download_button(
            label="📥 결과 다운로드",
            data=out.getvalue(),
            file_name=f"KOO_V8_71_Result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
