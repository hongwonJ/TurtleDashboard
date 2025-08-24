# services/kiwoom_service.py

import json
import logging
import asyncio
import time
import websockets
import requests
import pandas as pd

from typing import Any, List, Dict, Optional
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

# 디버그 로깅 활성화를 위한 설정
if logger.level == logging.NOTSET:
    logger.setLevel(logging.DEBUG)

class KiwoomAPIService:
    def __init__(self):
        self.app_key       = Config.KIWOOM_APP_KEY
        self.app_secret    = Config.KIWOOM_APP_SECRET
        self.base_url      = Config.KIWOOM_BASE_URL
        self.wss_url       = Config.KIWOOM_WSS_URL + "/api/dostk/websocket"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        # 선발급: 인스턴스 초기화 시 토큰 발급
        try:
            self.get_access_token(force_refresh=True)
            logger.info(f"Access token pre-fetched at init, expires at {self.token_expires_at}.")
        except Exception as e:
            logger.error(f"초기 토큰 발급 실패: {e}")

    def get_access_token(self, force_refresh: bool = False) -> str:
        token_url = f"{self.base_url}/oauth2/token"
        logger.debug(f"토큰 요청 - force_refresh: {force_refresh}, 현재 토큰 존재: {bool(self.access_token)}, 만료시간: {self.token_expires_at}")
        
        if force_refresh or not self.access_token or datetime.now() >= (self.token_expires_at or datetime.min):
            logger.debug(f"새 토큰 발급 시작 - URL: {token_url}")
            headers = {"Content-Type": "application/json;charset=UTF-8"}
            body = {
                "grant_type": "client_credentials",
                "appkey":    self.app_key,
                "secretkey": "***"  # 보안상 마스킹
            }
            logger.debug(f"토큰 요청 헤더: {headers}")
            logger.debug(f"토큰 요청 본문: {body}")
            
            try:
                resp = requests.post(token_url, headers=headers, json={
                    "grant_type": "client_credentials",
                    "appkey":    self.app_key,
                    "secretkey": self.app_secret
                }, timeout=30)
                logger.debug(f"토큰 응답 상태코드: {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                logger.debug(f"토큰 응답 데이터 키: {list(data.keys())}")
                
                self.access_token   = data.get("token", "")
                self.token_expires_at = datetime.now() + timedelta(hours=23)
                logger.info(f"새 토큰 발급 성공 - 만료시간: {self.token_expires_at}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"토큰 발급 네트워크 오류: {e}", exc_info=True)
                self.access_token = ""
                self.token_expires_at = None
            except Exception as e:
                logger.error(f"토큰 발급 실패: {e}", exc_info=True)
                self.access_token = ""
                self.token_expires_at = None
        else:
            logger.debug("기존 토큰 재사용")
            
        return self.access_token

    def get_ws_headers(self) -> Dict[str, str]:
        token = self.get_access_token()
        headers: Dict[str, str] = {
            "appkey":    self.app_key,
            "secretkey": self.app_secret
        }
        if token:
            headers["Authorization"] = f"Bearer {token[:20]}..."  # 토큰 일부만 로깅
            logger.debug(f"WebSocket 헤더 생성 완료 - 토큰 길이: {len(token)}")
        else:
            logger.warning("WebSocket 헤더에 토큰이 없음")
            
        # 실제 헤더에는 전체 토큰 포함
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        return headers

    async def get_condition_list(self) -> List[Dict[str, str]]:
        url       = self.wss_url
        login_msg = {"trnm": "LOGIN", "token": self.get_access_token()}
        list_req  = {"trnm": "CNSRLST"}

        try:
            async with websockets.connect(url, extra_headers=self.get_ws_headers()) as ws:
                # 로그인
                await ws.send(json.dumps(login_msg))
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        msg = json.loads(raw)
                    except asyncio.TimeoutError:
                        logger.error("로그인 응답 타임아웃 (10초)")
                        return []
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 파싱 실패: {e}, 원본 데이터: {raw[:200]}...")
                        continue
                        
                    if msg.get("trnm") == "PING":
                        logger.debug("PING 메시지 수신 및 응답")
                        await ws.send(raw)
                        continue
                    if msg.get("trnm") == "LOGIN":
                        if msg.get("return_code") != 0:
                            logger.error(f"로그인 실패 - 코드: {msg.get('return_code')}, 메시지: {msg.get('return_msg')}")
                            logger.debug(f"전체 로그인 응답: {msg}")
                            return []
                        logger.info("WebSocket 로그인 성공")
                        break

                # 조건검색식 목록 요청
                logger.info("조건검색 목록 요청 전송")
                await ws.send(json.dumps(list_req))
                
                start = time.time()
                while time.time() - start < 30:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw)
                    except asyncio.TimeoutError:
                        logger.debug("조건검색 목록 응답 대기 중... (5초 타임아웃)")
                        continue
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON 파싱 실패: {e}, 데이터: {raw[:200]}...")
                        continue
                        
                    if msg.get("trnm") == "PING":
                        logger.debug("PING 메시지 수신 및 응답")
                        await ws.send(raw)
                        continue
                    if msg.get("trnm") == "CNSRLST":
                        if msg.get("return_code") != 0:
                            logger.error(f"조건식 목록 조회 실패 - 코드: {msg.get('return_code')}, 메시지: {msg.get('return_msg')}")
                            logger.debug(f"전체 CNSRLST 응답: {msg}")
                            return []
                        data_list = msg.get("data", [])
                        logger.debug(f"원본 조건식 데이터: {data_list[:3]}...")  # 처음 3개만 로깅
                        results = [{"seq": int(item[0]), "name": item[1]} for item in data_list]
                        logger.info(f"조건검색 목록 조회 성공: {len(results)}개")
                        logger.debug(f"조건식 목록: {[r['name'] for r in results[:5]]}...")  # 처음 5개 이름만
                        return results

                logger.error("조건식 목록 조회 타임아웃")
                return []

        except Exception as e:
            logger.error(f"get_condition_list 오류: {e}")
            return []

    async def request_condition(self, seq: str) -> List[Dict[str, str]]:
        """조건검색 요청 (재연결 로직 포함)"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"조건검색 seq={seq} 시도 {attempt + 1}/{max_retries}")
                result = await self._request_condition_single(seq)
                if result:  # 성공시 즉시 반환
                    logger.info(f"조건검색 seq={seq} 성공: {len(result)}개")
                    return result
                logger.warning(f"조건검색 seq={seq} 시도 {attempt + 1} 실패, 재시도...")
                await asyncio.sleep(2)  # 2초 대기 후 재시도
            except Exception as e:
                logger.error(f"조건검색 seq={seq} 시도 {attempt + 1} 오류: {e}")
                if attempt == max_retries - 1:  # 마지막 시도
                    logger.error(f"조건검색 seq={seq} 최종 실패")
                    return []
                await asyncio.sleep(2)
        
        return []
    
    async def _request_condition_single(self, seq: str) -> List[Dict[str, str]]:
        """단일 조건검색 요청 (내부 함수)"""
        url        = self.wss_url
        login_msg  = {"trnm": "LOGIN", "token": self.get_access_token()}
        list_req   = {"trnm": "CNSRLST"}
        all_results: List[Dict[str, str]] = []
        cont_yn    = "N"
        next_key   = ""
        page_num   = 1

        # WebSocket 연결 설정 강화
        try:
            async with websockets.connect(
                url, 
                extra_headers=self.get_ws_headers(),
                ping_interval=20,    # 20초마다 ping
                ping_timeout=10,     # ping 응답 10초 대기
                close_timeout=5,     # 연결 종료 5초 대기
                max_size=10**7       # 10MB 최대 메시지 크기
            ) as ws:
                # 1) 로그인
                await ws.send(json.dumps(login_msg))
                # → LOGIN 응답 대기 (기존 코드와 동일)

                # 2) 목록 조회 요청
                await ws.send(json.dumps(list_req))

                # → CNSRLST 응답 대기
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    if msg.get("trnm") == "CNSRLST" and msg.get("return_code") == 0:
                        break
                    elif msg.get("trnm") == "PING":
                        await ws.send(raw)

                # 3) 본격 조건검색 요청 (페이징)
                while True:
                    req = {
                        "trnm":        "CNSRREQ",
                        "seq":         seq,
                        "search_type": "0",
                        "stex_tp":     "K",
                        "cont_yn":     cont_yn,
                        "next_key":    next_key
                    }
                    logger.info(f"페이지 {page_num} 요청 (cont_yn={cont_yn})")
                    await ws.send(json.dumps(req))

                    page_start = time.time()
                    page_received = False
                    
                    while time.time() - page_start < 30:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            msg = json.loads(raw)
                        except asyncio.TimeoutError:
                            logger.warning(f"페이지 {page_num} 응답 대기 중...")
                            continue
                        except json.JSONDecodeError:
                            logger.warning(f"JSON 파싱 실패: {raw}")
                            continue

                        trnm = msg.get("trnm")
                        if trnm == "PING":
                            await ws.send(raw)
                            continue
                        elif trnm == "CNSRREQ":
                            if msg.get("return_code") != 0:
                                logger.error(f"조건검색 실패: {msg.get('return_msg')}")
                                return all_results

                            data_list = msg.get("data", [])
                            page = [
                                {
                                    "code":    d.get("9001"),
                                    "name":    d.get("302"),
                                    "current": d.get("10"),
                                    "sign":    d.get("25"),
                                    "change":  d.get("11"),
                                    "rate":    d.get("12"),
                                    "volume":  d.get("13"),
                                    "open":    d.get("16"),
                                    "high":    d.get("17"),
                                    "low":     d.get("18")
                                }
                                for d in data_list
                            ]
                            all_results.extend(page)
                            logger.info(f"페이지 {page_num}: {len(page)}개 (총 {len(all_results)}개)")

                            # 다음 페이지 여부 확인
                            next_cont_yn = msg.get("cont_yn")
                            next_next_key = msg.get("next_key")
                            logger.debug(f"페이지 {page_num} 완료 - cont_yn: {next_cont_yn}, next_key: {next_next_key}")
                            
                            if next_cont_yn == "Y" and next_next_key:
                                cont_yn  = "Y"
                                next_key = next_next_key
                                page_num += 1
                                page_received = True
                                logger.debug(f"다음 페이지 {page_num} 준비")
                                break
                            else:
                                logger.info(f"모든 페이지 완료 - 총 {len(all_results)}개")
                                return all_results
                        else:
                            logger.debug(f"다른 메시지 수신: {trnm}, 데이터: {str(msg)[:100]}...")

                    # 페이지 타임아웃 체크
                    if not page_received:
                        logger.error(f"페이지 {page_num} 타임아웃 (30초)")
                        return all_results
                
                # 4) 모든 페이지 조회 완료 후 결과 반환
                return all_results
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"_request_condition_single WebSocket 연결 종료: {e}", exc_info=True)
            raise
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"_request_condition_single WebSocket 오류: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"_request_condition_single 예상치 못한 오류: {e}", exc_info=True)
            raise

    def get_daily_candles(self,
                        stk_cd: str,
                        count: int = 60,
                        upd_stkpc_tp: str = "1",
                        base_dt: Optional[str] = None) -> pd.DataFrame:
        """
        주식일봉차트조회 (ka10081)
        
        :param stk_cd: 종목코드 (e.g. '039490')
        :param count: 최대 조회일수
        :param upd_stkpc_tp: 수정주가구분 (0: 원본, 1: 수정)
        :param base_dt: 기준일자 (YYYYMMDD), None이면 당일
        :return: pandas.DataFrame
        """
        # 키움 API 주식일봉차트조회 엔드포인트
        url = f"{self.base_url}/api/dostk/chart"
        
        # 기준일자 설정
        if not base_dt:
            base_dt = datetime.now().strftime('%Y%m%d')
        
        all_data: List[Dict[str, Any]] = []
        cont_yn = None
        next_key = None
        page_num = 1
        
        try:
            logger.info(f"일별 캔들 데이터 조회 시작: {stk_cd}, count={count}, base_dt={base_dt}")
            
            while len(all_data) < count and page_num <= 20:  # 최대 20페이지
                
                # 헤더 설정
                headers = {
                    'Content-Type': 'application/json;charset=UTF-8',
                    'authorization': f"Bearer {self.get_access_token()}",
                    'api-id': 'ka10081'  # 주식일봉차트조회
                }
                
                # 연속조회 헤더 설정
                if cont_yn:
                    headers['cont-yn'] = cont_yn
                if next_key:
                    headers['next-key'] = next_key
                
                # 요청 본문
                body = {
                    'stk_cd': stk_cd,
                    'base_dt': base_dt,
                    'upd_stkpc_tp': upd_stkpc_tp
                }
                
                logger.info(f"페이지 {page_num} 요청 (cont-yn: {cont_yn})")
                
                # POST 요청
                resp = requests.post(url, headers=headers, json=body, timeout=30)
                
                if resp.status_code != 200:
                    logger.error(f"HTTP 오류: {resp.status_code}, {resp.text}")
                    break
                
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON 파싱 실패: {e}")
                    break
                
                # 차트 데이터 추출
                chart_data = data.get('stk_dt_pole_chart_qry', [])
                
                if not chart_data:
                    logger.info("더 이상 차트 데이터가 없습니다.")
                    break
                
                all_data.extend(chart_data)
                logger.info(f"페이지 {page_num}: {len(chart_data)}개 데이터 수신 (총 {len(all_data)}개)")
                
                # 응답 헤더에서 연속조회 정보 확인
                cont_yn = resp.headers.get('cont-yn')
                next_key = resp.headers.get('next-key')
                
                # 연속조회가 필요없거나 충분한 데이터를 얻었으면 종료
                if cont_yn != 'Y' or len(all_data) >= count:
                    logger.info("조회 완료")
                    break
                
                page_num += 1
            
            # 요청한 개수만큼 자르기
            sliced_data = all_data[:count]
            
            if not sliced_data:
                logger.warning("조회된 데이터가 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(sliced_data)
            logger.debug(f"원본 DataFrame 생성 완료 - 모양: {df.shape}, 컬럼: {list(df.columns)}")
            
            # 키움 API 응답 필드명에 맞게 컬럼 매핑
            column_mapping = {
                'dt': 'date',           # 일자
                'open_pric': 'open',    # 시가
                'high_pric': 'high',    # 고가
                'low_pric': 'low',      # 저가
                'cur_prc': 'close',     # 현재가(종가)
                'trde_qty': 'volume'    # 거래량
            }
            
            # 컬럼명 변경
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=available_columns)
            
            df['stock_code'] = stk_cd
            # 필요한 컬럼만 선택
            required_columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume']
            available_required_columns = [col for col in required_columns if col in df.columns]
            df = df[available_required_columns]
            # 데이터 타입 변환
            try:
                # 날짜 변환
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
                    
                # 숫자 컬럼 변환
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                # 날짜 기준 정렬 (최신순)
                if 'date' in df.columns:
                    df = df.sort_values('date', ascending=False).reset_index(drop=True)
                    
            except Exception as e:
                logger.warning(f"데이터 타입 변환 중 오류: {e}")
            
            logger.info(f"일별 캔들 데이터 조회 완료: {len(df)}개")
            logger.info(f"데이터 컬럼: {list(df.columns)}")
            
            # 기본 컬럼이 있는지 확인
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.warning(f"누락된 컬럼: {missing_columns}")
            
            return df
            
        except requests.exceptions.Timeout as e:
            logger.error(f"요청 타임아웃 (30초): {e}", exc_info=True)
            return pd.DataFrame()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"연결 오류: {e}", exc_info=True)
            return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            logger.error(f"네트워크 오류: {e}", exc_info=True)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"일별 캔들 조회 예상치 못한 오류: {e}", exc_info=True)
            return pd.DataFrame()