// ----------------------------------------
// BASE URL FOR IMAGES
// ----------------------------------------
const BASE_URL =
  "https://smartcart-ai-data.s3.ap-south-1.amazonaws.com/all_images/";

// Fallback image SVG
const NO_IMAGE_SVG =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><rect width='200' height='200' fill='%23eee'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23666' font-size='14'>no image</text></svg>";

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
  if (name === "deleted") loadDeleted(true);
  if (name === "orphans") loadOrphans();

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
    const imgUrl = r.image ? `${BASE_URL}${r.image}` : NO_IMAGE_SVG;
    const altText = r.title || "product image";

    tb.innerHTML += `
      <tr>
        <td>${r.id}</td>
        <td><img loading="lazy" src="${imgUrl}" alt="${altText}" style="width:80px;height:auto;" onerror="this.onerror=null;this.src='${NO_IMAGE_SVG}'" /></td>
        <td>${r.title}</td>
        <td>${r.seller_id}</td>
        <td>${r.created_at}</td>
        <td>
          <button class="btn-sm approveBtn" data-id="${r.id}" style="background-color: #4caf50; color: white;">Train</button>
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

// ⭐ NEW: TRAIN ALL
document.getElementById("trainAllBtn").onclick = async () => {
  if (
    !confirm(
      "Are you sure you want to train all pending products? This might take a while."
    )
  )
    return;

  const btn = document.getElementById("trainAllBtn");
  const originalText = btn.textContent;
  btn.textContent = "Training...";
  btn.disabled = true;

  try {
    const res = await fetch("/admin/approve-all", { method: "POST" });
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || "Failed to train all");

    alert(`Successfully trained ${j.count} products!`);
    loadPending(true);
    loadFaissStats(); // Update stats immediately
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
};

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
    const imgUrl = r.image ? `${BASE_URL}${r.image}` : NO_IMAGE_SVG;
    const altText = r.title || "product image";

    tb.innerHTML += `
      <tr>
        <td>${r.id}</td>
        <td><img loading="lazy" src="${imgUrl}" alt="${altText}" style="width:80px;height:auto;" onerror="this.onerror=null;this.src='${NO_IMAGE_SVG}'" /></td>
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
// DELETED PRODUCTS (WITH PAGINATION)
// ----------------------------------------
let deletedOffset = 0;
const deletedLimit = 20;

async function loadDeleted(reset = false) {
  const tb = document.querySelector("#deletedTable tbody");

  if (reset) {
    deletedOffset = 0;
    tb.innerHTML = "";
  }

  const res = await fetch(
    `/admin/deleted-products?offset=${deletedOffset}&limit=${deletedLimit}`
  );
  const rows = await res.json();

  for (const r of rows) {
    const imgUrl = r.image ? `${BASE_URL}${r.image}` : NO_IMAGE_SVG;
    const altText = r.title || "product image";

    tb.innerHTML += `
      <tr>
        <td>${r.id}</td>
        <td><img loading="lazy" src="${imgUrl}" alt="${altText}" style="width:80px;height:auto;" onerror="this.onerror=null;this.src='${NO_IMAGE_SVG}'" /></td>
        <td>${r.title}</td>
        <td>${r.seller_id}</td>
        <td>${r.created_at}</td>
        <td>
          <button class="btn-sm permDeleteBtn" data-id="${r.id}" style="background-color: #f44336; color: white;">Permanently Delete</button>
        </td>
      </tr>
    `;
  }

  document.querySelectorAll(".permDeleteBtn").forEach((btn) => {
    btn.onclick = () => permanentDeleteProduct(btn.dataset.id);
  });

  deletedOffset += rows.length;

  const loadMoreBtn = document.getElementById("deletedLoadMore");
  loadMoreBtn.style.display = rows.length < deletedLimit ? "none" : "block";
}

document.getElementById("deletedLoadMore").onclick = () => loadDeleted(false);

async function permanentDeleteProduct(id) {
  if (
    !confirm(
      "Are you sure you want to PERMANENTLY delete this product? This cannot be undone."
    )
  )
    return;

  const res = await fetch(`/admin/permanent-delete/${id}`, {
    method: "DELETE",
  });
  const j = await res.json();
  if (!res.ok) return alert("Error: " + j.detail);

  loadDeleted(true);
}

document.getElementById("deleteAllDeletedBtn").onclick = async () => {
  if (
    !confirm(
      "Are you sure you want to PERMANENTLY delete ALL deleted products? This cannot be undone."
    )
  )
    return;

  const btn = document.getElementById("deleteAllDeletedBtn");
  btn.textContent = "Deleting...";
  btn.disabled = true;

  try {
    const res = await fetch("/admin/permanent-delete-all", {
      method: "DELETE",
    });
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || "Failed to delete all");

    alert(`Permanently deleted ${j.count} products.`);
    loadDeleted(true);
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.textContent = "Delete All";
    btn.disabled = false;
  }
};

// ----------------------------------------
// ORPHAN IMAGES
// ----------------------------------------
async function loadOrphans() {
  const tb = document.querySelector("#orphansTable tbody");
  tb.innerHTML = "<tr><td colspan='3'>Loading...</td></tr>";

  try {
    const res = await fetch("/admin/orphan-images");
    const files = await res.json();

    if (!res.ok) throw new Error(files.detail || "Failed to load orphans");

    if (!files.length) {
      tb.innerHTML = "<tr><td colspan='3'>No orphan images found.</td></tr>";
      return;
    }

    tb.innerHTML = "";
    for (const f of files) {
      const imgUrl = f ? `${BASE_URL}${f}` : NO_IMAGE_SVG;

      tb.innerHTML += `
        <tr>
          <td><img loading="lazy" src="${imgUrl}" alt="${f}" style="width:80px;height:auto;" onerror="this.onerror=null;this.src='${NO_IMAGE_SVG}'" /></td>
          <td>${f}</td>
          <td>
            <button class="btn-sm deleteOrphanBtn" data-name="${f}" style="background-color: #f44336; color: white;">Delete</button>
          </td>
        </tr>
      `;
    }

    document.querySelectorAll(".deleteOrphanBtn").forEach((btn) => {
      btn.onclick = () => deleteOrphan(btn.dataset.name);
    });
  } catch (err) {
    tb.innerHTML = `<tr><td colspan='3'>Error: ${err.message}</td></tr>`;
  }
}

async function deleteOrphan(filename) {
  if (!confirm(`Delete ${filename} permanently?`)) return;

  const res = await fetch(`/admin/orphan-images/${filename}`, {
    method: "DELETE",
  });
  const j = await res.json();

  if (!res.ok) return alert("Error: " + j.detail);
  loadOrphans();
}

document.getElementById("cleanAllOrphansBtn").onclick = async () => {
  if (
    !confirm(
      "Are you sure you want to delete ALL orphan images? This cannot be undone."
    )
  )
    return;

  const btn = document.getElementById("cleanAllOrphansBtn");
  btn.textContent = "Cleaning...";
  btn.disabled = true;

  try {
    const res = await fetch("/admin/orphan-images-all", { method: "DELETE" });
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || "Failed to clean");

    alert(`Cleaned ${j.deleted_count} images.`);
    loadOrphans();
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.textContent = "Clean All Unused Images";
    btn.disabled = false;
  }
};

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
