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
    
    print("5. 윗부분 찌꺼기 완벽 제거 및 CSS 강화 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    current_year = datetime.now().year
    start_keyword = f"{current_year}년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    # 1. 꼬리(일정등록) 자르기
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
        
    # 2. 머리(2026년) 찾기 및 상단 찌꺼기 이미지/버튼 제거
    year_idx = extracted_html.find(start_keyword)
    if year_idx != -1:
        # 연도 이후의 코드만 임시로 가져옴
        after_year_html = extracted_html[year_idx:]
        
        # 🌟 핵심: 연도 글자 이후에 처음으로 등장하는 "진짜 표 태그" 위치 찾기
        tag_idx = after_year_html.find('<thead')
        if tag_idx == -1: tag_idx = after_year_html.find('<tbody')
        if tag_idx == -1: tag_idx = after_year_html.find('<tr')
        
        # 표 태그가 발견되면 그 앞의 찌꺼기(스크린샷 부분)는 전부 버림
        if tag_idx != -1:
            extracted_html = after_year_html[tag_idx:]
        else:
            extracted_html = after_year_html
            
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 🎨 더 또렷하고 명확한 테이블 테두리 CSS
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 공유 일정</title>
        <style>
            :root {{
                --bg-color: #f8fafc;
                --text-main: #0f172a; /* 글씨 더 진하게 */
                --border-strong: #475569; /* 명확하고 진한 테두리 */
                --border-light: #94a3b8; /* 내부 셀 테두리도 또렷하게 */
                --header-bg: #e2e8f0;
                --hover-bg: #f1f5f9;
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
                border-bottom: 3px solid var(--border-strong);
                padding-bottom: 15px;
            }}
            h2 {{ margin: 0; font-size: 26px; color: #0f172a; letter-spacing: -0.5px; }}
            .sync-time {{ margin: 8px 0 0 0; font-size: 14px; color: #475569; font-weight: 500; }}
            
            .table-wrapper {{
                background: #ffffff;
                border-radius: 8px;
                /* 표 바깥쪽 전체를 감싸는 아주 굵은 테두리 */
                border: 2px solid var(--border-strong); 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                overflow-x: auto;
                max-height: 70vh; 
            }}
            
            table {{
                width: 100% !important;
                border-collapse: collapse !important;
                white-space: nowrap;
            }}
            th, td {{
                padding: 14px 18px !important;
                /* 모든 칸마다 뚜렷한 선 적용 */
                border: 1px solid var(--border-light) !important; 
                text-align: center !important;
                vertical-align: middle !important;
                font-size: 15px !important;
                color: var(--text-main) !important;
            }}
            th {{
                background-color: var(--header-bg) !important;
                font-weight: 800 !important;
                /* 제목줄 아랫부분은 더 굵은 선으로 구분 */
                border-bottom: 2px solid var(--border-strong) !important; 
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            td:hover {{
                background-color: var(--hover-bg) !important;
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
