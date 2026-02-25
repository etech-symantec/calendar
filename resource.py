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
    # [변경됨] 2. 상단 '일정' 메뉴 클릭
    # ------------------------------------------------------------------
    print("2. Clicking top '일정' (Schedule) menu...")
    try:
        # 기존에 사용했던 '일정' 메뉴 ID 재사용
        page.click('#topMenu300000000', timeout=20000)
    except Exception as e:
        print(f"[DEBUG] ID click failed, trying text: {e}")
        page.locator('text="일정"').first.click(timeout=20000)
    
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    # ------------------------------------------------------------------
    # [변경됨] 3. 좌측 '자원관리' -> '자원캘린더' 클릭
    # ------------------------------------------------------------------
    print("3. Clicking left '자원관리' -> '자원캘린더'...")
    try:
        # 1. 좌측 메뉴에서 '자원관리' 클릭 (폴더 열기)
        print("   - Clicking '자원관리'...")
        # 좌측 메뉴 영역(nav 등) 내의 텍스트를 찾는 것이 정확하나, 
        # 구조상 visible한 텍스트를 순차적으로 클릭합니다.
        page.locator('text="자원관리"').click(timeout=10000)
        time.sleep(1) # 메뉴가 펼쳐지는 시간 대기

        # 2. '자원캘린더' 클릭
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
    # 5. Extract HTML for Dashboard
    # ------------------------------------------------------------------
    print("5. Extracting Dashboard HTML...")
    extracted_html = ""
    try:
        # 테이블 ID가 동일하다고 가정 (#customListMonthDiv)
        extracted_html = frame.locator('#customListMonthDiv').inner_html(timeout=10000)
    except Exception as e:
        print(f"[DEBUG] Extraction error: {e}")
        try:
            extracted_html = page.locator('#customListMonthDiv').inner_html(timeout=10000)
        except:
            extracted_html = "<p>Failed to load data.</p>"
    print(f"[DEBUG] Extracted HTML length: {len(extracted_html)}")

    # ------------------------------------------------------------------
    # 6. Python-side Calculation for BOTH Teams
    # ------------------------------------------------------------------
    print("6. Calculating Today's Schedule for Blue & Yellow Teams...")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    # 요일 구하기 (0:월, ... 6:일)
    weekday_index = now.weekday()
    weekday_list = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_str = weekday_list[weekday_index]
    
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG] Target Date: {now.month}/{now.day} ({weekday_str})")

    today_blue_events = []
    today_yellow_events = []
    
    try:
        # 1. Locate the table
        table_handle = None
        try:
            table_handle = frame.locator('#customListMonthDiv table')
            if table_handle.count() == 0: raise Exception("No table in frame")
        except:
            table_handle = page.locator('#customListMonthDiv table')
        
        if table_handle and table_handle.count() > 0:
            # 2. Get all row data using JS evaluation
            rows_data = table_handle.first.evaluate("""(table) => {
                const rows = Array.from(table.rows);
                return rows.map(tr => {
                    return Array.from(tr.children).map(cell => ({
                        text: cell.innerText.trim(),
                        rowspan: parseInt(cell.getAttribute('rowspan') || 1, 10),
                        colspan: parseInt(cell.getAttribute('colspan') || 1, 10)
                    }));
                });
            }""")

            # 3. Python-side Table Flattening
            grid = []
            for r_idx, row in enumerate(rows_data):
                while len(grid) <= r_idx:
                    grid.append([])
                
                c_idx = 0
                for cell in row:
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                        c_idx += 1
                    
                    text = cell['text']
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
                            grid[target_row][target_col] = text
                    c_idx += colspan

            # 4. Filter Logic
            blue_team = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"]
            yellow_team = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"]
            
            print(f"[DEBUG] Processed {len(grid)} rows in Python.")
            
            for r_idx, row in enumerate(grid):
                # 첫 번째 줄은 헤더로 처리 (조건: 인덱스 0)
                is_header = (r_idx == 0)
                
                if len(row) < 3 and not is_header: continue

                # 데이터 추출
                date_txt = row[0]['text'] if row[0] else ""
                name_txt = row[-1]['text'] if row[-1] else ""
                # 일정명: 보통 3번째(index 2) 또는 2번째(index 1)
                title_txt = ""
                if len(row) > 2: title_txt = row[2]['text']
                elif len(row) > 1: title_txt = row[1]['text']

                # HTML Row 생성
                # 헤더면 class="header-row", 아니면 data-name 속성 추가
                tr_attrs = 'class="header-row"' if is_header else f'data-name="{name_txt}"'
                
                tr_html = f'<tr {tr_attrs}>'
                for cell in row:
                    if cell:
                        tag = 'th' if is_header else cell['tagName'] # 헤더는 th 강제
                        # 헤더 스타일 보정 (배경색 등)
                        style = cell['style']
                        if is_header: style += "; background-color: #e5e7eb; font-weight: bold;"
                        
                        tr_html += f'<{tag} class="{cell["className"]}" style="{style}">{cell["html"]}</{tag}>'
                    else:
                        tr_html += '<td></td>'
                tr_html += '</tr>'
                
                if is_header:
                    table_head_html += tr_html
                else:
                    table_body_html += tr_html

                # -----------------------
                # 잔디 전송용 데이터 추출 (헤더 제외)
                # -----------------------
                if is_header: continue

                clean_date = re.sub(r'\s+', '', date_txt)
                nums = re.findall(r'\d+', clean_date)
                
                if len(nums) < 2: continue
                
                m = int(nums[0])
                d = int(nums[1])
                
                if len(nums) >= 3 and int(nums[0]) > 2000:
                    m = int(nums[1])
                    d = int(nums[2])

                # Check Date
                if m == now.month and d == now.day:
                    # 🔵 Check Blue Team
                    if any(member in name_txt for member in blue_team):
                        if title_txt and title_txt not in today_blue_events:
                            today_blue_events.append(title_txt)
                            print(f"[DEBUG] [Blue] Found: {title_txt} ({name_txt})")
                    
                    # 🟡 Check Yellow Team
                    if any(member in name_txt for member in yellow_team):
                        if title_txt and title_txt not in today_yellow_events:
                            today_yellow_events.append(title_txt)
                            print(f"[DEBUG] [Yellow] Found: {title_txt} ({name_txt})")

        else:
            print("[ERROR] Table not found for data extraction.")

    except Exception as e:
        print(f"[ERROR] Python calculation failed: {e}")

    print(f"[DEBUG] Blue Events: {len(today_blue_events)}, Yellow Events: {len(today_yellow_events)}")

    # ------------------------------------------------------------------
    # 7. Create resource.html
    # ------------------------------------------------------------------
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
        <div class="table-container" id="wrapper">{extracted_html}</div>
        <script>
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];
            document.addEventListener("DOMContentLoaded", function() {{
                const table = document.querySelector('#wrapper table');
                if(!table) return;
                const trs = Array.from(table.rows);
                const grid = [];
                trs.forEach((tr, r) => {{
                    if (!grid[r]) grid[r] = [];
                    let c = 0;
                    Array.from(tr.cells).forEach(cell => {{
                        while (grid[r][c]) c++;
                        const rs = cell.rowSpan || 1;
                        const cs = cell.colSpan || 1;
                        for (let rr = 0; rr < rs; rr++) {{
                            for (let cc = 0; cc < cs; cc++) {{
                                if (!grid[r + rr]) grid[r + rr] = [];
                                grid[r + rr][c + cc] = {{ html: cell.innerHTML, tag: cell.tagName, cls: cell.className }};
                            }}
                        }}
                    }});
                }});
                let newBody = '<tbody>';
                for (let r = 0; r < grid.length; r++) {{
                    newBody += '<tr>';
                    grid[r].forEach(cell => {{ newBody += `<${{cell.tag}} class="${{cell.cls}}">${{cell.html}}</${{cell.tag}}>`; }});
                    newBody += '</tr>';
                }}
                table.innerHTML = newBody + '</tbody>';
                applyFilter('blue');
            }});

            function applyFilter(team) {{
                document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
                document.querySelector(`.btn-${{team}}`).classList.add('active');
                const rows = Array.from(document.querySelectorAll('#wrapper tbody tr'));
                rows.forEach(r => {{
                    r.classList.remove('hidden-row');
                    r.style.backgroundColor = '';
                    const first = r.children[0];
                    first.classList.remove('hidden-cell');
                    first.setAttribute('rowspan', 1);
                    Array.from(r.children).forEach(c => {{ c.style.color = ''; c.style.fontWeight = ''; }});
                }});
                let visible = rows.filter(r => {{
                    const name = r.cells[r.cells.length-1].innerText.trim();
                    if(team === 'all') return true;
                    if(team === 'blue') return blueTeam.some(m => name.includes(m));
                    if(team === 'yellow') return yellowTeam.some(m => name.includes(m));
                    return false;
                }});
                rows.forEach(r => {{ if(!visible.includes(r)) r.classList.add('hidden-row'); }});
                if(visible.length > 0) {{
                    let lastCell = visible[0].cells[0], lastText = lastCell.innerText.trim(), count = 1;
                    for(let i=1; i<visible.length; i++) {{
                        const cur = visible[i].cells[0], curText = cur.innerText.trim();
                        if(curText === lastText && curText !== "") {{ cur.classList.add('hidden-cell'); count++; lastCell.setAttribute('rowspan', count); }}
                        else {{ lastCell = cur; lastText = curText; count = 1; }}
                    }}
                }}
                const today = new Date(), tM = today.getMonth()+1, tD = today.getDate();
                const list = document.getElementById('today-list'); list.innerHTML = '';
                let todayCount = 0, currentIsToday = false;
                visible.forEach(r => {{
                    const dateCell = r.cells[0];
                    if(!dateCell.classList.contains('hidden-cell')) {{
                        const nums = dateCell.innerText.match(/\\d+/g);
                        if(nums && nums.length >= 2) {{
                            let m = parseInt(nums[0]), d = parseInt(nums[1]);
                            if(nums.length>=3 && parseInt(nums[0])>2000) {{ m=parseInt(nums[1]); d=parseInt(nums[2]); }}
                            currentIsToday = (m === tM && d === tD);
                        }}
                    }}
                    if(currentIsToday) {{
                        r.style.backgroundColor = '#fff1f2';
                        Array.from(r.cells).forEach(c => {{ c.style.color = '#9f1239'; c.style.fontWeight = 'bold'; }});
                        const tds = r.querySelectorAll('td');
                        if (tds.length >= 3) {{
                            const title = tds[1].innerText.trim();
                            const li = document.createElement('li');
                            li.innerText = title; 
                            list.appendChild(li); todayCount++;
                        }}
                    }}
                }});
                if(todayCount === 0) list.innerHTML = '<li>선택된 팀의 오늘 일정이 없습니다. 🎉</li>';
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
