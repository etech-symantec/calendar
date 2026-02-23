import os
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

def run(playwright):
    # GitHub Actions에서는 화면이 없으므로 headless=True 유지
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    USER_ID = os.environ.get("MY_SITE_ID", "")
    USER_PW = os.environ.get("MY_SITE_PW", "")

    print("1. 로그인 페이지 접속 중...")
    page.goto("http://gwa.youngwoo.co.kr/") 
    
    page.fill('#userId', USER_ID) 
    page.fill('#userPw', USER_PW)
    
    print("로그인 시도 중...")
    page.press('#userPw', 'Enter')
    page.wait_for_load_state('networkidle')
    time.sleep(3) # 메인 페이지 로딩 대기

    print("2. 상단 '일정' 메뉴 클릭 중...")
    page.click('#topMenu300000000') 
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    print("3. 좌측 '공유일정 전체보기' 메뉴 클릭 중...")
    # 🔥 수정 포인트 1: 띄어쓰기 반영 및 가장 확실한 태그 ID(#301040000_all_anchor) 적용
    try:
        # HTML 분석으로 찾아낸 고유 ID를 클릭 (가장 정확함)
        page.click('#301040000_all_anchor', timeout=5000)
    except Exception:
        # 혹시 ID가 바뀌었을 경우 텍스트(띄어쓰기 포함)로 클릭
        page.locator('text="공유일정 전체보기"').click(timeout=5000)
        
    time.sleep(3) # 클릭 후 우측 화면(iframe)이 바뀔 때까지 잠시 대기

    print("4. 우측 본문에서 '일정목록' 탭 클릭 중...")
    # 🔥 수정 포인트 2: 일정목록은 우측 본문 액자(iframe) 안에 있음
    frame = page.frame_locator('#_content')
    
    try:
        # iframe 안에서 '일정목록' 텍스트 클릭
        frame.locator('text="일정목록"').click(timeout=5000)
    except Exception:
        # 혹시 못 찾을 경우를 대비해 전체 페이지에서도 한번 더 찾아봄
        print("iframe 안에서 '일정목록'을 찾지 못해 전체 화면에서 시도합니다...")
        page.locator('text="일정목록"').click(timeout=5000)

    print("일정목록 데이터 불러오는 중...")
    time.sleep(5) # 테이블이 화면에 그려질 때까지 넉넉히 대기
    
    print("5. 데이터 스크래핑 및 HTML 생성 중...")
    table_html = ""
    try:
        # iframe 안의 테이블 HTML 복사
        table_html = frame.locator('table').first.inner_html(timeout=5000)
    except Exception:
        table_html = page.locator('table').first.inner_html(timeout=5000)
    
    # 5. 결과를 담은 웹페이지(index.html) 생성
    kst_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>그룹웨어 일정목록</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333; }
            h2 { border-bottom: 2px solid #0056b3; padding-bottom: 10px; }
            .sync-time { color: #6c757d; font-size: 14px; margin-bottom: 30px; }
            
            /* 가공된 날짜별 그룹 스타일 */
            .date-group { margin-bottom: 30px; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; }
            .date-header { background-color: #0056b3; color: white; padding: 12px 20px; font-size: 16px; font-weight: bold; }
            .styled-table { width: 100%; border-collapse: collapse; }
            .styled-table th, .styled-table td { border: 1px solid #eee; padding: 12px 20px; text-align: left; font-size: 14px; }
            .styled-table th { background-color: #f4f6f9; color: #495057; font-weight: 600; }
            .styled-table tr:hover { background-color: #fcfcfc; }
            
            /* 에러 시 보여줄 원본 표 스타일 */
            #raw-table table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #fff; font-size: 14px; text-align: left; }
            #raw-table th, #raw-table td { border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <h2>📅 업데이트된 공유 일정 목록</h2>
        <p class="sync-time">마지막 동기화: {kst_now}</p>
        
        <div id="grouped-container"></div>

        <div id="raw-table" style="display: none;">
            <table id="source-table">
                {table_html}
            </table>
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", function() {
                try {
                    const rawTable = document.getElementById("source-table");
                    const rows = Array.from(rawTable.querySelectorAll("tr"));
                    
                    // 데이터가 없는 경우 안전장치: 원본 테이블 강제 표시
                    if (rows.length < 2) {
                        document.getElementById("grouped-container").innerHTML = "<p><b>💡 분류할 데이터가 부족하여 원본 표를 그대로 표시합니다.</b></p>";
                        document.getElementById("raw-table").style.display = "block";
                        return;
                    }

                    // 1. 헤더(th) 추출
                    const headerRow = rows[0];
                    const headers = Array.from(headerRow.querySelectorAll("th, td")).map(el => el.innerText.trim());
                    
                    // 2. '일자' 관련 열 찾기
                    let dateIdx = headers.findIndex(h => h.includes("일자") || h.includes("일시") || h.includes("기간") || h.includes("날짜"));
                    if (dateIdx === -1) dateIdx = 1; // 못 찾으면 기본 2번째 열

                    // 3. 데이터 그룹화 작업
                    const groupedData = {};
                    let hasValidData = false;

                    for (let i = 1; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll("td");
                        if (cells.length > 0) {
                            hasValidData = true;
                            let dateText = cells[dateIdx] ? cells[dateIdx].innerText.trim() : "날짜 없음";
                            dateText = dateText.split('\\n')[0].trim(); // 첫 줄만 사용

                            if (!groupedData[dateText]) {
                                groupedData[dateText] = [];
                            }
                            groupedData[dateText].push(rows[i].innerHTML);
                        }
                    }

                    if (!hasValidData) throw new Error("유효한 표 데이터를 찾을 수 없습니다.");

                    // 4. 화면에 그리기
                    const container = document.getElementById("grouped-container");
                    for (const [date, trHTMLs] of Object.entries(groupedData)) {
                        const dateBlock = document.createElement("div");
                        dateBlock.className = "date-group";
                        
                        const headerHTML = `<div class="date-header">📆 ${date}</div>`;
                        const tableHead = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead>`;
                        const tableBody = `<tbody><tr>${trHTMLs.join("</tr><tr>")}</tr></tbody>`;
                        const tableHTML = `<table class="styled-table">${tableHead}${tableBody}</table>`;
                        
                        dateBlock.innerHTML = headerHTML + tableHTML;
                        container.appendChild(dateBlock);
                    }
                } catch (error) {
                    console.error("데이터 분류 중 에러 발생:", error);
                    // 에러 발생 시 안전장치: 에러 메시지와 함께 원본 표 표시
                    document.getElementById("grouped-container").innerHTML = "<p><b style='color:#d9534f;'>⚠️ 데이터를 예쁘게 꾸미는 중 문제가 발생하여 원본 표를 표시합니다.</b></p>";
                    document.getElementById("raw-table").style.display = "block";
                }
            });
        </script>
    </body>
    </html>
    """

    final_html = html_template.replace("{kst_now}", kst_now).replace("{table_html}", table_html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print("✅ 성공적으로 index.html을 생성했습니다!")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
