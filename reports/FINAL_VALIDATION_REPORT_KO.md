# 최종 데이터 검증 보고서

- 생성 시각: 2026-08-07T18:03:33+09:00
- 대상 폴더: `D:\Last_Team_Project_Fantasy_Weapon_Search`
- 최종 결과: **통과**
- 오류: 0건
- 경고: 0건

## 핵심 결과

| 검사 대상 | 개수 |
|---|---:|
| 최종 에셋 | 1,113 |
| PNG 이미지 | 1,113 |
| 출처·라이선스 기록 | 1,113 |
| 라이선스 확인 완료 | 1,113 |
| 평가 질의 | 160 |
| 평가 개념 | 80 |

## 데이터 분할

| 항목 | 개수 |
|---|---:|
| `train` | 886 |
| `validation` | 115 |
| `test` | 112 |

## 스타일 분포

| 항목 | 개수 |
|---|---:|
| `dark_fantasy` | 40 |
| `eastern` | 20 |
| `fantasy` | 184 |
| `holy_fantasy` | 52 |
| `medieval` | 801 |
| `modern` | 3 |
| `nature_fantasy` | 13 |

## 사용 방식 분포

| 항목 | 개수 |
|---|---:|
| `not_applicable` | 29 |
| `one_handed` | 829 |
| `two_handed` | 255 |

## 출처 연결 상태

| 항목 | 개수 |
|---|---:|
| `ambiguous_archive` | 161 |
| `manifest_matched` | 952 |

> `ambiguous_archive` 161건은 개별 파일 URL 대신 원본 압축파일 단위로 연결된 항목입니다. 라이선스가 `verified`인지는 별도로 전수 확인했습니다.

## 자동 검사 결과

- ✅ 필수 파일이 모두 존재함 (`required_files`)
- ✅ 전체 에셋 수가 예상값과 일치함 (`asset_count`)
- ✅ asset_id가 모두 고유함 (`unique_asset_ids`)
- ✅ 검색에 필요한 필수 메타데이터가 채워짐 (`required_metadata`)
- ✅ 사람용 JSON과 기본 메타데이터의 개수가 같음 (`pretty_count`)
- ✅ 사람용 JSON에 null 값이 없음 (`pretty_no_nulls`)
- ✅ 사람용 JSON 내용이 기본 메타데이터와 일치함 (`pretty_matches_main`)
- ✅ 한글과 영문 텍스트에 깨진 문자가 없음 (`utf8_text`)
- ✅ handedness 값이 최종 허용 체계에 맞음 (`handedness_values`)
- ✅ 모든 방패가 one_handed로 표시됨 (`shield_handedness`)
- ✅ style 값이 최종 허용 체계에 맞음 (`style_values`)
- ✅ PNG 이미지 수가 메타데이터 수와 일치함 (`image_count`)
- ✅ 모든 processed_file 이미지가 존재함 (`missing_processed_images`)
- ✅ 메타데이터에 없는 고아 이미지가 없음 (`orphan_images`)
- ✅ 동일 SHA-256 이미지가 없음 (`duplicate_hashes`)
- ✅ 중복으로 표시된 잔여 에셋이 없음 (`duplicate_flags`)
- ✅ 출처·라이선스 데이터가 모든 에셋을 덮음 (`source_coverage`)
- ✅ 메타데이터와 출처 원장의 URL·라이선스가 일치함 (`source_consistency`)
- ✅ 모든 라이선스 상태가 verified임 (`licenses_verified`)
- ✅ train/validation/test 개수가 예상값과 일치함 (`split_counts`)
- ✅ split 사이에 같은 asset_id가 겹치지 않음 (`split_overlap`)
- ✅ split 합집합이 전체 에셋과 정확히 일치함 (`split_coverage`)
- ✅ split 메타데이터가 최종 메타데이터와 동기화됨 (`split_metadata_sync`)
- ✅ split_manifest가 실제 split과 일치함 (`split_manifest`)
- ✅ 유사 이미지 그룹이 여러 split에 섞이지 않음 (`similarity_group_leakage`)
- ✅ 평가 질의와 정답 수가 예상값과 일치함 (`evaluation_count`)
- ✅ 평가 query_id가 모두 고유함 (`unique_query_ids`)
- ✅ 모든 평가 질의에 정확히 대응하는 정답이 있음 (`query_ground_truth_match`)
- ✅ 모든 평가 질의에 하나 이상의 정답이 있음 (`nonempty_answers`)
- ✅ 모든 평가 정답이 test split 안에 있음 (`answers_outside_test`)
- ✅ 각 평가 개념에 한·영 질의 쌍과 동일한 정답이 있음 (`bilingual_pairs`)
- ✅ 평가 요약과 결과 템플릿의 질의 수가 최신값임 (`evaluation_metadata`)
- ✅ 평가 질의에 깨진 문자가 없음 (`evaluation_utf8`)

## 의미

이 보고서에서 **통과**는 이미지와 메타데이터의 수가 맞고, 중복과 split 누수가 없으며,
출처·라이선스·style·handedness·평가 정답 세트가 서로 일관된다는 뜻입니다.
검색 모델의 실제 정확도는 아직 실행 전이며, `data/evaluation/evaluation_results_template.json`에
검색 결과를 넣어 별도로 측정해야 합니다.

Git 커밋이나 업로드는 이 검증 과정에 포함하지 않았습니다.
