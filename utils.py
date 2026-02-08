import os
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """PDF 파일에서 텍스트를 추출합니다."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""
    return text

def read_text_file(txt_path):
    """텍스트 파일 내용을 읽습니다."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading text file {txt_path}: {e}")
        return ""

def get_rag_context():
    """strategy_guide.pdf와 prompt_instructions.txt를 읽어 통합 컨텍스트를 반환합니다."""
    # 현재 디렉토리 기준
    pdf_path = "strategy_guide.pdf"
    txt_path = "prompt_instructions.txt"
    
    pdf_text = extract_text_from_pdf(pdf_path)
    instruction_text = read_text_file(txt_path)
    
    combined_context = f"""
    === Strategy Guide (From PDF) ===
    {pdf_text}
    
    === System Instructions ===
    {instruction_text}
    """
    return combined_context
