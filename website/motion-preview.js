/* Local, progressive UI motion. No recruiting actions or AI services are called. */
(()=>{'use strict';
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let observer,frame=0,heroBound=false;
 function refresh(){
  if(reduced.matches){document.querySelectorAll('.reveal-pending').forEach(el=>el.classList.remove('reveal-pending'));return}
  document.documentElement.classList.add('motion-ready');
  if(!observer&&'IntersectionObserver'in window)observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.remove('reveal-pending');entry.target.classList.add('reveal-visible');observer.unobserve(entry.target)}}),{threshold:.07,rootMargin:'0px 0px 24px 0px'});
  document.querySelectorAll('[data-reveal]:not([data-observed])').forEach((el,i)=>{el.dataset.observed='true';el.style.setProperty('--reveal-delay',Math.min(i%3,2)*70+'ms');if(observer){el.classList.add('reveal-pending');observer.observe(el)}});
  const hero=document.querySelector('.studio-scene');
  if(hero&&!heroBound&&matchMedia('(hover:hover) and (pointer:fine)').matches){heroBound=true;hero.addEventListener('pointermove',e=>{if(reduced.matches)return;const r=hero.getBoundingClientRect();hero.style.setProperty('--art-x',((e.clientX-r.left)/r.width-.5)*7+'px');hero.style.setProperty('--art-y',((e.clientY-r.top)/r.height-.5)*5+'px')});hero.addEventListener('pointerleave',()=>{hero.style.setProperty('--art-x','0px');hero.style.setProperty('--art-y','0px')})}
 }
 document.addEventListener('click',event=>{
  const tab=event.target.closest('[data-work-scene]');
  if(tab){
   const stage=tab.closest('[data-work]'),image=stage.querySelector('.work-scene-image'),video=stage.querySelector('video'),play=stage.querySelector('[data-play-recording]'),scene=stage.querySelector('.work-scene');
   if(tab.getAttribute('aria-pressed')==='true')return;
   stage.querySelectorAll('[data-work-scene]').forEach(b=>b.setAttribute('aria-pressed',String(b===tab)));image.src=tab.dataset.image;image.alt=stage.querySelector('h3').innerText+'：'+tab.innerText;image.hidden=false;
   if(video){video.pause();video.hidden=true;video.src=tab.dataset.video;video.poster=tab.dataset.image;play.hidden=false}
   scene.classList.remove('scene-changing');requestAnimationFrame(()=>scene.classList.add('scene-changing'));return;
  }
  const play=event.target.closest('[data-play-recording]');
  if(play){const stage=play.closest('[data-work]'),video=stage.querySelector('video');document.querySelectorAll('.work-scene-video').forEach(v=>{if(v!==video)v.pause()});play.hidden=true;stage.querySelector('.work-scene-image').hidden=true;video.hidden=false;video.play().catch(()=>{video.hidden=true;play.hidden=false;stage.querySelector('.work-scene-image').hidden=false;const status=document.querySelector('#status');if(status)status.textContent='实录暂未播放，可重试或打开完整案例。'})}
 });
 document.addEventListener('keydown',event=>{const tab=event.target.closest('[data-work-scene]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const tabs=[...tab.parentElement.querySelectorAll('button')],i=tabs.indexOf(tab),next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowLeft'?-1:1)+tabs.length)%tabs.length;tabs[next].focus();tabs[next].click()});
 function setup(){
  const meter=document.createElement('div');meter.className='scroll-meter';meter.setAttribute('aria-hidden','true');meter.innerHTML='<span></span>';document.body.append(meter);
  const top=document.createElement('button');top.className='back-to-top';top.type='button';top.textContent='↑';top.setAttribute('aria-label','回到页面顶部');document.body.append(top);top.addEventListener('click',()=>{window.scrollTo({top:0,behavior:reduced.matches?'instant':'smooth'});const brand=document.querySelector('.site-nav .brand');brand?.focus({preventScroll:true})});
  const update=()=>{const h=document.documentElement.scrollHeight-innerHeight;meter.style.setProperty('--page-progress',h>0?Math.max(0,Math.min(1,scrollY/h)):0);top.classList.toggle('is-visible',scrollY>700);frame=0};
  addEventListener('scroll',()=>{if(!frame)frame=requestAnimationFrame(update)},{passive:true});addEventListener('resize',update,{passive:true});document.addEventListener('portfolio:render',()=>{refresh();update()});reduced.addEventListener('change',refresh);refresh();update();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
 window.IsabellaMotion={refresh};
})();
