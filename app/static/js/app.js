// Small progressive enhancement; core forms work without JavaScript.
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('click', (event) => {
      if (!window.confirm(element.getAttribute('data-confirm') || 'Continue?')) event.preventDefault();
    });
  });
  document.querySelectorAll('.flash').forEach((message) => {
    window.setTimeout(() => message.classList.add('flash-fade'), 6000);
  });
});
