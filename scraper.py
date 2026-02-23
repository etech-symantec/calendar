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
    
    print("5. 지정된 영역 추출 및 UI 렌더링 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # ✂️ 지난번 찾으신 영역 그대로 슬라이싱
    start_keyword = "2026년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 🎨 필터링 기능과 모던 UI가 탑재된 마법의 HTML 템플릿
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>일정목록 대시보드</title>
        <style>
            :root {{
                --primary-color: #4f46e5;
                --bg-color: #f3f4f6;
                --text-color: #1f2937;
                --border-color: #e5e7eb;
            }}
            body {{
                font-family: 'Pretendard', 'Malgun Gothic', '맑은 고딕', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                padding: 30px;
                margin: 0;
            }}
            .header-container {{
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                margin-bottom: 20px;
                border-bottom: 2px solid var(--border-color);
                padding-bottom: 15px;
            }}
            h2 {{ margin: 0; color: #111827; font-size: 24px; }}
            .sync-time {{ color: #6b7280; font-size: 14px; margin: 0; }}
            
            .controls {{ margin-bottom: 20px; }}
            .search-box {{
                width: 100%;
                max-width: 400px;
                padding: 12px 16px;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                font-size: 15px;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                transition: all 0.2s;
            }}
            .search-box:focus {{
                outline: none;
                border-color: var(--primary-color);
                box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
            }}

            .table-container {{
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                overflow-x: auto;
                max-height: 75vh; /* 화면 길이에 맞춰 스크롤 생성 */
            }}
            
            /* 원본 테이블 강제 스타일링 */
            table {{
                width: 100% !important;
                border-collapse: collapse !important;
                text-align: center;
                white-space: nowrap; 
            }}
            th, td {{
                padding: 14px 16px !important;
                border: 1px solid var(--border-color) !important;
                vertical-align: middle;
            }}
            th {{
                background-color: #f9fafb !important;
                color: #374151 !important;
                font-weight: 600 !important;
                /* 스크롤 시 제목줄 고정 */
                position: sticky;
                top: 0;
                z-index: 10;
                box-shadow: 0 2px 2px -1px rgba(0,0,0,0.1);
            }}
            tr:hover td {{ background-color: #f0fdf4 !important; transition: 0.2s; }}
            
            /* 필터링 시 사용되는 숨김 클래스 */
            .hidden-row {{ display: none !important; }}
        </style>
    </head>
    <body>
        <div class="header-container">
            <h2>📅 그룹웨어 공유 일정 목록</h2>
            <p class="sync-time">🔄 마지막 동기화: {kst_now}</p>
        </div>
        
        <div class="controls">
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 검색어 입력 (이름, 일정명 등)...">
        </div>

        <div class="table-container">
            {extracted_html}
        </div>

        <script>
            // 실시간 검색(필터링) 기능
            document.addEventListener('DOMContentLoaded', () => {{
                const searchInput = document.getElementById('searchInput');
                const table = document.querySelector('.table-container table');
                
                if(!table) return;

                const rows = table.querySelectorAll('tr');

                searchInput.addEventListener('keyup', function(e) {{
                    const term = e.target.value.toLowerCase();
                    
                    rows.forEach(row => {{
                        // 제목줄(th만 있는 줄)은 숨기지 않고 항상 표시
                        if(row.querySelector('th') && !row.querySelector('td')) return;

                        const text = row.textContent.toLowerCase();
                        if (text.includes(term)) {{
                            row.classList.remove('hidden-row');
                        }} else {{
                            row.classList.add('hidden-row');
                        }}
                    }});
                }});
            }});
        </script>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print("✅ 성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
