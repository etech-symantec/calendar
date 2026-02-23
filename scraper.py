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
    
    print("5. 지정된 영역 추출 및 CSS 스타일링 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # 🌟 핵심 변경 부분: 현재 연도를 자동으로 가져와서 '년'을 붙임
    current_year = datetime.now().year
    start_keyword = f"{current_year}년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 공유 일정</title>
        <style>
            :root {{
                --bg-color: #f8fafc;
                --text-main: #334155;
                --border-light: #e2e8f0;
                --header-bg: #f1f5f9;
                --hover-bg: #f0fdf4;
            }}
            body {{
                font-family: 'Pretendard', 'Malgun Gothic', '맑은 고딕', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-main);
                padding: 40px;
                margin: 0;
            }}
            .header-area {{
                margin-bottom: 30px;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 15px;
            }}
            h2 {{ margin: 0; font-size: 26px; color: #0f172a; letter-spacing: -0.5px; }}
            .sync-time {{ margin: 8px 0 0 0; font-size: 14px; color: #64748b; }}
            
            .table-wrapper {{
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                border: 1px solid var(--border-light);
                overflow-x: auto;
                max-height: 70vh; 
            }}
            
            table {{
                width: 100% !important;
                border-collapse: collapse !important;
                white-space: nowrap;
            }}
            th, td {{
                padding: 16px 20px !important;
                border: 1px solid var(--border-light) !important;
                text-align: center !important;
                vertical-align: middle !important;
                font-size: 15px !important;
            }}
            th {{
                background-color: var(--header-bg) !important;
                color: #1e293b !important;
                font-weight: 700 !important;
                position: sticky;
                top: 0;
                z-index: 10;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }}
            td:hover {{
                background-color: var(--hover-bg) !important;
                cursor: default;
            }}
        </style>
    </head>
    <body>
        <div class="header-area">
            <h2>📅 그룹웨어 공유 일정 목록</h2>
            <p class="sync-time">🔄 마지막 동기화: {kst_now}</p>
        </div>
        
        <div class="table-wrapper">
            <table>
                {extracted_html}
            </table>
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
