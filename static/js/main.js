// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
  console.log('Turtle Dashboard loaded');

  const refreshBtn = document.querySelector('.refresh-btn');
  refreshBtn.addEventListener('click', handleRefresh);

  // 30초마다 자동 새로고침
  setInterval(handleRefresh, 30000);

  // 마지막 업데이트 시간 표시
  const status = document.querySelector('.status');
  if (status) {
    console.log('상태 정보:', status.textContent);
  }
});

async function handleRefresh() {
  const btn = document.querySelector('.refresh-btn');
  btn.textContent = '새로고침 중…';
  btn.disabled = true;

  try {
    const refreshRes = await fetch('/api/refresh');
    const refreshData = await refreshRes.json();

    if (refreshData.status !== 'success') {
      alert('새로고침 실패: ' + refreshData.message);
      return;
    }

    // API로부터 최신 데이터 가져와 테이블만 갱신
    await updateTables();
    updateTimestamp();

  } catch (err) {
    console.error(err);
    alert('오류가 발생했습니다: ' + err.message);
  } finally {
    btn.textContent = '🔄 새로고침';
    btn.disabled = false;
  }
}

async function updateTables() {
  const res = await fetch('/api/turtle-data');
  const { system1, system2 } = await res.json();

  const render = (selector, stocks) => {
    const tbody = document.querySelector(`${selector} tbody`);
    const noData = document.querySelector(`${selector} .no-data`);

    tbody.innerHTML = '';
    if (!stocks || stocks.length === 0) {
      noData.style.display = 'block';
      return;
    }
    noData.style.display = 'none';

          stocks.forEach(stock => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="stock-code">${stock.code}</td>
          <td class="stock-name">${stock.name}</td>
          <td class="date">${stock.entry_date || '-'}</td>
          <td class="price entry-price">${stock.entry_price != null ? Math.round(stock.entry_price).toLocaleString() : '-'}</td>
          <td class="price">${stock.current != null ? stock.current.toLocaleString() : '-'}</td>
          <td class="price stop-loss">${stock.stop_loss != null ? Math.round(stock.stop_loss).toLocaleString() : '-'}</td>
          <td class="price trailing-stop">${stock.trailing_stop != null ? Math.round(stock.trailing_stop).toLocaleString() : '-'}</td>
          <td class="price add-position">${stock.add_position != null ? Math.round(stock.add_position).toLocaleString() : '-'}</td>
        `;
        tbody.appendChild(tr);
      });
  };

  render('.system1 .stock-table', system1);
  render('.system2 .stock-table', system2);
}

function updateTimestamp() {
  const el = document.querySelector('.last-updated');
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  el.textContent = `마지막 업데이트: ${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ` +
                   `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

// 수동 업데이트 함수
function manualUpdate() {
    fetch('/api/manual-update', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            window.location.reload();
        })
        .catch(error => {
            alert('업데이트 실패: ' + error);
        });
}

// 5분마다 자동 새로고침
setInterval(() => {
    window.location.reload();
}, 5 * 60 * 1000);
