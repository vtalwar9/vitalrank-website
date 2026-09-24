// ViTalRank — shared interactions
(function(){
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

  // Contact form (static demo — shows confirmation, no backend)
  var form = document.getElementById('contact-form');
  if (form) {
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      var note = document.getElementById('form-note');
      if (note) note.style.display = 'block';
      form.querySelectorAll('input,textarea').forEach(function(f){ f.value=''; });
      if (note) note.scrollIntoView({behavior:'smooth', block:'center'});
    });
  }

  // Duplicate marquee/testimonial tracks for seamless loops
  document.querySelectorAll('[data-loop]').forEach(function(track){
    track.innerHTML += track.innerHTML;
  });
})();
