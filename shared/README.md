# shared (v1.8-0001)

모든 컨테이너(dashboard-api / trader / trainer)가 공통으로 사용하는 Python 패키지 모듈입니다.

- settings: env/config schema
- logging: 공용 로깅
- db: 공용 DB 연결/모델/레포(스켈레톤)
- exchange: Upbit client(auth 포함) 스켈레톤
- telegram: notifier 스켈레톤
