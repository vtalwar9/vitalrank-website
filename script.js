// ViTalRank — shared interactions
(function(){
  document.documentElement.classList.add('js');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- cinematic motion pack (site-wide template) ---- */
  if (!reduceMotion) {
    // 1. Masked word reveals on hero H1s, section titles, CTA heading.
    //    Runs before the .reveal observer below so it can take over those nodes.
    //    CMS markers are HTML comments: only text nodes are split, markers survive.
    var maskTargets = document.querySelectorAll('.hero h1, .section-title, .cta-band h2');
    maskTargets.forEach(function(el){
      el.classList.add('mask-split');
      el.classList.remove('reveal');
      Array.prototype.slice.call(el.childNodes).forEach(function(n){
        if (n.nodeType !== 3 || !n.textContent.trim()) return;
        var frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach(function(part){
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(' ')); return; }
          var m = document.createElement('span'); m.className = 'wmask';
          var w = document.createElement('span'); w.className = 'wword'; w.textContent = part;
          m.appendChild(w); frag.appendChild(m);
        });
        el.replaceChild(frag, n);
      });
      var wi = 0;
      el.querySelectorAll('.wword').forEach(function(w){ w.style.animationDelay = (wi++ * 0.06) + 's'; });
    });
    if ('IntersectionObserver' in window) {
      var mio = new IntersectionObserver(function(es){
        es.forEach(function(e){ if (e.isIntersecting){ e.target.classList.add('in'); mio.unobserve(e.target); } });
      }, {threshold: 0.3});
      maskTargets.forEach(function(m){ mio.observe(m); });
    } else {
      maskTargets.forEach(function(m){ m.classList.add('in'); });
    }

    // 2. Particle field injected into every page hero (one lightweight canvas
    //    per hero; pauses off-screen and when the tab is hidden).
    if ('requestAnimationFrame' in window) {
      document.querySelectorAll('.hero').forEach(function(hero){
        var cv = document.createElement('canvas');
        cv.className = 'hero-particles';
        cv.setAttribute('aria-hidden', 'true');
        hero.insertBefore(cv, hero.firstChild);
        var ctx = cv.getContext('2d'), W = 0, H = 0, running = false, mx = -999, my = -999, ps = [];
        var N = window.innerWidth < 640 ? 36 : 64;
        function size(){ var r = hero.getBoundingClientRect(); W = cv.width = Math.max(1, r.width); H = cv.height = Math.max(1, r.height); }
        size();
        window.addEventListener('resize', size);
        for (var i = 0; i < N; i++) ps.push({x: Math.random(), y: Math.random(), r: Math.random()*1.7+0.5, vx: (Math.random()-.5)*.0009, vy: (Math.random()-.5)*.0009, a: Math.random()*.45+.12});
        hero.addEventListener('pointermove', function(e){
          var r = cv.getBoundingClientRect();
          mx = (e.clientX - r.left) / r.width; my = (e.clientY - r.top) / r.height;
        }, {passive: true});
        hero.addEventListener('pointerleave', function(){ mx = -999; my = -999; });
        function frame(){
          if (!running) return;
          ctx.clearRect(0, 0, W, H);
          for (var k = 0; k < ps.length; k++){
            var p = ps[k];
            var dx = p.x - mx, dy = p.y - my, d = Math.sqrt(dx*dx + dy*dy);
            if (d < .12 && d > 0){ p.x += dx/d*.004; p.y += dy/d*.004; }
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0) p.x = 1; if (p.x > 1) p.x = 0;
            if (p.y < 0) p.y = 1; if (p.y > 1) p.y = 0;
            ctx.beginPath(); ctx.arc(p.x*W, p.y*H, p.r, 0, 6.283);
            ctx.fillStyle = 'rgba(140,180,255,' + p.a + ')'; ctx.fill();
          }
          requestAnimationFrame(frame);
        }
        function kick(){ if (!running){ running = true; requestAnimationFrame(frame); } }
        function stop(){ running = false; }
        if ('IntersectionObserver' in window) {
          new IntersectionObserver(function(es){ es[0].isIntersecting ? kick() : stop(); }, {threshold: 0}).observe(hero);
        } else { kick(); }
        document.addEventListener('visibilitychange', function(){ document.hidden ? stop() : kick(); });
      });
    }

    // 3. Count-up on stat values (existing .fc-value content, unchanged claims).
    var counters = document.querySelectorAll('.fc-value');
    function animateCount(el){
      var m = el.textContent.trim().match(/^([^\d]*)(\d+)([\s\S]*)$/);
      if (!m) return;
      var pre = m[1], num = parseInt(m[2], 10), suf = m[3], t0 = null, dur = 1200;
      function tick(t){
        if (!t0) t0 = t;
        var k = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - k, 3);
        el.textContent = pre + Math.round(num * e) + suf;
        if (k < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }
    if (counters.length) {
      if ('IntersectionObserver' in window) {
        var cio = new IntersectionObserver(function(es){
          es.forEach(function(e){ if (e.isIntersecting){ animateCount(e.target); cio.unobserve(e.target); } });
        }, {threshold: 0.5});
        counters.forEach(function(c){ cio.observe(c); });
      } else {
        counters.forEach(animateCount);
      }
    }

    // 4. Magnetic buttons in page heroes (fine pointers only).
    if (window.matchMedia('(pointer:fine)').matches) {
      document.querySelectorAll('.hero .btn').forEach(function(btn){
        btn.addEventListener('pointermove', function(e){
          var r = btn.getBoundingClientRect();
          btn.style.transform = 'translate(' + ((e.clientX - (r.left + r.width/2)) * .22) + 'px,' + ((e.clientY - (r.top + r.height/2)) * .22) + 'px)';
        });
        btn.addEventListener('pointerleave', function(){ btn.style.transform = ''; });
      });
    }
  }

  // Mobile nav
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.main-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function(){ nav.classList.toggle('open'); });
    nav.querySelectorAll('a').forEach(function(a){
      a.addEventListener('click', function(){ nav.classList.remove('open'); });
    });
  }

  // Scroll reveal
  var els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && els.length) {
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); }
      });
    }, {threshold: 0.12});
    els.forEach(function(el){ io.observe(el); });
  } else {
    els.forEach(function(el){ el.classList.add('visible'); });
  }

  // Header shadow on scroll
  var bar = document.querySelector('.header-bar');
  if (bar) {
    var onScroll = function(){
      bar.style.boxShadow = window.scrollY > 40
        ? '0 14px 40px rgba(20,30,60,.14)'
        : '0 10px 34px rgba(20,30,60,.10)';
    };
    window.addEventListener('scroll', onScroll, {passive:true});
    onScroll();
  }

  // Hero background parallax (homepage)
  var heroBg = document.querySelector('.hero-home .hero-bg');
  var hero = document.querySelector('.hero-home');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (heroBg && hero && !reduceMotion && 'requestAnimationFrame' in window) {
    var ticking = false;
    var parallax = function(){
      var y = window.scrollY, h = hero.offsetHeight;
      if (y <= h) heroBg.style.transform = 'scale(1.15) translateY(' + (y * 0.15) + 'px)';
      ticking = false;
    };
    window.addEventListener('scroll', function(){
      if (!ticking) { requestAnimationFrame(parallax); ticking = true; }
    }, {passive:true});
  }

  // Contact form — submits to Netlify Forms (free), shows confirmation
  var form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      var note = document.getElementById('form-note');
      var btn = form.querySelector('button[type="submit"]');
      var data = new FormData(form);
      if (btn) btn.disabled = true;
      fetch('/', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams(data).toString()
      }).then(function(res){
        if (!res.ok) throw new Error('send failed');
        if (note) note.style.display = 'block';
        form.querySelectorAll('input,textarea').forEach(function(f){
          if (f.name !== 'form-name' && f.name !== 'bot-field') f.value = '';
        });
        if (note) note.scrollIntoView({behavior:'smooth', block:'center'});
      }).catch(function(){
        if (note) {
          note.textContent = 'Something went wrong sending your message. Please try again in a moment.';
          note.style.display = 'block';
          note.style.background = '#fdecec';
          note.style.color = '#a33';
        }
      }).finally(function(){
        if (btn) btn.disabled = false;
      });
    });
  }

  // Duplicate marquee/testimonial tracks for seamless loops
  document.querySelectorAll('[data-loop]').forEach(function(track){
    track.innerHTML += track.innerHTML;
  });
})();
