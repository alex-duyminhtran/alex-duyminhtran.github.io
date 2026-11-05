/* Progressive enhancement: the gallery also works with native scrolling and no JS. */
(() => {
  const gallery = document.getElementById('app-gallery');
  const back = document.getElementById('gallery-back');
  const forward = document.getElementById('gallery-forward');
  const controls = document.querySelector('.gallery-controls');
  if (!gallery || !back || !forward || !controls) return;

  const update = () => {
    back.disabled = gallery.scrollLeft <= 2;
    forward.disabled = gallery.scrollLeft + gallery.clientWidth >= gallery.scrollWidth - 2;
  };
  const move = direction => {
    const card = gallery.querySelector('.tour-card');
    const gap = parseFloat(getComputedStyle(gallery).columnGap) || 0;
    const distance = card ? card.getBoundingClientRect().width + gap : gallery.clientWidth;
    gallery.scrollBy({
      left: direction * distance,
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    });
  };
  back.addEventListener('click', () => move(-1));
  forward.addEventListener('click', () => move(1));
  gallery.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  controls.hidden = false;
  update();
})();
