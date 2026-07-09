# 📡 진주 네트워크 품질 대시보드

진주품질개선팀 내부용 eNodeB Cell KPI 분석 대시보드

## 기능
- LTE / 5G KPI 엑셀 파일 업로드 → 자동 분석
- DL/UL PRB 시간대별 추이
- 동시접속자 수 트렌드
- 불량 시간대 히트맵 (DL PRB 기준, 조정 가능)
- 일자별 주간 트렌드 비교
- SVC / 미지정 국소 구분 분석
- 모바일 반응형

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포
1. GitHub 레포에 push
2. share.streamlit.io 에서 레포 연결
3. Main file: `app.py`

## 지원 파일
- `Access_4G____eNodeB_Cell_KPI_성능이력_xxxx.xlsx`
- LTE 시트 + 5G 시트 포함
