const statusEl = document.querySelector('#status');
const warningsEl = document.querySelector('#warnings');
const postsEl = document.querySelector('#posts');
const sourceEl = document.querySelector('#source');

const label = { pinned: 'Pinned post', latest: 'Latest post' };

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

function render(data) {
  const fetched = data.fetchedAt ? new Date(data.fetchedAt).toLocaleString() : 'ยังไม่มีข้อมูล';
  statusEl.innerHTML = `<strong>${escapeHtml(data.runStatus || 'unknown')}</strong><span>อัปเดตล่าสุด: ${escapeHtml(fetched)}</span><span>${data.posts?.length || 0} โพสต์</span>`;
  sourceEl.href = data.source?.pageUrl || '#';
  if (data.warnings?.length) {
    warningsEl.classList.remove('hidden');
    warningsEl.innerHTML = `<strong>คำเตือน</strong><ul>${data.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul>`;
  } else {
    warningsEl.classList.add('hidden');
    warningsEl.innerHTML = '';
  }
  postsEl.innerHTML = (data.posts || []).map((post, index) => `
    <article class="post-card ${post.type === 'pinned' ? 'pinned' : ''}">
      <div class="card-top"><span class="badge">${escapeHtml(post.type === 'pinned' ? label.pinned : `${label.latest} ${index}`)}</span><span class="state ${escapeHtml(post.status)}">${escapeHtml(post.status)}</span></div>
      <h2>${escapeHtml(post.publishedLabel || 'ไม่ทราบเวลา')}</h2>
      <p class="post-text">${escapeHtml(post.text || post.visibleText || 'ไม่พบข้อความ')}</p>
      ${post.postUrl ? `<a class="post-link" target="_blank" rel="noreferrer" href="${escapeHtml(post.postUrl)}">เปิดโพสต์ต้นฉบับ</a>` : ''}
      ${post.warnings?.length ? `<div class="mini-warning">${post.warnings.map(escapeHtml).join(' · ')}</div>` : ''}
    </article>`).join('') || '<div class="empty">ยังไม่มีข้อมูลโพสต์</div>';
}

async function load() {
  statusEl.textContent = 'กำลังโหลดข้อมูล…';
  try {
    const candidates = [`/api/posts.json?ts=${Date.now()}`, `./data/posts.json?ts=${Date.now()}`];
    let response;
    for (const url of candidates) {
      const candidate = await fetch(url, { cache: 'no-store' });
      if (candidate.ok) { response = candidate; break; }
    }
    if (!response) throw new Error('ไม่พบ JSON API หรือไฟล์ข้อมูล');
    render(await response.json());
  } catch (error) {
    statusEl.innerHTML = `<strong>ยังโหลดข้อมูลไม่ได้</strong><span>${escapeHtml(error.message)}</span>`;
    postsEl.innerHTML = '<div class="empty">รัน collector ก่อน แล้วรีเฟรชหน้านี้</div>';
  }
}

document.querySelector('#refresh').addEventListener('click', load);
load();
