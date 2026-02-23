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
    
    print("5. 🌟 핵심: 'customListMonthDiv' 표 추출 (자바스크립트로 평탄화 예정)")
    
    extracted_html = ""
    try:
        extracted_html = frame.locator('#customListMonthDiv').inner_html(timeout=5000)
    except Exception:
        extracted_html = page.locator('#customListMonthDiv').inner_html(timeout=5000)
    
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
            /* 폰트 크기 30% 축소 (기본 16px -> 11px 수준) */
            body {{ font-family: 'Pretendard', sans-serif; padding: 15px; background-color: #f8f9fa; color: #333; font-size: 11px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 8px; margin: 0 0 10px 0; font-size: 16px; }}
            .sync-time {{ color: #7f8c8d; font-size: 10px; margin-bottom: 15px; text-align: right; }}
            
            /* 버튼 그룹 스타일 */
            .controls {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
            .btn-group {{ display: flex; gap: 5px; }}
            .btn {{ border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: bold; transition: 0.2s; }}
            .btn-blue {{ background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
            .btn-blue.active, .btn-blue:hover {{ background-color: #0ea5e9; color: white; }}
            
            .btn-yellow {{ background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047; }}
            .btn-yellow.active, .btn-yellow:hover {{ background-color: #eab308; color: white; }}
            
            .btn-all {{ background-color: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }}
            .btn-all.active, .btn-all:hover {{ background-color: #6b7280; color: white; }}

            /* 요약 박스 */
            .summary-box {{ background: #fff; border-left: 4px solid #e11d48; padding: 12px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            .summary-box h3 {{ margin: 0 0 8px 0; color: #e11d48; font-size: 13px; }}
            .summary-box ul {{ margin: 0; padding-left: 15px; line-height: 1.5; color: #333; }}
            .summary-box li {{ padding: 3px 0; border-bottom: 1px dashed #ffe4e6; }}
            .summary-box li:last-child {{ border-bottom: none; }}

            /* 테이블 스타일 (콤팩트) */
            .table-container {{ background: #fff; padding: 10px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; max-height: 80vh; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #d1d5db !important; padding: 6px 8px !important; text-align: center; white-space: nowrap; font-size: 11px; }}
            th {{ background-color: #e5e7eb !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; color: #374151; }}
            tbody tr:hover td, tbody tr:hover th {{ background-color: #f3f4f6 !important; transition: 0.1s; }}
            
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

        <div class="table-container" id="schedule-table-wrapper">
            {extracted_html}
        </div>

        <script>
            // ✅ 팀원 명단
            const blueTeam = ["신호근", "김상문", "홍진영", "강성준", "윤태리", "박동석"];
            const yellowTeam = ["백창렬", "권민주", "황현석", "이희찬", "이수재", "이윤재"];
            
            let currentFilter = 'blue';

            document.addEventListener("DOMContentLoaded", function() {{
                // 1. 로드 시 표 평탄화 (rowspan 해제)
                flattenTableAndInit();
                
                // 2. 초기 필터 적용
                applyFilter('blue'); 
            }});

            // 🛠️ 초기화 함수: rowspan을 모두 깨부수고 독립적인 셀로 만듦
            function flattenTableAndInit() {{
                const wrapper = document.getElementById('schedule-table-wrapper');
                const table = wrapper.querySelector('table');
                if (!table) return;

                const trs = Array.from(table.querySelectorAll('tr'));
                if (table.dataset.flattened) return;

                const grid = [];
                
                trs.forEach((tr, r) => {{
                    if (!grid[r]) grid[r] = [];
                    let c = 0;
                    Array.from(tr.children).forEach(cell => {{
                        while (grid[r][c]) c++;
                        
                        const rowspan = parseInt(cell.getAttribute('rowspan') || 1, 10);
                        const colspan = parseInt(cell.getAttribute('colspan') || 1, 10);
                        const html = cell.innerHTML;
                        const tagName = cell.tagName;
                        const className = cell.className;
                        const style = cell.getAttribute('style');

                        for (let rr = 0; rr < rowspan; rr++) {{
                            for (let cc = 0; cc < colspan; cc++) {{
                                if (!grid[r + rr]) grid[r + rr] = [];
                                grid[r + rr][c + cc] = {{ 
                                    html, tagName, className, style,
                                    isOriginal: (rr===0 && cc===0)
                                }};
                            }}
                        }}
                    }});
                }});

                let newHtml = '<tbody>';
                for (let r = 0; r < grid.length; r++) {{
                    newHtml += '<tr>';
                    if (grid[r]) {{
                        grid[r].forEach(cell => {{
                            let cellHtml = `<${{cell.tagName}} class="${{cell.className}}" style="${{cell.style || ''}}">${{cell.html}}</${{cell.tagName}}>`;
                            newHtml += cellHtml;
                        }});
                    }}
                    newHtml += '</tr>';
                }}
                newHtml += '</tbody>';
                
                table.innerHTML = newHtml;
                table.dataset.flattened = "true";
            }}

            // 🔍 필터링 및 동적 병합
            function applyFilter(team) {{
                currentFilter = team;
                
                document.querySelectorAll('.btn').forEach(btn => btn.classList.remove('active'));
                document.querySelector(`.btn-${{team}}`).classList.add('active');

                const rows = document.querySelectorAll('.table-container tbody tr');
                
                // 1단계: 모든 행과 셀 리셋
                rows.forEach(row => {{
                    row.classList.remove('hidden-row');
                    row.style.backgroundColor = '';
                    
                    const firstCell = row.children[0]; 
                    if(firstCell) {{
                        firstCell.classList.remove('hidden-cell');
                        firstCell.setAttribute('rowspan', 1);
                        firstCell.style.color = '';
                        firstCell.style.fontWeight = '';
                    }}
                    
                    Array.from(row.children).forEach(c => {{
                        if(c !== firstCell) {{
                            c.style.color = '';
                            c.style.fontWeight = '';
                        }}
                    }});
                }});

                // 2단계: 필터링
                let visibleRows = [];
                rows.forEach(row => {{
                    const tds = row.querySelectorAll('td');
                    if (tds.length < 2) return; 

                    const nameCell = tds[tds.length - 1]; 
                    const name = nameCell ? nameCell.innerText.trim() : "";
                    
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

                // 3단계: 보이는 행 재병합
                if (visibleRows.length > 0) {{
                    let lastDateCell = visibleRows[0].children[0]; 
                    let lastDateText = lastDateCell ? lastDateCell.innerText.trim() : "";
                    let spanCount = 1;

                    for (let i = 1; i < visibleRows.length; i++) {{
                        const row = visibleRows[i];
                        const dateCell = row.children[0]; 
                        
                        if (!dateCell) continue;

                        const currentDateText = dateCell.innerText.trim();

                        if (currentDateText === lastDateText && currentDateText !== "") {{
                            dateCell.classList.add('hidden-cell');
                            spanCount++;
                            lastDateCell.setAttribute('rowspan', spanCount);
                        }} else {{
                            lastDateCell = dateCell;
                            lastDateText = currentDateText;
                            spanCount = 1;
                        }}
                    }}
                }}

                // 4단계: 요약 업데이트 (포맷 수정됨!)
                refreshTodaySummary(visibleRows);
            }}

            function refreshTodaySummary(visibleRows) {{
                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                
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
                let currentGroupIsToday = false; 

                visibleRows.forEach(row => {{
                    const dateCell = row.children[0];
                    
                    if (dateCell && !dateCell.classList.contains('hidden-cell')) {{
                        currentGroupIsToday = isToday(dateCell.innerText);
                    }}

                    if (currentGroupIsToday) {{
                        row.style.backgroundColor = '#fff1f2';
                        Array.from(row.children).forEach(c => {{
                            c.style.color = '#9f1239';
                            c.style.fontWeight = 'bold';
                        }});

                        // ✅ 요약 데이터 추출 및 포맷 수정
                        const tds = row.querySelectorAll('td');
                        if (tds.length >= 3) {{
                            const time = tds[0].innerText.trim();
                            const title = tds[1].innerText.trim();
                            const name = tds[2].innerText.trim();
                            
                            const li = document.createElement('li');
                            // 💡 기존: `[${name}] ${title} (${time})`
                            // 🔥 수정: `title` 만 출력 (일정명)
                            li.innerText = title; 
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
