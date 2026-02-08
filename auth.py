import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# 권한 스코프 설정
SCOPES = [
    'https://www.googleapis.com/auth/blogger',
    'https://www.googleapis.com/auth/photoslibrary.sharing',
    'https://www.googleapis.com/auth/photoslibrary.appendonly',
    'https://www.googleapis.com/auth/photoslibrary.readonly', # 추가: 업로드 후 baseUrl 읽기 권한
    'https://www.googleapis.com/auth/userinfo.email',   # 추가: 사용자 이메일
    'https://www.googleapis.com/auth/userinfo.profile', # 추가: 사용자 프로필(이름, 사진)
    'openid' # Google Sign-In 필수 스코프 (자동 추가됨)
]

TOKEN_FILE = 'token.pickle'
CLIENT_SECRET_FILE = 'client_secret.json'

def authenticate_google_user():
    """
    Google OAuth 2.0 인증을 수행하고 creds 객체를 반환합니다.
    1. token.pickle 파일이 있으면 로드 (Local)
    2. Streamlit Cloud Secrets에 설정된 토큰 정보가 있으면 로드 (Cloud)
    3. 둘 다 없으면 새로운 인증 절차 시작 (Local Browser)
    """
    creds = None
    
    # 1. 로컬 토큰 파일 확인
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
            
    # 2. Streamlit Secrets 확인 (Cloud 환경)
    import streamlit as st
    if not creds and "google_oauth" in st.secrets:
        try:
            from google.oauth2.credentials import Credentials
            secret_info = st.secrets["google_oauth"]
            creds = Credentials(
                token=None,
                refresh_token=secret_info["refresh_token"],
                token_uri=secret_info["token_uri"],
                client_id=secret_info["client_id"],
                client_secret=secret_info["client_secret"],
                scopes=SCOPES
            )
        except Exception as e:
            st.error(f"Secrets 로드 중 오류: {e}")

    # 3. 유효한 자격 증명이 없으면 로그인 진행 (Local only)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Secrets가 있어도 Refresh 실패 시 재인증 시도 (하지만 Cloud에선 불가)
            if not os.path.exists(CLIENT_SECRET_FILE):
                # Cloud 환경에서 Secrets도 없고 파일도 없으면 에러
                if "google_oauth" not in st.secrets: # 중복 체크
                     st.error("Google 인증 정보를 찾을 수 없습니다. (Local: client_secret.json, Cloud: Secrets)")
                     return None
                
            if os.path.exists(CLIENT_SECRET_FILE):
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # 인증 성공 시 토큰 저장 (Local only)
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            
    return creds

def get_user_profile(creds):
    """
    인증된 사용자의 프로필 정보(이름, 이메일, 사진 URL)를 가져옵니다.
    """
    try:
        from googleapiclient.discovery import build
        service = build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        return user_info
    except Exception as e:
        print(f"Failed to fetch user profile: {e}")
        return None
