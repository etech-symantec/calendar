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

    print("1. Accessing login page and schedule page...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("2. Clicking top 'Schedule' menu...")
    page.click('#topMenu300000000', timeout=20000)
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. Clicking left 'View All Shared Schedules' menu...")
    try:
        page.click('#301040000_all_anchor', timeout=20000)
    except:
        print("[DEBUG] Selector click failed, retrying with text locator...")
        page.locator('text="공유일정 전체보기"').click(timeout=20000)
    time.sleep(3)

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
    # 5. Extract HTML for Dashboard (Keep existing logic)
    # ------------------------------------------------------------------
    print("5. Extracting Dashboard HTML...")
    extracted_html = ""
    try:
        extracted_html = frame.locator('#customListMonthDiv').inner_html(timeout=10000)
    except Exception as e:
        print(f"[DEBUG] Extraction error: {e}")
        try:
            extracted_html = page.locator('#customListMonthDiv').inner_html(timeout=10000)
        except:
            extracted_html = "<p>Failed to load data.</p>"

    # ------------------------------------------------------------------
    # 6. [NEW] Python-side Calculation for Jandi
    # ------------------------------------------------------------------
    print("6. Calculating Blue Team's Today Schedule (Python Logic)...")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    # 요일 구하기 (0:월, 1:화, ... 5:토, 6:일)
    weekday_index = now.weekday()
    weekday_list = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_str = weekday_list[weekday_index]
    
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    today_blue_events = []
    today_yellow_events = []
    today_green_events = []
    
    try:
        # 1. Locate the table
        # Try finding the table handle in frame or page
        table_handle = None
        try:
            table_handle = frame.locator('#customListMonthDiv table')
            if table_handle.count() == 0: raise Exception("No table in frame")
        except:
            table_handle = page.locator('#customListMonthDiv table')
        
        if table_handle and table_handle.count() > 0:
            # 2. Get all row data (text, rowspan, colspan) using JS evaluation for speed
            # We fetch raw data structures, then process logic in Python
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
                # Ensure grid has enough rows
                while len(grid) <= r_idx:
                    grid.append([])
                
                c_idx = 0
                for cell in row:
                    # Skip filled cells
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                        c_idx += 1
                    
                    # Fill cell data based on rowspan/colspan
                    text = cell['text']
                    rowspan = cell['rowspan']
                    colspan = cell['colspan']
                    
                    for rr in range(rowspan):
                        target_row = r_idx + rr
                        while len(grid) <= target_row:
                            grid.append([])
                        
                        for cc in range(colspan):
                            target_col = c_idx + cc
                            # Expand grid columns if needed
                            while len(grid[target_row]) <= target_col:
                                grid[target_row].append(None)
                            
                            grid[target_row][target_col] = text
                    
                    c_idx += colspan

            # 4. Filter Logic (Python)
            blue_team = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"]
            yellow_team = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"]
            green_team = ["김준엽", "이학주", "현태화", "곽진수", "이창환"]
            
            print(f"[DEBUG] Processed {len(grid)} rows in Python.")
            
            for row in grid:
                if len(row) < 3: continue

                date_txt = row[0]
                # Assuming Name is last, Title is 3rd (index 2) or 2nd (index 1)
                name_txt = row[-1]
                title_txt = row[2] if len(row) > 2 else row[1]

                # Parse Date
                # Remove spaces
                clean_date = re.sub(r'\s+', '', date_txt)
                # Find all numbers
                nums = re.findall(r'\d+', clean_date)
                
                if len(nums) < 2: continue
                
                m = int(nums[0])
                d = int(nums[1])
                
                # Handle year if present (e.g., 2026.02.24)
                if len(nums) >= 3 and int(nums[0]) > 2000:
                    m = int(nums[1])
                    d = int(nums[2])

                # Check conditions
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
                    
                    # 🟢 그린팀 체크
                    if any(member in name_txt for member in green_team):
                        if title_txt and title_txt not in today_green_events:
                            today_green_events.append(title_txt)
                            print(f"[DEBUG] [Green] Found: {title_txt} ({name_txt})")

        else:
            print("[ERROR] Table not found for data extraction.")

    except Exception as e:
        print(f"[ERROR] Python calculation failed: {e}")

    print(f"[DEBUG] Final list for Jandi: {today_blue_events}")

    # ------------------------------------------------------------------
    # 7. Create index.html
    # ------------------------------------------------------------------
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🌠%3C/text%3E%3C/svg%3E">
        <link rel="stylesheet" href="https://etech-symantec.github.io/style.css" />
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Do+Hyeon&display=swap" rel="stylesheet">
        <meta charset="UTF-8">
        <title>공유 일정 대시보드</title>
        <style>
            body {{ font-family: 'Pretendard', sans-serif; padding: 15px; background-color: #f8f9fa; color: #333; font-size: 11px; }}
            .container {{
                background:#fff; border-radius:14px; box-shadow:0 6px 18px rgba(0,0,0,0.08);
                margin:30px; padding:4px 32px;
              }}
            /* 제목과 버튼을 감싸는 컨테이너 */
            .header-container {{ display: flex; align-items: center; justify-content: space-between; margin-top: 10px; margin-bottom: 15px; border-bottom: 2px solid #34495e; padding-bottom: 10px; }}
            h2 {{ color: #2c3e50; margin: 0; font-size: 18px; }}
            .header-left {{ display: flex; align-items: baseline; gap: 10px; }}

            .nav-top {{ display: flex; gap: 8px; }}
            .nav-link {{ text-decoration: none; padding: 6px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; color: white; transition: 0.2s; }}
            .nav-link:hover {{ opacity: 0.9; }}
            .link-shared {{ background-color: #6366f1; }} /* Indigo */
            .link-resource {{ background-color: #10b981; }} /* Emerald */
            
            .sync-time {{ color: #7f8c8d; font-size: 11px; font-weight: normal; }}
            .controls {{ display: flex; justify-content: flex-end; align-items: center; margin-bottom: 15px; }}
            /* 버튼 그룹 스타일 */
            .btn-group {{ display: flex; gap: 5px; }}
            .btn {{ border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: bold; transition: 0.2s; }}
            
            .btn-blue {{ background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
            .btn-blue.active, .btn-blue:hover {{ background-color: #0ea5e9; color: white; }}
            .btn-yellow {{ background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047; }}
            .btn-yellow.active, .btn-yellow:hover {{ background-color: #eab308; color: white; }}
            .btn-green {{ background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
            .btn-green.active, .btn-green:hover {{ background-color: #22c55e; color: white; }}
            
            .btn-all {{ background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }}
            .btn-all.active, .btn-all:hover {{ background-color: #6b7280; color: white; }}
            /* 선택된 팀의 오늘 일정 박스 스타일 */
            .summary-box {{ background: #fff; border-left: 4px solid #e11d48; padding: 12px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .summary-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px dashed #ffe4e6; padding-bottom: 8px; }}
            .summary-box h3 {{ margin: 0; color: #e11d48; font-size: 13px; }}
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
        <!-- 공통 헤더 + 제목 + 버전 -->
        <script>
            window.pageTitle = "📅 공유 일정 대시보드";
            window.pageVersion = "ver.2026.3.2.01";
        </script>
        <script src="https://etech-symantec.github.io/header.js"></script>
        <div class="container">
            <div class="header-container">
                <div class="header-left">
                    <span class="sync-time">Update: {kst_now_str}</span>
                </div>
                <div class="nav-top">
                    <a href="https://etech-symantec.github.io/calendar/" class="nav-link link-shared">📅 공유일정</a>
                    <a href="https://etech-symantec.github.io/calendar/resource.html" class="nav-link link-resource">🚀 자원일정</a>
                </div>
            </div>
            
            <div class="summary-box">
                <div class="summary-header">
                    <h3>🔥 선택된 팀의 오늘 일정</h3>
                    <div class="btn-group">
                        <button class="btn btn-blue active" onclick="applyFilter('blue')">🔵 블루팀</button>
                        <button class="btn btn-yellow" onclick="applyFilter('yellow')">🟡 옐로우팀</button>
                        <button class="btn btn-green" onclick="applyFilter('green')">🟢 그린팀</button>
                        <button class="btn btn-all" onclick="applyFilter('all')">📋 전체보기</button>
                    </div>
                </div>
                <ul id="today-list"><li>데이터 로딩 중...</li></ul>
            </div>
            <div class="table-container" id="wrapper">{extracted_html}</div>
        </div>
        <script>
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];
            const greenTeam = ["김준엽", "이학주", "현태화", "곽진수", "이창환"];
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
                    if(team === 'green') return greenTeam.some(m => name.includes(m));
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

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("✅ index.html created!")

    # ------------------------------------------------------------------
    # 8. Jandi Notification Transmission
    # ------------------------------------------------------------------
    if JANDI_URL:
        print("[DEBUG] Jandi URL exists, proceeding with logic check...")

        # 주말 체크 (5:토요일, 6:일요일)
        if weekday_index >= 5:
            print(f"📭 [JANDI] 오늘은 주말({weekday_str}요일)이라 알림을 보내지 않습니다.")
            
        # 둘 중 하나라도 일정이 있으면 전송
        elif today_blue_events or today_yellow_events:
            print(f"🚀 [JANDI] Sending Combined Schedule...")
            
            # 메시지 작성 시작
            body_text = f"📢 **{now.month}/{now.day} ({weekday_str}) 일정**\n\n"
            
            # 🟦 블루팀 섹션 (일정이 있는 경우에만)
            if today_blue_events:
                body_text += "🟦 **[블루팀]**\n"
                for item in today_blue_events:
                    body_text += f"- {item}\n"
                body_text += "\n" # 줄바꿈

            # 🟨 옐로우팀 섹션 (일정이 있는 경우에만)
            if today_yellow_events:
                body_text += "🟨 **[옐로우팀]**\n"
                for item in today_yellow_events:
                    body_text += f"- {item}\n"

            # Payload 구성
            payload = {
                "body": body_text,
                "connectColor": "#00A1E9", 
                "connectInfo": [] 
            }

            headers = { "Accept": "application/vnd.tosslab.jandi-v2+json", "Content-Type": "application/json" }
            
            try:
                res = requests.post(JANDI_URL, json=payload, headers=headers)
                print(f"[DEBUG] Jandi Response Code: {res.status_code}")
                if res.status_code == 200:
                    print("✅ 잔디 전송 성공!")
                else:
                    print(f"❌ 잔디 실패: {res.status_code} {res.text}")
            except Exception as e:
                print(f"❌ 잔디 에러: {e}")
        else:
            print("📭 [JANDI] 오늘은 블루팀 일정이 없습니다.")
    else:
        print("⚠️ JANDI_WEBHOOK_URL 미설정")

    print("[DEBUG] Closing browser...")
    browser.close()
    print("[DEBUG] Script finished.")

with sync_playwright() as playwright:
    run(playwright)
