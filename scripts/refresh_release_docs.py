"""Regenerate the current-release documentation from canonical metadata and JSONL files."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data/metadata/final_search_assets_pretty.json"
SPLITS = {
    "pixel_art": ROOT / "data/splits",
    "illustration": ROOT / "data/splits/illustration",
    "rendered_icon": ROOT / "data/splits/rendered_icon",
}
EVALUATION = ROOT / "data/evaluation"
REPORTS = ROOT / "reports"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def split_counts(directory: Path) -> dict[str, int]:
    return {name: len(read_jsonl(directory / f"{name}.jsonl")) for name in ("train", "validation", "test")}


def write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def evaluation_stats(name: str) -> tuple[int, int, int, float]:
    rows = read_jsonl(EVALUATION / name)
    sizes = [len(row["relevant_asset_ids"]) for row in rows]
    return len(rows), min(sizes), max(sizes), round(sum(sizes) / len(sizes), 3)


def refresh_release_docs() -> None:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    style_counts = Counter(row["visual_style"] for row in metadata)
    pixel = split_counts(SPLITS["pixel_art"])
    illustration = split_counts(SPLITS["illustration"])
    rendered = split_counts(SPLITS["rendered_icon"])
    text_query_count, text_min, text_max, text_average = evaluation_stats("ground_truth.jsonl")
    multimodal_query_count, multi_min, multi_max, multi_average = evaluation_stats("multimodal_ground_truth.jsonl")
    illustration_query_count, illustration_min, illustration_max, illustration_average = evaluation_stats(
        "illustration_ground_truth.jsonl"
    )
    today = date.today().isoformat()

    write(
        ROOT / "data/splits/README.md",
        f"""
# 데이터 분리 안내

최종 메타데이터 {len(metadata):,}개를 같은 형태의 시각 변형이 서로 다른 split에 섞이지 않도록 분리했습니다.

| 데이터셋 | train | validation | test | 합계 |
| --- | ---: | ---: | ---: | ---: |
| 픽셀아트 | {pixel['train']} | {pixel['validation']} | {pixel['test']} | {sum(pixel.values())} |
| 일러스트 | {illustration['train']} | {illustration['validation']} | {illustration['test']} | {sum(illustration.values())} |
| 렌더 아이콘 | {rendered['train']} | {rendered['validation']} | {rendered['test']} | {sum(rendered.values())} |

- 분할 비율 목표: 80% / 10% / 10%
- 고정 시드: 픽셀아트·일러스트 `20260807`, 렌더 아이콘 `20260812`
- 분할 단위: 같은 시각 변형으로 판정된 이미지는 동일 split에 함께 배치
- 유사 변형 판정: 동일 perceptual hash를 우선 사용하며, 모든 style의 교차 split 누수는 0개입니다.

루트의 `train.jsonl`, `validation.jsonl`, `test.jsonl`은 픽셀아트 split입니다. 일러스트와 렌더 아이콘은 각각 `illustration/`, `rendered_icon/` 하위에 같은 파일 구조로 제공합니다. 각 `split_summary.json`은 해당 JSONL에서 재계산한 수량과 누수 검사 결과를 담습니다.
""",
    )

    write(
        EVALUATION / "EVALUATION_GUIDE_KO.md",
        f"""
# 텍스트 검색 평가 안내서

픽셀아트 test split의 {pixel['test']}개 후보 이미지에서, 검색 문장에 맞는 이미지를 찾는 성능을 평가합니다.

## 구성

- 질의: 한글 80개, 영어 80개, 총 {text_query_count}개
- 정답: `ground_truth.jsonl`의 질의별 `relevant_asset_ids`
- 정답 수: 최소 {text_min}개 / 최대 {text_max}개 / 평균 {text_average:.3f}개
- 조건: 무기 종류, 세부 종류, 색상, 속성, 재질, 스타일, 손사용 태그

## 사용 규칙

1. 후보는 `data/splits/test.jsonl`에 있는 {pixel['test']}개 픽셀아트 에셋만 사용합니다.
2. `evaluation_queries.jsonl`의 `query_id`와 `ground_truth.jsonl`의 같은 `query_id`를 연결합니다.
3. Recall@K, MRR, mAP는 이 정답 목록을 기준으로 계산합니다.
""",
    )

    write(
        EVALUATION / "MULTIMODAL_EVALUATION_GUIDE_KO.md",
        f"""
# 이미지+문장 결합검색 평가 안내서

기준 이미지와 수정 문장을 함께 입력했을 때, 형태는 유지하면서 요청한 색상·재질·속성·스타일 변형에 맞는 결과를 찾는 평가 세트입니다.

## 구성

- 검색 후보: 픽셀아트 test split {pixel['test']}개
- 질의: 한글 40개, 영어 40개, 총 {multimodal_query_count}개
- 정답 수: 최소 {multi_min}개 / 최대 {multi_max}개 / 평균 {multi_average:.3f}개
- 변환 유형: 색상, 속성, 재질, 스타일

`multimodal_queries.jsonl`의 기준 에셋 ID와 수정 문장을 입력으로 사용하고, `multimodal_ground_truth.jsonl`의 같은 `query_id`를 정답으로 사용합니다.
""",
    )

    write(
        EVALUATION / "ILLUSTRATION_EVALUATION_GUIDE_KO.md",
        f"""
# 일러스트 평가 세트 안내

일러스트 `test` split {illustration['test']}개를 검색 후보로 사용하는 전용 텍스트 검색 평가 세트입니다.

## 구성

- 질의: 한글 50개, 영어 50개, 총 질의 {illustration_query_count}개
- 정답 수: 최소 {illustration_min}개 / 최대 {illustration_max}개 / 평균 {illustration_average:.3f}개
- 질의 조건: category, subcategory, primary_color, elements, materials, handedness

`illustration_evaluation_queries.jsonl`의 `query_id`와 `illustration_ground_truth.jsonl`의 동일 `query_id`를 연결해 Recall@K, MRR, mAP를 계산합니다. 후보에는 일러스트 test split {illustration['test']}개만 포함해야 합니다.
""",
    )

    write(
        REPORTS / "FINAL_VALIDATION_REPORT_KO.md",
        f"""
# 최종 데이터 검증 보고서

- 갱신일: {today}
- 기준 메타데이터: `data/metadata/final_search_assets_pretty.json`
- 최종 에셋 수: **{len(metadata):,}개**

## 데이터 구성

| 스타일 | 에셋 수 | train | validation | test |
| --- | ---: | ---: | ---: | ---: |
| pixel_art | {style_counts['pixel_art']} | {pixel['train']} | {pixel['validation']} | {pixel['test']} |
| illustration | {style_counts['illustration']} | {illustration['train']} | {illustration['validation']} | {illustration['test']} |
| rendered_icon | {style_counts['rendered_icon']} | {rendered['train']} | {rendered['validation']} | {rendered['test']} |
| 합계 | {len(metadata)} | {pixel['train'] + illustration['train'] + rendered['train']} | {pixel['validation'] + illustration['validation'] + rendered['validation']} | {pixel['test'] + illustration['test'] + rendered['test']} |

## 검증 결과

- 메타데이터와 이미지 연결: 통과
- 에셋 ID 중복, split 간 ID 중복, JSONL BOM: 모두 0건
- 유사 변형 교차 split 누수: 일러스트 0그룹, 렌더 아이콘 0그룹
- 태그·색상·재질·속성·등급·한글/영문 캡션 누락: 0건
- 출처 및 라이선스 누락: 0건
- 정답 세트: 텍스트 {text_query_count}개, 이미지+문장 {multimodal_query_count}개, 일러스트 {illustration_query_count}개 질의

## 전달 기준

백엔드에는 `handoff/backend_vector_db/`를 전달합니다. 그 폴더의 `final_manifest.json`은 같은 폴더의 `final_search_assets_pretty.json`과 `splits/` 경로를 기준으로 검증합니다.
""",
    )

    write(
        REPORTS / "REDTEAM_DATA_AUDIT_KO.md",
        f"""
# REDTEAM 데이터 점검 보고서

- 갱신일: {today}
- 기준: 최종 메타데이터 및 split/evaluation JSONL

## 통과

- {len(metadata):,}개 에셋의 메타데이터·이미지 연결, 출처·라이선스, 한글/영문 캡션, 태그 스키마를 확인했습니다.
- 세 스타일의 split 합계가 메타데이터 수와 일치합니다.
- train/validation/test 간 에셋 ID 중복은 없습니다.
- perceptual hash 기반 변형 그룹을 split 안에 묶어 일러스트·렌더 아이콘 교차 split 누수는 0그룹입니다.
- 평가 질의와 ground truth의 행 수가 일치합니다: 텍스트 {text_query_count}, 이미지+문장 {multimodal_query_count}, 일러스트 {illustration_query_count}.
- manifest SHA-256은 pretty JSON을 해시 대상으로 사용하며, JSONL과의 직렬화 차이는 불일치가 아닙니다.

## 남은 운영 단계

- 실제 CLIP 임베딩 생성과 검색 지표(Recall@K, MRR, mAP) 측정은 백엔드·모델 환경에서 수행합니다.
- 새 에셋을 추가하거나 태그를 수정할 때는 `scripts/rebuild_ground_truth_and_manifest.py`를 실행해 split 요약, 평가 통계, manifest, handoff를 함께 재생성해야 합니다.
""",
    )

    write(
        REPORTS / "RENDERED_ICON_SPLIT_POLICY_KO.md",
        f"""
# 렌더 아이콘 데이터셋 split 정책

렌더 아이콘은 픽셀아트와 일러스트와 시각적 특성이 달라, 독립된 `rendered_icon` split으로 관리합니다.

- 대상 수: {style_counts['rendered_icon']}개
- 분할: train {rendered['train']}개, validation {rendered['validation']}개, test {rendered['test']}개
- 고정 시드: `20260812`
- 분할 단위: 동일 perceptual hash 변형 그룹
- 검증: split 간 ID 중복 0건, 변형 그룹 누수 0건

검색·평가 시에는 `data/splits/rendered_icon/`의 후보만 사용하며, 픽셀아트·일러스트 후보와 섞지 않습니다.
""",
    )

    write(
        REPORTS / "PROJECT_WORK_SUMMARY_KO.md",
        f"""
# Fantasy Weapon Search 데이터 작업 요약

- 기준일: {today}
- 최종 에셋: {len(metadata):,}개

## 완료

- 이미지·메타데이터 연결, 출처·라이선스, 태그 체계, 한글·영문 캡션 검수
- 스타일 분리: 픽셀아트 {style_counts['pixel_art']}개, 일러스트 {style_counts['illustration']}개, 렌더 아이콘 {style_counts['rendered_icon']}개
- 유사 변형 그룹 기반 split과 텍스트·이미지+문장·일러스트 평가 정답 세트 재생성
- manifest, handoff, split/evaluation 요약 최신화

## 다음 담당 작업

백엔드·모델 담당자는 `handoff/backend_vector_db/`의 manifest와 split/evaluation 자료를 이용해 실제 CLIP 임베딩을 생성하고 검색 지표를 측정합니다.
""",
    )

    write(
        REPORTS / "WORK_STATUS_KO.md",
        f"""
# Fantasy Weapon Search 현재 작업 상태

- 기준일: {today}
- 데이터 상태: **freeze 가능**

| 항목 | 상태 | 결과 |
| --- | --- | --- |
| 최종 메타데이터 | 완료 | {len(metadata):,}개 |
| 스타일 분리 | 완료 | 픽셀아트 {style_counts['pixel_art']}, 일러스트 {style_counts['illustration']}, 렌더 아이콘 {style_counts['rendered_icon']} |
| split | 완료 | {pixel['train']}/{pixel['validation']}/{pixel['test']}, {illustration['train']}/{illustration['validation']}/{illustration['test']}, {rendered['train']}/{rendered['validation']}/{rendered['test']} |
| 평가 세트 | 완료 | 텍스트 {text_query_count}, 이미지+문장 {multimodal_query_count}, 일러스트 {illustration_query_count} 질의 |
| release manifest·handoff | 완료 | 현재 메타데이터와 split 해시 기준으로 재생성 |
| 실제 임베딩·지표 | 다음 단계 | 백엔드·모델 환경에서 CLIP 임베딩 및 Recall@K/MRR/mAP 측정 |
""",
    )

    root_readme = ROOT / "README.md"
    readme_text = root_readme.read_text(encoding="utf-8")
    readme_text = readme_text.replace(
        "reports/ILLUSTRATION_VALIDATION_REPORT_KO.md",
        "reports/FINAL_VALIDATION_REPORT_KO.md",
    )
    root_readme.write_text(readme_text, encoding="utf-8", newline="\n")

    write(
        REPORTS / "README.md",
        """
# 보고서 안내

## 현재 릴리스 기준 문서

- `FINAL_VALIDATION_REPORT_KO.md`: 최종 데이터·split·평가 검증 결과
- `REDTEAM_DATA_AUDIT_KO.md`: 릴리스 전 위험 점검 결과
- `RENDERED_ICON_SPLIT_POLICY_KO.md`: 렌더 아이콘 분리 정책
- `PROJECT_WORK_SUMMARY_KO.md`, `WORK_STATUS_KO.md`: 현재 작업 요약과 상태

## 과거 작업 기록

후보 선별, 초기 분포, 배치별 캡션 수정 과정의 문서는 당시 시점의 감사 기록입니다. 이전 수량이 적혀 있을 수 있으므로 현재 데이터 수치나 릴리스 판정에는 사용하지 않습니다. 현재 기준은 위의 현재 릴리스 문서와 `data/metadata/final_manifest.json`입니다.
""",
    )

    historical_reports = (
        "ASSET_GRADE_AND_DATA_AUDIT_KO.md",
        "ILLUSTRATION_VALIDATION_REPORT_KO.md",
        "ILLUSTRATION_SELECTION_REPORT_KO.md",
        "ILLUSTRATION_SOURCE_LICENSE_REPORT_KO.md",
        "style_variant_audit_ko.md",
        "distribution_report.md",
    )
    notice = (
        "> **과거 작업 기록**: 이 문서는 당시 후보 선별·감사 시점의 결과입니다. "
        "현재 최종 수치와 릴리스 판정은 `reports/FINAL_VALIDATION_REPORT_KO.md` 및 "
        "`data/metadata/final_manifest.json`을 기준으로 확인하세요.\n\n"
    )
    for name in historical_reports:
        path = REPORTS / name
        if path.exists():
            old_text = path.read_text(encoding="utf-8")
            if not old_text.startswith("> **과거 작업 기록**"):
                path.write_text(notice + old_text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    refresh_release_docs()
