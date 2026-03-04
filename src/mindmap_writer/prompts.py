DETECT_CHAPTERS_PROMPT = """You are analyzing pages from a Korean AICPA exam preparation study material PDF.
This material covers accounting (management/financial), business law, tax procedures, and ethics.
The pages contain a mix of typed text and handwritten Korean annotations.

Your task: Identify which pages begin a NEW chapter.

Look for these indicators of a chapter start:
- "Chapter N." or "제N장" headings
- Large bold titles that differ from the previous chapter
- A clear topic change with a new major heading
- Title pages that introduce a new section

For each chapter you detect, provide:
1. The page number where it starts (using the page numbers shown above each image)
2. The chapter title (in the original language, Korean or English)
3. The chapter number if visible

Respond in this exact JSON format:
```json
[
  {"page": 1, "chapter_number": 1, "title": "Chapter title here"},
  {"page": 15, "chapter_number": 2, "title": "Chapter title here"}
]
```

If a page does not start a new chapter, do not include it.
Only include clear chapter boundaries, not sub-section breaks.

Note: If chapter numbers reset (e.g., a new "Chapter 1" appears after Chapter 4+), this indicates
a new major section (대단원) has started. Still report it as a normal chapter boundary — the
numbering will be handled in post-processing."""

EXTRACT_HEADINGS_PROMPT = """AICPA 시험 대비 학습 자료(관리회계, 재무회계, 경영법, 세법, 윤리 포함)의 챕터 페이지들을 분석합니다.
타이핑된 텍스트와 손글씨 한국어 주석이 혼합되어 있습니다.

목표: 이 챕터의 Level 1 주요 목차(대주제)를 모두 추출하세요.

가이드라인:
- 인쇄된 제목과 손글씨 제목 모두 포함
- 영문 제목은 그대로 유지 (예: "A. Variable costing", "B. Income comparison")
- 한국어 부제/설명이 있으면 함께 표기 (예: "A. Variable costing 변동원가계산")
- 소주제(하위 항목)는 포함하지 마세요
- 자료에 나타나는 순서대로 나열

JSON 배열로 응답:
```json
["A. First heading", "B. Second heading", "C. Third heading"]
```"""

EXTRACT_CONTENT_PROMPT = """AICPA 시험 대비 학습 자료(관리회계, 경영법, 세법, 윤리 등)에서 시험 대비용 상세 내용을 추출합니다.
타이핑된 텍스트, 손글씨 한국어 주석, 도표, 표, 플로차트가 혼합되어 있습니다.

이 챕터의 Level 1 목차:
{headings}

목표: 위 각 목차 아래의 Level 2, Level 3 내용을 빠짐없이 추출하세요.

=== 언어/표기 스타일 ===
- 영문 전문 용어/약어(recognized term 또는 abbreviation)는 영어 먼저, 한국어 설명 바로 뒤
  예: "Variable costing 변동원가계산", "Sole proprietorship 개인사업자", "LLC 유한책임회사"
- 단, 영어 원문이 개념을 풀어쓴 일반 문장(description)이면 한국어로만 작성
  나쁜 예: "So near the maturity that insignificant risk of change in interest rates 만기가 가까워 이자율 변동 위험이 적음"
  좋은 예: "만기가 가까워 이자율 변동 위험이 적음"
- 영문 전문 용어가 조건절("when ~", "if ~")에 묻혀 있으면, 그 영문 용어를 앞으로 꺼낸다
  나쁜 예: "Revenue recognition when right of return exists 반품권 존재 시 수익 인식"
  좋은 예: "right of return 존재 시 Revenue recognition"
- 약어(DM, DL, OH, CPA, LLC 등)는 그대로 사용, 풀어쓰지 말 것
- 한 줄에 하나의 사실/개념만. 문장이 아닌 핵심어 나열 (텔레그래픽 스타일)
  나쁜 예: "변동원가계산은 FOH를 기간비용으로 처리하며 내부 보고 목적으로 사용됩니다"
  좋은 예: "Variable costing 변동원가계산 - FOH → Period cost (내부보고, Not GAAP)"
- 표기 관례:
  "/" : 대안/비교       예) "Variable/Absorption costing", "voluntary/involuntary"
  "→" : 결과/귀결     예) "FOH → Period cost", "생산>판매 → Absorption NI 더 큼"
  "=" : 정의/동치      예) "Partnership at will = life long K"
  "Except)" : 예외     조건·수치는 괄호: "(within 90 days)", "(Max 25%)", "(1/n)"

=== 구조/관계 표현 규칙 ===
- 개념의 하위 유형이나 구성 요소는 한 단계 들여쓰기로 표현
  예: "Product cost 구성" 아래에 "DM", "DL", "OH" 각각 나열
- 비교 대상(vs)은 같은 레벨에 나란히 배치한 뒤, 각각의 세부를 그 아래에
  예: "Variable costing" / "Absorption costing" 나란히 → 각 세부 사항을 하위에
- 비교 구조(X vs Y)에서 양쪽의 속성은 반드시 같은 tab depth에 위치해야 한다
  X의 속성과 Y의 속성이 각각 X, Y 아래 정확히 1단계 더 들여쓰기되어야 함
- 예외/조건은 별도 bullet: "Except) alimony, child support"
- 번호(1., 2., 요건 1, 요건 2, Step 1 등)는 순서가 실질적으로 의미있을 때만 사용
  예) 사용: 절차/프로세스 "Step 1: petition", "Step 2: order for relief"
  예) 사용 안 함: 요건 목록, 특성, 구성요소 → 번호 없이 그냥 bullet으로 나열
- PDF 원문에 번호가 붙어 있어도 절차/프로세스가 아니라면 번호 제거
  나쁜 예: "- 1. Account payable 매입채무", "- 2. Current liability 유동부채의 특성"
  좋은 예: "- Account payable 매입채무", "- Current liability 유동부채의 특성"
- 쉼표로 나열할 항목이 각각 독립적인 개념이면 하위 bullet로 분리
  나쁜 예: "- Identifiable intangible asset 식별 가능 무형자산: Patents, copyrights, trademarks, franchises, licenses"
  좋은 예: "- Identifiable intangible asset 식별 가능 무형자산"
           "\t\t- Patents"
           "\t\t- Copyrights"
           "\t\t- Trademarks"
           "\t\t- Franchises"
           "\t\t- Licenses"
  (단, 짧은 부연설명이나 괄호 안 병기는 유지: "(내부보고, Not GAAP)", "(alimony, child support)")

=== 수식/계산 규칙 ===
- 핵심 수식은 반드시 포함: "수식명: 수식" 형태
  예: "ROA: NI / Avg. Total Assets"
- 수식의 각 구성요소가 무엇인지 간단히 설명
- 계산 시 주의사항이 있으면 반드시 포함
  예: "주의: 분모는 기말 잔액이 아닌 평균 사용", "주의: 세전/세후 구분 필요"
- 단위나 부호 주의사항도 포함

=== 시험 핵심 요소 (반드시 캡처) ===
이 자료는 AICPA 시험 대비용입니다. 아래 유형은 시험에 자주 출제되므로 정확하고 빠짐없이 캡처하세요:

1. 수치/기한/비율 — 정확한 숫자 그대로
   예) "(within 90 days)", "(Max 25%)", "(>= $21,050)", "(5%/month)", "(2/3 vote)"
   주의: 연습문제에만 등장하는 수치(예제 속 "생산량 200,000개", "판매가 $40" 등)는
   일반 규칙인 것처럼 캡처하지 마세요. 법률/규정에 명시된 수치만 캡처하세요.

2. Default rule + override — 원칙과 변경 조건을 반드시 쌍으로
   예) "원칙: 1/n / agreement 있으면 기여도"
   예) "if profit agreement, also loss / if loss agreement, profit is 1/n"

3. Required vs NOT required — 구분 자체가 출제 포인트
   예) "General Partnership: filing NOT required" vs "LLC: must file to secretary of state"

4. Element list 요건 목록 — 하나도 빠짐없이
   예) Negligence: Duty / Breach of duty / Proximate cause / Injury (4개 전부)

5. Priority ranking — 번호와 함께 순서 명시
   예) "0순위 파산행정비용 / 1순위 secured creditor / 2순위 alimony"

6. Defense / Exception — 독립된 bullet 항목으로 분리
   예) "Defense: Negligence 요건 불만족 / GAAS 준수 / Statute of Limitation"

7. 조건별 결과 — 조건마다 결과를 명시
   예) "voluntary: insolvent X, no minimum debt / involuntary: insolvent O, debt >= $21,050"

8. 절차/프로세스 — Step 번호와 함께 순서대로
   예) "Step 1: petition filing / Step 2: order for relief / Step 3: automatic stay"

=== 충실성 규칙 ===
- 페이지에 보이는 내용만 추출. 교재에 없는 내용을 추가하거나 상상하지 마세요
- 손글씨 여백 메모는 시험 포인트일 가능성 높으므로 반드시 포함
- 도표/플로차트는 핵심 관계와 흐름을 bullet으로 설명
- 표는 핵심 데이터와 관계를 추출
- 예제와 그 풀이/설명도 포함

출력 형식 (탭 들여쓰기):
- Level 1 목차
\t- Level 2 세부사항
\t\t- Level 3 하위사항
\t\t\t- Level 4 세부 설명 or 추가 세부 (필요한 경우)
\t\t\t\t- Level 5 세부 설명 or 추가 세부 (필요한 경우)
\t\t- 또 다른 Level 3
\t- 또 다른 Level 2

내용상 계층 관계가 명확할 경우 Level 4~5까지 사용하세요.
빠짐없이 철저하게 추출하세요. 부족한 것보다 많은 것이 낫습니다."""

CHECK_MISSING_PROMPT = """추출된 학습 노트를 원본 페이지와 비교 검토합니다.
아래의 현재 추출된 마크다운을 위에 보이는 페이지 이미지와 대조하세요.

현재 추출된 마크다운:
---
{current_markdown}
---

예상 목차: {headings}

목표: 페이지에 보이지만 마크다운에서 누락된 내용을 찾으세요.

확인 항목:
1. 캡처되지 않은 손글씨 주석 (특히 여백 메모 — 시험 포인트일 가능성 높음)
2. 설명되지 않은 도표/플로차트 내용
3. 포함되지 않은 표 데이터
4. 누락된 수식이나 계산 과정
5. 빠진 예제나 사례
6. 목차 목록에서 충분히 다루지 않은 항목
7. 계산 시 주의사항이나 함정(trap)이 빠졌는지
8. 수치/기한/비율이 부정확하거나 누락된 경우 (예: "within X days", "Max Y%", "$Z 이상")
9. Default rule이 있는데 override 조건이 빠졌거나, 반대로 override만 있고 원칙이 없는 경우
10. "required" / "NOT required" 구분이 누락된 경우
11. Priority 순위가 불완전하거나 번호가 빠진 경우
12. Defense / Exception 항목이 일부 누락된 경우

JSON으로 응답:
```json
{{
  "missing_topics": ["누락 항목 1 설명", "누락 항목 2 설명"],
  "completeness_score": 0.85,
  "notes": "간단한 설명"
}}
```

누락이 없으면: {{"missing_topics": [], "completeness_score": 1.0, "notes": "Complete"}}"""

SUPPLEMENT_PROMPT = """추출된 노트에서 누락된 내용이 발견되었습니다.
위 페이지 이미지를 보고 아래 누락 항목만 추출하세요:

누락 항목:
{missing_topics}

현재 마크다운 (형식 참고 및 이미 추출된 내용 확인용):
---
{current_markdown}
---

=== 언어/표기 스타일 ===
- 영문 전문 용어/약어는 영어 먼저, 한국어 설명 바로 뒤
  예: "Variable costing 변동원가계산"
- 영어가 개념을 풀어쓴 일반 문장(description)이면 한국어로만
  예: "만기가 가까워 이자율 변동 위험이 적음" (영어 원문 버리고 한국어만)
- 영문 전문 용어가 조건절에 묻혀 있으면, 그 용어를 앞으로 꺼낸다
  나쁜 예: "Revenue recognition when right of return exists 반품권 존재 시 수익 인식"
  좋은 예: "right of return 존재 시 Revenue recognition"
- 약어(DM, DL, OH 등)는 그대로 사용
- 한 줄에 하나의 사실. 텔레그래픽 스타일 유지
- 표기 관례: "/" 대안, "→" 귀결, "=" 정의, "Except)" 예외

=== 충실성 규칙 ===
- 페이지에 보이는 내용만 추출. 교재에 없는 내용을 추가하지 마세요
- 수식은 반드시 포함하고, 계산 주의사항도 함께 기재

누락된 내용을 동일한 bullet+tab 형식으로 추출하세요.
각 항목은 가장 적절한 기존 목차 아래에 배치하세요.
보충 내용만 출력하세요."""

FORMAT_MARKDOWN_PROMPT = """학습 노트를 깔끔한 mindmap용 마크다운으로 정리합니다.

챕터: {chapter_title}
예상 목차: {headings}

원본 내용:
---
{raw_content}
---

=== 핵심 구조 규칙 (반드시 준수) ===
1. 첫 줄은 반드시 챕터 제목 1개만 Level 0으로 (탭 없이 "- Chapter N. 제목")
2. 예상 목차의 각 항목은 반드시 챕터 제목 아래 Level 1로 배치 (탭 1개 + "- ")
3. 세부 내용은 Level 2로 배치 (탭 2개 + "- ")
4. 즉, Level 0 항목은 전체에서 오직 1개 (챕터 제목)만 존재해야 함

=== 서식 규칙 ===
1. 모든 줄은 "- "로 시작 (탭 뒤에)
2. 들여쓰기는 탭 문자 사용 (스페이스 아님)
3. 기본 3단계(Level 0~2)를 사용하되, 내용상 계층 관계가 더 명확해지면 Level 3~4까지 사용 가능
   - Level 0 (탭 없음): 챕터 제목 (오직 1개)
   - Level 1 (탭 1개): 주요 목차
   - Level 2 (탭 2개): 세부 내용
   - Level 3 (탭 3개): 하위 세부 사항 (필요 시)
   - Level 4 (탭 4개): 최하위 세부 사항 (필요 시)
4. 항목 사이에 빈 줄 없음
5. 다른 마크다운 서식 사용 금지 (##, **, 숫자만 있는 줄 금지)

=== 언어/표기 스타일 ===
- 영문 전문 용어/약어(recognized term 또는 abbreviation)는 영어 먼저, 한국어 설명 바로 뒤
  예: "Variable costing 변동원가계산", "General Partnership 등록된 동업", "LLC 유한책임회사"
- 단, 영어 원문이 개념을 풀어쓴 일반 문장(description)이면 한국어로만 작성
  나쁜 예: "So near the maturity that insignificant risk of change in interest rates 만기가 가까워 이자율 변동 위험이 적음"
  좋은 예: "만기가 가까워 이자율 변동 위험이 적음"
- 약어(DM, DL, OH, LLC, CPA 등)는 그대로 사용
- 한 줄에 하나의 사실/개념. 문장이 아닌 핵심어 나열 (텔레그래픽 스타일)
- 표기 관례:
  "/" : 대안/비교       예) "Variable/Absorption costing", "voluntary/involuntary"
  "→" : 결과/귀결     예) "FOH → Period cost"
  "=" : 정의/동치      예) "Partnership at will = life long K"
  "Except)" : 예외     조건·수치는 괄호: "(within 90 days)", "(Max 25%)"

=== 내용 규칙 ===
- 원본 내용을 정확히 반영. 없는 내용을 추가하지 마세요
- 수식은 "수식명: 수식" 형태로 유지
- 주의사항은 "주의:" 접두사
- 비교 대상은 같은 레벨에 나란히, 각 세부는 하위에
- 비교 구조(X vs Y)에서 X의 속성과 Y의 속성은 반드시 같은 tab depth에 위치
  X의 속성과 Y의 속성이 각각 X, Y 아래 정확히 1단계 더 들여쓰기되어야 함
- 예외/조건은 별도 bullet: "Except) alimony, child support"
- 번호(1., 2., 요건 1, Step 1 등)는 순서가 실질적으로 의미있을 때만 사용
  순서 무관한 목록(요건, 특성, 구성요소 등)은 번호 없이 bullet으로만 나열
- PDF 원문에 번호가 붙어 있어도 절차/프로세스가 아니라면 번호 제거
  나쁜 예: "- 1. Account payable 매입채무", "- 2. Current liability 유동부채의 특성"
  좋은 예: "- Account payable 매입채무", "- Current liability 유동부채의 특성"
- 쉼표로 나열된 항목이 각각 독립적인 개념이면 하위 bullet로 분리
  나쁜 예: "- Identifiable intangible asset 식별 가능 무형자산: Patents, copyrights, trademarks, franchises, licenses"
  좋은 예: "- Identifiable intangible asset 식별 가능 무형자산"
           "\t\t- Patents"
           "\t\t- Copyrights"
           "\t\t- Trademarks"
           "\t\t- Franchises"
           "\t\t- Licenses"
  (단, 괄호 안 짧은 병기는 유지: "(내부보고, Not GAAP)", "(alimony, child support)")
- 시험 핵심 정보는 절대 생략/압축 금지:
  수치·기한·비율 / Default rule과 override 쌍 / required vs NOT required 구분
  Priority 순위 번호 / Defense·Exception 항목 / 조건별 결과 / 절차 Step 번호

예시 (Level 0은 챕터 제목 1개만, 필요 시 Level 3~4 사용):
- Chapter 3. Cost Reporting 원가보고
\t- A. Variable costing 변동원가계산 vs Absorption costing 전부원가계산
\t\t- Variable costing 변동원가계산
\t\t\t- FOH → Period cost (내부보고, Not GAAP)
\t\t\t- IS: 매출 - 변동원가 = CM - 고정원가 = NI
\t\t- Absorption costing 전부원가계산
\t\t\t- FOH → Product cost (외부보고, GAAP)
\t\t\t- IS: 매출 - CGS = Gross margin - S&A = NI
\t\t- Income diff: OI_A - OI_V = (생산 - 판매) × 단위당 FOH
\t\t\t- 생산 > 판매 → Absorption NI 더 큼 (FOH 재고에 이연)
\t\t\t- 생산 = 판매 → NI 동일
\t\t\t- 생산 < 판매 → Variable NI 더 큼
\t- B. Income comparison 이익 비교
\t\t- Inventory 증가 → Absorption NI 증가
\t\t- Inventory 감소 → Variable NI 증가
\t\t\t- Except) 생산=판매 시 동일

정리된 마크다운만 출력하세요. 설명 없이."""

REVIEW_STRUCTURE_PROMPT = """다음은 AICPA 시험 자료를 bullet+tab 마크다운으로 정리한 챕터 내용입니다.
내용을 읽고, 탭 들여쓰기 관계가 의미적으로 올바른지 검토한 뒤 오류를 수정하세요.

챕터: {chapter_title}

L1 목차 (구조 기준점):
{headings}

---
{content}
---

=== 검토 기준 ===

탭 관계 규칙:
- 어떤 개념의 세부 속성·유형·구성요소는 반드시 그 개념보다 탭 1개 더 들여쓰기
- 같은 계층 관계인 항목들은 동일한 탭 수를 가져야 한다
- 비교 구조(X vs Y)에서: X와 Y는 같은 탭, X의 속성들과 Y의 속성들도 각각 동일한 탭
- 들여쓰기는 한 번에 1단계씩만 증가 (한 번에 2단계 이상 점프 금지)

흔한 오류 패턴:
- X vs Y 비교에서 X의 속성들이 X와 같은 탭(형제)인데 Y의 속성들은 Y 아래(자식)인 경우
  → X의 속성들도 X 아래 자식으로 수정
- 개념 헤더(예: "Operational plan = Tactical plan")와 그 속성들이 같은 탭인 경우
  → 속성들은 헤더보다 탭 1개 더 들여쓰기
- 동일 계층의 개념(예: A, B, C 항목들)이 서로 다른 탭 수를 가진 경우
  → 같은 탭으로 통일

=== 수정 규칙 ===
- 탭 수만 조정. 텍스트 내용은 절대 변경 금지
- 줄을 추가하거나 삭제하지 말 것
- 구조가 이미 올바르면 원본 그대로 출력

수정된 마크다운만 출력하세요. 설명 없이."""
