(() => {
  'use strict';
  const box = document.querySelector('#exhibit .case-box');
  const video = document.querySelector('#cli-film');
  if (!box || !video) return;
  box.classList.add('cs-studio');
  const frame = box.querySelector('.film-frame');
  const heading = document.createElement('div');
  heading.className = 'cs-media-heading';
  heading.innerHTML = '<span>AI OPERATION RECORD / 2026.10.21</span><span><i></i>脱敏操作片段</span>';
  frame.before(heading);
  const cover = document.createElement('div');
  cover.className = 'cs-player-cover';
  cover.innerHTML = '<button type="button" aria-label="播放当前招聘操作实录"><span aria-hidden="true">▶</span>播放这段实录</button>';
  frame.append(cover);
  cover.querySelector('button').addEventListener('click',() => document.querySelector('#play-clip').click());
  const playback = document.createElement('div');
  playback.className = 'cs-playback';
  playback.innerHTML = '<span>PLAYBACK</span><progress value="0" max="1" aria-label="当前实录播放进度"></progress><span class="cs-playback-time">00:00 / --:--</span>';
  frame.after(playback);
  const time = number => Number.isFinite(number) ? `${String(Math.floor(number/60)).padStart(2,'0')}:${String(Math.floor(number%60)).padStart(2,'0')}` : '--:--';
  function syncPlayback() {
    cover.hidden = !video.paused && !video.ended;
    const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 1;
    playback.querySelector('progress').max = duration;
    playback.querySelector('progress').value = video.currentTime || 0;
    playback.querySelector('.cs-playback-time').textContent = `${time(video.currentTime)} / ${time(video.duration)}`;
  }
  for (const event of ['play','pause','ended','timeupdate','loadedmetadata','emptied','durationchange']) video.addEventListener(event,syncPlayback);
  box.querySelector('.account-data').append(box.querySelector('.history-account'));
  const scope = document.createElement('div');
  scope.className = 'cs-scope-note';
  scope.innerHTML = '<span aria-hidden="true">↳</span><p><b>每段，单独看结果。</b> 三段来自不同会话，不构成同批转化漏斗。打招呼中的 47 → 48 是累计任务核验；请求发出、附件到达与点击同意接收分别统计。</p>';
  box.append(scope);
  const nav = box.querySelector('.film-nav');
  nav.dataset.ownKeys = 'true';
  function syncStage() {
    nav.querySelectorAll('[data-clip]').forEach(button => { button.tabIndex = button.getAttribute('aria-selected') === 'true' ? 0 : -1; });
    syncPlayback();
  }
  nav.addEventListener('keydown',event => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const buttons = [...nav.querySelectorAll('[data-clip]')];
    const current = buttons.findIndex(button => button.getAttribute('aria-selected')==='true');
    const index = event.key==='Home'?0:event.key==='End'?buttons.length-1:(current+(event.key==='ArrowRight'?1:buttons.length-1))%buttons.length;
    buttons[index].click();buttons[index].focus();
  });
  nav.addEventListener('click',event => {
    if (!event.target.closest('[data-clip]')) return;
    syncStage();
    const panel = box.querySelector('#clip-description');
    panel.classList.remove('cs-change');
    requestAnimationFrame(() => panel.classList.add('cs-change'));
  });
  const sections = [...document.querySelectorAll('.cs-section-nav a')].map(link=>({link,target:document.querySelector(link.getAttribute('href'))})).filter(item=>item.target);
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) sections.forEach(item => item.link.setAttribute('aria-current',item.target===entry.target?'location':'false'));
    },{rootMargin:'-15% 0px -65% 0px'});
    sections.forEach(item=>observer.observe(item.target));
  }
  syncStage();
})();
