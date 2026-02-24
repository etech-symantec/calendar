import os
import time
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

def run(playwright):
    print("==================================================")
    print("🚀 스크립트 실행 시작 (디버그 모드)")
    print("==================================================")

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. 환경변수 확인
    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")
    JANDI_URL = os.environ.get("JANDI_WEBHOOK_URL", "")

    print(f"[DEBUG] ID 길이: {len(USER_ID)}, PW 길이: {len(USER_PW)}")
    print(f"[DEBUG] JANDI_URL 설정: {'✅ 설정됨' if JANDI_URL else '❌ 미설정'}")

    print("\n1. 그룹웨어 접속 중...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    print("2. 메뉴 이동 중...")
    page.click('#topMenu300000000', timeout=20000)
    time.sleep(2)

    try:
        page.click('#301040000_all_anchor', timeout=20000)
    except:
        print("[DEBUG] 메뉴 클릭 재시도...")
        page.locator('text="공유일정 전체보기"').click(timeout=20000)
    time.sleep(2)

    frame = page.frame_locator('#_content')
    try:
        frame.locator('text="일정목록"').click(timeout=20000)
    except:
        page.locator('text="일정목록"').click(timeout=20000)

    print("✅ 데이터 로딩 대기 (5초)...")
    time.sleep(5)
    
    # ------------------------------------------------------------------
    # 5. HTML 및 원본 데이터 추출
    # ------------------------------------------------------------------
    print("\n[STEP 5] 데이터 추출 시작")
    
    extracted_html = ""
    try:
        extracted_html = frame.locator('#customListMonthDiv').inner_html(timeout=10000)
        print(f"[DEBUG] HTML 추출 성공 (길이: {len(extracted_html)})")
    except:
        try:
            extracted_html = page.locator('#customListMonthDiv').inner_html(timeout=10000)
            print(f"[DEBUG] HTML 추출 성공 (메인 페이지, 길이: {len(extracted_html)})")
        except:
            extracted_html = "<p>데이터 로딩 실패</p>"
            print("[ERROR] HTML 추출 실패")

    # ------------------------------------------------------------------
    # 6. [디버깅 강화] 파이썬에서 직접 데이터 필터링 및 검증
    # ------------------------------------------------------------------
    print("\n[STEP 6] 상세 데이터 분석 (로그 확인 필수!)")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    print(f"[기준 날짜] 오늘: {now.month}월 {now.day}일")

    # JS는 오직 '표를 텍스트 리스트로 변환'하는 역할만 합니다. (로직 분리)
    raw_data_extraction_js = """
    () => {
        const div = document.querySelector('#customListMonthDiv');
        if (!div) return null;
        const table = div.querySelector('table');
        if (!table) return null;

        const trs = Array.from(table.querySelectorAll('tr'));
        const grid = [];

        // 테이블 평탄화 (Flattening)
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
        return grid; // 전체 데이터를 파이썬으로 반환
    }
    """

    raw_grid = []
    try:
        raw_grid = frame.evaluate(raw_data_extraction_js)
    except:
        raw_grid = page.evaluate(raw_data_extraction_js)

    if not raw_grid:
        print("[ERROR] 테이블 데이터를 가져오지 못했습니다. (raw_grid is None)")
        raw_grid = []

    # 파이썬에서 한 줄씩 검사하며 로그 출력
    today_blue_events = []
    blue_team = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"]

    print(f"[DEBUG] 총 {len(raw_grid)}개의 행을 검사합니다.")

    for i, row in enumerate(raw_grid):
        # 데이터가 너무 적은 행(헤더 등)은 패스
        if len(row) < 3:
            continue

        # 데이터 매핑 (인덱스 확인용)
        # 보통: [0:날짜, 1:시간, 2:일정명, 3:등록자]
        date_txt = row[0]
        # 일정명과 등록자 위치가 가변적일 수 있으므로 뒤에서부터 찾음
        name_txt = row[-1] 
        title_txt = row[2] if len(row) > 2 else row[1]

        # 1. 날짜 파싱 확인
        nums = "".join(filter(str.isdigit, date_txt)) # 숫자만 추출
        
        # 숫자 파싱 로직 디버깅
        parsed_month = -1
        parsed_day = -1
        
        # 20260224 형태 or 0224 형태
        if len(nums) >= 4 and int(nums[:4]) > 2000: # 연도 포함 (2026...)
             # 예: 20260224 -> index 4,5는 월, 6,7은 일 (단, 월/일이 한자리일 수도 있음)
             # 간단히 정규식 대신 배열 로직 사용 (기존 로직 유지하되 파이썬화)
             import re
             num_list = re.findall(r'\d+', date_txt)
             if len(num_list) >= 3:
                 parsed_month = int(num_list[1])
                 parsed_day = int(num_list[2])
        else:
             # 예: 2.24 -> ['2', '24']
             import re
             num_list = re.findall(r'\d+', date_txt)
             if len(num_list) >= 2:
                 parsed_month = int(num_list[0])
                 parsed_day = int(num_list[1])

        is_today = (parsed_month == now.month and parsed_day == now.day)
        
        # 2. 팀원 확인
        is_blue_member = any(member in name_txt for member in blue_team)

        # 3. 상세 로그 출력 (중요!)
        # 너무 많으면 오늘 날짜 근처만 출력하거나, 블루팀만 출력
        if is_today or is_blue_member:
            print(f"👉 [검사 중: Row {i}]")
            print(f"   - 원본 날짜: '{date_txt}' -> 인식된 날짜: {parsed_month}월 {parsed_day}일 (오늘인가? {is_today})")
            print(f"   - 작성자: '{name_txt}' (블루팀인가? {is_blue_member})")
            print(f"   - 일정명: '{title_txt}'")
            
            if is_today and is_blue_member:
                if title_txt and title_txt not in today_blue_events:
                    today_blue_events.append(title_txt)
                    print("   🎉 [채택] 전송 리스트에 추가됨!")
                else:
                    print("   ⚠️ [중복] 이미 리스트에 있음")
            else:
                print("   ❌ [제외] 조건 불일치")
    
    print(f"\n[최종 결과] 전송할 일정 리스트 ({len(today_blue_events)}건): {today_blue_events}")

    # ------------------------------------------------------------------
    # 7. index.html 생성
    # ------------------------------------------------------------------
    # 기존 HTML 생성 코드 유지
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
        <p class="sync-time">Update: {kst_now.strftime('%Y-%m-%d %H:%M:%S')}</p>
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
    print("✅ index.html 생성 완료!")

    # ------------------------------------------------------------------
    # 8. 잔디 알림 전송
    # ------------------------------------------------------------------
    if JANDI_URL:
        if today_blue_events:
            print(f"🚀 [JANDI] 블루팀 일정 {len(today_blue_events)}건 전송 시작")
            msg = f"🔥 **[블루팀] 오늘({now.month}/{now.day})의 일정입니다.**\n"
            for item in today_blue_events:
                msg += f"- {item}\n"
            
            payload = {
                "body": f"오늘의 블루팀 일정 ({now.month}/{now.day})",
                "connectColor": "#00A1E9",
                "connectInfo": [{ "title": "일정 목록", "description": msg }]
            }
            # Payload 디버깅 로그
            print(f"[DEBUG] 전송 Payload: {payload}")

            headers = { "Accept": "application/vnd.tosslab.jandi-v2+json", "Content-Type": "application/json" }
            
            try:
                res = requests.post(JANDI_URL, json=payload, headers=headers)
                print(f"[DEBUG] 잔디 응답 코드: {res.status_code}")
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

    print("🏁 스크립트 종료. 브라우저 닫는 중...")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
