import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

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
    
    # ✂️ 문자열 자르기 로직
    current_year = datetime.now().year
    start_keyword = f"{current_year}년" 
    end_keyword = "일정등록"
    
    extracted_html = raw_html
    
    # 1. '2026'(또는 지정한 키워드)이 있는 곳부터 끝까지만 남김
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    # 2. '일정등록' 글자가 있는 곳 앞까지만 딱 남김
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # CSS 테두리 강제 주입 및 JS 오늘 일정 하이라이트 추가
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
            
            /* 🔥 상단 오늘 일정 요약 박스 디자인 */
            .summary-box {{ background: #fff; border-left: 5px solid #e11d48; padding: 20px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            .summary-box h3 {{ margin: 0 0 10px 0; color: #e11d48; font-size: 18px; }}
            .summary-box ul {{ margin: 0; padding-left: 20px; line-height: 1.6; color: #333; }}
            .summary-box li {{ padding: 6px 0; border-bottom: 1px dashed #fecdd3; }}
            .summary-box li:last-child {{ border-bottom: none; }}

            /* 🔥 무조건 테두리가 보이게 강제하는 마법의 CSS */
            .table-container {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 10px !important; text-align: center; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; }}
        </style>
    </head>
    <body>
        <h2>📅 공유 일정 대시보드</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        
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
                // 1. 오늘 날짜 포맷 준비 (접속한 날짜 기준)
                const today = new Date();
                const m = today.getMonth() + 1;
                const d = today.getDate();
                const mm = String(m).padStart(2, '0');
                const dd = String(d).padStart(2, '0');

                // 그룹웨어에서 사용할 법한 모든 날짜 형식을 배열로 준비
                const todayFormats = [
                    `${{m}}월 ${{d}}일`, `${{m}}월${{d}}일`, 
                    `${{mm}}-${{dd}}`, `${{mm}}.${{dd}}`, `${{mm}}/${{dd}}`,
                    `${{m}}-${{d}}`, `${{m}}.${{d}}`, `${{m}}/${{d}}`
                ];

                const rows = document.querySelectorAll('.table-container tr');
                let todayEvents = [];
                let highlightCounter = 0; // rowspan(병합된 칸)을 계산하기 위한 카운터

                // 2. 표 전체를 한 줄씩 돌면서 오늘 날짜 검사
                rows.forEach(row => {{
                    const cells = row.querySelectorAll('th, td');
                    
                    cells.forEach(cell => {{
                        const text = cell.innerText.trim();
                        const isToday = todayFormats.some(fmt => text.includes(fmt));
                        
                        // 이 줄에서 오늘 날짜를 발견했다면?
                        if (isToday) {{
                            const rowspan = parseInt(cell.getAttribute('rowspan') || '1', 10);
                            highlightCounter = rowspan; // 합쳐진 칸의 개수만큼 하이라이트 횟수 충전!
                        }}
                    }});

                    // 3. 오늘 일정에 해당하는 줄이라면 (발견된 줄이거나 병합된 칸의 영향권 안)
                    if (highlightCounter > 0) {{
                        // 원본 표의 해당 줄 하이라이트 칠하기 (배경 핑크색, 글자 진하게)
                        row.querySelectorAll('td, th').forEach(c => {{
                            c.style.backgroundColor = '#fff1f2';
                            c.style.color = '#9f1239';
                            c.style.fontWeight = 'bold';
                        }});

                        // 상단 요약본에 넣을 텍스트 추출 (td 내용만 합치기)
                        let rowData = [];
                        row.querySelectorAll('td').forEach(c => {{
                            const txt = c.innerText.trim().replace(/\\n/g, ' '); // 줄바꿈 제거
                            if(txt) rowData.push(txt);
                        }});
                        
                        if(rowData.length > 0) {{
                            todayEvents.push(rowData.join(' | '));
                        }}
                        
                        highlightCounter--; // 한 줄 처리했으니 카운터 차감
                    }}
                }});

                // 4. 상단 요약 박스 업데이트
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
