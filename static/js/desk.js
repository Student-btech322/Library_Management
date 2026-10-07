let current = null;     // { student, active_issues, ... }
let selectedBook = null;

const $ = id => document.getElementById(id);

async function loadStats() {
  try {
    const s = await api('/api/stats');
    for (const k of ['books', 'titles', 'students', 'issued', 'overdue']) $('st-' + k).textContent = s[k];
  } catch (e) { toast(e.message, 'error'); }
}

async function lookupStudent(q) {
  q = (q || '').trim();
  if (!q) return;
  $('card-input').value = q;
  try {
    current = await api('/api/students/lookup?q=' + encodeURIComponent(q));
    renderStudent();
    $('book-input').disabled = false;
    $('book-cam').disabled = false;
    clearBook();
    $('book-input').focus();
  } catch (e) {
    current = null;
    $('student-box').innerHTML = `<div class="placeholder" style="color:var(--danger)">${esc(e.message)}<br><a href="/students">Register a new student</a></div>`;
    $('book-input').disabled = true;
    $('book-cam').disabled = true;
    $('book-box').innerHTML = '';
    $('card-input').select();
  }
}

function renderStudent() {
  const { student: s, active_issues: loans, total_issued, max_books } = current;
  const overdue = loans.filter(l => l.status === 'overdue');
  const fine = loans.reduce((a, l) => a + l.fine, 0);
  $('student-box').innerHTML = `
    <div class="student-panel">
      ${avatarHtml(s)}
      <div class="details">
        <div class="full" style="grid-column:1/-1"><span>Name</span><strong style="font-size:1.15rem">${esc(s.name)}</strong></div>
        <div><span>ID card no.</span><strong>${esc(s.card_id)}</strong></div>
        <div><span>Roll no.</span><strong>${esc(s.roll_no || '-')}</strong></div>
        <div><span>Branch</span><strong>${esc(s.branch || '-')}</strong></div>
        <div><span>Year</span><strong>${esc(s.year || '-')}</strong></div>
        <div><span>Email</span><strong>${esc(s.email || '-')}</strong></div>
        <div><span>Phone</span><strong>${esc(s.phone || '-')}</strong></div>
      </div>
    </div>
    <div class="row" style="margin:1rem 0 .5rem;justify-content:space-between">
      <h3 style="margin:0">Books currently issued (${loans.length}/${max_books})</h3>
      <span class="muted small">${total_issued} borrowed in total</span>
    </div>
    ${overdue.length ? `<div class="alert">${overdue.length} overdue book(s). Pending fine: &#8377;${fine}. Return before issuing new books.</div>` : ''}
    ${loans.length ? loans.map(l => `
      <div class="loan">
        <div class="info">
          <strong>${esc(l.book_title)}</strong>
          <span class="muted small">${esc(l.book_code)} &middot; Issued ${fmtDate(l.issue_date)} &middot; Due ${fmtDate(l.due_date)}${l.fine ? ` &middot; Fine &#8377;${l.fine}` : ''}</span>
        </div>
        ${statusBadge(l.status)}
        <button class="btn btn-sm" data-return="${l.id}">Return</button>
      </div>`).join('') : '<p class="muted small">No books issued.</p>'}`;
}

function clearBook() {
  selectedBook = null;
  $('book-input').value = '';
  $('book-suggest').hidden = true;
  $('book-box').innerHTML = `<p class="muted small" style="margin-top:1rem">Loan period: ${LIB.loanDays} days &middot; Max ${LIB.maxBooks} books per student &middot; Fine &#8377;${LIB.finePerDay}/day after due date.</p>`;
}

function selectBook(b) {
  selectedBook = b;
  $('book-suggest').hidden = true;
  $('book-input').value = b.title;
  const due = new Date(); due.setDate(due.getDate() + LIB.loanDays);
  const already = current.active_issues.some(l => l.book_id === b.id);
  const blocked = b.available <= 0 || already || current.active_issues.length >= current.max_books
    || current.active_issues.some(l => l.status === 'overdue');
  $('book-box').innerHTML = `
    <div class="book-box">
      <h3 style="margin-bottom:.25rem">${esc(b.title)}</h3>
      <div class="muted small">${esc(b.author || '')}</div>
      <div class="details" style="margin-top:.75rem">
        <div><span>Book code</span><strong>${esc(b.code)}</strong></div>
        <div><span>Category</span><strong>${esc(b.category || '-')}</strong></div>
        <div><span>Available</span><strong><span class="badge ${b.available > 0 ? 'ok' : 'zero'}">${b.available} of ${b.total_copies}</span></strong></div>
        <div><span>Due date</span><strong>${due.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })}</strong></div>
      </div>
      ${already ? '<div class="alert" style="margin-top:1rem">Student already has this book.</div>' : ''}
      <div class="row" style="margin-top:1rem">
        <button class="btn btn-success btn-lg" id="issue-btn" ${blocked ? 'disabled' : ''}>Issue to ${esc(current.student.name.split(' ')[0])}</button>
        <button class="btn" id="clear-book">Clear</button>
      </div>
    </div>`;
  $('issue-btn').onclick = issueBook;
  $('clear-book').onclick = () => { clearBook(); $('book-input').focus(); };
  if (!blocked) $('issue-btn').focus();
}

async function issueBook() {
  if (!current || !selectedBook) return;
  $('issue-btn').disabled = true;
  try {
    const r = await api('/api/issue', { method: 'POST', body: { card_id: current.student.card_id, book_code: selectedBook.code } });
    toast(`Issued "${r.book_title}" to ${r.student_name}. Due ${fmtDate(r.due_date)}`, 'success');
    await lookupStudent(current.student.card_id);
    loadStats();
  } catch (e) {
    toast(e.message, 'error');
    $('issue-btn').disabled = false;
  }
}

async function returnIssue(id) {
  try {
    const r = await api('/api/return/' + id, { method: 'POST' });
    toast(r.fine ? `Book returned. Collect fine: \u20B9${r.fine}` : 'Book returned on time', r.fine ? '' : 'success');
    await lookupStudent(current.student.card_id);
    loadStats();
  } catch (e) { toast(e.message, 'error'); }
}

async function findBookByCode(code) {
  try { selectBook(await api('/api/books/lookup?q=' + encodeURIComponent(code))); return true; }
  catch (_) { return false; }
}

let suggestions = [], suggestIdx = -1;
const searchBooks = debounce(async q => {
  if (!q.trim() || selectedBook) { $('book-suggest').hidden = true; return; }
  const results = await api('/api/books?limit=8&q=' + encodeURIComponent(q));
  if (selectedBook) return;
  suggestions = results;
  suggestIdx = -1;
  const box = $('book-suggest');
  box.innerHTML = suggestions.length ? suggestions.map((b, i) => `
    <div data-i="${i}"><strong>${esc(b.title)}</strong><br>
    <span class="muted small">${esc(b.code)} &middot; ${esc(b.author || '')} &middot; ${b.available} available</span></div>`).join('')
    : '<div class="muted">No matching books</div>';
  box.hidden = false;
}, 200);

$('card-form').onsubmit = e => { e.preventDefault(); lookupStudent($('card-input').value); };
$('card-cam').onclick = () => Scanner.open('Scan student ID card', lookupStudent);
$('book-cam').onclick = () => Scanner.open('Scan book barcode', async code => {
  if (!(await findBookByCode(code))) toast('No book found with code ' + code, 'error');
});
document.querySelectorAll('.sample').forEach(a => a.onclick = e => { e.preventDefault(); lookupStudent(a.textContent); });

$('book-input').oninput = e => { selectedBook = null; searchBooks(e.target.value); };
$('book-input').onkeydown = async e => {
  const items = [...$('book-suggest').querySelectorAll('[data-i]')];
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    if (!items.length) return;
    suggestIdx = (suggestIdx + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items.forEach((el, i) => el.classList.toggle('sel', i === suggestIdx));
  } else if (e.key === 'Enter') {
    e.preventDefault();
    const q = e.target.value.trim();
    if (!q) return;
    if (suggestIdx >= 0 && suggestions[suggestIdx]) return selectBook(suggestions[suggestIdx]);
    if (await findBookByCode(q)) return;           // barcode scanner input
    if (suggestions.length === 1) return selectBook(suggestions[0]);
  } else if (e.key === 'Escape') {
    $('book-suggest').hidden = true;
  }
};
$('book-suggest').onclick = e => {
  const el = e.target.closest('[data-i]');
  if (el) selectBook(suggestions[+el.dataset.i]);
};
document.addEventListener('click', e => {
  if (!e.target.closest('.suggest')) $('book-suggest').hidden = true;
  const ret = e.target.closest('[data-return]');
  if (ret) returnIssue(ret.dataset.return);
});

loadStats();
const preset = new URLSearchParams(location.search).get('card');
if (preset) lookupStudent(preset);
