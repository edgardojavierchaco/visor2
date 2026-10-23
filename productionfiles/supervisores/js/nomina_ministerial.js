document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sigse-cue-toggle').forEach(button => {
    button.addEventListener('click', () => {
      const detail = document.getElementById(button.dataset.target);
      if (!detail) return;
      const open = detail.hidden;
      detail.hidden = !open;
      button.setAttribute('aria-expanded', String(open));
      button.textContent = (open ? 'Ocultar' : 'Ver') + ' CUEANEXO (' +
        (button.dataset.count || button.textContent.match(/\d+/)?.[0] || '0') + ')';
    });
    button.dataset.count = button.textContent.match(/\d+/)?.[0] || '0';
  });
});
