# RAG 전처리 평가

10개 문서와 20개 질문으로 고정 글자 수 Baseline과 제목·문단 경계 및 metadata를 사용하는 Improved 전처리를 비교합니다.

```powershell
python evaluation/rag/evaluate.py --pipeline baseline --output evaluation/rag/baseline-results.json
python evaluation/rag/evaluate.py --pipeline improved --output evaluation/rag/improved-results.json
```

지표는 Recall@3, Evidence Hit Rate, Grounded Decision Accuracy, Insufficient Evidence Rejection Rate와 평균 검색 시간을 기록합니다. 이 평가는 작은 합성 한국어 규정 데이터와 lexical overlap 검색을 사용하므로 embedding 모델의 실제 품질이나 운영 성능을 나타내지 않습니다. 결과 파일은 스크립트를 실행해 생성하며 수치를 수동으로 작성하지 않습니다.

## 2026-08-06 실행 결과

| 지표 | Baseline | Improved |
|---|---:|---:|
| Recall@3 | 1.00 | 1.00 |
| Evidence Hit Rate | 1.00 | 1.00 |
| Grounded Decision Accuracy | 0.75 | 1.00 |
| Insufficient Evidence Rejection Rate | 0.00 | 1.00 |

Baseline 실패 5건은 모두 근거가 없어야 하는 질문을 임의 문서와 연결한 false positive였습니다. 대표 사례는 다음과 같습니다.

- `q16` 사내 카페 정책을 회의실·휴가 문서와 잘못 연결
- `q17` 해외 주재원 지원 질문에 score 0 문서를 반환
- `q19` 주차 할인 질문을 회사 장비 문장과 단어 일부가 겹친다는 이유로 연결

Improved 결과는 이 평가셋에서 실패 0건이지만, category가 정확히 주어지고 질문 표현이 문서와 유사한 합성 데이터라는 강한 조건이 있습니다. 따라서 실제 RAG 정확도 향상 수치로 일반화할 수 없습니다. 검색 latency는 실행마다 달라지며 JSON 결과 파일에 원 측정값을 보존합니다.
