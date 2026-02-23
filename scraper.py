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
    
    print("5. 지정된 영역 추출 및 테두리 생성 중...")
    
    raw_html = ""
    try:
        raw_html = frame.locator('body').inner_html(timeout=5000)
    except Exception:
        raw_html = page.locator('body').inner_html(timeout=5000)
    
    # KST (한국 표준시) 설정
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    # ✂️ 문자열 자르기
    current_year = now.year
    start_keyword = f"{current_year}년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
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
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 10px !important; text-align: center; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; }}
            
            /* 💡 병합이 해제되어 복사된 셀에 살짝 연한 배경을 주어 구분을 원하시면 아래 주석을 푸세요 */
            /* .unmerged-cell {{ background-color: #fafafa !important; }} */
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

                // ==========================================
                // 1. 표 평탄화 (rowspan 강제 해제 및 빈칸 채우기)
                // ==========================================
                const trs = Array.from(table.querySelectorAll('tr'));
                const grid = [];

                // 바둑판(grid) 배열에 모든 셀을 1:1로 복사해서 매핑
                trs.forEach((tr, r) => {{
                    if (!grid[r]) grid[r] = [];
                    let c = 0;
                    
                    Array.from(tr.children).forEach(cell => {{
                        while (grid[r][c]) c++; // 위에서 이미 합쳐져서 채워진 공간 건너뛰기
                        
                        const rowspan = parseInt(cell.getAttribute('rowspan') || 1, 10);
                        const colspan = parseInt(cell.getAttribute('colspan') || 1, 10);
                        
                        for (let rr = 0; rr < rowspan; rr++) {{
                            for (let cc = 0; cc < colspan; cc++) {{
                                if (!grid[r + rr]) grid[r + rr] = [];
                                
                                // 셀을 복제하고, 병합 속성(rowspan)을 제거
                                const clone = cell.cloneNode(true);
                                clone.removeAttribute('rowspan');
                                clone.removeAttribute('colspan');
                                
                                // 병합을 풀어서 생긴 복제본 셀에 클래스 추가 (선택적 스타일링용)
                                if (rr > 0 || cc > 0) clone.classList.add('unmerged-cell');
                                
                                grid[r + rr][c + cc] = clone;
                            }}
                        }}
                    }});
                }});

                // 완성된 바둑판 배열을 실제 화면(HTML)에 덮어쓰기
                trs.forEach((tr, r) => {{
                    tr.innerHTML = ''; // 기존 병합된 줄 삭제
                    if (grid[r]) {{
                        grid[r].forEach(cell => tr.appendChild(cell)); // 분리된 셀들로 다시 채우기
                    }}
                }});

                // ==========================================
                // 2. 오늘 일정 검사 및 하이라이트 (이제 각 줄이 독립적이므로 검사가 매우 쉬움!)
                // ==========================================
                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                
                const isToday = (text) => {{
                    if(!text) return false;
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

                    const isDateType = /[-./월일]/.test(clean);
                    return (m === tM && d === tD && isDateType);
                }};

                let todayEvents = [];

                trs.forEach(row => {{
                    if (row.querySelectorAll('td').length === 0) return; // 제목줄(헤더) 제외

                    let isRowToday = false;
                    
                    // 해당 줄에 오늘 날짜가 있는지 검사
                    row.querySelectorAll('th, td').forEach(cell => {{
                        if (isToday(cell.innerText)) {{
                            isRowToday = true;
                        }}
                    }});

                    // 오늘 일정이면 줄 전체 하이라이트 및 데이터 추출
                    if (isRowToday) {{
                        row.querySelectorAll('td, th').forEach(c => {{
                            c.style.backgroundColor = '#fff1f2';
                            c.style.color = '#9f1239';
                            c.style.fontWeight = 'bold';
                        }});

                        let rowData = [];
                        row.querySelectorAll('td').forEach(c => {{
                            const txt = c.innerText.trim().replace(/\\s+/g, ' '); 
                            if(txt) rowData.push(txt);
                        }});
                        
                        if(rowData.length > 0) {{
                            todayEvents.push(rowData.join(' | '));
                        }}
                    }}
                }});

                // ==========================================
                // 3. 상단 요약 박스 업데이트
                // ==========================================
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
