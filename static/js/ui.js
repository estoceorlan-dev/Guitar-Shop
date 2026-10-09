/* Small HTML enhancements; all forms also work without JavaScript. */
document.addEventListener('DOMContentLoaded', () => {
  const menu = document.querySelector('[data-menu]');
  menu?.addEventListener('click', () => {
    const open = document.body.classList.toggle('nav-open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      document.body.classList.remove('nav-open');
      menu?.setAttribute('aria-expanded', 'false');
    }
  });
  document.querySelectorAll('[data-print]').forEach(button => {
    button.addEventListener('click', () => window.print());
  });
  const total = document.querySelector('[data-order-total]');
  if (total) {
    const quantity = document.getElementById('field-quantity');
    const cost = document.getElementById('field-unit_cost');
    const update = () => {
      const amount = Math.max(0, Number(quantity.value) || 0) * Math.max(0, Number(cost.value) || 0);
      total.textContent = new Intl.NumberFormat('en-PH', {style: 'currency', currency: 'PHP'}).format(amount);
    };
    quantity.addEventListener('input', update);
    cost.addEventListener('input', update);
    update();
  }
});
