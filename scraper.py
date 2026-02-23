import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def run(playwright):
    # GitHub Actions에서는 화면이 없으므로 headless=True 유지
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")

    print("1. 로그인 페이지 접속 중...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    
    print("로그인 시도 중...")
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3) # 메인 페이지 로딩 대기

    print("2. 상단 '일정' 메뉴 클릭 중...")
    page.click('#topMenu300000000') 
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. 좌측 '공유일정 전체보기' 메뉴 클릭 중...")
    # 🔥 수정 포인트 1: 띄어쓰기 반영 및 가장 확실한 태그 ID(#301040000_all_anchor) 적용
    try:
        # HTML 분석으로 찾아낸 고유 ID를 클릭 (가장 정확함)
        page.click('#301040000_all_anchor', timeout=5000)
    except Exception:
        # 혹시 ID가 바뀌었을 경우 텍스트(띄어쓰기 포함)로 클릭
        page.locator('text="공유일정 전체보기"').click(timeout=5000)
        
    time.sleep(3) # 클릭 후 우측 화면(iframe)이 바뀔 때까지 잠시 대기

    print("4. 우측 본문에서 '일정목록' 탭 클릭 중...")
    # 🔥 수정 포인트 2: 일정목록은 우측 본문 액자(iframe) 안에 있음
    frame = page.frame_locator('#_content')
    
    try:
        # iframe 안에서 '일정목록' 텍스트 클릭
        frame.locator('text="일정목록"').click(timeout=5000)
    except Exception:
        # 혹시 못 찾을 경우를 대비해 전체 페이지에서도 한번 더 찾아봄
        print("iframe 안에서 '일정목록'을 찾지 못해 전체 화면에서 시도합니다...")
        page.locator('text="일정목록"').click(timeout=5000)

    print("일정목록 데이터 불러오는 중...")
    time.sleep(5) # 테이블이 화면에 그려질 때까지 넉넉히 대기
    
    print("5. 데이터 스크래핑 및 HTML 생성 중...")
    table_html = ""
    try:
        # iframe 안의 테이블 HTML 복사
        table_html = frame.locator('table').first.inner_html(timeout=5000)
    except Exception:
        table_html = page.locator('table').first.inner_html(timeout=5000)
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 일정목록</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; text-align: left; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; }}
            th {{ background-color: #f4f6f9; }}
        </style>
    </head>
    <body>
        <h2>업데이트된 공유 일정 목록</h2>
        <p>마지막 동기화: {kst_now}</p>
        <table>
            {table_html}
        </table>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print("✅ 성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
