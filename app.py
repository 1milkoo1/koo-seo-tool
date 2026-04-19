import streamlit as st
import pandas as pd
import re
import random
import io

# 1. 매칭용 텍스트 정제 (특수문자, 공백 무시)
def clean_for_match(text):
    if not text: return ""
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(text))

# 2. SEO 최적화 및 중복 단어 필터링 (순서 유지형)
def seo_optimized_cleaner(keyword, body_list, tail_list):
    """
    [절대 규칙]
    - 입력을 [키워드 -> 본문 -> 단위 -> 색상] 순으로 유지
    - 앞서 등장한 단어가 뒤의 단어를 포함하면 뒤의 단어를 삭제 (긴 단어 우선 생존)
    """
    all_candidates = []
    if keyword: all_candidates.append(keyword)
    all_candidates.extend(body_list)
    all_candidates.extend(tail_list)
    
    all_candidates = [str(w).strip() for w in all_candidates if str(w).strip() and str(w).strip().lower() != 'nan']
    
    final_res = []
    for i, word in enumerate(all_candidates):
        is_redundant = False
        for j, other in enumerate(all_candidates):
            if i == j: continue
            # 완전 일치 중복 제거 (먼저 나온 쪽 유지)
            if word == other and i > j:
                is_redundant = True
                break
            # 포함 관계 제거 (긴 단어 안에 짧은 단어가 있으면 짧은 쪽 삭제)
            if len(word) < len(other) and word in other:
                is_redundant = True
                break
        if not is_redundant:
            final_res.append(word)
            
    return final_res

# 3. 핵심 조립 엔진
def v8_30_engine(row, master_df, k_col, p_col):
    try:
        raw_k = str(row.get(k_col, '')).strip()
        k_list = [k.strip() for k in re.split(r'[,|/]+', raw_k) if len(k.strip()) >= 2]
        selected_k = random.choice(k_list) if k_list else ""

        orig_name = str(row.get(p_col, '')).strip()
        clean_orig = clean_for_match(orig_name)
        master_match = master_df[master_df.iloc[:, 0].apply(clean_for_match) == clean_orig]

        if not master_match.empty:
            m_data = master_match.iloc[0]
            
            # 사전 데이터 직접 수집
            noun = str(m_data.iloc[2]).strip()
            mods = [str(m_data.iloc[i]).strip() for i in range(3, 7) if str(m_data.iloc[i]).strip()]
            info_tails = [str(m_data.iloc[i]).strip() for i in range(7, 10) if str(m_data.iloc[i]).strip()]
            color_tail = [str(m_data.iloc[10]).strip()] if str(m_data.iloc[10]).strip() and str(m_data.iloc[10]).lower() != 'nan' else []

            # 세트 제거 로직
            has_quantity = any(re.search(r'\d', str(t)) for t in info_tails)
            if has_quantity:
                selected_k = selected_k.replace("세트", "").strip()
                noun = noun.replace("세트", "").strip()
                mods = [m.replace("세트", "").strip() for m in mods]
                info_tails = [t.replace("세트", "").strip() for t in info_tails]

            mix_body = [noun] + mods
            random.shuffle(mix_body)

            final_list = seo_optimized_cleaner(selected_k, mix_body, info_tails + color_tail)
            return " ".join(final_list).strip()
        else:
            return f"[사전미등록] {orig_name}"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 4. UI
st.set_page_config(page_title="KOO전용 상품명 마스터 V8.30", layout="wide")
st.title("🧚KOO전용 상품명 마스터 V8.30")

master_file = st.sidebar.file_uploader("1. 사전(Master) 업로드", type=["xlsx"])
target_file = st.file_uploader("2. 작업 대상(Target) 업로드", type=["xlsx"])

if master_file and target_file:
    raw_m_df = pd.read_excel(master_file, header=None)
    header_row_idx = 0
    for i, r in raw_m_df.iterrows():
        if '명사' in r.values:
            header_row_idx = i
            break
    m_df = pd.read_excel(master_file, skiprows=header_row_idx).fillna("")
    
    t_df = pd.read_excel(target_file).fillna("")
    t_df.columns = [str(c).strip() for c in t_df.columns]
    
    st.info(f"📂 현재 가공 대기 리스트: {len(t_df)}개 상품")

    p_col = next((c for c in t_df.columns if '상품명' in str(c) and '최종' not in str(c)), t_df.columns[0])
    k_col = next((c for c in t_df.columns if '키워드' in str(c)), None)

    if st.button("✨랜덤조합 가공 시작"):
        with st.spinner("KOO 마스터 엔진 가동 중..."):
            t_df['최종_조합_상품명'] = t_df.apply(lambda row: v8_30_engine(row, m_df, k_col, p_col), axis=1)
        
        st.success("✅ 가공 완료!")
        st.dataframe(t_df[[p_col, '최종_조합_상품명']].head(500), use_container_width=True)
        
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            t_df.to_excel(writer, index=False)
        st.download_button("📥 결과 다운로드", out.getvalue(), "KOO_MASTER_V8_30_Result.xlsx")
