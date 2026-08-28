// AI CAPTCHA — challenge client logic (source, readable).
// Build step: scripts/build_js.py obfuscates this into static/js/challenge.js.
// base_path is injected by the template as window.AICAPTCHA_BASE.
const base_path = window.AICAPTCHA_BASE;
const params = new URLSearchParams(window.location.search);
const sessionId = params.get('session');
let endTime = null;
let timerInterval = null;

async function loadPuzzle() {
    const res = await fetch(`${base_path}/api/session/${sessionId}`);
    const data = await res.json();
    if (data.session && data.session.status !== 'active') {
        window.location.href = `${base_path}/results?session=${sessionId}`;
        return;
    }
    const p = data.current_puzzle;
    if (!p) { window.location.href = `${base_path}/results?session=${sessionId}`; return; }
    document.getElementById('progress').innerHTML = `Puzzle <span class="pnum">${p.puzzle_index + 1}/${data.session.total_puzzles}</span>`;
    document.getElementById('question').textContent = p.question;
    document.getElementById('answer').value = '';
    document.getElementById('feedback').textContent = '';
    if (!endTime) {
        // Append 'Z' if the API omitted a tz marker so we always parse as UTC
        // (guards against a stale/cached naive timestamp from an older deploy).
        let started = data.session.started_at;
        if (started && !/[zZ]|[+-]\d\d:\d\d$/.test(started)) started += 'Z';
        endTime = new Date(started).getTime() + data.session.time_limit_total * 1000;
        startTimer();
    }
}

function startTimer() {
    const ring = document.getElementById('timer-ring');
    const tval = document.getElementById('timer');
    const total = (endTime - Date.now()) / 1000;
    timerInterval = setInterval(() => {
        const remaining = Math.max(0, Math.floor((endTime - Date.now()) / 1000));
        const pct = Math.max(0, Math.min(100, (remaining / total) * 100));
        ring.style.setProperty('--p', pct);
        ring.className = 'timer-ring' + (remaining <= 10 ? ' danger' : remaining <= 20 ? ' warn' : '');
        tval.textContent = `${remaining}s`;
        if (remaining <= 0) {
            clearInterval(timerInterval);
            window.location.href = `${base_path}/results?session=${sessionId}`;
        }
    }, 200);
}

document.getElementById('submit').addEventListener('click', async () => {
    const answer = document.getElementById('answer').value;
    const btn = document.getElementById('submit');
    btn.disabled = true; btn.textContent = 'Checking…';
    const res = await fetch(`${base_path}/api/session/${sessionId}/answer`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({answer}),
    });
    const data = await res.json();
    btn.disabled = false; btn.textContent = 'Submit Answer';
    if (data.session_status === 'completed' || data.session_status === 'expired' || data.session_status === 'failed' || data.status === 'expired') {
        window.location.href = `${base_path}/results?session=${sessionId}`;
        return;
    }
    const fb = document.getElementById('feedback');
    fb.textContent = data.correct ? '✅ Correct' : '❌ Wrong';
    fb.className = 'feedback ' + (data.correct ? 'ok' : 'bad');
    if (data.next_puzzle) {
        const totalPuzzles = data.total_puzzles || (data.session ? data.session.total_puzzles : 5);
        document.getElementById('progress').innerHTML = `Puzzle <span class="pnum">${data.next_puzzle.puzzle_index + 1}/${totalPuzzles}</span>`;
        document.getElementById('question').textContent = data.next_puzzle.question;
        document.getElementById('answer').value = '';
        document.getElementById('answer').focus();
    }
});

document.getElementById('answer').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        document.getElementById('submit').click();
    }
});

loadPuzzle();
