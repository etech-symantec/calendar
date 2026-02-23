import os
from playwright.sync_api import sync_playwright
from datetime import datetime

def run(playwright):
    # 1. 브라우저 실행 (headless=True 이면 화면이 보이지 않는 백그라운드 모드)
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # GitHub Secrets에서 아이디와 비밀번호 가져오기 (보안)
    USER_ID = os.environ.get("MY_SITE_ID")
    USER_PW = os.environ.get("MY_SITE_PW")

    try:
        print("로그인 페이지로 이동 중...")
        # 2. 로그인 페이지 접속
        page.goto("https://example.com/login")
        
        # 3. 아이디/비밀번호 입력 및 로그인 버튼 클릭
        # (웹사이트의 input 태그 id나 name 속성을 확인해서 수정하세요)
        page.fill('input[name="userid"]', USER_ID)
        page.fill('input[name="password"]', USER_PW)
        page.click('button[type="submit"]')
        
        # 로그인이 완료되고 페이지가 넘어갈 때까지 대기
        page.wait_for_load_state('networkidle')
        print("로그인 성공!")

        # 4. 목표 데이터가 있는 페이지로 이동
        page.goto("https://example.com/target-data-page")

        # 5. 특정 버튼 클릭하여 테이블 데이터 불러오기
        page.click('button#load-data-btn')

        print("테이블 데이터 렌더링 대기 중...")
        # 6. 테이블 요소가 화면에 나타날 때까지 대기 
        page.wait_for_selector('table.data-table', timeout=10000)

        # 7. 테이블의 전체 HTML 내용 추출
        table_html = page.inner_html('table.data-table')
        
        # 현재 시간 기록 (업데이트 확인용)
        kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 8. 결과를 담은 웹페이지(index.html) 생성
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>자동 업데이트 데이터 표</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>수집된 데이터</h1>
            <p>마지막 업데이트: {kst_now}</p>
            <table>
                {table_html}
            </table>
        </body>
        </html>
        """

        # index.html 파일 쓰기 (기존 파일 덮어쓰기)
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print("index.html 파일이 성공적으로 생성되었습니다!")

    except Exception as e:
        print(f"스크래핑 중 오류 발생: {e}")
        
    finally:
        # 작업이 끝나면 브라우저 닫기
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
