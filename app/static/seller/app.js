// =============================================
// SELLER APP — CLEAN FIXED VERSION
// =============================================

// -------------------------------------------------
// 1) GLOBAL BASE_URL (loaded dynamically from /config)
// -------------------------------------------------
let BASE_URL = ""; // will be filled before UI loads

async function loadConfigAndStart() {
  try {
    const res = await fetch("/config");
    if (!res.ok) throw new Error("Failed to fetch /config");

    const data = await res.json();
    BASE_URL = data.image_base_url || "";
    console.log("Loaded BASE_URL:", BASE_URL);
  } catch (err) {
    console.error("Could not load config:", err);
  }

  // Now that BASE_URL is ready → load UI logic
  initApp();
}

loadConfigAndStart();

// -------------------------------------------------
// 2) MAIN APPLICATION LOGIC
// -------------------------------------------------
function initApp() {
  const NO_IMAGE_SVG =
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='150' height='150'><rect width='150' height='150' fill='%23eee'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23666' font-size='14'>no image</text></svg>";

  // -----------------------------------
  // API ENDPOINTS
  // -----------------------------------
  const UPLOAD_URL = "/seller/upload-image";
  const CREATE_URL = "/seller/create-product";
  const LIST_URL = "/seller/products";
  const REGISTER_URL = "/seller/register";
  const LOGIN_URL = "/seller/login";
  const PRODUCT_URL = (id) => `/seller/products/${id}`;

  // -----------------------------------
  // AUTH HANDLING
  // -----------------------------------
  const regForm = document.getElementById("register-form");
  if (regForm) {
    const errorMsg = document.getElementById("error-msg");

    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("name").value;
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const res = await fetch(REGISTER_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        });

        const j = await res.json();
        if (!res.ok) throw new Error(j.detail || "Registration failed");

        alert("Registration successful! Please login.");
        window.location.href = "login.html";
      } catch (err) {
        errorMsg.textContent = err.message;
        errorMsg.style.display = "block";
      }
    });
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    const errorMsg = document.getElementById("error-msg");

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const res = await fetch(LOGIN_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        const j = await res.json();
        if (!res.ok) throw new Error(j.detail || "Login failed");

        localStorage.setItem("seller_id", j.seller_id);
        localStorage.setItem("seller_name", j.name);

        window.location.href = "index.html";
      } catch (err) {
        errorMsg.textContent = err.message;
        errorMsg.style.display = "block";
      }
    });
  }

  // -----------------------------------
  // AUTH CHECK FOR PRODUCT PAGES
  // -----------------------------------
  const sellerId = localStorage.getItem("seller_id");
  const sellerName = localStorage.getItem("seller_name");

  if (!regForm && !loginForm) {
    if (!sellerId) {
      window.location.href = "login.html";
      return;
    }
  }

  const sellerInfoDiv = document.getElementById("seller-info");
  if (sellerInfoDiv) {
    sellerInfoDiv.innerHTML = `
      Logged in as: <strong>${sellerName}</strong> (ID: ${sellerId})
      <button id="logoutBtn">Logout</button>
    `;
    document.getElementById("logoutBtn").onclick = () => {
      localStorage.removeItem("seller_id");
      localStorage.removeItem("seller_name");
      window.location.href = "login.html";
    };
  }

  // -----------------------------------
  // DOM ELEMENTS
  // -----------------------------------
  const refreshBtn = document.getElementById("refreshBtn");
  const uploadForm = document.getElementById("uploadForm");
  const imageFileInput = document.getElementById("imageFile");
  const imagePreview = document.getElementById("imagePreview");
  const uploadStatus = document.getElementById("uploadStatus");
  const productsTableBody = document.querySelector("#productsTable tbody");
  const editModal = document.getElementById("editModal");
  const closeEdit = document.getElementById("closeEdit");
  const editForm = document.getElementById("editForm");

  // -----------------------------------
  // IMAGE PREVIEW
  // -----------------------------------
  imageFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return (imagePreview.innerHTML = "");
    const url = URL.createObjectURL(file);
    imagePreview.innerHTML = `<img src="${url}" style="max-width:150px;" />`;
  });

  // -----------------------------------
  // IMAGE UPLOAD
  // -----------------------------------
  async function uploadImage(file) {
    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch(UPLOAD_URL, { method: "POST", body: fd });
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || "Upload failed");
    return j;
  }

  // -----------------------------------
  // CREATE PRODUCT
  // -----------------------------------
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    uploadStatus.textContent = "Processing...";

    try {
      const file = imageFileInput.files[0];
      if (!file) throw new Error("Please select an image");

      const up = await uploadImage(file);
      const filename = up.filename;

      const payload = {
        seller_id: parseInt(sellerId),
        title: document.getElementById("title").value,
        description: document.getElementById("description").value,
        price: parseFloat(document.getElementById("price").value || "0"),
        image: filename,
        main_category: document.getElementById("main_category").value,
        categories: document.getElementById("categories").value,
        product_url: document.getElementById("product_url").value,
        context: document.getElementById("context").value,
      };

      const res = await fetch(CREATE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || JSON.stringify(j));

      uploadStatus.textContent = `Product created: ${j.product_id}`;
      uploadForm.reset();
      imagePreview.innerHTML = "";
      loadProductsForSeller(sellerId);
    } catch (err) {
      uploadStatus.textContent = `Error: ${err.message}`;
    }
  });

  // -----------------------------------
  // LOAD PRODUCTS
  // -----------------------------------
  async function loadProductsForSeller(sid) {
    productsTableBody.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";

    try {
      const res = await fetch(`${LIST_URL}?seller_id=${sid}`);
      const rows = await res.json();

      if (!res.ok) throw new Error(rows.detail || "Failed to fetch");

      productsTableBody.innerHTML = "";

      for (const r of rows) {
        if (r.status === "deleted") continue;

        const imgUrl = r.image ? `${BASE_URL}${r.image}` : NO_IMAGE_SVG;

        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${r.id}</td>
          <td>
            <img loading="lazy" 
                 src="${imgUrl}" 
                 style="max-width:80px;" 
                 onerror="this.onerror=null;this.src='${NO_IMAGE_SVG}'" />
          </td>
          <td>${r.title || ""}</td>
          <td>${r.price ?? ""}</td>
          <td>${r.status}</td>
          <td>
            <button class="editBtn" data-id="${r.id}">Edit</button>
            ${
              r.status === "rejected"
                ? `<button class="resubmitBtn" data-id="${r.id}">Resubmit</button>`
                : ""
            }
            <button class="deleteBtn" data-id="${r.id}">Delete</button>
          </td>
        `;
        productsTableBody.appendChild(row);
      }

      document
        .querySelectorAll(".editBtn")
        .forEach((btn) =>
          btn.addEventListener("click", () => openEditModal(btn.dataset.id))
        );

      document.querySelectorAll(".deleteBtn").forEach((btn) =>
        btn.addEventListener("click", async () => {
          if (!confirm("Delete permanently?")) return;
          await deleteProduct(btn.dataset.id);
          loadProductsForSeller(sid);
        })
      );

      document.querySelectorAll(".resubmitBtn").forEach((btn) =>
        btn.addEventListener("click", async () => {
          await resubmitProduct(btn.dataset.id);
          loadProductsForSeller(sid);
        })
      );
    } catch (err) {
      productsTableBody.innerHTML = `<tr><td colspan='6'>Error: ${err.message}</td></tr>`;
    }
  }

  // -----------------------------------
  // RESUBMIT PRODUCT
  // -----------------------------------
  async function resubmitProduct(id) {
    const res = await fetch(`/seller/resubmit/${id}`, { method: "POST" });
    const j = await res.json();
    if (!res.ok) alert("Resubmit failed: " + j.detail);
    else alert("Product resubmitted");
  }

  // -----------------------------------
  // DELETE PRODUCT
  // -----------------------------------
  async function deleteProduct(id) {
    const res = await fetch(PRODUCT_URL(id), { method: "DELETE" });
    const j = await res.json();
    if (!res.ok) throw new Error(j.detail);
    return j;
  }

  // -----------------------------------
  // EDIT PRODUCT
  // -----------------------------------
  async function openEditModal(id) {
    const res = await fetch(PRODUCT_URL(id));
    const j = await res.json();
    if (!res.ok) return alert("Failed to fetch product");

    document.getElementById("edit_id").value = j.id;
    document.getElementById("edit_title").value = j.title || "";
    document.getElementById("edit_description").value = j.description || "";
    document.getElementById("edit_price").value = j.price || "";
    document.getElementById("edit_main_category").value = j.main_category || "";
    document.getElementById("edit_categories").value = j.categories || "";
    document.getElementById("edit_product_url").value = j.product_url || "";
    document.getElementById("edit_context").value = j.context || "";

    const statusSelect = document.getElementById("edit_status");
    const allowed = [...statusSelect.options].map((o) => o.value);
    statusSelect.value = allowed.includes(j.status) ? j.status : "pending";

    editModal.classList.remove("hidden");
  }

  closeEdit.addEventListener("click", () => editModal.classList.add("hidden"));

  editForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("edit_id").value;

    const payload = {
      title: document.getElementById("edit_title").value,
      description: document.getElementById("edit_description").value,
      price: parseFloat(document.getElementById("edit_price").value || "0"),
      main_category: document.getElementById("edit_main_category").value,
      categories: document.getElementById("edit_categories").value,
      product_url: document.getElementById("edit_product_url").value,
      context: document.getElementById("edit_context").value,
      status: document.getElementById("edit_status").value,
    };

    const res = await fetch(PRODUCT_URL(id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const j = await res.json();
    if (!res.ok) return alert("Update failed: " + j.detail);

    editModal.classList.add("hidden");
    loadProductsForSeller(sellerId);
  });

  // -----------------------------------
  // INITIAL LOAD
  // -----------------------------------
  refreshBtn.addEventListener("click", () => loadProductsForSeller(sellerId));

  loadProductsForSeller(sellerId);
}
