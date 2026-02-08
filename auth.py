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
    token.pickle 파일이 있으면 로드하고, 없거나 유효하지 않으면 새로 인증합니다.
    """
    creds = None
    
    # 토큰 파일이 존재하면 로드
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
            
    # 유효한 자격 증명이 없으면 로그인 진행
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(f"'{CLIENT_SECRET_FILE}' 파일을 찾을 수 없습니다. Google Cloud 콘솔에서 다운로드해주세요.")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 인증 성공 시 토큰 저장
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
