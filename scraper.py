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
    
    print("5. 🌟 핵심: 찌꺼기 무시하고 'customListMonthDiv' 표만 핀셋으로 추출 중!")
    
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

            .table-container {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; max-height: 65vh; }}
            table {{ border-collapse: collapse !important; width: 100% !important; }}
            table, th, td {{ border: 1px solid #2c3e50 !important; padding: 12px 10px !important; text-align: center; white-space: nowrap; }}
            th {{ background-color: #e2e8f0 !important; font-weight: bold !important; position: sticky; top: 0; z-index: 10; }}
            tbody tr:hover td, tbody tr:hover th {{ background-color: #f1f5f9 !important; transition: 0.2s; }}
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

                const rows = document.querySelectorAll('.table-container tbody tr');
                let todayEvents = [];
                
                // 💡 핵심: 병합된 칸(rowspan)을 기억하는 추적기 변수
                let activeRowSpan = 0; 
                let isTodayGroup = false;

                rows.forEach(row => {{
                    // 각 줄에서 '날짜(th)' 칸이 있는지 확인합니다.
                    const th = row.querySelector('th');

                    if (th) {{
                        // 날짜 칸이 있다면, 이게 몇 줄짜리 병합인지(rowspan) 가져옵니다. (없으면 1줄)
                        activeRowSpan = parseInt(th.getAttribute('rowspan') || '1', 10);
                        // 이 날짜가 '오늘'인지 확인합니다.
                        isTodayGroup = isToday(th.innerText);
                    }}

                    // 현재 줄이 '오늘 일정'의 범위(rowspan 카운터) 안에 속해 있다면?
                    if (isTodayGroup && activeRowSpan > 0) {{
                        // 줄 전체를 예쁜 핑크색으로 하이라이트!
                        row.style.backgroundColor = '#fff1f2';
                        row.querySelectorAll('th, td').forEach(c => {{
                            c.style.color = '#9f1239';
                            c.style.fontWeight = 'bold';
                        }});

                        // 요약 데이터 추출
                        const tds = row.querySelectorAll('td');
                        if (tds.length >= 3) {{
                            const time = tds[0].innerText.trim();
                            const title = tds[1].innerText.trim();
                            const name = tds[2].innerText.trim();
                            todayEvents.push(`[${{name}}] ${{title}} (${{time}})`);
                        }}
                    }}

                    // 카운터 1 차감 (이 줄을 처리했으니 다음 줄로 넘어갑니다)
                    if (activeRowSpan > 0) {{
                        activeRowSpan--;
                    }}
                }});

                // 상단 요약 업데이트
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
