document.querySelectorAll('.reply-button').forEach(button => {
  button.addEventListener('click', () => {
    document.getElementById('reply-parent').value = button.dataset.parent;
    document.getElementById('reply-name').textContent = button.dataset.author;
    document.getElementById('reply-indicator').hidden = false;
    document.getElementById('id_body').focus();
  });
});
document.getElementById('cancel-reply')?.addEventListener('click', () => {
  document.getElementById('reply-parent').value = '';
  document.getElementById('reply-indicator').hidden = true;
});
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
