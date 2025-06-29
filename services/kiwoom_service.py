# services/kiwoom_service.py

import json
import logging
import asyncio
import time
import websockets
import requests

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

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
        if force_refresh or not self.access_token or datetime.now() >= (self.token_expires_at or datetime.min):
            headers = {"Content-Type": "application/json;charset=UTF-8"}
            body = {
                "grant_type": "client_credentials",
                "appkey":    self.app_key,
                "secretkey": self.app_secret
            }
            try:
                resp = requests.post(token_url, headers=headers, json=body, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                self.access_token   = data.get("token", "")
                self.token_expires_at = datetime.now() + timedelta(hours=23)
            except Exception as e:
                logger.error(f"토큰 발급 실패: {e}")
                self.access_token = ""
                self.token_expires_at = None
        return self.access_token

    def get_ws_headers(self) -> Dict[str, str]:
        token = self.get_access_token()
        headers: Dict[str, str] = {
            "appkey":    self.app_key,
            "secretkey": self.app_secret
        }
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
                        logger.error("로그인 응답 타임아웃")
                        return []
                    except json.JSONDecodeError:
                        logger.warning(f"JSON 파싱 실패: {raw}")
                        continue
                        
                    if msg.get("trnm") == "PING":
                        await ws.send(raw)
                        continue
                    if msg.get("trnm") == "LOGIN":
                        if msg.get("return_code") != 0:
                            logger.error(f"로그인 실패: {msg.get('return_msg')}")
                            return []
                        logger.info("로그인 성공")
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
                        logger.warning("조건검색 목록 응답 대기 중...")
                        continue
                    except json.JSONDecodeError:
                        logger.warning(f"JSON 파싱 실패: {raw}")
                        continue
                        
                    if msg.get("trnm") == "PING":
                        await ws.send(raw)
                        continue
                    if msg.get("trnm") == "CNSRLST":
                        if msg.get("return_code") != 0:
                            logger.error(f"조건식 목록 조회 실패: {msg.get('return_msg')}")
                            return []
                        data_list = msg.get("data", [])
                        results = [{"seq": int(item[0]), "name": item[1]} for item in data_list]
                        logger.info(f"조건검색 목록 조회 성공: {len(results)}개")
                        return results

                logger.error("조건식 목록 조회 타임아웃")
                return []

        except Exception as e:
            logger.error(f"get_condition_list 오류: {e}")
            return []

    async def request_condition(self, seq: str) -> List[Dict[str, str]]:
        """
        조건검색 요청 (search_type=0 한 번만, 페이징 포함)
        """
        url        = self.wss_url
        login_msg  = {"trnm": "LOGIN", "token": self.get_access_token()}
        all_results: List[Dict[str, str]] = []
        cont_yn    = "N"
        next_key   = ""
        page_num   = 1

        try:
            async with websockets.connect(url, extra_headers=self.get_ws_headers()) as ws:
                # 로그인
                await ws.send(json.dumps(login_msg))
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        msg = json.loads(raw)
                    except asyncio.TimeoutError:
                        logger.error("로그인 응답 타임아웃")
                        return []
                    except json.JSONDecodeError:
                        logger.warning(f"JSON 파싱 실패: {raw}")
                        continue
                        
                    logger.info(f"로그인 단계 응답: {msg.get('trnm')}")
                    if msg.get("trnm") == "PING":
                        await ws.send(raw)
                        continue
                    if msg.get("trnm") == "LOGIN":
                        if msg.get("return_code") != 0:
                            logger.error(f"WebSocket LOGIN failed: {msg.get('return_msg')}")
                            return []
                        logger.info("로그인 성공")
                        break

                # 페이징으로 조회
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

                            # 다음 페이지 여부
                            if msg.get("cont_yn") == "Y" and msg.get("next_key"):
                                cont_yn  = "Y"
                                next_key = msg.get("next_key")
                                page_num += 1
                                page_received = True
                                break
                            else:
                                logger.info(f"모든 페이지 완료 - 총 {len(all_results)}개")
                                return all_results
                        else:
                            logger.info(f"다른 메시지 수신: {trnm}")

                    # 페이지 타임아웃 체크
                    if not page_received:
                        logger.error(f"페이지 {page_num} 타임아웃 (30초)")
                        return all_results

        except Exception as e:
            logger.error(f"request_condition 오류: {e}")
            return all_results
        

    def get_daily_candles(self,
                          stk_cd: str,
                          count: int = 60,
                          upd_stkpc_tp: str = "1",
                          base_dt: Optional[str] = None) -> pd.DataFrame:
        """
        Fetches up to `count` days of daily candle data for a given stock code.
        Uses REST API TR `stk_dt_pole_chart_qry` with paging (cont-yn / next-key).

        :param stk_cd: 종목코드 (e.g. '039490')
        :param count: 최대 조회일수
        :param upd_stkpc_tp: 수정주가구분 (0: 원본, 1: 수정)
        :param base_dt: 기준일자 (YYYYMMDD), default: today
        :return: pandas.DataFrame with columns [date, open, high, low, close, volume]
        """
        # Endpoint path for daily candle TR; adjust if needed
        endpoint_path = getattr(Config, 'KIWOOM_DAILY_CANDLE_PATH', '/daily-candle')
        url = f"{self.base_url}{endpoint_path}"

        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'api-id': 'stk_dt_pole_chart_qry',
            'appkey': self.app_key,
            'secretkey': self.app_secret
        }
        # Include auth token
        token = self.get_access_token()
        if token:
            headers['Authorization'] = f"Bearer {token}"

        cont_yn = None
        next_key = None
        all_data: List[Dict[str, Any]] = []

        # Default base_dt to today if not provided
        if not base_dt:
            base_dt = datetime.now().strftime('%Y%m%d')

        while True:
            # Set paging headers if available
            if cont_yn:
                headers['cont-yn'] = cont_yn
                headers['next-key'] = next_key or ''

            body = {
                'stk_cd': stk_cd,
                'base_dt': base_dt,
                'upd_stkpc_tp': upd_stkpc_tp
            }

            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()

            # Parse paging info
            cont_yn = resp.headers.get('cont-yn')
            next_key = resp.headers.get('next-key')

            # Parse body data
            data = resp.json().get('stk_dt_pole_chart_qry', [])
            all_data.extend(data)

            # Stop if no more pages or enough data
            if cont_yn != 'Y' or len(all_data) >= count:
                break

        # Trim to requested count
        sliced = all_data[:count]
        df = pd.DataFrame(sliced)
        if df.empty:
            return df

        # Rename and convert columns
        df = df.rename(columns={
            'dt': 'date',
            'open_pric': 'open',
            'high_pric': 'high',
            'low_pric': 'low',
            'cur_prc': 'close',
            'trde_qty': 'volume'
        })
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        return df
