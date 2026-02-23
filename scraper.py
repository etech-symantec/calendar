import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")

    print("1. 로그인 페이지 접속 중...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("2. 상단 '일정' 메뉴 클릭 중...")
    page.click('#topMenu300000000') 
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. 좌측 '공유일정 전체보기' 메뉴 클릭 중...")
    try:
        page.click('#301040000_all_anchor', timeout=5000)
    except Exception:
        page.locator('text="공유일정 전체보기"').click(timeout=5000)
        
    time.sleep(3)

    print("4. 우측 본문에서 '일정목록' 탭 클릭 중...")
    frame = page.frame_locator('#_content')
    
    try:
        frame.locator('text="일정목록"').click(timeout=5000)
    except Exception:
        page.locator('text="일정목록"').click(timeout=5000)

    print("일정목록 데이터 불러오는 중...")
    time.sleep(5)
    
    print("5. 지정된 영역 추출 및 테두리 생성 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # ✂️ 문자열 자르기 로직
    # 만약 화면에 연도가 "2026"이라고 표시된다면 아래 start_keyword를 화면에 보이는 실제 텍스트로 맞춰주세요.
    start_keyword = "2026" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    # 1. '2026'(또는 지정한 키워드)이 있는 곳부터 끝까지만 남김
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    # 2. '일정등록' 글자가 있는 곳 앞까지만 딱 남김
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # CSS 테두리 강제 주입 (!important 사용)
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>일정목록 추출</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background-color: #f8f9fa; color: #333; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; }}
            .sync-time {{ color: #7f8c8d; font-size: 13px; margin-bottom: 20px; }}
            
            /* 🔥 무조건 테두리가 보이게 강제하는 마법의 CSS */
            .table-container {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 10px !important; text-align: center; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; }}
        </style>
    </head>
    <body>
        <h2>📅 지정 영역 추출 결과</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        
        <div class="table-container">
            {extracted_html}
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print("✅ 성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
