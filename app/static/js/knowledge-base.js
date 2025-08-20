const API_BASE = '/documents';

let currentFileId = null;
let currentFileName = null;
let categories = [];
let currentPageSize = 10;
let allTextsForFile = [];
let searchTimeout = null;
let confirmDeleteHandler = null;

const qs = (sel, root = document) => root.querySelector(sel);
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function showModal(id) {
  const m = qs(`#${id}`);
  if (!m) return;
  m.classList.add('show');
  m.setAttribute('aria-hidden', 'false');
  const firstInput = qs('input, textarea', m);
  if (firstInput) firstInput.focus();
}

function closeModal(id) {
  const m = qs(`#${id}`);
  if (!m) return;
  m.classList.remove('show');
  m.setAttribute('aria-hidden', 'true');
}

function showLoading(targetId) {
  const el = qs(`#${targetId}`);
  if (!el) return;
  el.innerHTML = `<div class="loading"><div class="spinner"></div><span>Loading...</span></div>`;
}

function toast(message, kind = 'success') {
  const wrap = qs('#toastContainer');
  if (!wrap) return;
  const div = document.createElement('div');
  div.className = kind === 'error' ? 'error-message' : 'success-message';
  div.textContent = message;
  wrap.appendChild(div);
  setTimeout(() => { div.style.opacity = '0'; div.addEventListener('transitionend', () => div.remove()); }, 3000);
}
const showError = (m) => toast(m || 'Something went wrong', 'error');
const showSuccess = (m) => toast(m || 'Done', 'success');

function escapeHtml(str = '') {
  return String(str).replace(/[&<>"']/g, match => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[match]);
}

function formatDate(dateString) {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function setBtnLoading(btn, isLoading, labelWhenLoading = 'Saving…') {
  if (!btn) return;
  if (isLoading) {
    btn.dataset.prevText = btn.textContent;
    btn.textContent = labelWhenLoading;
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.prevText || btn.textContent;
    btn.disabled = false;
  }
}

async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(API_BASE + endpoint, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options
    });
    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`;
      try { const err = await response.json(); detail = err.detail || JSON.stringify(err); } catch {}
      throw new Error(detail);
    }
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  } catch (e) {
    console.error('API Error:', e);
    showError(e.message);
    throw e;
  }
}

async function loadCategories() {
  try {
    showLoading('categoriesList');
    const data = await apiCall('/categories');
    categories = normalizeCategories(data);
    renderCategories();
    if (!currentFileId) goHome();
  } catch {
    qs('#categoriesList').innerHTML = '<div class="error-message">Failed to load categories</div>';
  }
}

function normalizeCategories(payload) {
  if (!Array.isArray(payload) || payload.length === 0) return [];
  const looksFlat = 'file_id' in payload[0] && !('files' in payload[0]);
  if (!looksFlat) return payload.map(c => ({ ...c, files: Array.isArray(c.files) ? c.files : [] }));
  const map = new Map();
  for (const row of payload) {
    if (!map.has(row.category_id)) {
      map.set(row.category_id, { category_id: row.category_id, category_name: row.category_name, files: [] });
    }
    if (row.file_id) {
      map.get(row.category_id).files.push({ file_id: row.file_id, file_name: row.file_name });
    }
  }
  return Array.from(map.values());
}

function renderCategories() {
  const container = qs('#categoriesList');
  if (categories.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No categories yet</p></div>';
    return;
  }
  container.innerHTML = categories.map(cat => `
    <div class="category-item" data-category-id="${cat.category_id}">
      <div class="category-header" data-toggle-category="${cat.category_id}" aria-expanded="false">
        <div style="display:flex;align-items:center;gap:8px;flex:1;">
          <span class="expand-icon" aria-hidden="true">▶</span>
          <span class="category-name">${escapeHtml(cat.category_name)}</span>
        </div>
        <div class="category-actions">
          <button type="button" class="btn-icon btn-add" data-add-file="${cat.category_id}" title="Add File">+</button>
          <button type="button" class="btn-icon btn-edit-category" data-edit-category="${cat.category_id}" data-category-name="${escapeHtml(cat.category_name)}" title="Edit Category">✎</button>
          <button type="button" class="btn-icon btn-delete" data-delete-category="${cat.category_id}" title="Delete Category">×</button>
        </div>
      </div>
      <div class="files-list">
        ${(cat.files || []).map(file => `
          <div class="file-item" data-file-id="${file.file_id}" data-select-file="${file.file_id}" data-file-name="${escapeHtml(file.file_name)}">
            <span class="file-name">${escapeHtml(file.file_name)}</span>
            <button type="button" class="btn-icon btn-delete" data-delete-file="${file.file_id}" title="Delete File">×</button>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

function onCategoryListClick(e) {
  const target = e.target.closest('[data-add-file], [data-delete-category], [data-delete-file], [data-toggle-category], [data-select-file], [data-edit-category]');
  if (!target) return;
  e.stopPropagation();

  const { addFile, deleteCategory: delCat, deleteFile: delFile, toggleCategory: togCat, selectFile: selFile, editCategory: editCat } = target.dataset;

  if (addFile) openFileModal(Number(addFile));
  if (togCat) toggleCategory(Number(togCat));
  if (selFile) selectFile(Number(selFile), target.getAttribute('data-file-name'));
  if (editCat) enableCategoryEdit(Number(editCat), target.dataset.categoryName);

  if (delCat) {
    const catName = target.closest('.category-header').querySelector('.category-name').textContent;
    openDeleteConfirmModal('Delete Category', `This will delete "${catName}" and all its files.`, () => deleteCategory(Number(delCat)));
  }
  if (delFile) {
    const fileName = target.closest('.file-item').getAttribute('data-file-name');
    openDeleteConfirmModal('Delete File', `This will delete "${fileName}" and all its Q&A entries.`, () => deleteFile(Number(delFile)));
  }
}

function toggleCategory(categoryId) {
  const el = qs(`[data-category-id="${categoryId}"]`);
  const header = qs(`[data-toggle-category="${categoryId}"]`);
  if (!el || !header) return;
  const isExpanded = el.classList.toggle('expanded');
  header.setAttribute('aria-expanded', isExpanded);
}

function enableCategoryEdit(categoryId, currentName) {
  const nameSpan = qs(`.category-item[data-category-id="${categoryId}"] .category-name`);
  if (!nameSpan || nameSpan.querySelector('input')) return;

  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'search-input';
  input.value = currentName;
  
  const save = async () => {
    const newName = input.value.trim();
    if (newName && newName !== currentName) {
      try {
        await apiCall('/categories/update', {
          method: 'POST',
          body: JSON.stringify({ category_id: categoryId, category_name: newName })
        });
        showSuccess('Category updated');
        await loadCategories();
      } catch {
        nameSpan.textContent = currentName;
      }
    } else {
      nameSpan.textContent = currentName;
    }
  };

  input.addEventListener('blur', save);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') input.blur();
    if (e.key === 'Escape') {
      nameSpan.textContent = currentName;
      input.removeEventListener('blur', save);
      input.blur();
    }
  });

  nameSpan.textContent = '';
  nameSpan.appendChild(input);
  input.focus();
  input.select();
}

async function createCategory(name) {
  try {
    await apiCall('/categories', { method: 'POST', body: JSON.stringify({ category_name: name }) });
    showSuccess('Category created');
    await loadCategories();
  } catch {}
}

async function deleteCategory(categoryId) {
  try {
    await apiCall(`/categories/${categoryId}`, { method: 'DELETE' });
    showSuccess('Category deleted');
    if (currentFileId) {
      const fileEl = qs(`[data-file-id="${currentFileId}"]`);
      if (fileEl && fileEl.closest(`[data-category-id="${categoryId}"]`)) goHome();
    }
    await loadCategories();
  } catch (e) { throw e; }
}

async function createFile(name, categoryId) {
  try {
    await apiCall('/files', { method: 'POST', body: JSON.stringify({ file_name: name, category_id: categoryId }) });
    showSuccess('File created');
    await loadCategories();
    toggleCategory(categoryId);
  } catch {}
}

async function deleteFile(fileId) {
  try {
    await apiCall(`/files/${fileId}`, { method: 'DELETE' });
    showSuccess('File deleted');
    if (currentFileId === fileId) goHome();
    await loadCategories();
  } catch (e) { throw e; }
}

function selectFile(fileId, fileName) {
  currentFileId = fileId;
  currentFileName = fileName;
  qsa('.file-item.active').forEach(el => el.classList.remove('active'));
  qs(`.file-item[data-file-id="${fileId}"]`)?.classList.add('active');
  qs('#homeGrid').style.display = 'none';
  qs('#textEntries').style.display = 'grid';
  qs('#homeBtn').style.display = 'inline-block';
  qs('#mainTitle').textContent = fileName;
  qs('#mainSubtitle').textContent = 'Manage Q&A entries for this file';
  qs('#addTextBtn').disabled = false;
  loadTexts(fileId);
}

function goHome() {
  currentFileId = null;
  currentFileName = null;
  qsa('.file-item.active').forEach(el => el.classList.remove('active'));
  qs('#addTextBtn').disabled = true;
  qs('#homeBtn').style.display = 'none';
  qs('#mainTitle').textContent = 'All Files';
  qs('#mainSubtitle').textContent = 'Select a file to edit or search across all content';
  qs('#mainSearchSection').style.display = 'block';
  qs('#textEntries').style.display = 'none';
  qs('#statsSection').style.display = 'none';
  qs('#pagination').style.display = 'none';
  qs('#mainSearch').value = '';
  qs('#homeGrid').style.display = 'grid';
  renderHomePageGrid();
}

function renderHomePageGrid() {
  const container = qs('#homeGrid');
  const allFiles = categories.flatMap(cat => cat.files.map(file => ({ ...file, category_name: cat.category_name })));
  if (allFiles.length === 0) {
    container.innerHTML = `<div class="empty-state"><h3>No Files Found</h3><p>Create a category and add your first file.</p></div>`;
    return;
  }
  container.innerHTML = allFiles.map(file => `
    <div class="file-card" data-select-file="${file.file_id}" data-file-name="${escapeHtml(file.file_name)}">
      <div class="file-card-title">${escapeHtml(file.file_name)}</div>
      <div class="file-card-category">${escapeHtml(file.category_name)}</div>
    </div>
  `).join('');
}

async function loadTexts(fileId) {
  try {
    showLoading('textEntries');
    const data = await apiCall(`/files/${fileId}/texts`);
    allTextsForFile = Array.isArray(data.texts) ? data.texts : [];
    renderFileTextsPage(1);
  } catch {
    qs('#textEntries').innerHTML = '<div class="error-message">Failed to load entries.</div>';
  }
}

function renderFileTextsPage(page = 1) {
  const total = allTextsForFile.length;
  const start = (page - 1) * currentPageSize;
  const end = start + currentPageSize;
  const pageItems = allTextsForFile.slice(start, end);

  renderTexts(pageItems);
  updateStats(total, page);
  renderPagination(total, page, currentPageSize, 'file-browse', '');
}

function searchTextsInFile(query, page = 1) {
  const q = query.trim().toLowerCase();
  if (!q) {
    renderFileTextsPage(1);
    qs('#mainSubtitle').textContent = 'Manage Q&A entries for this file';
    return;
  }

  const filtered = allTextsForFile.filter(t =>
    (t.question || '').toLowerCase().includes(q) || (t.answer || '').toLowerCase().includes(q)
  );

  const total = filtered.length;
  const start = (page - 1) * currentPageSize;
  const end = start + currentPageSize;
  const pageItems = filtered.slice(start, end);

  renderTexts(pageItems);
  updateStats(total, page);
  renderPagination(total, page, currentPageSize, 'file-search', q);
  qs('#mainSubtitle').textContent = `Filtered by “${query.trim()}”`;
}

async function searchTextsGlobal(query, page = 1) {
  const q = query.trim();
  if (!q) { goHome(); return; }

  qs('#homeGrid').style.display = 'none';
  qs('#textEntries').style.display = 'grid';

  try {
    showLoading('textEntries');
    const data = await apiCall(`/texts/search?query=${encodeURIComponent(q)}&page=${page}&size=${currentPageSize}`);
    const texts = data.texts || [];
    renderTexts(texts);
    const total = data.total_texts || 0;
    updateStats(total, page);
    renderPagination(total, page, currentPageSize, 'global-search', q);
    qs('#mainTitle').textContent = `Search results`;
    qs('#mainSubtitle').textContent = `“${q}” across all files`;
  } catch {
    qs('#textEntries').innerHTML = '<div class="error-message">Search failed.</div>';
  }
}

function renderTexts(texts) {
  const container = qs('#textEntries');
  if (!texts || texts.length === 0) {
    container.innerHTML = `<div class="empty-state"><h3>No entries found</h3><p>Add a new Q&A entry or adjust your search.</p></div>`;
    qs('#statsSection').style.display = 'none';
    qs('#pagination').style.display = 'none';
    return;
  }
  container.innerHTML = texts.map(text => {
    const editPayload = JSON.stringify({ 
      id: text.text_id, 
      q: text.question, 
      a: text.answer,
      author: text.text_author
    });
    return `
    <div class="text-entry">
      <div class="text-entry-header">
        <span class="text-entry-id">#${text.text_id.substring(0, 8)}...</span>
        <div class="text-entry-actions">
          <button type="button" class="btn-text-action btn-edit" data-edit-text='${escapeHtml(editPayload)}'>Edit</button>
          <button type="button" class="btn-text-action btn-delete-text" data-delete-text="${text.text_id}">Delete</button>
        </div>
      </div>
      <p class="question">${escapeHtml(text.question)}</p>
      <p class="answer">${escapeHtml(text.answer)}</p>
      <div class="text-entry-footer">
        <span class="author">By: <strong>${escapeHtml(text.text_author)}</strong></span>
        <span class="date">Updated: ${formatDate(text.updated_at)}</span>
      </div>
    </div>
  `}).join('');
}

function updateStats(total, page = 1) {
  qs('#totalTexts').textContent = total;
  qs('#currentPage').textContent = page;
  qs('#statsSection').style.display = 'flex';
}

function renderPagination(total, page = 1, size = 10, mode = 'none', query = '') {
  const pages = Math.max(1, Math.ceil(total / size));
  const pag = qs('#pagination');
  
  pag.dataset.mode = mode;
  pag.dataset.query = query;

  if (pages <= 1) {
    pag.style.display = 'none';
    return;
  }
  pag.style.display = 'flex';

  const makeBtn = (p, label = p, disabled = false, active = false) => `<button type="button" ${disabled ? 'disabled' : ''} data-page="${p}" class="${active ? 'active' : ''}">${label}</button>`;
  
  let html = makeBtn(Math.max(1, page - 1), 'Prev', page === 1);
  
  const MAX_PAGES_SHOWN = 5;
  if (pages > MAX_PAGES_SHOWN) {
      let startPage = Math.max(1, page - Math.floor(MAX_PAGES_SHOWN / 2));
      let endPage = Math.min(pages, startPage + MAX_PAGES_SHOWN - 1);
      if (endPage - startPage + 1 < MAX_PAGES_SHOWN) {
        startPage = Math.max(1, endPage - MAX_PAGES_SHOWN + 1);
      }
      
      if (startPage > 1) html += makeBtn(1) + '<span>...</span>';
      for (let i = startPage; i <= endPage; i++) html += makeBtn(i, i, false, i === page);
      if (endPage < pages) html += '<span>...</span>' + makeBtn(pages);

  } else {
    for (let i = 1; i <= pages; i++) html += makeBtn(i, i, false, i === page);
  }

  html += makeBtn(Math.min(pages, page + 1), 'Next', page === pages);
  pag.innerHTML = html;
}

function openDeleteConfirmModal(title, message, onConfirm) {
  qs('#deleteModalTitle').textContent = title;
  qs('#deleteModalMessage').textContent = message;
  const form = qs('#deleteConfirmForm');
  if (confirmDeleteHandler) form.removeEventListener('submit', confirmDeleteHandler);
  confirmDeleteHandler = async (e) => {
    e.preventDefault();
    const btn = qs('#confirmDeleteBtn');
    setBtnLoading(btn, true, 'Deleting...');
    try {
      await onConfirm();
      closeModal('deleteConfirmModal');
    } catch {
    } finally {
      setBtnLoading(btn, false);
    }
  };
  form.addEventListener('submit', confirmDeleteHandler);
  showModal('deleteConfirmModal');
}

function wireFormsAndButtons() {
  qs('#openCategoryModalBtn').addEventListener('click', () => { qs('#categoryForm').reset(); showModal('categoryModal'); });
  qs('#addTextBtn').addEventListener('click', () => {
    qs('#textForm').reset();
    qs('#editingTextId').value = '';
    qs('#textFileId').value = currentFileId;
    qs('#textModalTitle').textContent = 'Add New Question';
    qs('#textSubmitBtn').textContent = 'Create Entry';
    showModal('textModal');
  });
  qs('#categoryForm').addEventListener('submit', async (e) => { e.preventDefault(); await createCategory(qs('#categoryName').value.trim()); closeModal('categoryModal'); });
  qs('#fileForm').addEventListener('submit', async (e) => { e.preventDefault(); await createFile(qs('#fileName').value.trim(), Number(qs('#fileCategoryId').value)); closeModal('fileModal'); });

  qs('#textForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const textId = qs('#editingTextId').value;
    const payload = {
      question: qs('#textQuestion').value.trim(),
      answer: qs('#textAnswer').value.trim(),
      text_author: qs('#textAuthor').value.trim()
    };
    if (!payload.question || !payload.answer || !payload.text_author) return;

    const btn = qs('#textSubmitBtn');
    setBtnLoading(btn, true);

    try {
      if (textId) {
        await apiCall(`/texts/update`, {
          method: 'POST',
          body: JSON.stringify({ text_id: textId, ...payload })
        });
        showSuccess('Entry updated');
      } else {
        const fileId = Number(qs('#textFileId').value);
        // Backend expects an object or a list
        await apiCall(`/files/${fileId}/texts`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showSuccess('Entry created');
      }
      closeModal('textModal');
      if (currentFileId) await loadTexts(currentFileId);
    } catch {} finally {
      setBtnLoading(btn, false);
    }
  });

  qs('#sidebarSearch').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    qsa('.category-item').forEach(item => {
      const name = qs('.category-name', item)?.textContent.toLowerCase() || '';
      item.style.display = name.includes(q) ? '' : 'none';
    });
  });

  qs('#mainSearch').addEventListener('input', (e) => {
    const q = e.target.value;
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        if (currentFileId) searchTextsInFile(q, 1);
        else searchTextsGlobal(q, 1);
    }, 300);
  });

  qs('#pagination').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-page]');
    if (!btn || btn.disabled) return;
    const page = Number(btn.dataset.page);
    const { mode, query } = e.currentTarget.dataset;

    if (mode === 'global-search') searchTextsGlobal(query, page);
    else if (mode === 'file-search') searchTextsInFile(query, page);
    else if (mode === 'file-browse') renderFileTextsPage(page);
  });

  qs('#pageSizeSelect').addEventListener('change', (e) => {
    currentPageSize = Number(e.target.value);
    const currentQuery = qs('#mainSearch').value.trim();
    if(currentFileId) {
        if(currentQuery) { searchTextsInFile(currentQuery, 1); }
        else { renderFileTextsPage(1); }
    } else {
        if(currentQuery) { searchTextsGlobal(currentQuery, 1); }
    }
  });
  
  qs('#textEntries').addEventListener('click', (e) => {
    const editBtn = e.target.closest('[data-edit-text]');
    const delBtn = e.target.closest('[data-delete-text]');
    if (editBtn) {
      const { id, q, a, author } = JSON.parse(editBtn.dataset.editText);
      qs('#textForm').reset();
      qs('#editingTextId').value = id;
      qs('#textQuestion').value = q;
      qs('#textAnswer').value = a;
      qs('#textAuthor').value = author || ''; // Set author
      qs('#textModalTitle').textContent = `Edit Entry #${id.substring(0,8)}...`;
      qs('#textSubmitBtn').textContent = 'Save Changes';
      showModal('textModal');
    }
    if (delBtn) {
      const id = delBtn.dataset.deleteText;
      openDeleteConfirmModal('Delete Entry', `Are you sure you want to delete Q&A entry #${id.substring(0,8)}...?`, () => deleteText(id));
    }
  });
}

function openFileModal(categoryId) { qs('#fileForm').reset(); qs('#fileCategoryId').value = categoryId; showModal('fileModal'); }


async function deleteText(textId) {
  try {
    await apiCall(`/texts/batch`, { method: 'DELETE', body: JSON.stringify({ text_ids: [textId] }) });
    showSuccess('Entry deleted');
    if (currentFileId) await loadTexts(currentFileId);
  } catch (e) { throw e; }
}


document.addEventListener('DOMContentLoaded', async () => {
  qsa('[data-close]').forEach(btn => btn.addEventListener('click', () => closeModal(btn.dataset.close)));
  qsa('.modal').forEach(modal => modal.addEventListener('click', e => { if (e.target === modal) closeModal(modal.id); }));
  qs('#categoriesList').addEventListener('click', onCategoryListClick);
  qs('#homeGrid').addEventListener('click', (e) => {
    const card = e.target.closest('.file-card[data-select-file]');
    if (card) selectFile(Number(card.dataset.selectFile), card.dataset.fileName);
  });
  qs('#homeBtn').addEventListener('click', goHome);
  qs('#sidebarHome').addEventListener('click', goHome);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.querySelector('.modal.show')) { closeModal(document.querySelector('.modal.show').id) } });

  wireFormsAndButtons();
  await loadCategories();
});