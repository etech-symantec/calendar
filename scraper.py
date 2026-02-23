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
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px; color: #333; }
            h2 { border-bottom: 3px solid #2c3e50; padding-bottom: 10px; color: #2c3e50; }
            .sync-time { color: #7f8c8d; font-size: 14px; margin-bottom: 30px; font-weight: 500; }
            
            /* 가공된 날짜별 그룹 스타일 */
            .date-group { margin-bottom: 35px; background: #fff; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); overflow: hidden; }
            .date-header { background-color: #34495e; color: white; padding: 14px 20px; font-size: 17px; font-weight: bold; letter-spacing: 0.5px; }
            .styled-table { width: 100%; border-collapse: collapse; }
            .styled-table th, .styled-table td { border-bottom: 1px solid #eee; padding: 14px 20px; text-align: left; font-size: 14.5px; }
            .styled-table th { background-color: #f8fafc; color: #34495e; font-weight: 600; border-bottom: 2px solid #e2e8f0; }
            .styled-table tr:last-child td { border-bottom: none; }
            .styled-table tr:hover { background-color: #f1f5f9; transition: background 0.2s; }
            
            /* 원본 테이블 숨김 */
            #raw-table { display: none; }
            #raw-table table { width: 100%; border-collapse: collapse; background: #fff; }
            #raw-table th, #raw-table td { border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <h2>📅 공유 일정 목록</h2>
        <p class="sync-time">🔄 마지막 동기화: {kst_now}</p>
        
        <div id="grouped-container"></div>

        <div id="raw-table">
            <table id="source-table">
                {table_html}
            </table>
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", function() {
                try {
                    // 원본 테이블 요소 찾기
                    const rawTable = document.getElementById("source-table").querySelector("table") || document.getElementById("source-table");
                    const trs = Array.from(rawTable.querySelectorAll("tr"));
                    
                    if (trs.length < 2) throw new Error("데이터가 없습니다.");

                    // 1단계: 병합된 셀(rowspan, colspan)을 완벽한 바둑판(2차원 배열)으로 펼치기
                    const grid = [];
                    for (let r = 0; r < trs.length; r++) {
                        const tds = trs[r].querySelectorAll("th, td");
                        let c = 0;
                        for (let i = 0; i < tds.length; i++) {
                            // 위에서 병합되어 내려온 빈 공간 건너뛰기
                            while (grid[r] && grid[r][c]) c++; 
                            
                            const td = tds[i];
                            const rowspan = parseInt(td.getAttribute("rowspan") || "1", 10);
                            const colspan = parseInt(td.getAttribute("colspan") || "1", 10);
                            const content = td.innerHTML; // 셀 안의 HTML(버튼, 링크 등) 그대로 복사
                            
                            // 병합된 크기만큼 grid에 데이터 채워넣기
                            for (let rr = 0; rr < rowspan; rr++) {
                                for (let cc = 0; cc < colspan; cc++) {
                                    if (!grid[r + rr]) grid[r + rr] = [];
                                    grid[r + rr][c + cc] = content;
                                }
                            }
                            c += colspan;
                        }
                    }

                    // 2단계: 헤더(제목줄) 추출 및 '날짜' 열 위치 찾기
                    const headers = grid[0].map(html => {
                        const tmp = document.createElement("div");
                        tmp.innerHTML = html;
                        return tmp.innerText.trim();
                    });
                    
                    let dateIdx = headers.findIndex(h => h.includes("일자") || h.includes("일시") || h.includes("기간") || h.includes("날짜"));
                    if (dateIdx === -1) dateIdx = 1; // 기본값: 2번째 열

                    // 3단계: 바둑판 데이터를 날짜별로 그룹화
                    const groupedData = {};
                    for (let r = 1; r < grid.length; r++) {
                        const rowData = grid[r];
                        if (!rowData || rowData.length === 0) continue;
                        
                        // 날짜 텍스트 깔끔하게 정제
                        const tmpDate = document.createElement("div");
                        tmpDate.innerHTML = rowData[dateIdx] || "날짜 없음";
                        let dateText = tmpDate.innerText.trim().split('\\n')[0]; 
                        if (!dateText) dateText = "분류 안 됨";

                        if (!groupedData[dateText]) groupedData[dateText] = [];
                        groupedData[dateText].push(rowData);
                    }

                    // 4단계: 날짜별로 예쁜 카드 형태의 새 테이블 그려주기
                    const container = document.getElementById("grouped-container");
                    for (const [date, rows] of Object.entries(groupedData)) {
                        const dateBlock = document.createElement("div");
                        dateBlock.className = "date-group";
                        
                        const headerHTML = `<div class="date-header">🗓️ ${date}</div>`;
                        
                        // 새 테이블 헤더 생성 (날짜 열은 제목에 썼으므로 숨김)
                        let tableHeadHTML = "<tr>";
                        headers.forEach((h, i) => {
                            if (i !== dateIdx) tableHeadHTML += `<th>${h}</th>`;
                        });
                        tableHeadHTML += "</tr>";

                        // 새 테이블 본문 데이터 생성
                        let tableBodyHTML = "";
                        rows.forEach(rowData => {
                            tableBodyHTML += "<tr>";
                            rowData.forEach((cellHtml, i) => {
                                if (i !== dateIdx) tableBodyHTML += `<td>${cellHtml}</td>`;
                            });
                            tableBodyHTML += "</tr>";
                        });

                        const tableHTML = `<table class="styled-table"><thead>${tableHeadHTML}</thead><tbody>${tableBodyHTML}</tbody></table>`;
                        
                        dateBlock.innerHTML = headerHTML + tableHTML;
                        container.appendChild(dateBlock);
                    }
                } catch (error) {
                    // 에러 발생 시 원본 테이블 강제 노출 (안전장치)
                    console.error("데이터 분류 에러:", error);
                    document.getElementById("grouped-container").innerHTML = "<p><b style='color:#e74c3c;'>⚠️ 표 구조가 특이하여 원본 형태로 표시합니다.</b></p>";
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
