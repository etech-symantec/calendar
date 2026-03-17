import os
import time
import requests
import re
import json
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

def run(playwright):
    # 🌟 [추가됨] 실행 시간 제한 로직 (KST 기준 07시 ~ 17시)
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    current_hour = now.hour

    # 7시 이전이거나 17시(오후 5시) 이후이면 종료 (17:59까지 작동하게 하려면 < 18로 수정)
    if not (7 <= current_hour < 17):
        print(f"[{now.strftime('%H:%M:%S')}] 현재 시간은 스크립트 작동 범위(07시~17시)가 아닙니다. 실행을 중단합니다.")
        return

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

    # 🌟 1. [추가됨] 브라우저 기본 경고창(Alert/Confirm)이 뜨면 무조건 '확인' 처리
    page.on("dialog", lambda dialog: dialog.accept())

    # 🌟 2. [추가됨] 사내 공지사항 등 HTML 레이어 팝업 닫기 시도
    print("[DEBUG] 팝업 창 유무를 확인하고 닫기를 시도합니다...")
    try:
        # ESC 키를 눌러서 닫히는 팝업 처리
        page.keyboard.press("Escape")
        time.sleep(1)
        
        # 흔히 쓰이는 닫기 버튼 텍스트를 찾아 클릭 (없으면 바로 넘어감)
        close_texts = ["닫기", "오늘 하루 보지 않기", "오늘 하루 이 창을 열지 않음", "확인", "취소", "Close", "X"]
        for txt in close_texts:
            close_btn = page.locator(f'text="{txt}"')
            if close_btn.count() > 0:
                close_btn.first.click(timeout=2000, force=True)
                print(f"[DEBUG] '{txt}' 버튼을 클릭하여 팝업을 닫았습니다.")
                time.sleep(1)
    except Exception as e:
        print("[DEBUG] 팝업 닫기 중 예외 발생 (무시하고 진행):", e)

    # ------------------------------------------------------------------
    # 2. 상단 '일정' 메뉴 클릭
    # ------------------------------------------------------------------
    print("2. Clicking top '일정' (Schedule) menu...")
    try:
        page.click('#topMenu300000000', timeout=10000)
    except Exception as e:
        print(f"[DEBUG] ID click failed, trying text: {e}")
        try:
            page.locator('text="일정"').first.click(timeout=15000, force=True)
        except Exception as e2:
            # 🌟 5. 최종 실패 시 에러 화면 캡처
            page.screenshot(path="debug_error.png", full_page=True)
            print("📸 [ERROR] 메뉴 클릭 실패! 에러 화면이 debug_error.png로 캡처되었습니다.")
            raise e2
    
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
    # 5. Extract HTML for Dashboard
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

    # 이미지 태그 삭제
    if extracted_html:
        extracted_html = extracted_html.replace('<img src="/schedule/resources/Images/ico/resources_ico.png">', '')

    print(f"[DEBUG] Extracted HTML length: {len(extracted_html)}")

    # ------------------------------------------------------------------
    # 6. Python-side Calculation
    # ------------------------------------------------------------------
    print("6. Calculating Today's Schedule for Teams...")
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    weekday_index = now.weekday()
    weekday_list = ["월", "화", "수", "목", "금", "토", "일"]
    weekday_str = weekday_list[weekday_index]
    
    kst_now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG] Target Date: {now.month}/{now.day} ({weekday_str})")

    today_blue_events = []
    today_yellow_events = []
    today_green_events = []
    today_red_events = []
    final_grid_data = [] 
    
    try:
        table_handle = None
        try:
            table_handle = frame.locator('#customListMonthDiv table')
            if table_handle.count() == 0: raise Exception("No table in frame")
        except:
            table_handle = page.locator('#customListMonthDiv table')
        
        if table_handle and table_handle.count() > 0:
            rows_data = table_handle.first.evaluate("""(table) => {
                const rows = Array.from(table.rows);
                return rows.map(tr => {
                    return Array.from(tr.children).map(cell => ({
                        text: cell.innerText.trim(),
                        html: cell.innerHTML, 
                        tagName: cell.tagName,
                        className: cell.className,
                        style: cell.getAttribute('style') || '',
                        rowspan: parseInt(cell.getAttribute('rowspan') || 1, 10),
                        colspan: parseInt(cell.getAttribute('colspan') || 1, 10)
                    }));
                });
            }""")

            grid = []
            for r_idx, row in enumerate(rows_data):
                while len(grid) <= r_idx:
                    grid.append([])
                
                c_idx = 0
                for cell in row:
                    while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                        c_idx += 1
                    
                    cell_html = cell['html'].replace('<img src="/schedule/resources/Images/ico/resources_ico.png">', '')

                    cell_obj = {
                        'text': cell['text'],
                        'html': cell_html, 
                        'tag': cell['tagName'],
                        'cls': cell['className'],
                        'style': cell['style']
                    }
                    
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
                            grid[target_row][target_col] = cell_obj
                    c_idx += colspan
            
            final_grid_data = grid

            # Filter Logic
            blue_team = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"]
            yellow_team = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"]
            green_team = ["김준엽", "이학주", "현태화", "곽진수", "이창환"]
            red_team = ["이병서", "이승훈1", "한혜민", "선혜선", "이다경", "김기태", "조성훈", "최정인", "김민혁", "최성복"]
            
            print(f"[DEBUG] Processed {len(grid)} rows in Python.")
            
            for row in grid:
                if len(row) < 3: continue

                date_txt = row[0]['text']
                name_txt = row[-1]['text']
                title_txt = row[2]['text'] if len(row) > 2 else row[1]['text']

                clean_date = re.sub(r'\s+', '', date_txt)
                nums = re.findall(r'\d+', clean_date)
                
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
                    
                    if any(member in name_txt for member in yellow_team):
                        if title_txt and title_txt not in today_yellow_events:
                            today_yellow_events.append(title_txt)

                    if any(member in name_txt for member in green_team):
                        if title_txt and title_txt not in today_green_events:
                            today_green_events.append(title_txt)
                            
                    if any(member in name_txt for member in red_team):
                        if title_txt and title_txt not in today_red_events:
                            today_red_events.append(title_txt)


        else:
            print("[ERROR] Table not found for data extraction.")

    except Exception as e:
        print(f"[ERROR] Python calculation failed: {e}")

    print(f"[DEBUG] Blue: {len(today_blue_events)}, Yellow: {len(today_yellow_events)}, Green: {len(today_green_events)}, Red: {len(today_red_events)}")

    # ------------------------------------------------------------------
    # 7. Create resource.html
    # ------------------------------------------------------------------
    json_grid_data = json.dumps(final_grid_data, ensure_ascii=False)

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
        <title>자원일정 대시보드</title>
        <style>
            body {{ font-family: 'Pretendard', sans-serif; padding: 15px; background-color: #f8f9fa; color: #333; font-size: 11px; }}
            .container {{
                background:#fff; border-radius:14px; box-shadow:0 6px 18px rgba(0,0,0,0.08);
                margin:30px; padding:4px 32px;
              }}
            .header-container {{ display: flex; align-items: center; justify-content: space-between; margin-top: 10px; margin-bottom: 15px; border-bottom: 2px solid #34495e; padding-bottom: 10px; }}
            h2 {{ color: #2c3e50; margin: 0; font-size: 18px; }}
            .header-left {{ display: flex; align-items: baseline; gap: 10px; }}
            
            .nav-top {{ display: flex; gap: 8px; }}
            .nav-link {{ text-decoration: none; padding: 6px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; color: white; transition: 0.2s; }}
            .nav-link:hover {{ opacity: 0.9; }}
            .link-shared {{ background-color: #6366f1; }} 
            .link-resource {{ background-color: #10b981; }} 

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

            .btn-red {{ background-color: #FBEFEF; color: #c53030; border: 1px solid #fca5a5; }}
            .btn-red.active, .btn-red:hover {{ background-color: #ef4444; color: white; }}

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

            /* 🌟 [수정됨] 타임라인 헤더 (날짜 이동 버튼) 스타일 */
            .timeline-header {{ display: flex; justify-content: flex-start; align-items: center; gap: 15px; margin-bottom: 5px; }}
            .date-nav-btn {{ background: #fff; border: 1px solid #d1d5db; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px; color: #4b5563; transition: 0.2s; }}
            .date-nav-btn:hover {{ background: #f3f4f6; color: #1f2937; }}
            .date-nav-btn.today-btn {{ background-color: #f8f9fa; border-color: #9ca3af; color: #374151; }}
            .date-nav-btn.today-btn:hover {{ background-color: #e5e7eb; }}
            .timeline-date-display {{ font-size: 14px; font-weight: bold; color: #1f2937; margin: 0; }}

            /* 타임라인 스타일 */
            #timeline-container {{ background: #fff; padding: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; overflow-x: auto; }}
            #timeline-chart {{ position: relative; height: 200px; border-top: 1px solid #e5e7eb; margin-top: 30px; min-width: 600px; }}
            .timeline-hour-marker {{ position: absolute; top: -25px; font-size: 10px; color: #6b7280; transform: translateX(-50%); }}
            
            /* 타임라인 그리드 선 */
            .timeline-grid-line {{ position: absolute; top: 0; bottom: 0; width: 1px; background-color: #f3f4f6; }}
            .timeline-grid-line.half-hour {{ border-left: 1px dashed #e5e7eb; background-color: transparent; width: 0; }} /* 30분 점선 */
            .timeline-now-line {{ position: absolute; top: 0; bottom: 0; width: 0; border-left: 2px dashed rgba(239, 68, 68, 0.5); z-index: 20; pointer-events: none; }}
            .timeline-now-label {{ position: absolute; top: -20px; font-size: 10px; font-weight: bold; color: white; background-color: rgba(239, 68, 68, 0.8); padding: 2px 4px; border-radius: 3px; transform: translateX(-50%); z-index: 21; }}

            /* 기본 막대 (회색) */
            .timeline-event-bar {{ position: absolute; height: 24px; background-color: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; padding: 4px 6px; font-size: 10px; color: #4b5563; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; box-shadow: 0 1px 2px rgba(0,0,0,0.05); cursor: pointer; }}
            .timeline-event-bar:hover {{ z-index: 10; overflow: visible; white-space: normal; height: auto; }}
            /* 🌟 [추가됨] 차량 (진한 회색) */
            .timeline-event-bar.vehicle {{ background-color: #6c7787; border: 1px solid #374151; color: #ffffff; }}
            
            /* 🌟 [추가됨] 시에스타/테라피 (점선 테두리) */
            .timeline-event-bar.rest {{ border-style: dashed !important; border-width: 1px !important; background-color: #d8e8e8; color: #334155; }}
            
            /* 팀별 색상 */
            .timeline-event-bar.blue {{ 
                background-color: #e0f2fe !important; 
                border-color: #bae6fd !important; 
                color: #0369a1 !important; 
                font-size: 12px !important; 
                font-weight: bold !important; 
            }}
            .timeline-event-bar.blue:hover {{ background-color: #f0f9ff !important; }}
            
            .timeline-event-bar.yellow {{ 
                background-color: #fef9c3 !important; 
                border-color: #fde047 !important; 
                color: #854d0e !important; 
                font-size: 12px !important; 
                font-weight: bold !important; 
            }}
            .timeline-event-bar.yellow:hover {{ background-color: #fefce8 !important; }}
            
            .timeline-event-bar.green {{ 
                background-color: #dcfce7 !important; 
                border-color: #bbf7d0 !important; 
                color: #166534 !important; 
                font-size: 12px !important; 
                font-weight: bold !important; 
            }}
            .timeline-event-bar.green:hover {{ background-color: #f0fdf4 !important; }}
            
            .timeline-event-bar.red {{ 
                background-color: #FBEFEF !important; 
                border-color: #fca5a5 !important; 
                color: #c53030 !important; 
                font-size: 12px !important; 
                font-weight: bold !important; 
            }}
            .timeline-event-bar.red:hover {{ background-color: #fee2e2 !important; }}
            
            /* 🌟 [추가됨] 미니맵 툴팁 스타일 (회의실 이미지 기반 순수 CSS 구현) */
            .minimap-tooltip {{ position: fixed; background: #f8f9fa; border: 2px solid #cbd5e1; box-shadow: 0 10px 25px rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; z-index: 99999; display: none; pointer-events: none; }}
            .minimap-title {{ font-size: 12px; font-weight: bold; color: #334155; margin-bottom: 8px; text-align: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }}
            .minimap-grid {{ display: grid; grid-template-columns: 60px 60px 20px 60px 60px; grid-template-rows: repeat(4, auto); gap: 6px; }}
            .minimap-grid .room {{ border: 1.5px solid #475569; text-align: center; font-size: 10px; padding: 6px 2px; border-radius: 3px; background: #fff; color: #1e293b; display: flex; flex-direction: column; justify-content: center; line-height: 1.2; transition: all 0.15s ease-in-out; }}
            .minimap-grid .room.empty {{ border: none; background: transparent; }}
            .minimap-grid .room.highlight {{ background: #3b82f6; color: #fff; font-weight: bold; border-color: #2563eb; box-shadow: 0 0 8px rgba(59, 130, 246, 0.6); transform: scale(1.08); z-index: 10; }}
        </style>
    </head>
    <body>
        <!-- 공통 헤더 + 제목 + 버전 -->
        <script>
            window.pageTitle = "📅 자원 일정 대시보드";
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
    
            <div id="timeline-container">
               <div class="timeline-header">
                    <button class="date-nav-btn" onclick="changeTimelineDate(-1)">◀ 어제</button>
                    <button class="date-nav-btn today-btn" onclick="resetToToday()">오늘</button>
                    <button class="date-nav-btn" onclick="changeTimelineDate(1)">내일 ▶</button>
                    <h3 id="timeline-date-display" class="timeline-date-display">📅 타임라인 로딩 중...</h3>
                </div>
                <div id="timeline-chart"></div>
            </div>
    
            <div class="summary-box">
                <div class="summary-header">
                    <h3>🔥 선택된 팀의 오늘 일정</h3>
                    <div class="btn-group">
                        <button class="btn btn-blue active" onclick="applyFilter('blue')">🔵 블루팀</button>
                        <button class="btn btn-yellow" onclick="applyFilter('yellow')">🟡 옐로우팀</button>
                        <button class="btn btn-green" onclick="applyFilter('green')">🟢 그린팀</button>
                        <button class="btn btn-red" onclick="applyFilter('red')">🔴 영업팀</button>
                        <button class="btn btn-all" onclick="applyFilter('all')">📋 전체보기</button>
                    </div>
                </div>
                <ul id="today-list"><li>데이터 로딩 중...</li></ul>
            </div>
            
            <div class="table-container" id="wrapper">
                <table></table>
            </div>
        </div>

        <div id="minimap-tooltip" class="minimap-tooltip">
            <div class="minimap-title">📍 회의실 위치</div>
            <div class="minimap-grid">
                <div class="room" id="room-1703">1703<br>에끌레어</div>
                <div class="room" id="room-1706">1706<br>바클라바</div>
                <div class="room empty"></div>
                <div class="room" id="room-1804">1804<br>휘낭시에</div>
                <div class="room" id="room-1807">1807<br>퀸아망</div>
                
                <div class="room" id="room-1702">1702<br>도넛</div>
                <div class="room" id="room-1705">1705<br>파르페</div>
                <div class="room empty"></div>
                <div class="room" id="room-1803">1803<br>까눌레</div>
                <div class="room" id="room-1806">1806<br>다쿠아즈</div>
                
                <div class="room" id="room-1701">1701<br>마카롱</div>
                <div class="room" id="room-1704">1704<br>푸딩</div>
                <div class="room empty"></div>
                <div class="room" id="room-1802">1802<br>스콘</div>
                <div class="room" id="room-1805">1805<br>와플</div>
                
                <div class="room empty"></div>
                <div class="room empty"></div>
                <div class="room empty"></div>
                <div class="room" id="room-1801">1801<br>마들렌</div>
                <div class="room empty"></div>
            </div>
        </div>

        <script>
            const gridData = {json_grid_data}; 
            
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];
            const greenTeam = ["김준엽", "이학주", "현태화", "곽진수", "이창환"];
            const redTeam = ["이병서", "이승훈1", "한혜민", "선혜선", "이다경", "김기태", "조성훈", "최정인", "김민혁", "최성복"];

            // 🌟 [추가됨] 현재 타임라인이 보여주는 날짜 변수
            let currentTimelineDate = new Date();

            document.addEventListener("DOMContentLoaded", function() {{
                renderTable();
                applyFilter('blue');
                renderTimeline(); 
            }});

            function renderTable() {{
                const table = document.querySelector('#wrapper table');
                if (!gridData || gridData.length === 0) {{
                    table.innerHTML = "<tr><td>데이터가 없습니다.</td></tr>";
                    return;
                }}

                let html = '<tbody>';
                gridData.forEach((row, rowIndex) => {{
                    let rowClass = (rowIndex === 0) ? 'header-row' : '';
                    html += `<tr class="${{rowClass}}">`;
                    row.forEach(cell => {{
                        if(cell) {{
                            let style = cell.style;
                            if(rowIndex === 0) style += "; background-color: #e5e7eb; font-weight: bold;";
                            html += `<${{cell.tag}} class="${{cell.cls}}" style="${{style}}">${{cell.html}}</${{cell.tag}}>`;
                        }} else {{
                            html += '<td></td>';
                        }}
                    }});
                    html += '</tr>';
                }});
                html += '</tbody>';
                table.innerHTML = html;
            }}

            function applyFilter(team) {{
                document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
                document.querySelector(`.btn-${{team}}`).classList.add('active');
                
                const rows = Array.from(document.querySelectorAll('#wrapper tbody tr'));
                
                let visibleRows = [];

                rows.forEach((r, idx) => {{
                    if(idx === 0) {{ 
                        r.classList.remove('hidden-row');
                        return;
                    }}

                    const cells = r.querySelectorAll('td, th');
                    if(cells.length === 0) return;
                    const name = cells[cells.length-1].innerText.trim();
                    
                    let isVisible = false;
                    if(team === 'all') isVisible = true;
                    if(team === 'blue' && blueTeam.some(m => name.includes(m))) isVisible = true;
                    if(team === 'yellow' && yellowTeam.some(m => name.includes(m))) isVisible = true;
                    if(team === 'green' && greenTeam.some(m => name.includes(m))) isVisible = true;
                    if(team === 'red' && redTeam.some(m => name.includes(m))) isVisible = true;

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
                    if(r.classList.contains('header-row') || r.rowIndex === 0) return;

                    const cells = r.querySelectorAll('td, th');
                    if(cells.length < 2) return;

                    const dateText = cells[0].innerText;
                    const nums = dateText.match(/\\d+/g);
                    
                    if(nums && nums.length >= 2) {{
                        let m = parseInt(nums[0]);
                        let d = parseInt(nums[1]);
                        if(nums.length >= 3 && parseInt(nums[0]) > 2000) {{ m = parseInt(nums[1]); d = parseInt(nums[2]); }}
                        isTodayGroup = (m === tM && d === tD);
                    }}

                    if(isTodayGroup) {{
                        r.style.backgroundColor = '#fff1f2'; 
                        const time = cells[1] ? cells[1].innerText.trim() : "";
                        const resource = cells[2] ? cells[2].innerText.trim() : "";
                        const li = document.createElement('li');
                        
                        // 💡 요청된 포맷: [시간] [자원명]
                        li.innerText = `[${{time}}] ${{resource}}`;
                        list.appendChild(li);
                        count++;
                    }} else {{
                        r.style.backgroundColor = ''; 
                    }}
                }});

                if(count === 0) list.innerHTML = '<li>선택된 팀의 오늘 일정이 없습니다. 🎉</li>';
            }}

            // 🌟 [추가됨] 버튼 클릭 시 날짜 변경 함수
            function changeTimelineDate(offset) {{
                currentTimelineDate.setDate(currentTimelineDate.getDate() + offset);
                renderTimeline();
            }}
            
            function resetToToday() {{
                currentTimelineDate = new Date();
                renderTimeline();
            }}

            function renderTimeline() {{
                const timelineChart = document.getElementById('timeline-chart');
                timelineChart.innerHTML = ''; // 🌟 차트 초기화 (다시 그리기 위함)

                // 🌟 현재 선택된 타임라인 날짜 가져오기
                const tY = currentTimelineDate.getFullYear();
                const tM = currentTimelineDate.getMonth() + 1;
                const tD = currentTimelineDate.getDate();
                const days = ['일', '월', '화', '수', '목', '금', '토'];
                const tDayStr = days[currentTimelineDate.getDay()];

                // 🌟 제목 업데이트 (오늘인지 아닌지 판별)
                const actualToday = new Date();
                const isActuallyToday = (tY === actualToday.getFullYear() && tM === actualToday.getMonth() + 1 && tD === actualToday.getDate());
                const titlePrefix = isActuallyToday ? "오늘 " : "";
                
                const dateDisplay = document.getElementById('timeline-date-display');
                dateDisplay.innerText = `📅 ${{titlePrefix}}전체 일정 타임라인 (${{tM}}/${{tD}} ${{tDayStr}})`;

                let todayEvents = [];

                if (gridData) {{
                    gridData.forEach((row, idx) => {{
                        if (idx === 0) return; 
                        const dateText = row[0].text;
                        const nums = dateText.match(/\\d+/g);
                        let isTargetDate = false;
                        if (nums && nums.length >= 2) {{
                            let m = parseInt(nums[0]), d = parseInt(nums[1]);
                            if (nums.length >= 3 && parseInt(nums[0]) > 2000) {{ m = parseInt(nums[1]); d = parseInt(nums[2]); }}
                            // 🌟 선택된 날짜와 일치하는지 확인
                            isTargetDate = (m === tM && d === tD);
                        }}

                        if (isTargetDate) {{
                            let timeText = row[1] ? row[1].text : ""; 
                            let startTimeStr = "09:00", endTimeStr = "18:00";
                            
                            if (!timeText.toUpperCase().includes("ALL")) {{
                                const timeMatch = timeText.match(/(\\d{{2}}:\\d{{2}})(?:\\s*-\\s*(\\d{{2}}:\\d{{2}}))?/);
                                if (timeMatch) {{
                                    startTimeStr = timeMatch[1];
                                    if (timeMatch[2]) {{
                                        endTimeStr = timeMatch[2];
                                    }} else {{
                                        let [sh, sm] = startTimeStr.split(':').map(Number);
                                        let endH = sh + 1;
                                        endTimeStr = `${{endH.toString().padStart(2, '0')}}:${{sm.toString().padStart(2, '0')}}`;
                                    }}
                                }}
                            }}

                            let resourceName = row[2] ? row[2].text : "자원";
                            let eventTitle = row[3] ? row[3].text : "";
                            if (!eventTitle) eventTitle = resourceName; 
                            
                            let bookerName = row[row.length - 1] ? row[row.length - 1].text : "";

                            // 🌟 18시 이후 일정 잘라내기 (Clamp)
                            let startMin = timeStringToMinutes(startTimeStr);
                            let endMin = timeStringToMinutes(endTimeStr);
                            const limitMin = 18 * 60; // 18시 = 1080분

                            if (startMin < limitMin) {{
                                if (endMin > limitMin) endMin = limitMin; // 18시 넘으면 18시로 고정
                                todayEvents.push({{ start: startMin, end: endMin, timeStr: timeText, resource: resourceName, title: eventTitle, name: bookerName }});
                            }}
                        }}
                    }});
                }}

                const startHour = 9, endHour = 18;
                const totalMinutes = (endHour - startHour) * 60;
                
                for (let h = startHour; h <= endHour; h++) {{
                    const position = ((h - startHour) * 60 / totalMinutes) * 100;
                    const marker = document.createElement('div');
                    marker.className = 'timeline-hour-marker';
                    marker.style.left = `${{position}}%`;
                    marker.innerText = `${{h.toString().padStart(2, '0')}}:00`;
                    timelineChart.appendChild(marker);

                    const gridLine = document.createElement('div');
                    gridLine.className = 'timeline-grid-line';
                    gridLine.style.left = `${{position}}%`;
                    timelineChart.appendChild(gridLine);

                    if (h < endHour) {{
                        const halfPos = ((h + 0.5 - startHour) * 60 / totalMinutes) * 100;
                        const halfLine = document.createElement('div');
                        halfLine.className = 'timeline-grid-line half-hour';
                        halfLine.style.left = `${{halfPos}}%`;
                        timelineChart.appendChild(halfLine);
                    }}
                }}

                // 현재 시간 표시 (선택된 날짜가 '오늘'이고, 09~18시 사이일 때만)
                if (isActuallyToday) {{
                    const now = new Date();
                    const curH = now.getHours();
                    const curM = now.getMinutes();
                    const curTotalMin = curH * 60 + curM;
                    const startTotalMin = startHour * 60;
                    const endTotalMin = endHour * 60;

                    if (curTotalMin >= startTotalMin && curTotalMin <= endTotalMin) {{
                        const nowPos = ((curTotalMin - startTotalMin) / totalMinutes) * 100;
                        const nowLine = document.createElement('div');
                        nowLine.className = 'timeline-now-line';
                        nowLine.style.left = `${{nowPos}}%`;
                        
                        const nowLabel = document.createElement('div');
                        nowLabel.className = 'timeline-now-label';
                        nowLabel.innerText = "Now";
                        nowLabel.style.left = `${{nowPos}}%`;

                        timelineChart.appendChild(nowLine);
                        timelineChart.appendChild(nowLabel);
                    }}
                }}

                todayEvents.sort((a, b) => a.start - b.start);
                const levels = []; 

                // 🌟 [추가됨] 미니맵에 사용할 룸 매핑 데이터
                const roomKeys = ["1701", "마카롱", "1702", "도넛", "1703", "에끌레어", "1704", "푸딩", "1705", "파르페", "1706", "바클라바", "1801", "마들렌", "1802", "스콘", "1803", "까눌레", "1804", "휘낭시에", "1805", "와플", "1806", "다쿠아즈", "1807", "퀸아망"];
                const roomIds = ["1701", "1701", "1702", "1702", "1703", "1703", "1704", "1704", "1705", "1705", "1706", "1706", "1801", "1801", "1802", "1802", "1803", "1803", "1804", "1804", "1805", "1805", "1806", "1806", "1807", "1807"];

                todayEvents.forEach(event => {{
                    let levelIndex = levels.findIndex(end => event.start >= end);
                    if (levelIndex === -1) {{
                        levelIndex = levels.length;
                        levels.push(event.end);
                    }} else {{
                        levels[levelIndex] = event.end; 
                    }}

                    const startMinutesFromBase = Math.max(0, event.start - (startHour * 60));
                    const duration = Math.max(10, event.end - event.start); 
                    const left = (startMinutesFromBase / totalMinutes) * 100;
                    const width = (duration / totalMinutes) * 100;
                    const top = levelIndex * 30;

                    const bar = document.createElement('div');
                    bar.className = 'timeline-event-bar';
                    
                    if (blueTeam.some(m => event.name.includes(m))) {{
                        bar.classList.add('blue');
                    }} else if (yellowTeam.some(m => event.name.includes(m))) {{
                        bar.classList.add('yellow');
                    }} else if (greenTeam.some(m => event.name.includes(m))) {{
                        bar.classList.add('green');
                    }} else if (redTeam.some(m => event.name.includes(m))) {{
                        bar.classList.add('red');
                    }}

                    // 🌟 [추가됨] 차량 (진한 회색)
                    // 자원명이나 예약명에 '차량'이 포함되면 vehicle 클래스 추가
                    if (event.resource.includes("차량") || event.title.includes("차량")) {{
                        bar.classList.add('vehicle');
                    }}
                    
                    // 🌟 [추가됨] 시에스타/테라피 (점선)
                    // 자원명이나 예약명에 '시에스타' 또는 '테라피'가 포함되면 rest 클래스 추가
                    if (event.resource.includes("시에스타") || event.title.includes("시에스타") || 
                        event.resource.includes("테라피") || event.title.includes("테라피")) {{
                        bar.classList.add('rest');
                    }}

                    bar.style.left = `${{left}}%`;
                    bar.style.width = `${{width}}%`;
                    bar.style.top = `${{top}}px`;
                    
                    // 💡 타임라인 바: [자원명] [예약명]
                    bar.innerText = `[${{event.resource}}] ${{event.title}}`;
                    bar.title = `[${{event.name}}] ${{event.title}} (${{event.timeStr}})`; 

                    // 🌟 [추가됨] 미니맵 마우스 이벤트 바인딩
                    bar.addEventListener('mouseenter', (e) => {{
                        let targetId = null;
                        for(let i=0; i<roomKeys.length; i++) {{
                            if(event.resource.includes(roomKeys[i]) || event.title.includes(roomKeys[i])) {{
                                targetId = "room-" + roomIds[i];
                                break;
                            }}
                        }}

                        if(targetId) {{
                            document.querySelectorAll('.minimap-grid .room').forEach(el => el.classList.remove('highlight'));
                            const targetEl = document.getElementById(targetId);
                            if(targetEl) targetEl.classList.add('highlight');

                            const tooltip = document.getElementById('minimap-tooltip');
                            tooltip.style.display = 'block';
                            
                            let x = e.clientX + 15;
                            let y = e.clientY + 15;
                            if (x + tooltip.offsetWidth > window.innerWidth) x = e.clientX - tooltip.offsetWidth - 10;
                            if (y + tooltip.offsetHeight > window.innerHeight) y = e.clientY - tooltip.offsetHeight - 10;
                            
                            tooltip.style.left = x + 'px';
                            tooltip.style.top = y + 'px';
                        }}
                    }});

                    bar.addEventListener('mousemove', (e) => {{
                        const tooltip = document.getElementById('minimap-tooltip');
                        if(tooltip.style.display === 'block') {{
                            let x = e.clientX + 15;
                            let y = e.clientY + 15;
                            if (x + tooltip.offsetWidth > window.innerWidth) x = e.clientX - tooltip.offsetWidth - 10;
                            if (y + tooltip.offsetHeight > window.innerHeight) y = e.clientY - tooltip.offsetHeight - 10;
                            tooltip.style.left = x + 'px';
                            tooltip.style.top = y + 'px';
                        }}
                    }});

                    bar.addEventListener('mouseleave', (e) => {{
                        document.getElementById('minimap-tooltip').style.display = 'none';
                    }});
                    
                    timelineChart.appendChild(bar);
                }});

                timelineChart.style.height = `${{(levels.length || 1) * 30 + 20}}px`;
            }}

            function timeStringToMinutes(timeStr) {{
                const [h, m] = timeStr.split(':').map(Number);
                return h * 60 + m;
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
