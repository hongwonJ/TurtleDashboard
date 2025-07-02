// 터틀 대시보드 메인 JavaScript

document.addEventListener('DOMContentLoaded', () => {
    console.log('🐢 터틀 대시보드 로드 완료');
    
    // 상태 정보 로그
    const status = document.querySelector('.status');
    if (status) {
        console.log('상태:', status.textContent.trim());
    }
});

// 키움 API 데이터 업데이트 함수
function manualUpdate() {
    const btn = document.querySelector('.update-btn-small');
    const originalText = btn.textContent;
    
    // 버튼 상태 변경
    btn.textContent = '⏳ 업데이트 중...';
    btn.disabled = true;
    
    fetch('/api/manual-update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('응답 상태:', response.status);
        
        if (!response.ok) {
            throw new Error(`서버 오류: ${response.status}`);
        }
        
        // 응답 텍스트 먼저 확인
        return response.text();
    })
    .then(text => {
        console.log('응답 텍스트:', text.substring(0, 100));
        
        try {
            // 안전한 JSON 파싱
            const data = JSON.parse(text);
            return data;
        } catch (jsonError) {
            console.error('JSON 파싱 오류:', jsonError);
            console.error('응답 내용:', text);
            throw new Error('서버 응답 형식 오류');
        }
    })
    .then(data => {
        console.log('업데이트 결과:', data);
        
        if (data.status === 'success') {
            if (data.data_status === 'initializing') {
                // 백그라운드 업데이트 시작됨
                btn.textContent = '🔄 Processing...';
                btn.disabled = true;
                
                // 진행 상황 주기적 확인
                checkUpdateProgress(btn, originalText);
            } else {
                // 이미 완료된 상태
                btn.textContent = '✅ 완료!';
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            throw new Error(data.message || '업데이트 실패');
        }
    })
    .catch(error => {
        console.error('업데이트 오류:', error);
        alert(`❌ 업데이트 실패: ${error.message}`);
        
        // 버튼 상태 복원
        btn.textContent = originalText;
        btn.disabled = false;
    });
}

// 진행 상황 확인 함수
function checkUpdateProgress(btn, originalText) {
    let attempts = 0;
    const maxAttempts = 120; // 2분 (1초마다 체크)
    
    const intervalId = setInterval(() => {
        attempts++;
        
        fetch('/api/turtle-data')
            .then(response => response.json())
            .then(data => {
                console.log(`진행 상황 [${attempts}/${maxAttempts}]:`, data.status_message);
                
                if (data.status === 'updated') {
                    // 완료됨
                    clearInterval(intervalId);
                    btn.textContent = '✅ 완료!';
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else if (data.status === 'error') {
                    // 오류 발생
                    clearInterval(intervalId);
                    btn.textContent = originalText;
                    btn.disabled = false;
                    alert('❌ 업데이트 실패 - 서버 로그를 확인하세요');
                } else if (data.status === 'collecting') {
                    // 수집 중
                    btn.textContent = '📊 Collecting data...';
                } else {
                    // 초기화 중
                    btn.textContent = '⚙️ Initializing...';
                }
                
                // 최대 시간 초과
                if (attempts >= maxAttempts) {
                    clearInterval(intervalId);
                    btn.textContent = originalText;
                    btn.disabled = false;
                    alert('⏰ 업데이트 시간 초과 - 페이지를 새로고침 해주세요');
                }
            })
            .catch(error => {
                console.error('진행 상황 확인 오류:', error);
                // 오류가 발생해도 계속 시도
            });
    }, 1000); // 1초마다 확인
}

// 자동 새로고침 제거됨 - 오후 4시 스케줄 업데이트만 사용
