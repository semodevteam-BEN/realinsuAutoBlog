import google.generativeai as genai
from google import genai as new_genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_fixed
import time
import base64
import os

# Gemini 모델 설정 함수
def configure_gemini(api_key):
    genai.configure(api_key=api_key)

def list_available_models():
    """사용 가능한 Gemini 모델 리스트를 반환합니다."""
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except Exception as e:
        return [f"Error listing models: {str(e)}"]

# 1. Planning Step
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_planning_step(context, keyword, audience, goal, model_name='models/gemini-1.5-flash'):
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    [Context]
    {context}
    
    [Task]
    당신은 전문 블로그 기획자입니다. 다음 정보를 바탕으로 블로그 포스팅 기획안을 작성해주세요.
    
    1. 타겟 키워드: {keyword}
    2. 타겟 독자: {audience}
    3. 글의 목적: {goal}
    
    [Output Format]
    다음 항목들을 명확히 구분하여 출력해주세요:
    1. 제목 후보 (5개) - 클릭을 유도하는 매력적인 제목
    2. 태그 (7개) - 콤마로 구분
    3. 상세 목차 (Outline) - AEA 구조(권위-근거-행동)를 적용하여 서론, 본론(3~4개 소주제), 결론으로 구성. 각 섹션에 들어갈 핵심 내용 요약 포함.
    """
    
    response = model.generate_content(prompt)
    return response.text

# 2. Writing Step
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_content_step(context, plan, keyword, audience, model_name='models/gemini-1.5-flash'):
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    [Context]
    {context}
    
    [Approved Plan]
    {plan}
    
    [Task]
    위 기획안을 바탕으로 블로그 본문을 작성해주세요.
    
    [Guidelines]
    1. 분량: 공백 포함 2,500자 이상 (상세하게 작성)
    2. 어조: 전문적이고 신뢰감 있는 "하십시오"체 (~입니다, ~합니다) 또는 친근한 "해요"체. (일관성 유지)
    3. **핵심: 가독성을 위한 서식 활용 (아래 CSS 클래스 필수 사용)**
       - 글의 시작 부분에 반드시 아래 <style> 태그를 포함하세요.
       - **가독성 강화: 문단이 길어지지 않도록 1~2문장마다 줄바꿈(<br>)을 적극적으로 사용하세요.**
       - **모바일 환경을 고려하여 호흡을 짧게 가져가세요.**
       - 주요 내용에는 반드시 박스 스타일(.info-box, .fact-box, .solution-box)을 사용하세요.
       - 경고나 주의사항은 .warning-header를 사용하세요.
       - 장점/단점 나열 시 .ok-list, .check-list를 사용하세요.
       
    [Available CSS Classes & Structure]
    <style>
        .blog-body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.8; color: #333; }}
        .warning-header {{ background-color: #fff5f5; border: 2px solid #e74c3c; padding: 20px; border-radius: 10px; margin-bottom: 40px; text-align: center; }}
        .warning-title {{ color: #c0392b; font-weight: 900; font-size: 1.4em; margin-bottom: 15px; }}
        h3.section-title {{ color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-top: 60px; font-weight: 800; }}
        h4.sub-title {{ color: #0056b3; margin-top: 35px; font-weight: 700; }}
        .info-box {{ background-color: #f0f7ff; border: 1px solid #cce5ff; padding: 20px; border-radius: 8px; margin: 25px 0; }}
        .fact-box {{ background-color: #fff0f0; border: 1px solid #ffc9c9; padding: 20px; border-radius: 8px; margin: 25px 0; }}
        .solution-box {{ background-color: #e8f4fd; border: 1px solid #b6d4fe; padding: 20px; border-radius: 8px; margin: 25px 0; }}
        .red-text {{ color: #e74c3c; font-weight: bold; }}
        .blue-text {{ color: #0056b3; font-weight: bold; }}
        ul.check-list {{ list-style: none; padding-left: 0; }}
        ul.check-list li {{ padding-left: 28px; position: relative; margin-bottom: 10px; }}
        ul.check-list li::before {{ content: "\\274C"; position: absolute; left: 0; }}
        ul.ok-list {{ list-style: none; padding-left: 0; }}
        ul.ok-list li {{ padding-left: 28px; position: relative; margin-bottom: 10px; }}
        ul.ok-list li::before {{ content: "\\2705"; position: absolute; left: 0; }}
    </style>

    [Output Structure Example]
    <div class="blog-body">
        <div class="warning-header">...</div>
        <p>서론...</p>
        <h3 class="section-title">1. 소제목</h3>
        <div class="fact-box">...</div>
        ...
    </div>

    4. 내용:
       - 독자의 공감을 이끌어내는 도입부 (스토리텔링)
       - 구체적인 근거와 데이터, 예시를 활용한 본론
       - 명확한 행동 유도(Call To Action)가 포함된 결론
    5. 주의(CRITICAL):
       - **절대 마크다운 코드 블록(```html)을 사용하지 마세요.**
       - 순수한 HTML 코드만 출력하세요.
       - 이미지 위치는 적절히 <br> 등으로 공간만 비워두세요 (이미지는 별도 삽입됨).
    """
    
    response = model.generate_content(prompt)
    content = response.text
    
    import re
    import textwrap
    
    # 1. ```...``` 패턴 (언어 지정 무관) 추출 시도
    # (?:\w+)? : html, xml, css 등 어떤 단어가 와도 매칭
    pattern = r"```(?:\w+)?\s*(.*?)\s*```"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        content = match.group(1)
    else:
        # 2. 매칭 안되면(쌍이 안맞거나 등), 라인 단위로 ``` 포함된 줄 제거 (Fallback)
        pass 
        
    # [CRITICAL Fix 2]
    # dedent만으로는 부족함 (혼재된 들여쓰기 등).
    # 아예 모든 줄의 앞 공백을 제거(lstrip)해버리고, 혹시 모를 ``` 잔재도 제거.
    # HTML은 들여쓰기가 없어도 렌더링에 문제 없음.
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        s_line = line.strip()
        # ```로 시작하거나 끝나는 줄은 제거 (코드 블록 잔재)
        if s_line.startswith("```") or s_line.endswith("```"):
            continue
        # 모든 줄의 앞 공백 제거 (Indented Code Block 방지)
        cleaned_lines.append(line.lstrip())
        
    content = "\n".join(cleaned_lines).strip()
    
    return content

# 3. Image Prompt Generation
def generate_image_prompt(plan, keyword, audience, model_name='models/gemini-2.0-flash'):
    model = genai.GenerativeModel(model_name)
    prompt = f"""
    블로그 글의 주제와 기획안을 바탕으로 독자의 시선을 사로잡을 수 있는 '직관적인 애니메이션 스타일'의 일러스트 묘사 프롬프트를 1개 작성해주세요.
    상세하고 구체적으로 묘사하세요.
    **반드시 한글(Korean)로 작성해주세요.**
    이미지 내에 텍스트가 포함된다면, 반드시 **한글**로 표현되도록 묘사하세요. (예: '보험'이라는 글자가 적힌 방패...)
    전체적인 분위기는 한국적인 정서에 맞게 조정해주세요.
    
    [Blog Info]
    - Keyword: {keyword}
    - Target Audience: {audience}
    
    [Post Plan & Context]
    {plan}
    """
    response = model.generate_content(prompt)
    return response.text

# 4. Real Image Generator
def generate_real_image(prompt, api_key, model_name='models/imagen-4.0-generate-001'):
    """
    모델을 사용하여 실제 이미지를 생성합니다.
    - Imagen 계열: client.models.generate_images 이용
    - Gemini 계열 (Image Preview 등): client.models.generate_content 이용
    생성된 이미지를 로컬에 저장하고 경로를 반환합니다.
    """
    client = new_genai.Client(api_key=api_key)
    
    timestamp = int(time.time())
    filename = f"generated_image_{timestamp}.png" # Gemini 3 might exit jpg, but saving as png is fine
    filepath = os.path.abspath(filename)
    
    try:
        # 1. Gemini 계열 (generate_content)
        if "gemini" in model_name.lower() and "image" in model_name.lower():
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            image_saved = False
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # 이미지 데이터 추출
                        image_bytes = part.inline_data.data
                        with open(filepath, "wb") as f:
                            f.write(image_bytes)
                        image_saved = True
                        break
            
            if image_saved:
                return filepath
            else:
                # 텍스트로 에러가 올 수 있음
                error_text = response.text if response.text else "No image data found in response."
                raise Exception(f"Gemini Image Gen Failed: {error_text[:200]}")

        # 2. Imagen 계열 (generate_images)
        else:
            response = client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1"
                )
            )
            
            if response.generated_images:
                image_item = response.generated_images[0]
                image_bytes = image_item.image.image_bytes
                
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                    
                return filepath
            else:
                raise Exception("No images generated by Imagen API.")
                
    except Exception as e:
         raise Exception(f"Image Generation failed using {model_name}: {str(e)}")

# 5. Mock Image Generator (Legacy/Fallback)
def generate_image_mock(prompt):
    """
    실제 이미지 생성 대신 Lorem Picsum URL 또는 
    단순 텍스트 기반 플레이스홀더 이미지를 반환합니다.
    """
# 6. Base64 Image Converter (For direct embedding)
def get_image_base64(image_path):
    """
    로컬 이미지 파일을 최적화(리사이징+압축)한 후 Base64 문자열로 변환합니다.
    (Blogger API 용량 제한 및 속도 문제 해결)
    """
    try:
        from PIL import Image
        import io
        
        # 이미지 열기
        with Image.open(image_path) as img:
            # 1. 리사이징 (가로 최대 800px)
            max_width = 800
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 2. RGB 모드 변환 (PNG -> JPG 변환 시 필수)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # 3. 메모리 버퍼에 JPEG로 저장 (압축률 70%)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70)
            buffer.seek(0)
            
            # 4. Base64 인코딩
            encoded_string = base64.b64encode(buffer.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded_string}"
            
    except Exception as e:
        print(f"Base64 conversion (optimization) failed: {e}")
        # 실패 시 원본 그대로 시도 (비상용)
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:image/png;base64,{encoded_string}"
        except:
            return None
