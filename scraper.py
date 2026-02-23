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
    
    # 5. 결과를 담은 웹페이지(index.html) 생성
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 일정목록</title>
        <style>
            body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; background-color: #f8f9fa; padding: 20px; color: #333; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; }}
            .sync-time {{ color: #7f8c8d; font-size: 13px; margin-bottom: 20px; }}
            
            /* 그룹웨어 원본 표 스타일을 그대로 살리는 CSS */
            .table-container {{ overflow-x: auto; background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                border-top: 2px solid #4a5568; 
                font-size: 14px;
            }}
            th, td {{ 
                border: 1px solid #cbd5e1; 
                padding: 12px 15px; 
                /* rowspan으로 칸이 합쳐졌을 때 글자가 중앙에 오도록 설정 */
                vertical-align: middle; 
                text-align: center; 
            }}
            th {{ 
                background-color: #f1f5f9; 
                font-weight: bold; 
                color: #4a5568;
            }}
            
            /* 내용이 길 수 있는 제목 같은 부분은 왼쪽 정렬을 원하시면 
               아래 nth-child 숫자를 타겟 열 번호로 맞춰 수정하시면 됩니다. */
            /* td:nth-child(3) {{ text-align: left; }} */
            
            tbody tr:hover {{ background-color: #f8fafc; }}
        </style>
    </head>
    <body>
        <h2>📅 공유 일정 목록</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        
        <div class="table-container">
            <table>
                {table_html}
            </table>
        </div>
    </body>
    </html>
    """

    # index.html 파일 쓰기
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print("✅ 성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
