// Roda logo depois da abertura no index.html, antes de ela aparecer na tela.
// A abertura passa uma vez por sessão; se a página recarregar, o app aparece direto.
try {
  if (sessionStorage.getItem('aberturaVista')) document.querySelector('.abertura').remove();
} catch { /* sem armazenamento */ }
