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
    const btn = document.querySelector('.update-btn');
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
    .then(response => response.json())
    .then(data => {
        console.log('업데이트 결과:', data);
        
        if (data.status === 'success') {
            // 성공 메시지 표시
            btn.textContent = '✅ 완료!';
            setTimeout(() => {
                window.location.reload();
            }, 1000);
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

// 5분마다 자동 페이지 새로고침 (새로운 데이터 확인용)
setInterval(() => {
    console.log('🔄 자동 새로고침 (5분 경과)');
    window.location.reload();
}, 5 * 60 * 1000);
