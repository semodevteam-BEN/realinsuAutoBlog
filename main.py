import streamlit as st
import os
import base64
from auth import authenticate_google_user, get_user_profile
from utils import get_rag_context
from generator import configure_gemini, generate_planning_step, generate_content_step, generate_image_prompt, list_available_models, generate_real_image
from blogger_api import upload_post, get_blog_info, get_blog_list

# 사용자 요청에 의한 API Key 고정 (Base64 Obfuscation)
_OBFUSCATED_KEY = "QUl6YVN5RG1UX3VVcElmSkxLbWtEcHpPMDlvMkJDM0pPRklPOU1F"


# 페이지 설정
st.set_page_config(
    page_title="SEO Blogger Auto-Poster",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: bold;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        margin-bottom: 1rem;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None
if 'gemini_api_key' not in st.session_state:
    # 초기화 시 암호화된 키 복호화하여 자동 설정
    try:
        if _OBFUSCATED_KEY:
            decoded_key = base64.b64decode(_OBFUSCATED_KEY).decode('utf-8')
            st.session_state.gemini_api_key = decoded_key
            configure_gemini(decoded_key) # 즉시 설정
        else:
            st.session_state.gemini_api_key = ""
    except Exception:
        st.session_state.gemini_api_key = ""

if 'current_step' not in st.session_state:
    st.session_state.current_step = 0 # 0: Input, 1: Plan, 2: Write, 3: Image, 4: Publish
if 'plan_result' not in st.session_state:
    st.session_state.plan_result = ""
if 'content_result' not in st.session_state:
    st.session_state.content_result = ""
if 'image_url' not in st.session_state:
    st.session_state.image_url = ""
if 'final_post_url' not in st.session_state:
    st.session_state.final_post_url = ""

# 사이드바: 설정 및 인증
with st.sidebar:
    st.title("⚙️ 설정")
    
    # 1. Google 인증
    if st.session_state.auth_creds:
        # 로그인 상태: 프로필 정보 표시 및 로그아웃
        try:
            # 프로필 정보 가져오기 시도 (토큰 만료 등으로 실패할 수 있음)
            user_profile = get_user_profile(st.session_state.auth_creds)
            
            if user_profile:
                # 프로필 카드 디자인
                st.markdown(f"""
                <div style="background-color: #f1f3f4; padding: 15px; border-radius: 10px; display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <img src="{user_profile.get('picture', '')}" style="width: 40px; height: 40px; border-radius: 50%;">
                    <div>
                        <div style="font-weight: bold; font-size: 14px; color: #333;">{user_profile.get('name', 'User')}</div>
                        <div style="font-size: 12px; color: #666;">{user_profile.get('email', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.info("로그인 상태입니다.")
        except:
             st.warning("프로필 정보를 불러오지 못했습니다.")

        if st.button("🚪 로그아웃 (Logout)", type="primary"):
            st.session_state.auth_creds = None
            st.rerun()

        st.divider()

        # 2. 모델 선택 (로그인 시에만 노출)
        # st.subheader("2. Gemini Model 선택")
        if st.session_state.gemini_api_key:
            if 'available_models' not in st.session_state:
                 try:
                     # 1. API에서 동적으로 모델 가져오기
                     fetched_models = list_available_models()
                     # 에러 메시지가 리스트에 들어있는 경우 방지
                     if fetched_models and "Error" in fetched_models[0]:
                         fetched_models = []
                 except:
                     fetched_models = []
                 
                 # 2. 필수 모델 (하드코딩 - 사용자 요청 반영)
                 essential_models = [
                     "models/gemini-3-pro-preview",       # Text Default
                     "models/gemini-3-flash-preview",     # Image Prompt Default
                     "models/gemini-3-pro-image-preview", # Real Image Default
                     "models/gemini-2.5-pro",
                     "models/gemini-2.0-flash", 
                     "models/imagen-4.0-generate-001"
                 ]
                 
                 # 3. 합치기 (중복 제거 & 순서 보장)
                 # 필수 모델을 우선 배치
                 final_models = []
                 for m in essential_models:
                     final_models.append(m)
                     
                 for m in fetched_models:
                     if m not in final_models and "gemini" in m:
                         final_models.append(m)
                         
                 st.session_state.available_models = final_models
                 
            # 글작성용 모델 (Default: gemini-3-pro-preview)
            def_text = "models/gemini-3-pro-preview"
            if def_text not in st.session_state.available_models:
                st.session_state.available_models.insert(0, def_text)
                
            def_img_prompt = "models/gemini-3-flash-preview"
            if def_img_prompt not in st.session_state.available_models:
                st.session_state.available_models.append(def_img_prompt)
    
            # UI는 유지하되 기본값을 사용자가 원하는 대로 고정
            st.markdown("### 2. 모델 설정")
            # st.caption("※ 모델 설정")
            
            # 1. 글작성 모델
            text_index = st.session_state.available_models.index(def_text) if def_text in st.session_state.available_models else 0
            text_model = st.selectbox("📝 글작성용 모델", st.session_state.available_models, index=text_index, key="text_model_select")
            st.session_state.selected_text_model = text_model
            
            # 2. 이미지 프롬프트 모델
            img_index = st.session_state.available_models.index(def_img_prompt) if def_img_prompt in st.session_state.available_models else 0
            image_model = st.selectbox("🎨 이미지 프롬프트용 모델", st.session_state.available_models, index=img_index, key="image_model_select")
            st.session_state.selected_image_model = image_model
            
            # 3. 실제 이미지 생성 모델 (New)
            def_real_img = "models/gemini-3-pro-image-preview"
            if def_real_img not in st.session_state.available_models:
                 st.session_state.available_models.append(def_real_img)
                 
            real_img_index = st.session_state.available_models.index(def_real_img) if def_real_img in st.session_state.available_models else 0
            real_image_model = st.selectbox("🖼️ 실제 이미지 생성 모델", st.session_state.available_models, index=real_img_index, key="real_image_model_select")
            st.session_state.selected_real_image_model = real_image_model
            
        else:
            # API Key가 없으면 모델 선택도 안보이게 (보통 고정되어 있어서 이럴 일은 거의 없음)
            pass
        
        st.divider()
        
        # 3. 타겟 블로그 선택
        st.markdown("### 3. 타겟 블로그 선택")
        if 'blogger_list' not in st.session_state:
            try: 
                with st.spinner("블로그 목록 가져오는 중..."):
                    from blogger_api import get_blog_list
                    st.session_state.blogger_list = get_blog_list(st.session_state.auth_creds)
            except:
                st.session_state.blogger_list = []
                
        if st.session_state.blogger_list:
            # 블로그 이름 리스트 생성 (ID 매핑용)
            # name과 url을 같이 보여줘서 구분 쉽게
            blog_options = {}
            option_keys = []
            for b in st.session_state.blogger_list:
                key = f"{b['name']} ({b['url']})"
                blog_options[key] = b['id']
                option_keys.append(key)
                
            selected_blog_name = st.selectbox("업로드할 블로그", option_keys, label_visibility="collapsed")
            if selected_blog_name:
                st.session_state.selected_blog_id = blog_options[selected_blog_name]
                # st.caption(f"ID: {st.session_state.selected_blog_id}")
            
        else:
            st.warning("계정에 연결된 블로그가 없습니다.")
            st.session_state.selected_blog_id = None

        st.divider()

        # 4. 새 포스팅 만들기 (초기화)
        if st.button("🔄 새 포스팅 만들기 (Reset)"):
            # 입력값 및 결과 초기화
            keys_to_reset = ['current_step', 'plan_result', 'content_result', 'image_url', 'final_post_url']
            for key in keys_to_reset:
                st.session_state[key] = "" if key != 'current_step' else 0
            st.rerun()
            
    else:
        # 로그아웃 상태: 로그인 버튼 표시
        st.warning("먼저 로그인을 진행해주세요.")
        if st.button("Google 로그인 / 인증 갱신"):
            try:
                creds = authenticate_google_user()
                st.session_state.auth_creds = creds
                st.success("인증 성공! ✅")
                st.rerun()
            except Exception as e:
                st.error(f"인증 실패: {e}")


# 메인 영역
st.title("🚀 SEO 최적화 구글 블로거 포스팅")
st.markdown("전략적 글쓰기와 AI 자동화를 통해 블로그 성장을 가속화하세요.")

if not st.session_state.auth_creds or not st.session_state.gemini_api_key:
    st.warning("사이드바에서 [Google 로그인]과 [Gemini API Key] 설정을 먼저 완료해주세요.")
    st.stop()

# RAG Context 로드 (한번만)
if 'rag_context' not in st.session_state:
    with st.spinner("지식 베이스(PDF, Instructions) 로딩 중..."):
        st.session_state.rag_context = get_rag_context()
        if not st.session_state.rag_context.strip():
             st.warning("전략 가이드 파일이나 프롬프트 파일을 읽지 못했습니다. 파일 위치를 확인해주세요.")

# 입력 폼
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        keyword = st.text_input("타겟 키워드", placeholder="예: 4세대 실손보험")
    with col2:
        audience = st.text_input("타겟 독자", placeholder="예: 보험료 인상이 걱정되는 50대")
    
    goal = st.selectbox("글의 목적", ["정보 제공", "신뢰 구축", "문의 유도", "전환/판매"])

# 진행 상태 바
progress_bar = st.progress(0)

# --- Step A: 기획 (Planning) ---
st.header("Step A: 기획 (Planning)")
if st.button("기획안 생성하기", disabled=st.session_state.current_step > 0):
    if not keyword or not audience:
        st.error("키워드와 독자 정보를 입력해주세요.")
    else:
        with st.spinner("AI가 기획안을 작성 중입니다... (제목, 태그, 목차)"):
            try:
                # 모델명 전달 (Text Model)
                model_to_use = st.session_state.get('selected_text_model', 'models/gemini-2.5-pro')
                plan = generate_planning_step(st.session_state.rag_context, keyword, audience, goal, model_name=model_to_use)
                st.session_state.plan_result = plan
                st.session_state.current_step = 1
                progress_bar.progress(25)
            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

if st.session_state.current_step >= 1:
    plan_text = st.text_area("기획안 확인 및 수정 (필요시 수정 후 '확인' 버튼 클릭)", 
                             value=st.session_state.plan_result, height=300)
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        if st.button("기획안 확정 및 글쓰기 시작"):
            st.session_state.plan_result = plan_text # 수정 사항 저장
            st.session_state.current_step = 2
            st.rerun()
    with col_a2:
        if st.button("🔄 기획안 다시 생성하기 (Regenerate)"):
            st.session_state.plan_result = ""
            st.session_state.current_step = 0
            st.rerun()

# --- Step B: 집필 (Writing) ---
if st.session_state.current_step >= 2:
    st.divider()
    st.header("Step B: 집필 (Writing)")
    progress_bar.progress(50)
    
    if not st.session_state.content_result:
        with st.spinner("AI가 본문을 집필 중입니다... (2,000자 이상, HTML 형식)"):
            try:
                # 모델명 전달 (Text Model)
                model_to_use = st.session_state.get('selected_text_model', 'models/gemini-2.5-pro')
                content = generate_content_step(st.session_state.rag_context, st.session_state.plan_result, keyword, audience, model_name=model_to_use)
                # 고정 푸터 추가 (버튼 스타일 적용)
                footer_style = """
                <br><br>
                <div style="text-align: center; margin-top: 30px;">
                    <p style="font-size: 1.1em; font-weight: bold; color: #333;">지금 당신의 보험을 확인해 보세요</p>
                    <a href="https://myhom.me/realinsuguide/contract" target="_blank" 
                       style="display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 1em; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                       내 보험 확인해보기 (클릭)
                    </a>
                </div>
                """
                st.session_state.content_result = content + footer_style
            except Exception as e:
                st.error(f"글쓰기 중 오류 발생: {e}")

    if st.session_state.content_result:
        tab1, tab2 = st.tabs(["미리보기 (Rendered)", "HTML 소스"])
        with tab1:
            st.markdown(st.session_state.content_result, unsafe_allow_html=True)
        with tab2:
            st.text_area("HTML Source", st.session_state.content_result, height=200)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("본문 확정 및 이미지 생성"):
                st.session_state.current_step = 3
                st.rerun()
        with col_b2:
            if st.button("🔄 본문 다시 작성하기 (Regenerate)"):
                st.session_state.content_result = ""
                st.rerun()

# --- Step C: 이미지 자동화 (Image) ---
if st.session_state.current_step >= 3:
    st.divider()
    st.header("Step C: 이미지 자동화 (Image)")
    progress_bar.progress(75)
    
    if not st.session_state.image_url:
        with st.spinner("본문 내용을 분석하여 이미지 프롬프트를 생성하고, 이미지를 준비 중입니다..."):
            try:
                # 1. 프롬프트 생성 (Image Model 사용 - gemini-2.0-flash)
                model_to_use = st.session_state.get('selected_image_model', 'models/gemini-2.0-flash')
                # 2024-02-07 Fix: HTML(CSS포함) 대신 기획안과 키워드를 전달하여 정확도 향상
                img_prompt = generate_image_prompt(
                    st.session_state.plan_result, 
                    keyword, 
                    audience, 
                    model_name=model_to_use
                )
                st.info(f"생성된 프롬프트: {img_prompt}")
                
                # 2. 진짜 이미지 생성 (New Model 적용)
                real_model_to_use = st.session_state.get('selected_real_image_model', 'models/gemini-3-pro-image-preview')
                generated_image_path = generate_real_image(img_prompt, st.session_state.gemini_api_key, model_name=real_model_to_use)
                
                if generated_image_path:
                    # 3. 이미지 처리: Base64 임베딩 (Google Photos 오류 회피)
                    try:
                        from generator import get_image_base64
                        base64_img = get_image_base64(generated_image_path)
                        
                        if base64_img:
                            st.session_state.image_url = "Base64 Image Embedded" # URL 대신 상태 표시
                            img_tag = f'<div style="text-align: center;"><img src="{base64_img}" alt="{keyword}" style="max-width: 100%; height: auto;" /></div><br>'
                            st.session_state.content_result = img_tag + st.session_state.content_result
                            st.success(f"이미지 생성({real_model_to_use}) 및 본문 삽입 성공! (Base64 Embedding)")
                            
                            # 로컬 이미지 표시
                            st.image(generated_image_path, caption=f"Generated by {real_model_to_use}", use_container_width=True)
                        else:
                            st.error("이미지 Base64 변환 실패.")
                    except Exception as e:
                        st.error(f"이미지 임베딩 중 오류: {e}")
                        
                else:
                    st.error("이미지 생성 실패.")
            
            except Exception as e:
                st.error(f"이미지 처리 중 오류 발생: {e}")

    if st.session_state.image_url:
        # 이미 위에서 보여줬으므로 여기선 생략하거나 최종 확인용
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("발행 준비 완료"):
                st.session_state.current_step = 4
                st.rerun()
        with col_c2:
             if st.button("🔄 이미지 다시 생성하기 (Regenerate)"):
                st.session_state.image_url = ""
                # 본문에서 기존 이미지 태그 제거 (선택 사항이지만 깔끔하게)
                if "base64" in st.session_state.content_result[:500]: # 대략 앞부분에 있는지 체크
                     # 간단히 재작성 유도 대신 그냥 이미지만 다시 생성하고 본문은 놔둘 수도 있음.
                     # 하지만 본문에 이미지가 박혀버렸으므로, 본문도 원복해야 함.
                     # -> 이게 복잡하므로 본문 재작성 없이 이미지만 교체하려면 본문에서 <img> 태그를 찾아 지워야 함.
                     # 일단 단순하게 '이미지 생성' 단계만 리셋하면, 다음 루프에서 또 이미지를 앞에 '추가'하게 됨 (중복).
                     # 해결책: Step B 결과(순수 본문)를 따로 저장해두지 않았음.
                     # 차선책: image_url 리셋 시, content_result에서 앞부분 <img> 태그 제거 시도.
                     import re
                     st.session_state.content_result = re.sub(r'<div style="text-align: center;"><img src="data:image/.*?" .*?</div><br>', '', st.session_state.content_result, count=1)
                st.rerun()

# --- Step D: 발행 (Publishing) ---
if st.session_state.current_step >= 4:
    st.divider()
    st.header("Step D: 발행 (Publishing)")
    progress_bar.progress(100)
    
    if st.button("Blogger에 초안(Draft)으로 업로드"):
        with st.spinner("Blogger로 업로드 중..."):
            # 선택된 블로그 ID 사용 (없으면 기본값 사용 시도)
            target_blog_id = st.session_state.get('selected_blog_id')
            
            # 만약 선택된 것이 없으면(초기 로딩 전 등), get_blog_info로 첫번째 가져옴 (강제 로드)
            if not target_blog_id:
                default_blog = get_blog_info(st.session_state.auth_creds)
                if default_blog:
                    target_blog_id = default_blog['id']
            
            if target_blog_id:
                post_title = f"{keyword} - {audience}를 위한 필수 가이드"
                labels = ["정보", keyword, "자동포스팅", "AI"]
                
                post = upload_post(
                    st.session_state.auth_creds,
                    target_blog_id,
                    post_title,
                    st.session_state.content_result,
                    labels
                )
                
                if post:
                    st.success(f"포스팅 성공! 글 ID: {post['id']}")
                    st.markdown(f"### [블로그 관리자 페이지 바로가기](https://www.blogger.com/blog/posts/{target_blog_id})")
                    st.json(post)
                else:
                    st.error("포스팅 업로드 실패.")
            else:
                st.error("업로드할 블로그 정보를 찾을 수 없습니다. 사이드바 설정을 확인해주세요.")
