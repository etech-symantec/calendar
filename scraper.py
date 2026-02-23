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
    
    print("5. 데이터 스크래핑 및 '시간 항목(2번째 열)' 제거 중...")
    
    # ⭐️ 핵심: 화면의 표를 바둑판처럼 계산해서, 칸 병합에 상관없이 정확히 2번째 열만 뽑아버리는 알고리즘
    remove_second_col_js = """(table) => {
        const rows = Array.from(table.querySelectorAll('tr'));
        const grid = [];
        
        rows.forEach((row, r) => {
            let c = 0;
            const cells = Array.from(row.querySelectorAll('th, td'));
            cells.forEach(cell => {
                if (!grid[r]) grid[r] = [];
                while (grid[r][c]) c++; // 위에서 이미 병합되어 내려온 칸 건너뛰기
                
                const rowSpan = parseInt(cell.getAttribute('rowspan') || 1, 10);
                const colSpan = parseInt(cell.getAttribute('colspan') || 1, 10);
                
                for (let i = 0; i < rowSpan; i++) {
                    for (let j = 0; j < colSpan; j++) {
                        if (!grid[r + i]) grid[r + i] = [];
                        grid[r + i][c + j] = true;
                    }
                }
                
                // 2번째 열(인덱스 1)에 해당하는 셀이면 삭제 마커(data-delete) 표시
                if (c === 1) {
                    cell.setAttribute('data-delete', 'true');
                }
                c += colSpan;
            });
        });
        
        // 표시된 셀들을 HTML DOM에서 완전히 삭제
        table.querySelectorAll('[data-delete="true"]').forEach(el => el.remove());
        return table.innerHTML;
    }"""
    
    table_html = ""
    try:
        table_html = frame.locator('table').first.evaluate(remove_second_col_js)
    except Exception:
        table_html = page.locator('table').first.evaluate(remove_second_col_js)
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 원본 표 모양을 그대로 렌더링하는 심플한 HTML 템플릿
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
            
            .table-container {{ overflow-x: auto; background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            table {{ width: 100%; border-collapse: collapse; border-top: 2px solid #4a5568; font-size: 14px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 12px 15px; vertical-align: middle; text-align: center; }}
            th {{ background-color: #f1f5f9; font-weight: bold; color: #4a5568; }}
            tbody tr:hover {{ background-color: #f8fafc; }}
        </style>
    </head>
    <body>
        <h2>📅 공유 일정 목록 (시간 제외)</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        
        <div class="table-container">
            <table>
                {table_html}
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
