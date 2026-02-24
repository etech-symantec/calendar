import os
import time
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 환경변수 로드
    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")
    # Secrets에 넣었다면 아래 코드로 충분합니다. 
    # 만약 Variables 탭에 두셨다면 os.environ.get("JANDI_WEBHOOK_URL")로 가져옵니다.
    JANDI_URL = os.environ.get("JANDI_WEBHOOK_URL", "")

    print("1. 로그인 및 일정 페이지 접속 중...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    page.click('#topMenu300000000') 
    time.sleep(2)

    try:
        page.click('#301040000_all_anchor', timeout=5000)
    except:
        page.locator('text="공유일정 전체보기"').click(timeout=5000)
    time.sleep(2)

    frame = page.frame_locator('#_content')
    try:
        frame.locator('text="일정목록"').click(timeout=5000)
    except:
        page.locator('text="일정목록"').click(timeout=5000)

    print("2. 데이터 로딩 대기 중...")
    time.sleep(5)
    
    # ------------------------------------------------------------------
    # 🌟 핵심: 대시보드 요약 로직을 브라우저에서 실행하고 결과(리스트)를 바로 가져옴
    # ------------------------------------------------------------------
    print("3. 블루팀 오늘 일정 추출 중 (요약 박스 데이터 추출)...")
    
    combined_js_logic = """
    (dateInfo) => {
        const div = document.querySelector('#customListMonthDiv');
        if (!div) return { html: "", todayBlueEvents: [] };
        const table = div.querySelector('table');
        if (!table) return { html: div.innerHTML, todayBlueEvents: [] };

        const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
        const trs = Array.from(table.rows);
        const grid = [];

        // 1. 모든 행 평탄화 (rowspan 해제)
        trs.forEach((tr, r) => {
            if (!grid[r]) grid[r] = [];
            let c = 0;
            Array.from(tr.cells).forEach(cell => {
                while (grid[r][c]) c++;
                const rowspan = cell.rowSpan || 1;
                const colspan = cell.colSpan || 1;
                const innerHTML = cell.innerHTML;
                const text = cell.innerText.trim();
                const tagName = cell.tagName;
                for (let rr = 0; rr < rowspan; rr++) {
                    for (let cc = 0; cc < colspan; cc++) {
                        if (!grid[r + rr]) grid[r + rr] = [];
                        grid[r + rr][c + cc] = { tagName, innerHTML, text };
                    }
                }
            });
        });

        // 2. 오늘 날짜 및 블루팀 필터링 (잔디 전송용)
        const tM = dateInfo.month;
        const tD = dateInfo.day;
        const todayBlueEvents = [];

        grid.forEach(row => {
            if (row.length < 3) return;
            
            // 날짜 확인 (첫 번째 칸)
            const dateText = row[0].text.replace(/\\s+/g, '');
            const nums = dateText.match(/\\d+/g);
            if (!nums || nums.length < 2) return;
            
            let m = parseInt(nums[0], 10);
            let d = parseInt(nums[1], 10);
            if(nums.length >= 3 && parseInt(nums[0]) > 2000) { m = parseInt(nums[1], 10); d = parseInt(nums[2], 10); }

            if (m === tM && d === tD) {
                // 이름 확인 (마지막 칸)
                const name = row[row.length - 1].text;
                if (blueTeam.some(mem => name.includes(mem))) {
                    // 일정명 (중간 칸 - 제목 열)
                    // 보통 0:날짜, 1:시간, 2:일정명, 3:등록자 순서임
                    const title = row[2] ? row[2].text : row[1].text;
                    if (title && !todayBlueEvents.includes(title)) {
                        todayBlueEvents.push(title);
                    }
                }
            }
        });

        return {
            rawHtml: div.innerHTML,
            todayBlueEvents: todayBlueEvents
        };
    }
    """

    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    result = {"rawHtml": "", "todayBlueEvents": []}
    try:
        result = frame.evaluate(combined_js_logic, {"month": now.month, "day": now.day})
    except:
        result = page.evaluate(combined_js_logic, {"month": now.month, "day": now.day})

    extracted_html = result['rawHtml']
    blue_events = result['todayBlueEvents']
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    # ------------------------------------------------------------------
    # 4. index.html 생성 (기존 대시보드 코드 유지)
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
                        const li = document.createElement('li'); li.innerText = r.cells[2].innerText.trim();
                        list.appendChild(li); todayCount++;
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
    print("✅ index.html 생성 완료!")

    # ------------------------------------------------------------------
    # 5. 잔디 알림 전송 (JS에서 반환받은 blue_events 리스트 사용)
    # ------------------------------------------------------------------
    if JANDI_URL:
        if blue_events:
            print(f"🚀 블루팀 일정 {len(blue_events)}건 발견! 잔디 전송 중...")
            msg = f"🔥 **[블루팀] 오늘({now.month}/{now.day})의 일정입니다.**\n"
            for item in blue_events:
                msg += f"- {item}\n"
            
            payload = {{
                "body": f"오늘의 블루팀 일정 ({now.month}/{now.day})",
                "connectColor": "#00A1E9",
                "connectInfo": [{{ "title": "일정 목록", "description": msg }}]
            }}
            headers = {{ "Accept": "application/vnd.tosslab.jandi-v2+json", "Content-Type": "application/json" }}
            
            try:
                res = requests.post(JANDI_URL, json=payload, headers=headers)
                if res.status_code == 200: print("✅ 잔디 전송 성공!")
                else: print(f"❌ 잔디 실패: {res.status_code} {res.text}")
            except Exception as e: print(f"❌ 잔디 에러: {e}")
        else:
            print("📭 오늘은 블루팀 일정이 없습니다. (알림 생략)")
    else:
        print("⚠️ JANDI_WEBHOOK_URL이 설정되지 않았습니다.")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
