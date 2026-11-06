(function () {
  "use strict";
  var body = document.body;
  try { if (localStorage.getItem("menu-recolhido") === "1") body.classList.add("menu-recolhido"); } catch (e) {}
  var t = document.getElementById("toggle-menu");
  if (t) t.addEventListener("click", function () {
    body.classList.toggle("menu-recolhido");
    try { localStorage.setItem("menu-recolhido", body.classList.contains("menu-recolhido") ? "1" : "0"); } catch (e) {}
  });

  document.addEventListener("submit", function (ev) {
    var msg = ev.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) ev.preventDefault();
  });

  document.querySelectorAll("select.select-busca").forEach(function (sel, n) {
    var dl = document.createElement("datalist");
    dl.id = "dl-busca-" + n;
    var mapa = {};
    Array.prototype.forEach.call(sel.options, function (o) {
      if (!o.value) return;
      var op = document.createElement("option");
      op.value = o.text;
      dl.appendChild(op);
      mapa[o.text] = o.value;
    });
    var inp = document.createElement("input");
    inp.type = "text";
    inp.className = sel.className.replace("form-select", "form-control");
    inp.setAttribute("list", dl.id);
    inp.placeholder = "Digite número ou nome…";
    inp.autocomplete = "off";
    if (sel.required) { inp.required = true; sel.required = false; }
    var atual = sel.options[sel.selectedIndex];
    if (atual && atual.value) inp.value = atual.text;
    inp.addEventListener("input", function () {
      sel.value = mapa[inp.value] || "";
      inp.setCustomValidity(inp.value && !sel.value ? "Escolha um recruta da lista." : "");
    });
    sel.style.display = "none";
    sel.parentNode.insertBefore(inp, sel);
    sel.parentNode.insertBefore(dl, sel);
  });
})();
