/**
 * DevOps Learning Hub — Application Logic
 * Tab switching, favourites (API-backed), projects (API-backed)
 */

(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════
  // XSS-safe HTML escaping
  // ═══════════════════════════════════════════════════════
  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;')
      .replace(/'/g,  '&#39;');
  }

  // ═══════════════════════════════════════════════════════
  // TOP TABS (Learning / Personal)
  // ═══════════════════════════════════════════════════════
  document.querySelectorAll('.top-tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var tab = this.getAttribute('data-tab');
      document.querySelectorAll('.top-tab-btn').forEach(function(b) { b.classList.remove('active'); });
      this.classList.add('active');
      document.querySelectorAll('.page-pane').forEach(function(p) { p.classList.remove('active'); });
      document.getElementById('pane-' + tab).classList.add('active');
      window.scrollTo(0, 0);
    });
  });

  // ═══════════════════════════════════════════════════════
  // PERSONAL SUB-TABS (Projects / Notes / Bookmarks)
  // ═══════════════════════════════════════════════════════
  document.querySelectorAll('.personal-subtab').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      var tab = this.getAttribute('data-subtab');
      document.querySelectorAll('.personal-subtab').forEach(function(b) { b.classList.remove('active'); });
      this.classList.add('active');
      document.querySelectorAll('.subtab-pane').forEach(function(p) { p.classList.remove('active'); });
      document.getElementById('subtab-' + tab).classList.add('active');
    });
  });

  // ═══════════════════════════════════════════════════════
  // PROJECTS CRUD (API-backed)
  // ═══════════════════════════════════════════════════════

  function renderProjects(projects) {
    var grid = document.getElementById('projects-grid');
    var empty = document.getElementById('projects-empty');
    if (!grid) return;
    grid.querySelectorAll('.project-card').forEach(function(c) { c.remove(); });
    if (!projects || projects.length === 0) {
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';
    projects.forEach(function(proj) {
      var card = document.createElement('div');
      card.className = 'project-card';
      card.setAttribute('data-proj-id', proj.id);
      var t = escapeHtml(proj.title);
      var u = escapeHtml(proj.url);
      var dateStr = proj.added ? new Date(proj.added).toLocaleDateString() : '';
      card.innerHTML =
        '<button class="delete-btn" title="Delete project" data-proj-id="' + escapeHtml(String(proj.id)) + '">&#x2715;</button>' +
        '<h3><a href="' + u + '" target="_blank" rel="noopener">' + t + '</a></h3>' +
        '<div class="project-link"><a href="' + u + '" target="_blank" rel="noopener">' + u + '</a></div>' +
        '<div class="project-date">Added: ' + escapeHtml(dateStr) + '</div>';
      grid.appendChild(card);
    });
  }

  function loadProjects() {
    fetch('/api/projects')
      .then(function(r) { return r.json(); })
      .then(function(data) { renderProjects(data); })
      .catch(function() { renderProjects([]); });
  }

  // Modal
  var modal = document.getElementById('project-modal');
  if (modal) {
    document.getElementById('add-project-btn').addEventListener('click', function() {
      modal.classList.add('open');
      document.getElementById('proj-title').focus();
    });
    document.getElementById('modal-cancel').addEventListener('click', function() {
      modal.classList.remove('open');
      document.getElementById('proj-title').value = '';
      document.getElementById('proj-url').value = '';
    });
    document.getElementById('modal-save').addEventListener('click', function() {
      var title = document.getElementById('proj-title').value.trim();
      var url = document.getElementById('proj-url').value.trim();
      if (!title || !url) return;
      fetch('/api/projects')
        .then(function(r) { return r.json(); })
        .then(function(projects) {
          projects.push({ id: Date.now().toString(36), title: title, url: url, added: Date.now() });
          return fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projects)
          });
        })
        .then(function() {
          loadProjects();
          modal.classList.remove('open');
          document.getElementById('proj-title').value = '';
          document.getElementById('proj-url').value = '';
        })
        .catch(function() { /* silent fail */ });
    });
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.classList.remove('open');
        document.getElementById('proj-title').value = '';
        document.getElementById('proj-url').value = '';
      }
    });
  }

  // Delete project
  var projectsGrid = document.getElementById('projects-grid');
  if (projectsGrid) {
    projectsGrid.addEventListener('click', function(e) {
      if (!e.target.classList.contains('delete-btn')) return;
      var id = e.target.getAttribute('data-proj-id');
      fetch('/api/projects/' + encodeURIComponent(id), { method: 'DELETE' })
        .then(function() { loadProjects(); })
        .catch(function() { /* silent fail */ });
    });
  }

  // Initial load
  loadProjects();

  // ═══════════════════════════════════════════════════════
  // FAVOURITES (API-backed, synced across both views)
  // ═══════════════════════════════════════════════════════

  function syncStarButtons(favid, isFavourite) {
    document.querySelectorAll('.star-btn[data-favid="' + favid + '"]').forEach(function(btn) {
      btn.classList.toggle('active', isFavourite);
      btn.textContent = isFavourite ? '\u2605' : '\u2606';
      btn.title = isFavourite ? 'Remove from favourites' : 'Add to favourites';
    });
  }

  function renderFavourites(favs) {
    var grid = document.getElementById('favourites-grid');
    var empty = document.getElementById('fav-empty');
    if (!grid) return;
    grid.querySelectorAll('.card').forEach(function(c) { c.remove(); });
    if (!favs || favs.length === 0) {
      if (empty) empty.style.display = 'block';
      return;
    }
    if (empty) empty.style.display = 'none';
    favs.forEach(function(fav) {
      if (!fav || typeof fav !== 'object' || !fav.name) return;
      var card = document.createElement('div');
      card.className = 'card';
      var safeName = escapeHtml(fav.name);
      var safeUrl = escapeHtml(fav.url);
      card.innerHTML =
        '<button class="star-btn active" data-favid="' + escapeHtml(fav.id) + '" data-name="' + escapeHtml(fav.name) + '" data-url="' + escapeHtml(fav.url) + '" title="Remove from favourites">&#x2605;</button>' +
        '<h3><a href="' + safeUrl + '" target="_blank" rel="noopener">' + safeName + '</a></h3>' +
        '<p>' + safeUrl + '</p>';
      grid.appendChild(card);
    });
  }

  function updateFavCount(favs) {
    var count = favs ? favs.length : 0;
    var el = document.getElementById('favourites-count');
    if (!el) return;
    el.textContent = count;
    el.classList.toggle('hidden', count === 0);
  }

  function loadFavourites() {
    fetch('/api/favourites')
      .then(function(r) { return r.json(); })
      .then(function(favs) {
        updateFavCount(favs);
        renderFavourites(favs);
        var favIds = {};
        favs.forEach(function(f) { if (f && typeof f === 'object' && f.id) favIds[f.id] = true; });
        document.querySelectorAll('.star-btn').forEach(function(btn) {
          var id = btn.getAttribute('data-favid');
          var isFav = !!favIds[id];
          btn.classList.toggle('active', isFav);
          btn.textContent = isFav ? '\u2605' : '\u2606';
          btn.title = isFav ? 'Remove from favourites' : 'Add to favourites';
        });
      })
      .catch(function() { updateFavCount([]); });
  }

  // Star button click handler
  document.addEventListener('click', function(e) {
    if (!e.target.classList.contains('star-btn')) return;
    var id = e.target.getAttribute('data-favid');
    var name = e.target.getAttribute('data-name');
    var url = e.target.getAttribute('data-url');
    var wasActive = e.target.classList.contains('active');
    // Optimistic toggle
    syncStarButtons(id, !wasActive);
    // Sync with server
    fetch('/api/favourites')
      .then(function(r) { return r.json(); })
      .then(function(favs) {
        var idx = favs.findIndex(function(f) { return f && f.id === id; });
        if (!wasActive) {
          if (idx < 0) favs.push({ id: id, name: name, url: url });
        } else {
          if (idx >= 0) favs.splice(idx, 1);
        }
        return fetch('/api/favourites', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(favs)
        }).then(function() { return favs; });
      })
      .then(function(favs) {
        updateFavCount(favs);
        renderFavourites(favs);
        var favIds = {};
        favs.forEach(function(f) { if (f && typeof f === 'object' && f.id) favIds[f.id] = true; });
        document.querySelectorAll('.star-btn').forEach(function(btn) {
          var bid = btn.getAttribute('data-favid');
          var isFav = !!favIds[bid];
          btn.classList.toggle('active', isFav);
          btn.textContent = isFav ? '\u2605' : '\u2606';
          btn.title = isFav ? 'Remove from favourites' : 'Add to favourites';
        });
      })
      .catch(function() { /* silent fail */ });
  });

  // Initial load
  loadFavourites();

  // ═══════════════════════════════════════════════════════
  // LEARNING NAV active state on scroll
  // ═══════════════════════════════════════════════════════
  var navLinks = document.querySelectorAll('.learning-nav a');
  var sections = document.querySelectorAll('.section');
  window.addEventListener('scroll', function() {
    if (document.querySelector('#pane-personal').classList.contains('active')) return;
    var scrollY = window.scrollY + 80;
    var current = '';
    sections.forEach(function(sec) {
      var top = sec.offsetTop;
      if (top <= scrollY) current = sec.getAttribute('id');
    });
    navLinks.forEach(function(a) {
      a.classList.toggle('active', a.getAttribute('href') === '#' + current);
    });
  });

})();
