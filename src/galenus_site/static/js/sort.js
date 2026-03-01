document.getElementById('selnav').addEventListener('change', function(e) {
  document.querySelectorAll('.title-list').forEach(function(el) { el.hidden = true; });
  document.getElementById('list-' + e.target.value).hidden = false;
});
