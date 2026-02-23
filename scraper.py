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
    
    print("5. 데이터 추출 및 마법의 UI 템플릿 적용 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # 앞뒤 불필요한 부분 자르기
    start_keyword = "2026년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    now = datetime.now()
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    today_formats = [
        now.strftime('%Y-%m-%d'),
        now.strftime('%Y.%m.%d'),
        now.strftime('%Y/%m/%d'),
        f"{now.month:02d}-{now.day:02d}",
        f"{now.month:02d}.{now.day:02d}",
        f"{now.month:02d}/{now.day:02d}",
        f"{now.month}월 {now.day}일",
        f"{now.month}-{now.day}",
        f"{now.month}.{now.day}",
        f"{now.month}/{now.day}"
    ]
    today_js_array = str(today_formats)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>스마트 일정 대시보드</title>
        <style>
            :root {{ --primary: #4f46e5; --bg: #f3f4f6; --text: #1f2937; --border: #e5e7eb; }}
            body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; background: var(--bg); color: var(--text); padding: 30px; margin: 0; }}
            .header-container {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 25px; border-bottom: 2px solid var(--border); padding-bottom: 15px; }}
            h2 {{ margin: 0; font-size: 24px; color: #111827; }}
            .sync-time {{ margin: 0; font-size: 14px; color: #6b7280; }}
            
            .search-container {{ margin-bottom: 30px; }}
            .search-box {{ width: 100%; max-width: 500px; padding: 14px 20px; border: 1px solid var(--border); border-radius: 10px; font-size: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s; }}
            .search-box:focus {{ outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1); }}
            
            .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }}
            .section-title.today {{ color: #e11d48; }}
            .section-title.all {{ color: #4338ca; margin-top: 40px; }}
            
            .table-container {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow-x: auto; max-height: 50vh; margin-bottom: 20px; border: 1px solid var(--border); }}
            
            .styled-table {{ width: 100%; border-collapse: collapse; text-align: left; white-space: nowrap; }}
            .styled-table th, .styled-table td {{ padding: 14px 18px; border-bottom: 1px solid var(--border); }}
            .styled-table th {{ background-color: #f9fafb; font-weight: 600; color: #374151; position: sticky; top: 0; z-index: 10; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .styled-table tbody tr:hover {{ background-color: #f0fdf4; transition: 0.2s; }}
            
            .empty-msg {{ padding: 30px; text-align: center; color: #9ca3af; font-size: 15px; }}
        </style>
    </head>
    <body>
        <div class="header-container">
            <h2>📅 스마트 공유 일정</h2>
            <p class="sync-time">🔄 마지막 동기화: {kst_now_str}</p>
        </div>
        
        <div class="search-container">
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 참석자, 회의명 등을 검색하세요 (엔터 불필요)">
        </div>

        <div class="section-title today">🔥 오늘 일정</div>
        <div id="today-container" class="table-container"></div>

        <div class="section-title all">📋 전체 일정</div>
        <div id="all-container" class="table-container"></div>

        <div id="raw-content" style="display: none;">
            <table>{extracted_html}</table>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                const rawContent = document.getElementById('raw-content');
                let table = rawContent.querySelector('table');
                
                // 표를 찾을 수 없다면 중지
                if(!table || !table.rows || table.rows.length < 1) {{
                    document.getElementById('all-container').innerHTML = '<div class="empty-msg">표 데이터를 찾을 수 없습니다.</div>';
                    return;
                }}

                // 🌟 핵심 버그 픽스: querySelectorAll 대신 table.rows를 사용하여 안쪽 중첩 표의 간섭을 원천 차단!
                const trs = table.rows; 
                const matrix = [];
                for(let i=0; i<trs.length; i++) matrix.push([]);

                for(let r=0; r<trs.length; r++) {{
                    const cells = trs[r].cells; // 현재 줄의 칸만 가져옵니다.
                    let c = 0;
                    for(let i=0; i<cells.length; i++) {{
                        // 위에서 합쳐진 빈 공간 건너뛰기
                        while(matrix[r][c] !== undefined) c++;
                        
                        const cell = cells[i];
                        const rowspan = cell.rowSpan || 1;
                        const colspan = cell.colSpan || 1;
                        const html = cell.innerHTML;
                        const text = cell.innerText.trim();

                        // 바둑판에 데이터 채워넣기
                        for(let rr=0; rr<rowspan; rr++) {{
                            for(let cc=0; cc<colspan; cc++) {{
                                if(!matrix[r+rr]) matrix[r+rr] = [];
                                matrix[r+rr][c+cc] = {{ html, text }};
                            }}
                        }}
                    }}
                }}

                // 헤더와 데이터 분리
                const headers = matrix[0] || [];
                const bodyData = matrix.slice(1).filter(row => row && row.length > 0);

                // '날짜' 열 똑똑하게 찾기
                let dateIdx = headers.findIndex(h => h && (h.text.includes('일자') || h.text.includes('일시') || h.text.includes('날짜')));
                if(dateIdx === -1 && bodyData.length > 0) {{
                    dateIdx = bodyData[0].findIndex(c => c && (/[0-9]{{2,4}}[-./][0-9]{{1,2}}/.test(c.text) || c.text.includes('월')));
                }}
                if(dateIdx === -1) dateIdx = 1;

                // 오늘 일정 분류
                const todayFormats = {today_js_array};
                const isToday = (text) => todayFormats.some(fmt => text.includes(fmt));

                const todayData = bodyData.filter(row => row[dateIdx] && isToday(row[dateIdx].text));
                const allData = bodyData;

                // 테이블 그리기 함수
                const renderTable = (containerId, data) => {{
                    const container = document.getElementById(containerId);
                    if(data.length === 0) {{
                        container.innerHTML = '<div class="empty-msg">해당하는 일정이 없습니다.</div>';
                        return;
                    }}

                    let html = '<table class="styled-table"><thead><tr>';
                    headers.forEach(h => {{
                        if(h) html += `<th>${{h.text}}</th>`;
                    }});
                    html += '</tr></thead><tbody>';

                    data.forEach(row => {{
                        html += '<tr>';
                        row.forEach(cell => {{
                            if(cell) html += `<td>${{cell.html}}</td>`;
                        }});
                        html += '</tr>';
                    }});
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }};

                // 실시간 필터링
                const applyFilter = (term) => {{
                    term = term.toLowerCase();
                    const filterFn = row => row.some(cell => cell && cell.text.toLowerCase().includes(term));
                    
                    renderTable('today-container', term ? todayData.filter(filterFn) : todayData);
                    renderTable('all-container', term ? allData.filter(filterFn) : allData);
                }};

                applyFilter('');

                document.getElementById('searchInput').addEventListener('keyup', (e) => {{
                    applyFilter(e.target.value);
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
