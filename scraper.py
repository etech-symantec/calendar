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
    
    print("5. 🌟 핵심: 'customListMonthDiv' 표를 찾아 '완전 평탄화' 상태로 추출 중!")
    
    # 💡 브라우저 안에서 미리 모든 rowspan을 해제하여 '1행 1날짜' 상태로 만듭니다.
    # 이렇게 해야 나중에 자바스크립트로 필터링 후 다시 예쁘게 합칠 수 있습니다.
    extract_js = """
    () => {
        // customListMonthDiv 안에 있는 테이블 찾기
        const div = document.querySelector('#customListMonthDiv');
        if (!div) return "<p>일정 테이블을 찾을 수 없습니다.</p>";
        
        const table = div.querySelector('table');
        if (!table) return "<p>테이블이 없습니다.</p>";

        const trs = Array.from(table.rows);
        const grid = [];
        
        // 1. 바둑판(grid)에 모든 셀을 1:1로 펼치기 (평탄화)
        trs.forEach((tr, r) => {
            if (!grid[r]) grid[r] = [];
            let c = 0;
            Array.from(tr.cells).forEach(cell => {
                while (grid[r][c]) c++; // 이미 채워진 자리 건너뛰기
                
                const rowspan = cell.rowSpan || 1;
                const colspan = cell.colSpan || 1;
                
                for (let rr = 0; rr < rowspan; rr++) {
                    for (let cc = 0; cc < colspan; cc++) {
                        if (!grid[r + rr]) grid[r + rr] = [];
                        
                        // 셀 복제 및 속성 초기화 (rowspan 제거)
                        const clone = cell.cloneNode(true);
                        clone.removeAttribute('rowspan');
                        clone.removeAttribute('colspan');
                        
                        grid[r + rr][c + cc] = clone;
                    }
                }
            });
        });
        
        // 2. 평탄화된 데이터로 새로운 HTML 문자열 생성
        let html = '<table class="flattened-table">';
        
        // thead (있다면)
        const thead = table.querySelector('thead');
        if(thead) html += thead.outerHTML;

        // tbody
        html += '<tbody>';
        for (let r = 0; r < grid.length; r++) {
            // 헤더 줄(th만 있는 줄)은 제외하고 데이터 줄만 가져옴 (보통 tbody 안)
            // 혹은 기존 구조를 유지하되 grid 기반으로 재구성
            if (!grid[r] || grid[r].length === 0) continue;
            
            html += '<tr>';
            for (let c = 0; c < grid[r].length; c++) {
                const cell = grid[r][c];
                if (cell) {
                    html += cell.outerHTML;
                }
            }
            html += '</tr>';
        }
        html += '</tbody></table>';
        
        return html;
    }
    """
    
    extracted_html = ""
    try:
        extracted_html = frame.evaluate(extract_js)
    except Exception:
        extracted_html = page.evaluate(extract_js)
    
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    kst_now = now.strftime('%Y-%m-%d %H:%M:%S')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>일정목록 대시보드</title>
        <style>
            /* 폰트 크기 및 전체적인 사이즈 축소 */
            body {{ font-family: 'Pretendard', sans-serif; padding: 10px; background-color: #f8f9fa; color: #333; font-size: 12px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 5px; margin: 0 0 10px 0; font-size: 16px; }}
            .sync-time {{ color: #7f8c8d; font-size: 11px; margin-bottom: 10px; text-align: right; }}
            
            /* 버튼 그룹 스타일 */
            .controls {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .btn-group {{ display: flex; gap: 5px; }}
            .btn {{ border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; transition: 0.2s; }}
            
            .btn-blue {{ background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
            .btn-blue.active, .btn-blue:hover {{ background-color: #0ea5e9; color: white; border-color: #0284c7; }}
            
            .btn-yellow {{ background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047; }}
            .btn-yellow.active, .btn-yellow:hover {{ background-color: #eab308; color: white; border-color: #ca8a04; }}
            
            .btn-all {{ background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }}
            .btn-all.active, .btn-all:hover {{ background-color: #6b7280; color: white; border-color: #4b5563; }}

            /* 요약 박스 */
            .summary-box {{ background: #fff; border-left: 4px solid #e11d48; padding: 10px; margin-bottom: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .summary-box h3 {{ margin: 0 0 5px 0; color: #e11d48; font-size: 13px; }}
            .summary-box ul {{ margin: 0; padding-left: 20px; line-height: 1.4; color: #333; font-size: 12px; }}
            .summary-box li {{ padding: 2px 0; border-bottom: 1px dashed #ffe4e6; }}
            .summary-box li:last-child {{ border-bottom: none; }}

            /* 테이블 스타일 (콤팩트) */
            .table-container {{ background: #fff; padding: 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #d1d5db !important; padding: 6px 8px !important; text-align: center; white-space: nowrap; font-size: 11px; }}
            
            /* 제목줄(Header) */
            thead tr {{ background-color: #e5e7eb !important; }}
            th {{ background-color: #e5e7eb !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; color: #374151; }}
            
            /* 호버 효과 */
            tbody tr:hover td {{ background-color: #f3f4f6 !important; }}
            
            /* 필터링용 숨김 클래스 */
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
            <ul id="today-list">
                <li>데이터 로딩 중...</li>
            </ul>
        </div>
        <p class="sync-time">Update: {kst_now}</p>

        <div class="table-container">
            {extracted_html}
        </div>

        <script>
            // ✅ 팀원 설정
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];
            
            let currentFilter = 'blue';

            document.addEventListener("DOMContentLoaded", function() {{
                // 초기 실행: 블루팀 필터 적용
                applyFilter('blue');
            }});

            function applyFilter(team) {{
                currentFilter = team;
                
                // 1. 버튼 활성화 스타일 변경
                document.querySelectorAll('.btn').forEach(btn => btn.classList.remove('active'));
                document.querySelector(`.btn-${{team}}`).classList.add('active');

                const rows = document.querySelectorAll('.table-container tbody tr');
                
                // 2. 먼저 모든 행과 셀을 '초기화' (숨김 해제, rowspan 1로 리셋)
                // 이것이 화면 깨짐을 방지하는 핵심입니다.
                rows.forEach(row => {{
                    row.classList.remove('hidden-row');
                    row.style.backgroundColor = ''; // 배경색 리셋
                    row.querySelectorAll('th, td').forEach(cell => {{
                        cell.classList.remove('hidden-cell'); // 숨겨진 셀 보이기
                        cell.setAttribute('rowspan', 1); // 병합 해제
                        cell.style.color = ''; 
                        cell.style.fontWeight = '';
                    }});
                }});

                // 3. 필터링 로직: 조건에 맞지 않는 행 숨기기
                let visibleRows = [];
                rows.forEach(row => {{
                    const tds = row.querySelectorAll('td');
                    if (tds.length < 3) return; // 데이터가 없는 줄 패스

                    const name = tds[2].innerText.trim(); // 등록자 이름 (보통 마지막 열)
                    let isVisible = false;

                    if (team === 'all') {{
                        isVisible = true;
                    }} else if (team === 'blue') {{
                        isVisible = blueTeam.some(member => name.includes(member));
                    }} else if (team === 'yellow') {{
                        isVisible = yellowTeam.some(member => name.includes(member));
                    }}

                    if (isVisible) {{
                        visibleRows.push(row);
                    }} else {{
                        row.classList.add('hidden-row');
                    }}
                }});

                // 4. [핵심] 보이는 행들끼리 날짜 재병합 (Dynamic Re-merge)
                if (visibleRows.length > 0) {{
                    let lastDateCell = visibleRows[0].querySelector('th'); // 첫 줄의 날짜 칸
                    let lastDateText = lastDateCell ? lastDateCell.innerText.trim() : "";
                    let spanCount = 1;

                    for (let i = 1; i < visibleRows.length; i++) {{
                        const row = visibleRows[i];
                        const dateCell = row.querySelector('th'); // 현재 줄의 날짜 칸
                        
                        if (!dateCell) continue;

                        const currentDateText = dateCell.innerText.trim();

                        if (currentDateText === lastDateText && currentDateText !== "") {{
                            // 이전 줄과 날짜가 같으면? -> 현재 날짜 칸 숨기고, 이전 날짜 칸을 늘림
                            dateCell.classList.add('hidden-cell');
                            spanCount++;
                            lastDateCell.setAttribute('rowspan', spanCount);
                        }} else {{
                            // 날짜가 달라지면? -> 새로운 기준점이 됨
                            lastDateCell = dateCell;
                            lastDateText = currentDateText;
                            spanCount = 1;
                        }}
                    }}
                }}

                // 5. 오늘 일정 요약 업데이트 & 하이라이트
                updateSummaryAndHighlight(visibleRows);
            }}

            function updateSummaryAndHighlight(visibleRows) {{
                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                
                // 텍스트에서 날짜 숫자만 뽑아내서 비교하는 함수
                const isToday = (text) => {{
                    if(!text) return false;
                    const clean = text.replace(/\\s+/g, '');
                    const nums = clean.match(/\\d+/g);
                    if(!nums || nums.length < 2) return false;

                    let m = parseInt(nums[0], 10);
                    let d = parseInt(nums[1], 10);
                    
                    if(nums.length >= 3 && parseInt(nums[0]) > 2000) {{
                        m = parseInt(nums[1], 10);
                        d = parseInt(nums[2], 10);
                    }}
                    return (m === tM && d === tD);
                }};

                const ul = document.getElementById('today-list');
                ul.innerHTML = '';
                let todayCount = 0;

                // 현재 보이는 행들 중에서만 오늘 날짜 찾기
                // 주의: 병합된 셀(hidden-cell)의 날짜 텍스트는 읽을 수 없으므로, 
                // 해당 그룹의 대표 셀(lastValidDate)을 기억해야 함.
                
                let currentGroupIsToday = false;

                visibleRows.forEach(row => {{
                    const dateCell = row.querySelector('th');
                    
                    // 날짜 셀이 보이는 상태라면(대표 셀), 오늘인지 새로 검사
                    if (dateCell && !dateCell.classList.contains('hidden-cell')) {{
                        currentGroupIsToday = isToday(dateCell.innerText);
                    }}

                    // 오늘 그룹에 속한 행이라면 처리
                    if (currentGroupIsToday) {{
                        // 하이라이트
                        row.style.backgroundColor = '#fff1f2';
                        row.querySelectorAll('td').forEach(c => c.style.color = '#9f1239');
                        const visibleTh = row.querySelector('th:not(.hidden-cell)');
                        if(visibleTh) visibleTh.style.color = '#9f1239';

                        // 요약 추가
                        const tds = row.querySelectorAll('td');
                        if (tds.length >= 3) {{
                            const time = tds[0].innerText.trim();
                            const title = tds[1].innerText.trim();
                            const name = tds[2].innerText.trim();
                            
                            const li = document.createElement('li');
                            li.innerText = `[${{name}}] ${{title}} (${{time}})`;
                            ul.appendChild(li);
                            todayCount++;
                        }}
                    }}
                }});

                if (todayCount === 0) {{
                    const li = document.createElement('li');
                    li.style.color = '#999';
                    li.innerText = '선택된 팀의 오늘 일정이 없습니다. 🎉';
                    ul.appendChild(li);
                }}
            }}
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
