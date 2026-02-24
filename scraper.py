import os
import time
import requests
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

    # [LOG] Check sensitive variables (masked)
    print(f"[DEBUG] USER_ID: {'***' + USER_ID[-2:] if len(USER_ID) > 2 else '***'} (Length: {len(USER_ID)})")
    print(f"[DEBUG] USER_PW: {'***' + USER_PW[-1:] if len(USER_PW) > 1 else '***'} (Length: {len(USER_PW)})")
    print(f"[DEBUG] JANDI_URL: {'Set' if JANDI_URL else 'Not Set'}")

    print("1. Accessing login page and schedule page...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3) # Slightly increased loading time

    print("2. Clicking top 'Schedule' menu...")
    page.click('#topMenu300000000', timeout=20000) # Timeout increased to 20s
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. Clicking left 'View All Shared Schedules' menu...")
    try:
        # Wait 20 seconds
        page.click('#301040000_all_anchor', timeout=20000)
    except:
        print("[DEBUG] Selector click failed, retrying with text locator...")
        page.locator('text="공유일정 전체보기"').click(timeout=20000)
    time.sleep(3)

    print("4. Clicking 'Schedule List' tab in right content...")
    frame = page.frame_locator('#_content')
    try:
        # Previously errored part: changed 5000 -> 20000 (20s) to wait sufficiently
        frame.locator('text="일정목록"').click(timeout=20000)
    except:
        print("[DEBUG] Frame locator failed, retrying on main page...")
        page.locator('text="일정목록"').click(timeout=20000)

    print("✅ Page entry successful! Waiting for data loading...")
    time.sleep(5)
    
    # ------------------------------------------------------------------
    # 5. [Existing Logic] Extract HTML for Dashboard
    # ------------------------------------------------------------------
    print("5. Extracting Dashboard HTML...")
    extracted_html = ""
    try:
        extracted_html = frame.locator('#customListMonthDiv').inner_html(timeout=10000)
    except Exception as e:
        print(f"[DEBUG] Frame extraction error: {e}")
        try:
            extracted_html = page.locator('#customListMonthDiv').inner_html(timeout=10000)
        except Exception as e2:
            print(f"[DEBUG] Page extraction error: {e2}")
            extracted_html = "<p>Failed to load data.</p>"
    
    # [LOG] Check extracted HTML length
    print(f"[DEBUG] Length of extracted_html: {len(extracted_html)} chars")

    # ------------------------------------------------------------------
    # 6. [NEW] Extract Blue Team's Today Schedule separately (for Jandi)
    # ------------------------------------------------------------------
    print("6. Analyzing today's schedule for Jandi transmission...")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # [LOG] Check Time
    print(f"[DEBUG] Current KST Time: {kst_now_str}")
    print(f"[DEBUG] Target Date: Month={now.month}, Day={now.day}")

    jandi_extraction_js = """
    (dateInfo) => {
        const div = document.querySelector('#customListMonthDiv');
        // rawHtml is used as a key for error handling in Python
        if (!div) return { rawHtml: "", todayBlueEvents: [] };
        
        const table = div.querySelector('table');
        if (!table) return { rawHtml: div.innerHTML, todayBlueEvents: [] };

        const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
        const trs = Array.from(table.querySelectorAll('tr'));
        const grid = [];

        // 1. Table Flattening
        trs.forEach((tr, r) => {
            if (!grid[r]) grid[r] = [];
            let c = 0;
            Array.from(tr.children).forEach(cell => {
                while (grid[r][c]) c++;
                const rowspan = parseInt(cell.getAttribute('rowspan') || 1, 10);
                const colspan = parseInt(cell.getAttribute('colspan') || 1, 10);
                const text = cell.innerText.trim();
                for (let rr = 0; rr < rowspan; rr++) {
                    for (let cc = 0; cc < colspan; cc++) {
                        if (!grid[r + rr]) grid[r + rr] = [];
                        grid[r + rr][c + cc] = text;
                    }
                }
            });
        });

        // 2. Filter Today & Blue Team
        const targetM = dateInfo.month;
        const targetD = dateInfo.day;
        const events = [];

        grid.forEach(row => {
            if (!row || row.length < 3) return;

            const dateTxt = row[0];
            const nameTxt = row[row.length - 1];
            // Event name: usually at index 2, check safely (if missing, check index 1)
            const titleTxt = row[2] || row[1];

            const nums = dateTxt.replace(/\\s+/g, '').match(/\\d+/g);
            if (!nums || nums.length < 2) return;

            let m = parseInt(nums[0]);
            let d = parseInt(nums[1]);
            if (nums.length >= 3 && parseInt(nums[0]) > 2000) {
                m = parseInt(nums[1]);
                d = parseInt(nums[2]);
            }

            if (m === targetM && d === targetD) {
                if (blueTeam.some(member => nameTxt.includes(member))) {
                    if (!events.includes(titleTxt)) {
                        events.push(titleTxt);
                    }
                }
            }
        });

        return {
            rawHtml: div.innerHTML,
            todayBlueEvents: events
        };
    }
    """

    # result = {"rawHtml": "", "todayBlueEvents": []}
    extraction_result_obj = {} # Renamed for clarity in logging
    try:
        print("[DEBUG] Executing JS in frame...")
        extraction_result_obj = frame.evaluate(jandi_extraction_js, {"month": now.month, "day": now.day})
    except:
        try:
            print("[DEBUG] Executing JS in page...")
            extraction_result_obj = page.evaluate(jandi_extraction_js, {"month": now.month, "day": now.day})
        except Exception as e:
            print(f"⚠️ Data analysis failed: {e}")
            extraction_result_obj = {}

    # Extract list using key 'todayBlueEvents'
    today_blue_events = extraction_result_obj.get('todayBlueEvents', [])
    
    # [LOG] Extracted Events
    print(f"[DEBUG] today_blue_events content: {today_blue_events}")
    print(f"[DEBUG] Count of events found: {len(today_blue_events)}")

    # ------------------------------------------------------------------
    # 7. Create index.html (Dashboard)
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

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"[DEBUG] list content: {list}")
    print(f"[DEBUG] today-list content: {today-list}"
    print("✅ index.html 생성 완료!")

    # ------------------------------------------------------------------
    # 8. Jandi Notification Transmission
    # ------------------------------------------------------------------
    if JANDI_URL:
        print("[DEBUG] Jandi URL exists, proceeding with logic check...")
        if today_blue_events:
            print(f"🚀 [JANDI] Sending {len(today_blue_events)} Blue Team events...")
            msg = f"🔥 **[블루팀] 오늘({now.month}/{now.day})의 일정입니다.**\n"
            for item in today_blue_events:
                msg += f"- {item}\n"
            
            payload = {
                "body": f"오늘의 블루팀 일정 ({now.month}/{now.day})",
                "connectColor": "#00A1E9",
                "connectInfo": [{ "title": "일정 목록", "description": msg }]
            }
            # [LOG] Payload content
            print(f"[DEBUG] Payload to send: {payload}")

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
