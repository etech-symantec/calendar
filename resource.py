import os
import time
import requests
import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

def run(playwright):
    print("--------------------------------------------------")
    print("🚀 Script Started: checking environment variables...")
    
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Load environment variables
    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")
    JANDI_URL = os.environ.get("JANDI_WEBHOOK_URL", "")

    # [LOG] Check sensitive variables
    print(f"[DEBUG] USER_ID: {'***' + USER_ID[-2:] if len(USER_ID) > 2 else '***'} (Length: {len(USER_ID)})")
    print(f"[DEBUG] JANDI_URL: {'Set' if JANDI_URL else 'Not Set'}")

    print("1. Accessing login page...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    # ------------------------------------------------------------------
    # 2. 상단 '일정' 메뉴 클릭
    # ------------------------------------------------------------------
    print("2. Clicking top '일정' (Schedule) menu...")
    try:
        page.click('#topMenu300000000', timeout=20000)
    except Exception as e:
        print(f"[DEBUG] ID click failed, trying text: {e}")
        page.locator('text="일정"').first.click(timeout=20000)
    
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    # ------------------------------------------------------------------
    # 3. 좌측 '자원관리' -> '자원캘린더' 클릭
    # ------------------------------------------------------------------
    print("3. Clicking left '자원관리' -> '자원캘린더'...")
    try:
        print("   - Clicking '자원관리'...")
        page.locator('text="자원관리"').click(timeout=10000)
        time.sleep(1) 

        print("   - Clicking '자원캘린더'...")
        page.locator('text="자원캘린더"').click(timeout=10000)
    except Exception as e:
        print(f"[ERROR] Left menu navigation failed: {e}")
        
    time.sleep(3)

    # ------------------------------------------------------------------
    # 4. 우측 본문에서 '일정목록' 탭 클릭
    # ------------------------------------------------------------------
    print("4. Clicking 'Schedule List' tab in right content...")
    frame = page.frame_locator('#_content')
    try:
        frame.locator('text="일정목록"').click(timeout=20000)
    except:
        print("[DEBUG] Frame locator failed, retrying on main page...")
        page.locator('text="일정목록"').click(timeout=20000)

    print("✅ Page entry successful! Waiting for data loading...")
    time.sleep(5)
    
    # ------------------------------------------------------------------
    # 5 & 6. 데이터 추출 및 분석 (파이썬에서 HTML 생성)
    # ------------------------------------------------------------------
    print("5. Extracting & Processing Data...")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    weekday_index = now.weekday()
    weekday_list = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_str = weekday_list[weekday_index]
    
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG] Target Date: {now.month}/{now.day} ({weekday_str})")

    today_blue_events = []
    today_yellow_events = []
    
    # HTML Table Rows를 저장할 변수
    table_rows_html = ""

    try:
        # 1. Locate the table
        table_handle = None
        try:
            table_handle = frame.locator('#customListMonthDiv table')
            if table_handle.count() == 0: raise Exception("No table in frame")
        except:
            table_handle = page.locator('#customListMonthDiv table')
        
        if table_handle and table_handle.count() > 0:
            # 2. Get all row data (텍스트 + HTML 스타일 포함)
            # 파이썬으로 가공하기 쉽게 데이터를 구조화해서 가져옵니다.
            rows_data = table_handle.first.evaluate("""(table) => {
                const rows = Array.from(table.rows);
                return rows.map(tr => {
                    return Array.from(tr.children).map(cell => ({
                        text: cell.innerText.trim(),
                        html: cell.innerHTML, 
                        tagName: cell.tagName.toLowerCase(),
                        className: cell.className,
                        style: cell.getAttribute('style') || '',
                        rowspan: parseInt(cell.getAttribute('rowspan') || 1, 10),
                        colspan: parseInt(cell.getAttribute('colspan') || 1, 10)
                    }));
                });
            }""")

            # 3. Python-side Table Flattening & HTML Generation
            grid = []
            
            # (A) Flatten Logic
            for r_idx, row in enumerate(rows_data):
                while len(grid) <= r_idx:
                    grid.append([])
                
                c_idx = 0
                for cell in row:
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                        c_idx += 1
                    
                    cell_obj = cell # Keep full object
                    rowspan = cell['rowspan']
                    colspan = cell['colspan']
                    
                    for rr in range(rowspan):
                        target_row = r_idx + rr
                        while len(grid) <= target_row:
                            grid.append([])
                        
                        for cc in range(colspan):
                            target_col = c_idx + cc
                            while len(grid[target_row]) <= target_col:
                                grid[target_row].append(None)
                            # 셀 데이터를 복사해서 넣음
                            grid[target_row][target_col] = cell_obj
                    c_idx += colspan
            
            # (B) Filtering & HTML Generation Logic
            blue_team = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"]
            yellow_team = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"]
            
            print(f"[DEBUG] Processed {len(grid)} rows in Python.")
            
            for row in grid:
                if len(row) < 3: continue

                # 날짜 및 이름 추출 (분석용)
                date_txt = row[0]['text']
                name_txt = row[-1]['text']
                title_txt = row[2]['text'] if len(row) > 2 else row[1]['text']

                # 날짜 파싱
                clean_date = re.sub(r'\s+', '', date_txt)
                nums = re.findall(r'\d+', clean_date)
                
                # HTML Row 생성 (파이썬에서 직접 그림)
                # 이 행의 작성자를 data-name 속성에 넣어서 나중에 JS로 필터링하기 쉽게 만듦
                tr_html = f'<tr data-name="{name_txt}">'
                for cell in row:
                    if cell:
                        # 원본 스타일과 클래스를 유지하며 셀 생성
                        tr_html += f'<{cell["tagName"]} class="{cell["className"]}" style="{cell["style"]}">{cell["html"]}</{cell["tagName"]}>'
                    else:
                        tr_html += '<td></td>'
                tr_html += '</tr>'
                
                table_rows_html += tr_html # 전체 HTML에 추가

                # -----------------------
                # 잔디 전송용 데이터 추출
                # -----------------------
                if len(nums) < 2: continue
                m = int(nums[0])
                d = int(nums[1])
                if len(nums) >= 3 and int(nums[0]) > 2000:
                    m = int(nums[1])
                    d = int(nums[2])

                if m == now.month and d == now.day:
                    if any(member in name_txt for member in blue_team):
                        if title_txt and title_txt not in today_blue_events:
                            today_blue_events.append(title_txt)
                            print(f"[DEBUG] [Blue] Found: {title_txt} ({name_txt})")
                    
                    if any(member in name_txt for member in yellow_team):
                        if title_txt and title_txt not in today_yellow_events:
                            today_yellow_events.append(title_txt)
                            print(f"[DEBUG] [Yellow] Found: {title_txt} ({name_txt})")

        else:
            print("[ERROR] Table not found for data extraction.")
            table_rows_html = "<tr><td>데이터를 불러오지 못했습니다. (테이블 없음)</td></tr>"

    except Exception as e:
        print(f"[ERROR] Python calculation failed: {e}")
        table_rows_html = f"<tr><td>에러 발생: {e}</td></tr>"

    print(f"[DEBUG] Blue Events: {len(today_blue_events)}, Yellow Events: {len(today_yellow_events)}")

    # ------------------------------------------------------------------
    # 7. Create resource.html
    # ------------------------------------------------------------------
    # 파이썬이 만든 HTML 테이블 행(table_rows_html)을 템플릿에 바로 꽂아넣습니다.
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>일정 대시보드</title>
        <style>
            body {{ font-family: 'Pretendard', sans-serif; padding: 15px; background-color: #f8f9fa; color: #333; font-size: 11px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 8px; margin: 0 0 10px 0; font-size: 16px; }}
            .sync-time {{ color: #7f8c8d; font-size: 10px; margin-bottom: 15px; text-align: right; }}
            .controls {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .btn-group {{ display: flex; gap: 5px; }}
            .btn {{ border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: bold; transition: 0.2s; }}
            .btn-blue {{ background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
            .btn-blue.active, .btn-blue:hover {{ background-color: #0ea5e9; color: white; }}
            .btn-yellow {{ background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047; }}
            .btn-yellow.active, .btn-yellow:hover {{ background-color: #eab308; color: white; }}
            .btn-all {{ background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }}
            .btn-all.active, .btn-all:hover {{ background-color: #6b7280; color: white; }}
            .summary-box {{ background: #fff; border-left: 4px solid #e11d48; padding: 12px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .summary-box h3 {{ margin: 0 0 8px 0; color: #e11d48; font-size: 13px; }}
            .summary-box ul {{ margin: 0; padding-left: 20px; line-height: 1.5; color: #333; }}
            .summary-box li {{ padding: 3px 0; border-bottom: 1px dashed #ffe4e6; }}
            .table-container {{ background: #fff; padding: 10px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; max-height: 80vh; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #d1d5db !important; padding: 6px 8px !important; text-align: center; white-space: nowrap; font-size: 11px; }}
            th {{ background-color: #e5e7eb !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; color: #374151; }}
            .hidden-row {{ display: none !important; }}
            .hidden-cell {{ display: none !important; }}
        </style>
    </head>
    <body>
        <div class="controls">
            <h2>📅 일정 대시보드</h2>
            <div class="btn-group">
                <button class="btn btn-blue active" onclick="applyFilter('blue')">🔵 블루팀</button>
                <button class="btn btn-yellow" onclick="applyFilter('yellow')">🟡 옐로우팀</button>
                <button class="btn btn-all" onclick="applyFilter('all')">📋 전체보기</button>
            </div>
        </div>
        <div class="summary-box">
            <h3>🔥 선택된 팀의 오늘 일정</h3>
            <ul id="today-list"><li>데이터 로딩 중...</li></ul>
        </div>
        <p class="sync-time">Update: {kst_now_str}</p>
        
        <div class="table-container" id="wrapper">
            <table id="scheduleTable">
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>

        <script>
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];

            document.addEventListener("DOMContentLoaded", function() {{
                applyFilter('blue'); // 초기 필터
            }});

            function applyFilter(team) {{
                // 버튼 스타일 변경
                document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
                document.querySelector(`.btn-${{team}}`).classList.add('active');
                
                const rows = Array.from(document.querySelectorAll('#scheduleTable tbody tr'));
                let visibleRows = [];

                rows.forEach(r => {{
                    // 파이썬에서 넣어준 data-name 속성을 확인
                    const name = r.getAttribute('data-name') || "";
                    let isVisible = false;

                    if(team === 'all') isVisible = true;
                    else if(team === 'blue' && blueTeam.some(m => name.includes(m))) isVisible = true;
                    else if(team === 'yellow' && yellowTeam.some(m => name.includes(m))) isVisible = true;

                    if(isVisible) {{
                        r.classList.remove('hidden-row');
                        visibleRows.push(r);
                    }} else {{
                        r.classList.add('hidden-row');
                    }}
                }});

                updateSummary(visibleRows);
            }}

            function updateSummary(visibleRows) {{
                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                const list = document.getElementById('today-list'); 
                list.innerHTML = '';
                
                let count = 0;
                let isTodayGroup = false;

                visibleRows.forEach(r => {{
                    // 첫 번째 셀(날짜) 확인
                    const firstCell = r.querySelector('td, th');
                    if(!firstCell) return;
                    
                    const dateText = firstCell.innerText;
                    const nums = dateText.match(/\\d+/g);
                    
                    if(nums && nums.length >= 2) {{
                        let m = parseInt(nums[0]);
                        let d = parseInt(nums[1]);
                        if(nums.length >= 3 && parseInt(nums[0]) > 2000) {{ m = parseInt(nums[1]); d = parseInt(nums[2]); }}
                        
                        isTodayGroup = (m === tM && d === tD);
                    }}

                    if(isTodayGroup) {{
                        r.style.backgroundColor = '#fff1f2'; 
                        // 일정명 추출 (보통 3번째 또는 2번째 셀)
                        const cells = r.querySelectorAll('td');
                        const title = cells[2] ? cells[2].innerText.trim() : (cells[1] ? cells[1].innerText.trim() : "일정");
                        
                        const li = document.createElement('li');
                        li.innerText = title;
                        list.appendChild(li);
                        count++;
                    }} else {{
                        r.style.backgroundColor = ''; 
                    }}
                }});

                if(count === 0) list.innerHTML = '<li>선택된 팀의 오늘 일정이 없습니다. 🎉</li>';
            }}
        </script>
    </body>
    </html>
    """

    with open("resource.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("✅ resource.html created!")

    

    print("[DEBUG] Closing browser...")
    browser.close()
    print("[DEBUG] Script finished.")

with sync_playwright() as playwright:
    run(playwright)
