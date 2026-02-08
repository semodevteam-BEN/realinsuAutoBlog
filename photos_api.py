import requests
import os
from googleapiclient.discovery import build

def upload_image_to_photos(creds, image_path_or_url):
    """
    이미지를 Google Photos에 업로드하고 사용 가능한 URL을 반환합니다.
    주의: Google Photos API로 얻은 baseUrl은 일정 시간 후 만료될 수 있습니다.
    """
    
    # 1. 이미지 데이터 준비
    image_data = None
    filename = "blog_image.jpg"
    
    if image_path_or_url.startswith("http"):
        try:
            response = requests.get(image_path_or_url)
            response.raise_for_status()
            image_data = response.content
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None
    else:
        if os.path.exists(image_path_or_url):
            with open(image_path_or_url, 'rb') as f:
                image_data = f.read()
                filename = os.path.basename(image_path_or_url)
        else:
            print("File not found.")
            return None

    if not image_data:
        return None

    # 2. Upload Bytes
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-Protocol': 'raw',
        'X-Goog-Upload-File-Name': filename
    }
    
    upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
    
    try:
        response = requests.post(upload_url, headers=headers, data=image_data)
        response.raise_for_status()
        upload_token = response.text
        
        # 3. Album 생성 또는 찾기
        service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
        album_id = get_or_create_album(service, "Auto-Post Images")
        
        # 4. Media Item 생성
        new_item_body = {
            "albumId": album_id,
            "newMediaItems": [{
                "description": "Uploaded via Blogger Auto-Post App",
                "simpleMediaItem": {"uploadToken": upload_token}
            }]
        }
        
        result = service.mediaItems().batchCreate(body=new_item_body).execute()
        
        if "newMediaItemResults" in result:
            item = result["newMediaItemResults"][0]
            
            status = item.get("status", {})
            if status.get("code", 0) != 0:
                error_msg = status.get("message", "Unknown Error")
                raise Exception(f"Photo Creation Failed (API Status): {error_msg}")

            if "mediaItem" in item:
                return _get_base_url_with_fallback(service, item, album_id)
                
            raise Exception(f"No mediaItem in response. Item dump: {item}")
            
        return None
        
    except Exception as e:
        raise Exception(f"Google Photos Upload Error: {str(e)}")

def _get_base_url_with_fallback(service, item, album_id):
    """
    mediaItem에서 baseUrl을 추출하되, 없을 경우 ID 조회 및 앨범 검색을 통해 재시도합니다.
    최후의 수단으로 productUrl을 반환합니다.
    """
    media_item = item["mediaItem"]
    base_url = media_item.get("baseUrl")
    
    # 1차 확보 성공
    if base_url:
        return base_url

    # Fallback 시작
    item_id = media_item.get("id")
    if item_id:
        try:
            # 2차: ID로 상세 조회
            fetched_item = service.mediaItems().get(mediaItemId=item_id).execute()
            base_url = fetched_item.get("baseUrl")
            
            if not base_url:
                # 3차: 앨범 내 검색
                search_body = {"albumId": album_id, "pageSize": 5}
                search_results = service.mediaItems().search(body=search_body).execute()
                for ai in search_results.get("mediaItems", []):
                    if ai.get("id") == item_id:
                        base_url = ai.get("baseUrl")
                        break
        except Exception as e:
            print(f"Fallback fetch failed: {e}")

    # 최종 결과 반환
    if base_url:
        return base_url
    
    # 최후의 수단: productUrl
    product_url = media_item.get("productUrl")
    if product_url:
        return product_url
        
    raise Exception(f"Failed to retrieve baseUrl or productUrl. Item Dump: {str(item)}")

def get_or_create_album(service, album_title):
    """지정된 제목의 앨범을 찾고, 없으면 생성하여 ID를 반환합니다."""
    try:
        results = service.albums().list(pageSize=50).execute()
        albums = results.get('albums', [])
        
        for album in albums:
            if album.get('title') == album_title:
                return album.get('id')
        
        new_album = {'album': {'title': album_title}}
        created_album = service.albums().create(body=new_album).execute()
        return created_album.get('id')
        
    except Exception as e:
        print(f"Album creation failed: {e}")
        return None
