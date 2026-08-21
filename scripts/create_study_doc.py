"""3번 백엔드 학습 문서를 생성한다. [실행 차단 - 내용이 최신이 아님]

이 스크립트가 만드는 학습 가이드는 어댑터 통합 시점(2026-08-19)에서 멈춰 있고,
그 뒤 바뀐 구조를 반영하지 않는다. 그대로 생성하면 **틀린 내용을 가르치는 문서**가
나오므로 아래 목록을 고치기 전까지 실행하지 않는다. 파일 끝의 진입점을 주석
처리해 두었다.

갱신해야 할 곳 (장 번호는 생성되는 문서 기준) —

3장 구조도 본문 / 8장
    "필터는 유사도 순위를 만든 후 제거한다", "FAISS에서 전체 후보를 받은 뒤
    필터링한다"고 적혀 있으나 실제는 반대다. search_service_adapter가
    `_candidate_indices`로 후보를 먼저 좁힌 뒤 그 안에서 순위를 매긴다.
    응답의 candidate_count가 그 선필터 결과 수다. 8장 콜아웃이 "대규모에서는
    필터 선적용이 필요하다"고 개선 과제처럼 적은 것도 이미 되어 있는 일이다.

5장 파일별 역할과 읽는 순서
    - `app/service.py`는 존재하지 않는다(삭제된 모듈).
    - `app/embeddings.py`, `app/vector_store.py`는 더 이상 운영 검색 경로가
      아니다. 각각 build_index 전용, manifest 생성용으로만 남아 있고 주요
      메서드는 주석 처리했다.
    - 빠진 파일: app/official_search.py(질의 재작성·필터 정규화·로그·응답 조립),
      src/retrieval/search_service_adapter.py(실제 FAISS 검색),
      app/service_manifest.py, app/config.py, app/query_terms.py.

7장 API
    - 표에 GET /search/text, /filters/coverage, /images, / 가 빠져 있다.
    - 7.1 예시가 `"categories": ["sword"]`다. categories는 값 하나만 받는
      호환 별칭이므로 정식 이름 `category`를 쓴다.
    - 7.3 "가중치 합이 1이 아니어도 자동 정규화한다"는 지금 틀리다. 합이 1이
      아니면 400이다.

9장 / 13장
    `scripts/build_index.py` 실행을 안내하지만 그 스크립트는 베이스라인
    임베더로 운영 인덱스를 덮어써서 진입점을 막아 두었다. 인덱스 재생성은
    `scripts/build_final_index.py`다. `D:\AI_Cache` 경로 안내도 특정 PC
    기준이고, 서비스가 캐시 경로를 하드코딩해 HF_HOME을 바꿔도 옮겨지지 않는다.

10장 / 12장 실습 C·D
    - elapsed_ms는 이미 요청 전체 시간이고 search_elapsed_ms가 검색 구간이다.
      미들웨어(record_request_start)도 이미 있다. "별도로 기록해야 한다"는
      콜아웃과 실습 D는 성립하지 않는다.
    - 실습 C의 shape_tags 필터는 이미 동작하고, `AssetRepository.FILTER_FIELDS`
      라는 속성은 없다(SCALAR_FILTER_FIELDS / LIST_FILTER_FIELDS로 나뉘었다).

15장
    체크리스트의 "필터의 OR/AND 규칙"에서 OR은 없다. 목록 필터는 지정한 값을
    모두 가진 에셋만 남기는 AND 하나다.

산출물은 docs/BACKEND_VECTORDB_STUDY_GUIDE_KO.docx 로 나간다.

현재 기준 내용은 docs/BACKEND_FEATURES_KO.md(기능 동작),
docs/BACKEND_FINAL_GUIDE_KO.md(실행·운영), docs/TEST_KEYWORDS_KO.md(질의 예시)에
있다. 학습 문서를 되살릴 때는 그 세 문서를 원본으로 삼으면 된다.
"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
# 인수인계본에는 개인 작업 폴더가 포함되지 않으므로 저장소 문서 폴더에 만든다.
OUTPUT = ROOT / "docs" / "BACKEND_VECTORDB_STUDY_GUIDE_KO.docx"

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
NAVY = "203748"
MUTED = "667085"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
CODE_BG = "F6F8FA"
WHITE = "FFFFFF"
GREEN = "26734D"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_geometry(table, widths_dxa):
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_w = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
            tc_w.set(qn("w:w"), str(widths_dxa[idx]))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_font(run, name="Malgun Gothic", size=None, color=None, bold=None, italic=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def style_document(doc):
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(1)
    sec.left_margin = sec.right_margin = Inches(1)
    sec.header_distance = sec.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Malgun Gothic"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    specs = {
        "Title": (28, NAVY, 0, 8),
        "Subtitle": (13, MUTED, 0, 14),
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (11.5, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in specs.items():
        style = doc.styles[name]
        style.font.name = "Malgun Gothic"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = name != "Subtitle"
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for style_name in ("List Bullet", "List Number"):
        style = doc.styles[style_name]
        style.font.name = "Malgun Gothic"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Malgun Gothic")
        style.font.size = Pt(10.5)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_font(run, size=9, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def add_header_footer(doc):
    section = doc.sections[0]
    hp = section.header.paragraphs[0]
    hp.text = "Fantasy Weapon Search  |  Backend & Vector DB Study Guide"
    set_font(hp.runs[0], size=8.5, color=MUTED)
    add_page_number(section.footer.paragraphs[0])


def add_body(doc, text, bold_start=None):
    p = doc.add_paragraph()
    if bold_start and text.startswith(bold_start):
        r1 = p.add_run(bold_start)
        set_font(r1, bold=True)
        r2 = p.add_run(text[len(bold_start):])
        set_font(r2)
    else:
        r = p.add_run(text)
        set_font(r)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        set_font(p.add_run(item))


def add_steps(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Number")
        set_font(p.add_run(item))


def add_code(doc, code):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    set_cell_shading(cell, CODE_BG)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    for idx, line in enumerate(code.splitlines()):
        if idx:
            p.add_run().add_break()
        set_font(p.add_run(line), name="Consolas", size=8.5, color="24292F")
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_callout(doc, label, text, fill=LIGHT_BLUE):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(f"{label}  ")
    set_font(r, bold=True, color=DARK_BLUE)
    set_font(p.add_run(text))
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    set_repeat_table_header(table.rows[0])
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        set_cell_shading(cell, LIGHT_BLUE)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(p.add_run(header), size=9.5, bold=True, color=DARK_BLUE)
    for row_data in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row_data):
            p = cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            set_font(p.add_run(str(value)), size=9.2)
    set_table_geometry(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def page_break(doc):
    doc.add_page_break()


def build():
    doc = Document()
    style_document(doc)
    add_header_footer(doc)

    # Editorial cover
    doc.add_paragraph().paragraph_format.space_after = Pt(78)
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(kicker.add_run("PROJECT STUDY GUIDE"), size=10, bold=True, color=BLUE)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(title.add_run("판타지 무기 검색 백엔드"), size=28, bold=True, color=NAVY)
    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(subtitle.add_run("FastAPI · OpenCLIP · FAISS로 이해하는 3번 파트"), size=14, color=DARK_BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("구현 결과를 따라가며 배우는 실습형 학습 자료"), size=10.5, color=MUTED, italic=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(84)
    add_callout(doc, "현재 상태", "이미지 1,391개의 512차원 임베딩과 커스텀 residual adapter 학습·평가를 완료했습니다. 텍스트·이미지·멀티모달 검색 API도 구현했으며, 현재 남은 핵심 작업은 최종 adapter 서비스를 FastAPI와 연결하는 것입니다.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run("프로젝트 위치  D:\\2. Fantasy_Weapon_Search-main"), size=9.5, color=MUTED)

    page_break(doc)
    doc.add_heading("1. 이 문서의 학습 목표", level=1)
    add_body(doc, "이 문서는 이미 완성된 코드를 그냥 실행하는 데서 끝나지 않고, 요청이 들어와 검색 결과가 반환되기까지의 흐름을 스스로 설명하고 수정할 수 있도록 돕는다.")
    add_bullets(doc, [
        "멀티모달 검색에서 임베딩이 어떤 역할을 하는지 설명한다.",
        "OpenCLIP이 이미지와 텍스트를 같은 벡터 공간에 배치하는 원리를 이해한다.",
        "FAISS의 내적 검색이 정규화된 벡터에서 코사인 유사도와 같아지는 이유를 이해한다.",
        "FastAPI 엔드포인트와 서비스·저장소 계층의 책임을 구분한다.",
        "텍스트·이미지·멀티모달 검색을 직접 호출하고 결과를 점검한다.",
        "데이터나 모델이 바뀌었을 때 인덱스를 다시 만들고 장애를 진단한다.",
    ])
    add_callout(doc, "추천 학습법", "각 장을 읽은 다음 반드시 명령을 직접 실행하고, 응답 JSON의 asset_id·score·metadata를 눈으로 확인한다.", LIGHT_GRAY)

    doc.add_heading("2. 자동으로 진행된 작업", level=1)
    add_table(doc, ["영역", "완료 내용", "상태"], [
        ("환경", "D 드라이브 Python 3.11 및 프로젝트 .venv", "완료"),
        ("모델 연구", "OpenCLIP ViT-B-16 + 이미지·텍스트 residual adapter", "완료"),
        ("서비스 모델", "현재 app은 ViT-B-32 baseline, adapter 연결 필요", "진행 필요"),
        ("Vector DB", "FAISS IndexFlatIP, 1,391개 × 512차원", "완료"),
        ("API", "텍스트·이미지·멀티모달 검색과 필터·상세 조회", "완료"),
        ("운영", "검색 로그, Dockerfile, 실행 스크립트", "완료"),
        ("검증", "tests/ 22개, compileall 및 pip check", "통과"),
    ], [1650, 5910, 1800])

    page_break(doc)
    doc.add_heading("3. 전체 구조를 한눈에 보기", level=1)
    add_code(doc, "사용자/프론트엔드\n        |\n        v\nFastAPI  app/main.py\n        | HTTP 검증 및 응답 변환\n        v\nOfficialSearchAdapter\n        |\n        v\nWeaponSearchService (custom adapter)\n   |                     |\n   v                     v\nOpenCLIP + Adapter     Metadata Filters\n        \\               /\n         v             v\n          FAISS Top-K Search\n                  |\n                  v\n          검색 결과 + 이미지 URL")
    add_body(doc, "핵심은 이미지와 문장을 모두 동일한 512차원 벡터로 바꾼 뒤, 질의 벡터와 가장 가까운 이미지 벡터를 찾는 것이다. 메타데이터 필터는 벡터 유사도 순위를 만든 후 조건에 맞지 않는 결과를 제거한다.")

    doc.add_heading("4. 꼭 알아야 할 핵심 개념", level=1)
    doc.add_heading("4.1 임베딩", level=2)
    add_body(doc, "임베딩은 이미지나 문장의 의미를 숫자 배열로 표현한 것이다. 이 프로젝트에서는 하나의 이미지 또는 문장이 512개의 실수로 바뀐다. 모양과 의미가 비슷할수록 벡터 방향도 가까워지는 것이 목표다.")
    doc.add_heading("4.2 OpenCLIP", level=2)
    add_body(doc, "CLIP은 이미지 인코더와 텍스트 인코더를 함께 학습해 이미지와 설명 문장을 같은 공간에 배치한다. 따라서 '불타는 검'이라는 문장 벡터와 실제 불꽃 검 이미지 벡터 사이의 유사도를 바로 계산할 수 있다.")
    doc.add_heading("4.3 코사인 유사도와 내적", level=2)
    add_body(doc, "벡터를 길이 1로 정규화하면 두 벡터의 내적은 코사인 유사도와 같다. 1에 가까울수록 방향이 비슷하다. 이 구현은 임베딩을 정규화하고 FAISS IndexFlatIP로 내적을 계산한다.")
    add_code(doc, "normalized = vector / ||vector||\nscore = query_vector · image_vector\n# 정규화된 벡터에서는 score == cosine_similarity")
    doc.add_heading("4.4 FAISS", level=2)
    add_body(doc, "FAISS는 많은 벡터에서 가까운 벡터를 빠르게 찾는 라이브러리다. 현재 데이터는 1,391개로 작아서 정확한 전수 검색인 IndexFlatIP를 사용한다. 데이터가 수십만 개 이상이면 IVF나 HNSW 같은 근사 검색 구조를 검토할 수 있다.")

    page_break(doc)
    doc.add_heading("5. 파일별 역할과 읽는 순서", level=1)
    add_table(doc, ["순서", "파일", "학습 포인트"], [
        ("1", "app/main.py", "API 경로, 요청 검증, 앱 시작 과정"),
        ("2", "app/service.py", "벡터 결합, 검색, 필터 적용, 로그"),
        ("3", "app/embeddings.py", "OpenCLIP 로딩과 임베딩 정규화"),
        ("4", "app/vector_store.py", "FAISS 인덱스 로딩과 Top-K 검색"),
        ("5", "app/repository.py", "JSONL 메타데이터와 필터 규칙"),
        ("6", "app/schemas.py", "요청·응답 데이터 구조와 유효성 검사"),
        ("7", "scripts/build_index.py", "이미지 전체 인코딩과 인덱스 저장"),
        ("8", "tests/", "정상 동작을 자동으로 확인하는 방법"),
    ], [800, 2800, 5760])

    doc.add_heading("6. 서버 시작 실습", level=1)
    add_steps(doc, [
        "PowerShell을 연다.",
        "프로젝트 폴더로 이동한다.",
        "실행 스크립트로 서버를 시작한다.",
        "브라우저에서 Swagger 문서를 연다.",
        "GET /health를 실행해 assets와 vectors가 각각 1391인지 확인한다.",
    ])
    add_code(doc, 'cd "D:\\2. Fantasy_Weapon_Search-main"\n.\\scripts\\run_api.ps1\n\n# 브라우저\nhttp://127.0.0.1:8000/docs')
    add_callout(doc, "정상 기준", "GET /health 응답이 status=ok, assets=1391, vectors=1391이면 데이터·FAISS·모델 연결이 정상이다.")

    page_break(doc)
    doc.add_heading("7. API별 동작 이해", level=1)
    add_table(doc, ["메서드", "경로", "역할"], [
        ("GET", "/health", "서버·데이터·벡터 상태 확인"),
        ("GET", "/filters", "필터 값과 각 값의 에셋 수 반환"),
        ("GET", "/assets/{id}", "특정 에셋의 상세 메타데이터 반환"),
        ("POST", "/search/text", "자연어를 임베딩해 이미지 검색"),
        ("POST", "/search/image", "업로드 이미지를 임베딩해 유사 이미지 검색"),
        ("POST", "/search/multimodal", "이미지·텍스트 벡터를 가중 결합해 검색"),
    ], [1150, 3050, 5160])

    doc.add_heading("7.1 텍스트 검색", level=2)
    add_code(doc, '{\n  "query": "붉은 불꽃 검",\n  "top_k": 5,\n  "filters": {\n    "categories": ["sword"],\n    "elements": ["fire"]\n  }\n}')
    add_body(doc, "처리 흐름: query 검증 → 텍스트 임베딩 → FAISS 전수 검색 → 메타데이터 필터 → 상위 5개 응답 → 로그 기록")

    doc.add_heading("7.2 이미지 검색", level=2)
    add_body(doc, "multipart/form-data로 PNG, JPEG 또는 WEBP를 업로드한다. 10MB를 넘거나 이미지로 해석할 수 없는 파일은 거절한다. 데이터셋 원본 이미지를 올리면 같은 asset_id가 1위에 나오는지 확인할 수 있다.")
    add_code(doc, "시험 이미지\ndata/processed/pixel_art/asset_000057.png")

    doc.add_heading("7.3 멀티모달 검색", level=2)
    add_body(doc, "이미지 벡터와 텍스트 벡터를 가중합한 뒤 다시 길이 1로 정규화한다. 가중치 합이 1이 아니어도 서버에서 자동 정규화한다.")
    add_code(doc, "combined = image_weight × image_vector\n         + text_weight  × text_vector\ncombined = combined / ||combined||")

    page_break(doc)
    doc.add_heading("8. 필터가 적용되는 방식", level=1)
    add_body(doc, "각 필터 그룹 안에서는 하나라도 일치하면 통과하고, 서로 다른 필터 그룹은 모두 만족해야 한다. 예를 들어 categories가 sword, axe이고 elements가 fire이면 '검 또는 도끼'이면서 동시에 fire인 에셋만 남는다.")
    add_bullets(doc, [
        "categories → metadata.category",
        "colors → metadata.colors",
        "elements → metadata.elements",
        "materials → metadata.materials",
        "styles → metadata.style",
        "handedness → metadata.handedness",
    ])
    add_callout(doc, "구현상 특징", "현재는 정확한 Top-K를 보장하기 위해 FAISS에서 전체 후보를 받은 뒤 필터링한다. 1,391개에서는 충분히 빠르지만 대규모 데이터에서는 필터 선적용이나 별도 메타데이터 인덱스가 필요하다.", LIGHT_GRAY)

    doc.add_heading("9. 데이터와 인덱스의 관계", level=1)
    add_body(doc, "FAISS 파일은 이미지 자체를 저장하지 않는다. 벡터 순서와 asset_id 순서를 별도 파일로 함께 유지한다. 두 파일 중 하나만 바뀌면 검색 결과와 메타데이터가 잘못 연결될 수 있다.")
    add_bullets(doc, [
        "storage/indexes/weapons.faiss: 이미지 벡터 1,391개",
        "storage/indexes/weapon_ids.json: 같은 순서의 asset_id 목록",
        "data/metadata/final_search_assets.jsonl: 표시와 필터에 쓰는 메타데이터",
        "data/processed/pixel_art/: 브라우저에 제공할 이미지",
    ])
    add_body(doc, "이미지 추가·삭제, 모델 교체, 전처리 방식 변경이 있으면 인덱스를 다시 생성해야 한다.")
    add_code(doc, "$env:HF_HOME = 'D:\\AI_Cache\\huggingface'\n$env:TORCH_HOME = 'D:\\AI_Cache\\torch'\n.\\.venv\\Scripts\\python.exe .\\scripts\\build_index.py --batch-size 64")

    page_break(doc)
    doc.add_heading("10. 검색 로그와 성능 관찰", level=1)
    add_body(doc, "각 검색은 storage/logs/search.jsonl에 한 줄짜리 JSON으로 기록된다. 요청 시각, 검색 방식, 질의, 필터, Top-K, 결과 수와 FAISS 검색 시간이 포함된다.")
    add_code(doc, "Get-Content .\\storage\\logs\\search.jsonl -Tail 10")
    add_callout(doc, "주의", "현재 elapsed_ms는 임베딩 생성 시간을 제외한 FAISS 검색·필터 구간이다. 전체 API 지연시간을 측정하려면 요청 시작부터 응답 직전까지의 시간을 미들웨어에서 별도로 기록해야 한다.", LIGHT_GRAY)

    doc.add_heading("11. 테스트 읽기", level=1)
    add_body(doc, "테스트는 변경 후 기존 기능이 망가지지 않았는지 알려주는 안전망이다. test_repository.py는 데이터·필터를, test_api_integration.py는 실제 모델과 API 전체 흐름을 검사한다.")
    add_code(doc, ".\\.venv\\Scripts\\python.exe -m pytest -q tests\n.\\.venv\\Scripts\\python.exe -m compileall app src scripts tests\n.\\.venv\\Scripts\\python.exe -m pip check")
    add_bullets(doc, [
        "정상 기준은 22 passed이다. 저장소 루트의 평가 스크립트가 수집되지 않도록 tests 경로를 지정한다.",
        "동일 이미지 검색에서 asset_000057이 첫 번째인지 확인한다.",
        "텍스트 검색 결과가 지정한 category 필터를 지키는지 확인한다.",
        "멀티모달 요청이 결과 3개를 반환하는지 확인한다.",
    ])

    page_break(doc)
    doc.add_heading("12. 직접 해보는 실습 과제", level=1)
    doc.add_heading("실습 A — API 익숙해지기", level=2)
    add_steps(doc, [
        "'붉은 검', '얼음 방패', '나무 활'을 각각 텍스트 검색한다.",
        "같은 질의를 필터 없이 실행한 결과와 category 필터를 적용한 결과를 비교한다.",
        "상위 5개 결과의 score와 caption_ko를 표로 기록한다.",
    ])
    doc.add_heading("실습 B — 가중치 비교", level=2)
    add_steps(doc, [
        "기준 이미지 한 장과 그 이미지에 없는 속성의 문장을 준비한다.",
        "이미지/텍스트 가중치를 0.8/0.2, 0.5/0.5, 0.2/0.8로 바꾼다.",
        "각 조건의 상위 5개가 어떻게 달라지는지 관찰하고 이유를 설명한다.",
    ])
    doc.add_heading("실습 C — 새 필터 추가", level=2)
    add_steps(doc, [
        "shape_tags 필터를 SearchFilters에 추가한다.",
        "AssetRepository.FILTER_FIELDS에 필드 연결을 추가한다.",
        "텍스트 검색 JSON과 이미지 검색 폼에서 값을 받을 수 있게 한다.",
        "필터 단위 테스트를 하나 추가하고 전체 테스트를 실행한다.",
    ])
    doc.add_heading("실습 D — 전체 응답시간 측정", level=2)
    add_steps(doc, [
        "FastAPI 미들웨어에서 요청 시작 시각을 기록한다.",
        "응답 직전에 총 소요 시간을 X-Process-Time-Ms 헤더에 넣는다.",
        "텍스트·이미지 검색의 전체 시간과 현재 elapsed_ms를 비교한다.",
    ])

    page_break(doc)
    doc.add_heading("13. 자주 발생하는 문제와 해결", level=1)
    add_table(doc, ["증상", "가능한 원인", "확인·해결"], [
        ("python 실행 실패", "가상환경 경로 오류", ".venv\\Scripts\\python.exe 존재 확인"),
        ("서버 시작 실패", "FAISS 파일 없음", "scripts/build_index.py 실행"),
        ("모델 다운로드 반복", "캐시 경로 미지정", "D:\\AI_Cache 환경변수 확인"),
        ("이미지 404", "processed_file 또는 mount 경로 오류", "메타데이터 상대경로 확인"),
        ("필터 결과 0개", "허용 값과 철자 불일치", "GET /filters에서 실제 값 확인"),
        ("검색 결과 이상", "모델·인덱스 버전 불일치", "같은 모델로 인덱스 재생성"),
        ("메모리 부족", "batch-size가 큼", "64에서 32 또는 16으로 낮춤"),
    ], [2300, 2800, 4260])

    doc.add_heading("14. 팀원과 합의할 항목", level=1)
    add_bullets(doc, [
        "모델 담당자: 최종 모델명, 임베딩 차원, 정규화, 전처리, 모델 버전",
        "데이터 담당자: asset_id 안정성, 필드 사전, 데이터 변경 전달 방식",
        "프론트엔드 담당자: API 주소, 오류 형식, 필터 UI, 이미지 URL, CORS",
        "QA 담당자: 평가 질의, 정답 기준, 실패 사례 기록, 응답시간 기준",
        "배포 담당자: CPU/GPU, 모델 캐시 볼륨, 로그 보존, 외부 접근 주소",
    ])
    add_callout(doc, "모델·평가 완료", "ViT-B-16 residual adapter 학습과 평가를 완료했습니다. validation mean Recall@5는 0.771277에서 0.941490으로 향상됐고, 멀티모달 test의 최적 가중치는 이미지 0.4 / 텍스트 0.6입니다.")
    add_callout(doc, "다음 핵심 단계", "최종 adapter 서비스(src/retrieval/search_service_adapter.py)를 FastAPI에 연결하고, 프론트엔드에서 실제 API를 호출하는 통합 시험을 진행한다.")

    page_break(doc)
    doc.add_heading("15. 완료 체크리스트", level=1)
    add_bullets(doc, [
        "□ 서버를 혼자 실행하고 종료할 수 있다.",
        "□ /health 응답의 assets와 vectors 의미를 설명할 수 있다.",
        "□ 텍스트·이미지·멀티모달 검색의 입력 형식 차이를 안다.",
        "□ 이미지·텍스트 가중치가 결과에 미치는 영향을 설명할 수 있다.",
        "□ 메타데이터 필터의 OR/AND 규칙을 설명할 수 있다.",
        "□ 이미지 또는 모델 변경 후 인덱스를 다시 만들 수 있다.",
        "□ pytest 실패 메시지에서 실패한 기능을 찾을 수 있다.",
        "□ 검색 로그에서 최근 요청과 처리시간을 확인할 수 있다.",
        "□ 프론트엔드 담당자에게 API 주소와 Swagger 문서를 전달할 수 있다.",
    ])

    doc.add_heading("16. 핵심 용어 정리", level=1)
    add_table(doc, ["용어", "뜻"], [
        ("임베딩", "이미지·텍스트의 의미를 나타내는 숫자 벡터"),
        ("멀티모달", "이미지와 텍스트처럼 서로 다른 형식을 함께 처리하는 방식"),
        ("코사인 유사도", "두 벡터 방향이 얼마나 비슷한지 나타내는 값"),
        ("Top-K", "유사도가 높은 결과 K개"),
        ("Vector DB", "벡터를 저장하고 유사한 벡터를 검색하는 시스템"),
        ("FAISS", "Meta가 공개한 벡터 유사도 검색 라이브러리"),
        ("Swagger", "브라우저에서 API 명세를 보고 직접 호출하는 화면"),
        ("JSONL", "한 줄에 JSON 객체 하나를 저장하는 파일 형식"),
    ], [2200, 7160])

    add_callout(doc, "학습 완료 기준", "코드를 외우는 것이 아니라 '요청 → 임베딩 → FAISS → 필터 → 응답' 흐름을 자신의 말로 설명하고, 작은 기능 하나를 테스트와 함께 수정할 수 있으면 된다.", LIGHT_BLUE)

    doc.core_properties.title = "판타지 무기 검색 백엔드·Vector DB 학습 가이드"
    doc.core_properties.subject = "FastAPI, OpenCLIP, FAISS 기반 3번 파트 학습 자료"
    doc.core_properties.author = "Fantasy Weapon Search Team"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


# [실행 차단] 위 docstring의 갱신 목록을 처리하기 전에는 문서를 만들지 않는다.
# 되살리려면 아래 두 줄의 주석을 풀면 된다.
# if __name__ == "__main__":
#     build()
