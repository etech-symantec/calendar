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
    # HTML에서 확인된 실제 도메인으로 접속
    page.goto("http://gwa.youngwoo.co.kr/") 
    
    # 2. 아이디 / 비밀번호 입력 (분석된 ID 적용)
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    
    # 3. 로그인 버튼 누르기 (엔터키로 로그인 실행)
    print("로그인 시도 중...")
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3) # 메인 페이지가 뜰 때까지 넉넉히 대기

    print("2. 상단 '일정' 메뉴 클릭 중...")
    # 상단 메뉴 '일정' 버튼 ID 직접 클릭
    page.click('#topMenu300000000') 
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. 좌측 '공유일정전체보기' 및 '일정목록' 클릭 중...")
    
    # 비즈박스 그룹웨어는 본문이 _content 라는 id의 iframe(액자) 안에 들어있습니다.
    frame = page.frame_locator('#_content')
    
    try:
        print("iframe 내부에서 메뉴 탐색...")
        frame.locator('text="공유일정전체보기"').click(timeout=5000)
        time.sleep(2)
        frame.locator('text="일정목록"').click(timeout=5000)
    except Exception:
        print("iframe에 없어서 전체 화면에서 탐색합니다...")
        page.locator('text="공유일정전체보기"').click(timeout=5000)
        time.sleep(2)
        page.locator('text="일정목록"').click(timeout=5000)

    print("일정목록 테이블 렌더링 대기 중...")
    time.sleep(5) # 테이블 데이터를 불러올 시간 대기
    
    # 4. 데이터 스크래핑
    print("4. 데이터 스크래핑 중...")
    table_html = ""
    try:
        # iframe 안의 첫 번째 테이블 내용을 가져옴
        table_html = frame.locator('table').first.inner_html(timeout=5000)
    except Exception:
        # 못 찾으면 전체 화면의 첫 번째 테이블을 가져옴
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
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
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

    # 결과물 쓰기
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print("성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
