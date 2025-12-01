// ----------------------------------------
// GLOBAL PAGINATION STATE
// ----------------------------------------
let pendingOffset = 0;
const pendingLimit = 20;

let approvedOffset = 0;
const approvedLimit = 50;

// ----------------------------------------
// Redirect to login if not authenticated
// ----------------------------------------
function checkLogin() {
  const admin_id = localStorage.getItem("admin_id");
  if (!admin_id && window.location.pathname.includes("index.html")) {
    window.location.href = "/static/admin/login.html";
  }
}
checkLogin();

// ----------------------------------------
// ADMIN LOGIN PAGE
// ----------------------------------------
if (window.location.pathname.includes("login.html")) {
  document.getElementById("loginBtn").onclick = async () => {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();

    const res = await fetch("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const j = await res.json();

    if (!res.ok) {
      document.getElementById("loginStatus").textContent =
        j.detail || "Login failed";
      return;
    }

    localStorage.setItem("admin_id", j.admin_id);
    window.location.href = "/static/admin/index.html";
  };
}

// ----------------------------------------
// LOGOUT
// ----------------------------------------
if (window.location.pathname.includes("index.html")) {
  document.getElementById("logoutBtn").onclick = () => {
    localStorage.removeItem("admin_id");
    window.location.href = "/static/admin/login.html";
  };
}

// ----------------------------------------
// TABS + LOAD STATS WHEN TOOLS TAB IS OPENED
// ----------------------------------------
function activateTab(name) {
  document
    .querySelectorAll(".tab")
    .forEach((t) => t.classList.remove("active"));
  document
    .querySelectorAll(".panel")
    .forEach((p) => (p.style.display = "none"));

  document.querySelector(`.tab[data-tab=${name}]`).classList.add("active");
  document.getElementById(`${name}Panel`).style.display = "block";

  if (name === "pending") loadPending(true);
  if (name === "approved") loadApproved(true);

  // ⭐ Load FAISS stats only when Tools tab is opened
  if (name === "tools") loadFaissStats();
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => activateTab(tab.dataset.tab);
});

// ----------------------------------------
// PENDING PRODUCTS (WITH PAGINATION)
// ----------------------------------------
async function loadPending(reset = false) {
  const tb = document.querySelector("#pendingTable tbody");

  if (reset) {
    pendingOffset = 0;
    tb.innerHTML = "";
  }

  const res = await fetch(
    `/admin/pending-products?offset=${pendingOffset}&limit=${pendingLimit}`
  );
  const rows = await res.json();

  for (const r of rows) {
    tb.innerHTML += `
      <tr>
        <td>${r.id}</td>
        <td><img src="/images/${r.image}" /></td>
        <td>${r.title}</td>
        <td>${r.seller_id}</td>
        <td>${r.created_at}</td>
        <td>
          <button class="btn-sm approveBtn" data-id="${r.id}">Approve</button>
          <button class="btn-sm rejectBtn" data-id="${r.id}">Reject</button>
        </td>
      </tr>
    `;
  }

  document.querySelectorAll(".approveBtn").forEach((btn) => {
    btn.onclick = () => approveProduct(btn.dataset.id);
  });
  document.querySelectorAll(".rejectBtn").forEach((btn) => {
    btn.onclick = () => rejectProduct(btn.dataset.id);
  });

  pendingOffset += rows.length;

  const loadMoreBtn = document.getElementById("pendingLoadMore");
  loadMoreBtn.style.display = rows.length < pendingLimit ? "none" : "block";
}

document.getElementById("pendingLoadMore").onclick = () => loadPending(false);

async function approveProduct(id) {
  const res = await fetch(`/admin/approve/${id}`, { method: "POST" });
  const j = await res.json();
  if (!res.ok) return alert("Error: " + j.detail);
  loadPending(true);
}

async function rejectProduct(id) {
  const res = await fetch(`/admin/reject/${id}`, { method: "POST" });
  const j = await res.json();
  if (!res.ok) return alert("Error: " + j.detail);
  loadPending(true);
}

// ----------------------------------------
// APPROVED PRODUCTS (WITH PAGINATION)
// ----------------------------------------
async function loadApproved(reset = false) {
  const tb = document.querySelector("#approvedTable tbody");

  if (reset) {
    approvedOffset = 0;
    tb.innerHTML = "";
  }

  const res = await fetch(
    `/admin/approved-products?offset=${approvedOffset}&limit=${approvedLimit}`
  );
  const rows = await res.json();

  for (const r of rows) {
    tb.innerHTML += `
      <tr>
        <td>${r.id}</td>
        <td><img src="/images/${r.image}" /></td>
        <td>${r.title}</td>
        <td>${r.seller_id}</td>
        <td>${r.approved_at}</td>
        <td>
          <button class="btn-sm deleteBtn" data-id="${r.id}">Delete</button>
        </td>
      </tr>
    `;
  }

  document.querySelectorAll(".deleteBtn").forEach((btn) => {
    btn.onclick = () => deleteProduct(btn.dataset.id);
  });

  approvedOffset += rows.length;

  const loadMoreBtn = document.getElementById("approvedLoadMore");
  loadMoreBtn.style.display = rows.length < approvedLimit ? "none" : "block";
}

document.getElementById("approvedLoadMore").onclick = () => loadApproved(false);

async function deleteProduct(id) {
  if (!confirm("Delete this product permanently?")) return;

  const res = await fetch(`/admin/delete/${id}`, { method: "DELETE" });
  const j = await res.json();
  if (!res.ok) return alert("Error: " + j.detail);

  loadApproved(true);
}

// ----------------------------------------
// ⭐ NEW: FAISS STATS FETCHER
// ----------------------------------------
async function loadFaissStats() {
  try {
    const res = await fetch("/admin/faiss-stats");
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || "Failed to load stats");

    // MATCH HTML IDs
    document.getElementById("stat_total_products").textContent =
      j.total_products;

    document.getElementById("stat_approved_products").textContent =
      j.approved_products;

    document.getElementById("stat_faiss_vectors").textContent = j.faiss_vectors;
  } catch (err) {
    console.error("Failed loading stats:", err);
  }
}

// ----------------------------------------
// TOOLS
// ----------------------------------------
document.getElementById("rebuildBtn").onclick = async () => {
  const res = await fetch("/admin/rebuild-faiss", { method: "POST" });
  const j = await res.json();

  document.getElementById("toolsStatus").textContent =
    "Rebuilt FAISS Index. Vectors: " + j.count;

  loadFaissStats();
};

document.getElementById("backupBtn").onclick = async () => {
  const res = await fetch("/admin/backup-faiss", { method: "POST" });
  const j = await res.json();

  document.getElementById("toolsStatus").textContent =
    "Backup created → " + j.path;
};

// ----------------------------------------
// Initial tab (pending)
// ----------------------------------------
if (window.location.pathname.includes("index.html")) {
  activateTab("pending");
}
