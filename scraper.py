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
    
    print("5. 화면 원본 데이터 100% 추출 중...")
    
    # 표만 가져오는 게 아니라, iframe(액자) 안의 <body> 태그 전체 내용을 긁어옵니다!
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # CSS나 자바스크립트 없이, 긁어온 원본만 덜렁 보여주는 가장 단순한 형태
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>원본 화면 디버깅</title>
        <style>
            body {{ padding: 20px; }}
            .debug-header {{ border: 2px solid red; padding: 10px; margin-bottom: 20px; font-weight: bold; }}
            /* 원본 표가 너무 커서 잘리지 않게 스크롤 추가 */
            .content-wrapper {{ overflow: auto; border: 1px solid #ccc; padding: 10px; }}
        </style>
    </head>
    <body>
        <div class="debug-header">
            🚨 디버깅 모드: 가공되지 않은 100% 원본 화면입니다. (추출 시간: {kst_now})
        </div>
        
        <div class="content-wrapper">
            {raw_html}
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
