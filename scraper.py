import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def run(playwright):
    # 처음 테스트할 때는 headless=False로 브라우저 창을 띄워서 동작을 눈으로 확인하세요!
    # 완벽히 작동하면 나중에 GitHub Actions에 올릴 때 True로 바꿉니다.
    browser = playwright.chromium.launch(headless=False)
    
    # 팝업 무시 및 세션 유지를 위한 컨텍스트 생성
    context = browser.new_context()
    page = context.new_page()

    # GitHub Secrets 등에서 환경 변수 가져오기
    USER_ID = os.environ.get("MY_SITE_ID", "테스트아이디입력")
    USER_PW = os.environ.get("MY_SITE_PW", "테스트비밀번호입력")

    try:
        print("1. 로그인 페이지 접속 중...")
        # TODO: 실제 그룹웨어 로그인 주소로 변경하세요.
        page.goto("http://gwa.youngwoo.co.kr/") 
        
        # 로그인 입력 및 클릭 (개발자 도구 F12를 눌러 실제 input의 id나 name을 확인하세요)
        page.fill('input[id="userId"]', USER_ID) 
        page.fill('input[id="password"]', USER_PW)
        page.click('button.login_submit') # 로그인 버튼 클릭
        
        # 메인 페이지(gwa_usermain)가 완전히 로딩될 때까지 대기
        page.wait_for_load_state('networkidle')
        print("로그인 완료! 메인 페이지 진입")

        # -------------------------------------------------------------------
        print("2. '일정' 메뉴 클릭 중...")
        # 텍스트 기반으로 '일정' 메뉴 클릭 (a 태그나 버튼)
        # 그룹웨어 특성상 상단 GNB가 별도의 프레임(iframe)에 있을 수도 있습니다.
        page.click('text="일정"') 
        
        # 캘린더 페이지(gwa_calendar) 로딩 대기
        page.wait_for_load_state('networkidle')
        time.sleep(2) # 애니메이션이나 트리 메뉴 로딩을 위해 잠시 대기

        # -------------------------------------------------------------------
        print("3. 좌측 '공유일정전체보기' 및 '일정목록' 클릭 중...")
        
        # 주의: 그룹웨어는 좌측 메뉴(LNB)와 본문 영역이 iframe으로 나뉘어 있는 경우가 아주 많습니다.
        # 만약 아래 click() 코드가 요소를 찾지 못해 에러가 난다면, iframe 내부를 탐색해야 합니다.
        
        page.click('text="공유일정전체보기"')
        time.sleep(1) # 하위 메뉴가 펼쳐지는 시간 대기
        
        page.click('text="일정목록"')
        
        print("일정목록 테이블 렌더링 대기 중...")
        # -------------------------------------------------------------------
        print("4. 데이터 스크래핑 중...")
        
        # 본문 iframe 안에서 테이블이 나타날 때까지 대기 (테이블 클래스나 ID 확인 필요)
        page.wait_for_selector('table.schedule_list_table', timeout=10000)

        # 테이블의 전체 HTML 내용 추출
        table_html = page.inner_html('table.schedule_list_table')
        
        kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 5. 결과를 담은 웹페이지(index.html) 생성
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>그룹웨어 일정목록</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
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
            
        print("성공적으로 index.html을 생성했습니다!")

    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
