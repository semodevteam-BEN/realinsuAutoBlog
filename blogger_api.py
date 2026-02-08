from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def get_blog_info(creds):
    """사용자의 블로그 정보를 가져옵니다 (첫 번째 블로그 사용 - Legacy)."""
    try:
        service = build('blogger', 'v3', credentials=creds)
        blogs = service.blogs().listByUser(userId='self').execute()
        
        if 'items' in blogs and len(blogs['items']) > 0:
            return blogs['items'][0]
        else:
            return None
    except HttpError as error:
        print(f"Blogger Info Error: {error}")
        return None

def get_blog_list(creds):
    """사용자의 모든 블로그 리스트를 가져옵니다."""
    try:
        service = build('blogger', 'v3', credentials=creds)
        blogs = service.blogs().listByUser(userId='self').execute()
        return blogs.get('items', [])
    except HttpError as error:
        print(f"Blogger List Error: {error}")
        return []

def upload_post(creds, blog_id, title, content, labels):
    """Blogger에 글을 '초안(draft)' 상태로 업로드합니다."""
    try:
        service = build('blogger', 'v3', credentials=creds)
        
        # labels가 문자열이면 리스트로 변환 (콤마 기준)
        if isinstance(labels, str):
            labels = [l.strip() for l in labels.split(',')]
            
        body = {
            "kind": "blogger#post",
            "title": title,
            "content": content,
            "labels": labels
        }
        
        # isDraft=True로 설정하여 초안으로 저장
        posts = service.posts().insert(blogId=blog_id, body=body, isDraft=True).execute()
        
        return posts
        
    except HttpError as error:
        # 오류 상세 정보 포함하여 재발생 (UI에서 확인 가능하도록)
        error_content = error.content.decode('utf-8') if error.content else "Unknown Error"
        raise Exception(f"Blogger Upload Error: {error} - {error_content}")
