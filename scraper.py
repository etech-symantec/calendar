import os
import time
import json
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
    
    print("5. 데이터 추출 및 상단 오늘 일정 분리 세팅 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # ✂️ 문자열 자르기 로직
    now = datetime.now()
    current_year = now.year
    start_keyword = f"{current_year}년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    # ⭐️ 자바스크립트가 오늘 날짜를 인식할 수 있도록 다양한 포맷 생성
    today_formats = [
        now.strftime('%Y-%m-%d'), now.strftime('%Y.%m.%d'), now.strftime('%Y/%m/%d'),
        f"{now.month:02d}-{now.day:02d}", f"{now.month:02d}.{now.day:02d}", f"{now.month:02d}/{now.day:02d}",
        f"{now.month}월 {now.day}일", f"{now.month}-{now.day}", f"{now.month}.{now.day}", f"{now.month}/{now.day}"
    ]
    today_js_array = json.dumps(today_formats)
    kst_now = now.strftime('%Y-%m-%d %H:%M:%S')

    # CSS 테두리 강제 주입 및 오늘 일정 스크립트 추가
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 공유 일정</title>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; background-color: #f8f9fa; color: #333; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; margin-top: 30px; }}
            .sync-time {{ color: #7f8c8d; font-size: 13px; margin-bottom: 20px; }}
            
            /* 테이블 기본 디자인 */
            .table-container {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; margin-bottom: 40px; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 10px !important; text-align: center; white-space: nowrap; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; }}
            
            /* 오늘 일정 전용 하이라이트 디자인 */
            .today-highlight {{ border: 2px solid #e11d48; box-shadow: 0 4px 15px rgba(225, 29, 72, 0.15); }}
            .today-title {{ color: #e11d48; border-bottom: 2px solid #e11d48; margin-top: 10px; }}
            .empty-msg {{ padding: 20px; text-align: center; color: #6b7280; font-style: italic; font-size: 15px; }}
        </style>
    </head>
    <body>
        <h2 class="today-title">🔥 오늘 일정</h2>
        <div id="today-container" class="table-container today-highlight">
            <div class="empty-msg">데이터를 분석 중입니다...</div>
        </div>

        <h2>📋 전체 일정 목록</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        <div class="table-container" id="raw-table-container">
            {extracted_html}
        </div>

        <script>
            // 원본 표를 해치지 않고 오늘 일정만 복사해오는 마법의 스크립트
            document.addEventListener('DOMContentLoaded', () => {{
                const rawContainer = document.getElementById('raw-table-container');
                const table = rawContainer.querySelector('table');
                const todayContainer = document.getElementById('today-container');

                if(!table || !table.rows || table.rows.length < 1) {{
                    todayContainer.innerHTML = '<div class="empty-msg">표 데이터를 찾을 수 없습니다.</div>';
                    return;
                }}

                // 원본 표의 합쳐진 칸(rowspan)을 메모리상에서만 평평하게 폅니다.
                const trs = table.rows; 
                const matrix = [];
                for(let i=0; i<trs.length; i++) matrix.push([]);

                for(let r=0; r<trs.length; r++) {{
                    const cells = trs[r].cells;
                    let c = 0;
                    for(let i=0; i<cells.length; i++) {{
                        while(matrix[r][c] !== undefined) c++;
                        
                        const cell = cells[i];
                        const rowspan = cell.rowSpan || 1;
                        const colspan = cell.colSpan || 1;
                        const html = cell.innerHTML;
                        const text = cell.innerText.trim();

                        for(let rr=0; rr<rowspan; rr++) {{
                            for(let cc=0; cc<colspan; cc++) {{
                                if(!matrix[r+rr]) matrix[r+rr] = [];
                                matrix[r+rr][c+cc] = {{ html: html, text: text }};
                            }}
                        }}
                    }}
                }}

                const headers = matrix[0] || [];
                const bodyData = matrix.slice(1).filter(row => row && row.length > 0);

                // 날짜 열 자동 탐색
                let dateIdx = headers.findIndex(h => h && (h.text.includes('일자') || h.text.includes('일시') || h.text.includes('날짜')));
                if(dateIdx === -1 && bodyData.length > 0) {{
                    dateIdx = bodyData[0].findIndex(c => c && (/[0-9]{{2,4}}[-./][0-9]{{1,2}}/.test(c.text) || c.text.includes('월')));
                }}
                if(dateIdx === -1) dateIdx = 1;

                // 오늘 날짜 필터링
                const todayFormats = {today_js_array};
                const isToday = (text) => todayFormats.some(fmt => text.includes(fmt));

                const todayData = bodyData.filter(row => row[dateIdx] && isToday(row[dateIdx].text));

                // 오늘 일정이 없을 경우 처리
                if(todayData.length === 0) {{
                    todayContainer.innerHTML = '<div class="empty-msg">오늘은 예정된 공유 일정이 없습니다. 🎉</div>';
                    return;
                }}

                // 오늘 일정 표 새로 그리기
                let newHtml = '<table><thead><tr>';
                headers.forEach(h => {{
                    if(h) newHtml += `<th>${{h.text}}</th>`;
                }});
                newHtml += '</tr></thead><tbody>';

                todayData.forEach(row => {{
                    newHtml += '<tr>';
                    row.forEach(cell => {{
                        if(cell) newHtml += `<td>${{cell.html}}</td>`;
                    }});
                    newHtml += '</tr>';
                }});
                newHtml += '</tbody></table>';

                // 상단 컨테이너에 복사된 오늘 표 삽입
                todayContainer.innerHTML = newHtml;
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
