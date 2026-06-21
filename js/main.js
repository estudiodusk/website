// ============================================================
// DUSK ESTÚDIO CRIATIVO — Main JS
// ============================================================

// === Nav scroll effect ===
const nav = document.querySelector('nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  });
}

// === Hamburger menu ===
const burger   = document.getElementById('burger');
const navMob   = document.getElementById('nav-mobile');

if (burger && navMob) {
  burger.addEventListener('click', () => {
    burger.classList.toggle('open');
    navMob.classList.toggle('open');
    document.body.style.overflow = navMob.classList.contains('open') ? 'hidden' : '';
  });

  navMob.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      burger.classList.remove('open');
      navMob.classList.remove('open');
      document.body.style.overflow = '';
    });
  });
}

// === Scroll reveal ===
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.anim').forEach(el => observer.observe(el));

// === Contact form ===
const form = document.getElementById('contact-form');
if (form) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const btn = form.querySelector('.form-submit');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Mensagem enviada ✓';
    btn.style.background = '#16a34a';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.background = '';
      form.reset();
    }, 3000);
  });
}

// === Smooth counter animation ===
function animateCount(el) {
  const target = parseInt(el.dataset.count);
  const duration = 1800;
  const start = performance.now();

  const tick = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target) + (el.dataset.suffix || '');
    if (progress < 1) requestAnimationFrame(tick);
  };

  requestAnimationFrame(tick);
}

const countObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCount(entry.target);
      countObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-count]').forEach(el => countObserver.observe(el));
