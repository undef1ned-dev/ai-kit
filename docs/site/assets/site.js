// AIKit docs — hand-written, not generated. Search index: assets/search-index.js (scripts/generate-docs.py)
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var toast = document.querySelector("[data-toast]");
  function showToast() {
    if (!toast) return;
    toast.classList.add("show");
    setTimeout(function () { toast.classList.remove("show"); }, 1600);
  }

  // ── Theme ──
  function storeTheme(theme) {
    try { localStorage.setItem("aikit-theme", theme); } catch (e) { /* storage may be unavailable */ }
  }
  var themeButton = document.querySelector("[data-theme-toggle]");
  if (themeButton) {
    themeButton.addEventListener("click", function () {
      var current = document.documentElement.dataset.theme ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      storeTheme(next);
    });
  }

  // ── Mobile navigation ──
  var navToggle = document.querySelector("[data-nav-toggle]");
  if (navToggle) {
    navToggle.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
    document.querySelector(".content").addEventListener("click", function () { document.body.classList.remove("nav-open"); });
  }

  // ── Copy buttons ──
  function copy(text, button) {
    function done() {
      var label = button.textContent;
      button.classList.add("copied");
      button.textContent = "Скопировано";
      showToast();
      setTimeout(function () { button.classList.remove("copied"); button.textContent = label; }, 1500);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else {
      fallbackCopy(text);
      done();
    }
  }
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (e) { /* nothing else to try */ }
    document.body.removeChild(area);
  }
  document.addEventListener("click", function (event) {
    var button = event.target.closest(".copy-btn");
    if (!button) return;
    if (button.hasAttribute("data-copy-code")) {
      copy(button.closest(".code-block").querySelector("code").textContent, button);
    } else {
      copy(button.getAttribute("data-copy"), button);
    }
  });

  // ── Table of contents: highlight the current section ──
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (tocLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    tocLinks.forEach(function (link) { byId[decodeURIComponent(link.hash.slice(1))] = link; });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        tocLinks.forEach(function (link) { link.classList.remove("active"); });
        var link = byId[entry.target.id];
        if (link) link.classList.add("active");
      });
    }, { rootMargin: "-70px 0px -70% 0px" });
    Object.keys(byId).forEach(function (id) {
      var heading = document.getElementById(id);
      if (heading) observer.observe(heading);
    });
  }

  // ── Search ──
  var input = document.querySelector("[data-search]");
  var box = document.querySelector("[data-search-results]");
  var index = window.AIKIT_SEARCH || [];
  var snippetLength = window.AIKIT_SNIPPET || 220;
  var selected = -1;
  var MAX_RESULTS = 12;

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function highlight(text, terms) {
    var html = escapeHtml(text);
    terms.forEach(function (term) {
      var safe = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      html = html.replace(new RegExp("(" + escapeHtml(safe) + ")", "gi"), "<mark>$1</mark>");
    });
    return html;
  }
  function snippet(text, terms) {
    var lower = text.toLowerCase();
    var position = lower.indexOf(terms[0]);
    var start = Math.max(0, position - 60);
    var space = text.indexOf(" ", start);
    if (start > 0 && space !== -1 && space < position) start = space + 1;
    var part = text.slice(start, start + snippetLength);
    return (start > 0 ? "… " : "") + part + (start + snippetLength < text.length ? " …" : "");
  }
  function search(query) {
    var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return [];
    var results = [];
    index.forEach(function (item) {
      var title = item.t.toLowerCase();
      var text = item.x.toLowerCase();
      var score = 0;
      for (var i = 0; i < terms.length; i++) {
        var inTitle = title.indexOf(terms[i]) !== -1;
        var inText = text.indexOf(terms[i]) !== -1;
        if (!inTitle && !inText) return;
        score += inTitle ? 10 : 1;
        if (title === terms[i] || title === "/" + terms[i]) score += 20;
        if (title.indexOf(terms[i]) === 0 || title.indexOf("/" + terms[i]) === 0) score += 5;
      }
      results.push({ item: item, score: score });
    });
    results.sort(function (a, b) { return b.score - a.score; });
    return results.slice(0, MAX_RESULTS).map(function (r) { return r.item; });
  }
  function render(query) {
    var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    var results = search(query);
    selected = -1;
    if (!query.trim()) { box.hidden = true; return; }
    if (!results.length) {
      box.innerHTML = '<div class="search-empty">Ничего не найдено. Попробуй другое слово — например, «профиль», «скилл» или имя агента.</div>';
      box.hidden = false;
      return;
    }
    box.innerHTML = results.map(function (item) {
      var page = item.k ? item.k + " · " + item.p : item.p;
      return '<a class="search-result" href="' + item.u + '">' +
        '<span class="search-result-head"><span class="search-result-title">' + highlight(item.t, terms) + "</span>" +
        '<span class="search-result-page">' + escapeHtml(page) + "</span></span>" +
        (item.x ? '<span class="search-result-text">' + highlight(snippet(item.x, terms), terms) + "</span>" : "") +
        "</a>";
    }).join("");
    box.hidden = false;
  }
  function move(step) {
    var items = box.querySelectorAll(".search-result");
    if (!items.length) return;
    selected = (selected + step + items.length) % items.length;
    Array.prototype.forEach.call(items, function (el, i) { el.classList.toggle("selected", i === selected); });
    items[selected].scrollIntoView({ block: "nearest" });
  }
  if (input && box) {
    input.addEventListener("input", function () { render(input.value); });
    input.addEventListener("focus", function () { if (input.value.trim()) render(input.value); });
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
      else if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
      else if (event.key === "Enter") {
        var items = box.querySelectorAll(".search-result");
        var target = items[selected >= 0 ? selected : 0];
        if (target) window.location.href = target.href;
      } else if (event.key === "Escape") { box.hidden = true; input.blur(); }
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".search")) box.hidden = true;
    });
    document.addEventListener("keydown", function (event) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if ((event.key === "/" && !typing) || (event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey))) {
        event.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  // ── Catalog: tabs, filter, deep links ──
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-panel]"));
  var filter = document.querySelector("[data-catalog-filter]");
  var empty = document.querySelector(".filter-empty");

  function activate(id) {
    tabs.forEach(function (tab) { tab.classList.toggle("active", tab.getAttribute("data-tab") === id); });
    panels.forEach(function (panel) { panel.classList.toggle("active", panel.id === id); });
    applyFilter();
  }
  function applyFilter() {
    if (!filter) return;
    var query = filter.value.toLowerCase().trim();
    var panel = document.querySelector("[data-panel].active");
    if (!panel) return;
    var visible = 0;
    panel.querySelectorAll(".entry-card").forEach(function (card) {
      var match = !query || card.getAttribute("data-filter").indexOf(query) !== -1;
      if (match) { card.removeAttribute("data-hidden"); visible++; } else { card.setAttribute("data-hidden", ""); }
    });
    if (empty) empty.hidden = !(query && !visible);
  }
  function openHash() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    var target = id && document.getElementById(id);
    if (!panels.length) return;
    var panel = target && target.closest ? target.closest("[data-panel]") : null;
    if (panel) {
      activate(panel.id);
      if (target !== panel) {
        target.scrollIntoView({ block: "start" });
        target.classList.remove("flash");
        void target.offsetWidth;
        target.classList.add("flash");
      }
    } else if (!document.querySelector("[data-panel].active")) {
      activate(panels[0].id);
    }
    if (target && target.classList.contains("preset-card")) target.classList.add("flash");
  }
  if (tabs.length) {
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () { activate(tab.getAttribute("data-tab")); });
    });
    if (filter) filter.addEventListener("input", applyFilter);
    window.addEventListener("hashchange", openHash);
    openHash();
  }
})();
