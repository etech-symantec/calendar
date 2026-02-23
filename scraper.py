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
    
    # 앞뒤 불필요한 부분 자르기 (원본 데이터 보존)
    start_keyword = "2026년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    now = datetime.now()
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # ⭐️ 오늘 날짜를 식별하기 위한 다양한 포맷 생성 (그룹웨어 날짜 표시 형식이 어떻든 잡아내기 위함)
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

    # 🎨 필터링 및 분리 렌더링이 포함된 스마트 대시보드 HTML
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>스마트 일정 대시보드</title>
        <style>
            :root {{
                --primary: #4f46e5;
                --bg: #f3f4f6;
                --text: #1f2937;
                --border: #e5e7eb;
            }}
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
            
            /* 평탄화된 독립적 행 디자인 (검색에 최적화) */
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
                const trs = Array.from(rawContent.querySelectorAll('tr'));
                
                if(trs.length < 2) {{
                    document.getElementById('all-container').innerHTML = '<div class="empty-msg">가져올 데이터가 부족합니다.</div>';
                    return;
                }}

                // 1. 합쳐진 칸(rowspan)을 완벽한 2차원 배열(바둑판)로 풀기
                const matrix = [];
                for(let i=0; i<trs.length; i++) matrix.push([]);

                for(let r=0; r<trs.length; r++) {{
                    const cells = trs[r].querySelectorAll('th, td');
                    let c = 0;
                    for(let i=0; i<cells.length; i++) {{
                        while(matrix[r][c] !== undefined) c++;
                        
                        const cell = cells[i];
                        const rowspan = parseInt(cell.getAttribute('rowspan') || 1, 10);
                        const colspan = parseInt(cell.getAttribute('colspan') || 1, 10);
                        const html = cell.innerHTML;
                        const text = cell.innerText.trim();

                        for(let rr=0; rr<rowspan; rr++) {{
                            for(let cc=0; cc<colspan; cc++) {{
                                if(!matrix[r+rr]) matrix[r+rr] = [];
                                matrix[r+rr][c+cc] = {{ html, text }};
                            }}
                        }}
                    }}
                }}

                // 2. 헤더와 데이터 분리
                let headers = [];
                let bodyData = [];
                if(trs[0].querySelector('th')) {{
                    headers = matrix[0];
                    bodyData = matrix.slice(1).filter(row => row.length > 0);
                }} else {{
                    // 원본에서 제목줄이 잘렸을 경우 기본 헤더 임시 생성
                    headers = matrix[0].map((_, i) => ({{ text: `항목 ${{i+1}}`, html: `항목 ${{i+1}}` }}));
                    bodyData = matrix.filter(row => row.length > 0);
                }}

                // 3. '날짜' 열 똑똑하게 찾기
                let dateIdx = headers.findIndex(h => h.text.includes('일자') || h.text.includes('일시') || h.text.includes('날짜') || h.text.includes('기간'));
                if(dateIdx === -1 && bodyData.length > 0) {{
                    dateIdx = bodyData[0].findIndex(c => /\\d{{2,4}}[-./]\\d{{1,2}}/.test(c.text) || c.text.includes('월'));
                }}
                if(dateIdx === -1) dateIdx = 1; // 기본 백업값

                // 4. 오늘 데이터 / 전체 데이터 깔끔하게 분류
                const todayFormats = {today_js_array};
                const isToday = (text) => todayFormats.some(fmt => text.includes(fmt));

                let todayData = bodyData.filter(row => row[dateIdx] && isToday(row[dateIdx].text));
                let allData = bodyData;

                // 5. 테이블 렌더링 함수 (평탄화된 독립적인 행 구조 적용 -> 검색 버그 해결!)
                const renderTable = (containerId, data) => {{
                    const container = document.getElementById(containerId);
                    if(data.length === 0) {{
                        container.innerHTML = '<div class="empty-msg">해당하는 일정이 없습니다.</div>';
                        return;
                    }}

                    let html = '<table class="styled-table"><thead><tr>';
                    headers.forEach(h => html += `<th>${{h.text}}</th>`);
                    html += '</tr></thead><tbody>';

                    data.forEach(row => {{
                        html += '<tr>';
                        row.forEach(cell => html += `<td>${{cell.html}}</td>`);
                        html += '</tr>';
                    }});
                    html += '</tbody></table>';
                    container.innerHTML = html;
                }};

                // 6. 완벽하게 동작하는 실시간 검색(필터링) 기능
                const applyFilter = (term) => {{
                    term = term.toLowerCase();
                    const filterFn = row => row.some(cell => cell.text.toLowerCase().includes(term));
                    
                    renderTable('today-container', term ? todayData.filter(filterFn) : todayData);
                    renderTable('all-container', term ? allData.filter(filterFn) : allData);
                }};

                // 초기 그리기
                applyFilter('');

                // 검색창 키보드 입력 이벤트
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
