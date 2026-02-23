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
    
    if start_keyword in extracted_html:
        extracted_html = extracted_html[extracted_html.find(start_keyword):]
        
    if end_keyword in extracted_html:
        extracted_html = extracted_html[:extracted_html.find(end_keyword)]
    
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
                const today = new Date();
                const tM = today.getMonth() + 1;
                const tD = today.getDate();
                
                // 💡 핵심: 어떤 텍스트가 들어오든 숫자만 뽑아서 '오늘'인지 판별하는 마법의 함수
                const isToday = (text) => {{
                    if(!text) return false;
                    
                    // 1. 공백 완벽 제거
                    const clean = text.replace(/\\s+/g, '');
                    
                    // 2. 텍스트 안에서 연속된 숫자들만 배열로 추출 (예: "2026.02.23" -> ["2026", "02", "23"])
                    const nums = clean.match(/\\d+/g);
                    if(!nums || nums.length < 2) return false;

                    let m, d;
                    // 연도(2026 등)가 포함된 경우
                    if(nums.length >= 3 && parseInt(nums[0]) > 2000) {{
                        m = parseInt(nums[1], 10);
                        d = parseInt(nums[2], 10);
                    }} else {{
                        // 연도 없이 월, 일만 있는 경우
                        m = parseInt(nums[0], 10);
                        d = parseInt(nums[1], 10);
                    }}

                    // 3. 시간 데이터(예: 09:30)와 날짜를 착각하지 않도록 날짜 구분자 기호 검사
                    const isDateType = /[-./월일]/.test(clean);
                    
                    return (m === tM && d === tD && isDateType);
                }};

                const rows = document.querySelectorAll('.table-container tr');
                let todayEvents = [];
                let highlightCounter = 0; 

                rows.forEach(row => {{
                    // 제목줄(헤더)은 검사 제외
                    if (row.querySelectorAll('td').length === 0) return;

                    const cells = row.querySelectorAll('th, td');
                    let foundTodayInThisRow = false;
                    let maxRowSpan = 1;

                    // 줄 안의 모든 칸 검사
                    cells.forEach(cell => {{
                        if (isToday(cell.innerText)) {{
                            foundTodayInThisRow = true;
                            const rs = parseInt(cell.getAttribute('rowspan') || '1', 10);
                            if (rs > maxRowSpan) maxRowSpan = rs;
                        }}
                    }});

                    if (foundTodayInThisRow) {{
                        highlightCounter = maxRowSpan; 
                    }}

                    // 오늘 일정 하이라이트 및 요약 데이터 추출
                    if (highlightCounter > 0) {{
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
                        
                        highlightCounter--; 
                    }}
                }});

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
