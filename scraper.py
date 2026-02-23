import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

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
    
    print("5. 🌟 핵심: 화면에서 단 1개의 진짜 표만 찾아 완벽하게 평탄화 추출 중...")
    
    # 💡 이전처럼 어설프게 텍스트를 자르는 대신,
    # 브라우저 안에서 가장 데이터가 많은 '진짜 표' 딱 하나만 찾아서 평탄화 후 가져옵니다!
    extract_js = """
    () => {
        const tables = document.querySelectorAll('table');
        let targetTable = null;
        let maxRows = 0;
        
        // 1. 화면에 있는 표들 중 가장 줄(Row)이 많은 표가 진짜 데이터 표임
        tables.forEach(tbl => {
            if (tbl.rows.length > maxRows) {
                maxRows = tbl.rows.length;
                targetTable = tbl;
            }
        });
        
        if (!targetTable) return "<p>데이터 표를 찾을 수 없습니다.</p>";

        // 2. 찾아낸 단 1개의 표를 완벽하게 평탄화
        const trs = Array.from(targetTable.rows);
        const grid = [];
        
        trs.forEach((tr, r) => {
            if (!grid[r]) grid[r] = [];
            let c = 0;
            Array.from(tr.cells).forEach(cell => {
                while (grid[r][c]) c++;
                
                const rowspan = cell.rowSpan || 1;
                const colspan = cell.colSpan || 1;
                
                for (let rr = 0; rr < rowspan; rr++) {
                    for (let cc = 0; cc < colspan; cc++) {
                        if (!grid[r + rr]) grid[r + rr] = [];
                        const clone = cell.cloneNode(true);
                        clone.removeAttribute('rowspan');
                        clone.removeAttribute('colspan');
                        
                        // 복제된 빈칸은 살짝 연한 배경 처리
                        if (rr > 0 || cc > 0) {
                            clone.style.backgroundColor = '#f8fafc';
                            clone.style.color = '#64748b'; 
                        }
                        
                        grid[r + rr][c + cc] = clone;
                    }
                }
            });
        });
        
        // 3. 평탄화된 배열로 새로운 HTML 테이블 '1개'만 조립해서 파이썬으로 보냄
        let html = '<table>';
        for (let r = 0; r < grid.length; r++) {
            html += '<tr>';
            const row = grid[r];
            if (row) {
                for (let c = 0; c < row.length; c++) {
                    const cell = row[c];
                    if (cell) {
                        html += cell.outerHTML;
                    }
                }
            }
            html += '</tr>';
        }
        html += '</table>';
        
        return html;
    }
    """
    
    extracted_html = ""
    try:
        extracted_html = frame.evaluate(extract_js)
    except Exception:
        extracted_html = page.evaluate(extract_js)
    
    # KST (한국 표준시) 설정
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    kst_now = now.strftime('%Y-%m-%d %H:%M:%S')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>일정목록 추출</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background-color: #f8f9fa; color: #333; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; }}
            .sync-time {{ color: #7f8c8d; font-size: 13px; margin-bottom: 20px; }}
            
            .summary-box {{ background: #fff; border-left: 5px solid #e11d48; padding: 20px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            .summary-box h3 {{ margin: 0 0 10px 0; color: #e11d48; font-size: 18px; }}
            .summary-box ul {{ margin: 0; padding-left: 20px; line-height: 1.6; color: #333; }}
            .summary-box li {{ padding: 6px 0; border-bottom: 1px dashed #fecdd3; }}
            .summary-box li:last-child {{ border-bottom: none; }}

            .table-container {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 10px !important; text-align: center; white-space: nowrap; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; }}
        </style>
    </head>
    <body>
        <h2>📅 공유 일정 대시보드</h2>
        <p class="sync-time">마지막 동기화: {kst_now} (KST)</p>
        
        <div class="summary-box">
            <h3>🔥 오늘의 일정 요약</h3>
            <ul id="today-list">
                <li>데이터를 분석 중입니다...</li>
            </ul>
        </div>

        <div class="table-container">
            {extracted_html}
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                const table = document.querySelector('.table-container table');
                if (!table) return;

                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                
                const isToday = (text) => {{
                    if(!text) return false;
                    // 시간(09:00-18:00)을 날짜로 착각하는 것을 방지
                    if(text.includes(':')) return false; 
                    
                    const clean = text.replace(/\\s+/g, '');
                    const nums = clean.match(/\\d+/g);
                    if(!nums || nums.length < 2) return false;

                    let m, d;
                    if(nums.length >= 3 && parseInt(nums[0]) > 2000) {{
                        m = parseInt(nums[1], 10);
                        d = parseInt(nums[2], 10);
                    }} else {{
                        m = parseInt(nums[0], 10);
                        d = parseInt(nums[1], 10);
                    }}

                    return (m === tM && d === tD);
                }};

                const rows = table.rows;
                let todayEvents = [];

                for (let i = 0; i < rows.length; i++) {{
                    const row = rows[i];
                    if (row.cells.length === 0 || row.cells[0].tagName === 'TH') continue;

                    let isRowToday = false;
                    
                    // 각 줄의 앞부분(최대 3칸)만 검사해서 오늘 날짜가 있는지 확인
                    for (let j = 0; j < Math.min(row.cells.length, 3); j++) {{
                        if (isToday(row.cells[j].innerText)) {{
                            isRowToday = true;
                            break;
                        }}
                    }}

                    if (isRowToday) {{
                        // 줄 전체 하이라이트
                        Array.from(row.cells).forEach(c => {{
                            c.style.backgroundColor = '#fff1f2';
                            c.style.color = '#9f1239';
                            c.style.fontWeight = 'bold';
                        }});

                        // 요약 내용 추출
                        let rowData = [];
                        Array.from(row.cells).forEach(c => {{
                            const txt = c.innerText.trim().replace(/\\s+/g, ' '); 
                            if(txt) rowData.push(txt);
                        }});
                        if(rowData.length > 0) {{
                            todayEvents.push(rowData.join(' | '));
                        }}
                    }}
                }}

                // 상단 요약 업데이트
                const ul = document.getElementById('today-list');
                ul.innerHTML = '';
                
                if (todayEvents.length > 0) {{
                    todayEvents.forEach(evt => {{
                        const li = document.createElement('li');
                        li.innerText = evt;
                        ul.appendChild(li);
                    }});
                }} else {{
                    const li = document.createElement('li');
                    li.style.color = '#666';
                    li.innerText = '오늘 예정된 일정이 없습니다. 🎉';
                    ul.appendChild(li);
                }}
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
