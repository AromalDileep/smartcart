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
// TABS
// ----------------------------------------
function activateTab(name) {
  // Remove active from all tabs
  document
    .querySelectorAll(".tab")
    .forEach((t) => t.classList.remove("active"));

  // Hide all panels
  document
    .querySelectorAll(".panel")
    .forEach((p) => (p.style.display = "none"));

  // Activate selected tab + panel
  document.querySelector(`.tab[data-tab=${name}]`).classList.add("active");
  document.getElementById(`${name}Panel`).style.display = "block";

  // Reset pagination when switching tabs
  if (name === "pending") {
    loadPending(true);
  }
  if (name === "approved") {
    loadApproved(true);
  }
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
    tb.innerHTML = ""; // clear table
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

  // Bind buttons
  document.querySelectorAll(".approveBtn").forEach((btn) => {
    btn.onclick = () => approveProduct(btn.dataset.id);
  });
  document.querySelectorAll(".rejectBtn").forEach((btn) => {
    btn.onclick = () => rejectProduct(btn.dataset.id);
  });

  // Update offset
  pendingOffset += rows.length;

  // Show/hide load more button
  const loadMoreBtn = document.getElementById("pendingLoadMore");
  if (rows.length < pendingLimit) {
    loadMoreBtn.style.display = "none";
  } else {
    loadMoreBtn.style.display = "block";
  }
}

// Load more button for pending
document.getElementById("pendingLoadMore").onclick = () => loadPending(false);

async function approveProduct(id) {
  const res = await fetch(`/admin/approve/${id}`, { method: "POST" });
  const j = await res.json();
  if (!res.ok) return alert("Error: " + j.detail);
  loadPending(true); // reload list
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

  // bind delete
  document.querySelectorAll(".deleteBtn").forEach((btn) => {
    btn.onclick = () => deleteProduct(btn.dataset.id);
  });

  // update offset
  approvedOffset += rows.length;

  // Show/hide Load More
  const loadMoreBtn = document.getElementById("approvedLoadMore");
  if (rows.length < approvedLimit) {
    loadMoreBtn.style.display = "none";
  } else {
    loadMoreBtn.style.display = "block";
  }
}

// Load more button for approved
document.getElementById("approvedLoadMore").onclick = () => loadApproved(false);

async function deleteProduct(id) {
  if (!confirm("Delete this product permanently?")) return;

  const res = await fetch(`/admin/delete/${id}`, { method: "DELETE" });
  const j = await res.json();

  if (!res.ok) return alert("Error: " + j.detail);

  loadApproved(true); // reload list cleanly
}

// ----------------------------------------
// TOOLS
// ----------------------------------------
document.getElementById("rebuildBtn").onclick = async () => {
  const res = await fetch("/admin/rebuild-faiss", { method: "POST" });
  const j = await res.json();
  document.getElementById("toolsStatus").textContent =
    "Rebuilt FAISS Index. Vectors: " + j.count;
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
