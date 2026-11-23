'use strict';
const data = JSON.parse(document.getElementById('report-data').textContent);
const search = document.getElementById('search');
const cards = [...document.querySelectorAll('.searchable')];
function filter() {
  let count = 0;
  const term = search.value.trim().toLowerCase();
  cards.forEach(card => { card.hidden = !card.dataset.search.includes(term); if (!card.hidden) count++; });
  document.getElementById('matches').textContent = `${count} of ${cards.length} concept and landscape entries shown${count ? '.' : '. No matches; reset to see all entries.'}`;
}
document.querySelector('.actions').hidden = false;
document.querySelector('.filter').hidden = false;
search.addEventListener('input', filter);
document.getElementById('reset').addEventListener('click', () => { search.value = ''; filter(); });
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.getElementById('download-md').addEventListener('click', () => download('disclosure.md', data.markdown, 'text/markdown'));
document.getElementById('download-json').addEventListener('click', () => download('disclosure.json', JSON.stringify(data.report, null, 2), 'application/json'));
let printState;
function beforePrint() {
  if (printState) return;
  printState = {search: search.value, details: [...document.querySelectorAll('details')].map(el => [el, el.open])};
  search.value = ''; filter(); printState.details.forEach(([el]) => { el.open = true; });
}
function afterPrint() {
  if (!printState) return;
  search.value = printState.search; printState.details.forEach(([el, open]) => { el.open = open; });
  printState = null; filter();
}
window.addEventListener('beforeprint', beforePrint); window.addEventListener('afterprint', afterPrint);
document.getElementById('print').addEventListener('click', () => { beforePrint(); window.print(); });
filter();
