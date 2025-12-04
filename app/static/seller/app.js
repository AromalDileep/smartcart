// app/static/seller/app.js
const UPLOAD_URL = "/seller/upload-image";
const CREATE_URL = "/seller/create-product";
const LIST_URL = "/seller/products";
const REGISTER_URL = "/seller/register";
const LOGIN_URL = "/seller/login";
const PRODUCT_URL = (id) => `/seller/products/${id}`;

document.addEventListener("DOMContentLoaded", () => {
  // -----------------------------------------------------
  // AUTH LOGIC (Register/Login pages)
  // -----------------------------------------------------
  const regForm = document.getElementById("register-form");
  if (regForm) {
    const errorMsg = document.getElementById("error-msg");

    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorMsg) errorMsg.style.display = "none";

      const name = document.getElementById("name").value;
      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const res = await fetch(REGISTER_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Registration failed");

        // Auto login or redirect to login
        alert("Registration successful! Please login.");
        window.location.href = "login.html";
      } catch (err) {
        if (errorMsg) {
          errorMsg.textContent = err.message;
          errorMsg.style.display = "block";
        } else {
          alert(err.message);
        }
      }
    });
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    const errorMsg = document.getElementById("error-msg");

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorMsg) errorMsg.style.display = "none";

      const email = document.getElementById("email").value;
      const password = document.getElementById("password").value;

      try {
        const res = await fetch(LOGIN_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        // Save session
        localStorage.setItem("seller_id", data.seller_id);
        localStorage.setItem("seller_name", data.name);

        window.location.href = "index.html";
      } catch (err) {
        if (errorMsg) {
          errorMsg.textContent = err.message;
          errorMsg.style.display = "block";
        } else {
          alert(err.message);
        }
      }
    });
  }
  // Check Auth
  const sellerId = localStorage.getItem("seller_id");
  const sellerName = localStorage.getItem("seller_name");

  // Only enforce auth if we are NOT on an auth page
  if (!regForm && !loginForm) {
    if (!sellerId) {
      window.location.href = "login.html";
      return;
    }
  }

  // Update UI with seller info
  const sellerInfoDiv = document.getElementById("seller-info");
  if (sellerInfoDiv) {
    sellerInfoDiv.innerHTML = `Logged in as: <strong>${sellerName}</strong> (ID: ${sellerId}) <button id="logoutBtn">Logout</button>`;

    document.getElementById("logoutBtn").addEventListener("click", () => {
      localStorage.removeItem("seller_id");
      localStorage.removeItem("seller_name");
      window.location.href = "login.html";
    });
  }

  const refreshBtn = document.getElementById("refreshBtn");
  const uploadForm = document.getElementById("uploadForm");
  const imageFileInput = document.getElementById("imageFile");
  const imagePreview = document.getElementById("imagePreview");
  const uploadStatus = document.getElementById("uploadStatus");
  const productsTableBody = document.querySelector("#productsTable tbody");

  const editModal = document.getElementById("editModal");
  const closeEdit = document.getElementById("closeEdit");
  const editForm = document.getElementById("editForm");

  // ===============================
  // IMAGE PREVIEW
  // ===============================
  imageFileInput.addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) {
      imagePreview.innerHTML = "";
      return;
    }
    const url = URL.createObjectURL(f);
    imagePreview.innerHTML = `<img src="${url}" style="max-width:150px;" />`;
  });

  // ===============================
  // IMAGE UPLOAD FUNCTION
  // ===============================
  async function uploadImage(file) {
    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch(UPLOAD_URL, { method: "POST", body: fd });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    return res.json(); // { filename, url }
  }

  // ===============================
  // CREATE PRODUCT
  // ===============================
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    uploadStatus.textContent = "Processing...";

    try {
      const title = document.getElementById("title").value;
      const description = document.getElementById("description").value;
      const price = parseFloat(document.getElementById("price").value || "0");
      const main_category = document.getElementById("main_category").value;
      const categories = document.getElementById("categories").value;
      const product_url = document.getElementById("product_url").value;
      const context = document.getElementById("context").value;

      const file = imageFileInput.files[0];
      if (!file) {
        uploadStatus.textContent = "Please select an image before submitting.";
        return;
      }

      // Upload image
      const up = await uploadImage(file);
      const filename = up.filename;

      // Build payload
      const payload = {
        seller_id: parseInt(sellerId), // Use logged in ID
        title,
        description,
        price,
        image: filename,
        main_category,
        categories,
        product_url,
        context,
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
      console.error(err);
    }
  });

  // ===============================
  // LOAD PRODUCTS
  // ===============================
  async function loadProductsForSeller(sid) {
    productsTableBody.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";

    try {
      const res = await fetch(`${LIST_URL}?seller_id=${sid}`);
      const rows = await res.json();

      if (!res.ok) throw new Error(rows.detail || "Failed to fetch");

      if (!rows.length) {
        productsTableBody.innerHTML =
          "<tr><td colspan='6'>No products</td></tr>";
        return;
      }

      productsTableBody.innerHTML = "";

      for (const r of rows) {
        if (r.status === "deleted") continue;

        const imgTag = r.image
          ? `<img src="/images/${r.image}" style="max-width:80px;">`
          : "";

        const resubmitBtn =
          r.status === "rejected"
            ? `<button class="resubmitBtn" data-id="${r.id}">Resubmit</button>`
            : "";

        const deleteBtn = `<button class="deleteBtn" data-id="${r.id}">Delete</button>`;

        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${r.id}</td>
          <td>${imgTag}</td>
          <td>${r.title || ""}</td>
          <td>${r.price != null ? r.price : ""}</td>
          <td>${r.status || ""}</td>
          <td>
            <button class="editBtn" data-id="${r.id}">Edit</button>
            ${resubmitBtn}
            ${deleteBtn}
          </td>
        `;

        productsTableBody.appendChild(tr);
      }

      // Bind Edit buttons
      document.querySelectorAll(".editBtn").forEach((btn) => {
        btn.onclick = () => openEditModal(btn.dataset.id);
      });

      // Bind Delete buttons
      document.querySelectorAll(".deleteBtn").forEach((btn) => {
        btn.onclick = async () => {
          const id = btn.dataset.id;
          if (!confirm("Delete this product permanently?")) return;
          await deleteProduct(id);
          loadProductsForSeller(sid);
        };
      });

      // Bind Resubmit buttons
      document.querySelectorAll(".resubmitBtn").forEach((btn) => {
        btn.onclick = async () => {
          await resubmitProduct(btn.dataset.id);
          loadProductsForSeller(sid);
        };
      });
    } catch (err) {
      productsTableBody.innerHTML = `<tr><td colspan='6'>Error: ${err.message}</td></tr>`;
    }
  }

  // ===============================
  // RESUBMIT PRODUCT
  // ===============================
  async function resubmitProduct(id) {
    const res = await fetch(`/seller/resubmit/${id}`, {
      method: "POST",
    });

    const j = await res.json();

    if (!res.ok) {
      alert("Resubmit failed: " + (j.detail || JSON.stringify(j)));
      return;
    }

    alert("Product resubmitted for approval");
  }

  // ===============================
  // DELETE PRODUCT
  // ===============================
  async function deleteProduct(id) {
    const res = await fetch(PRODUCT_URL(id), { method: "DELETE" });
    const j = await res.json();

    if (!res.ok) throw new Error(j.detail || JSON.stringify(j));
    return j;
  }

  // ===============================
  // OPEN EDIT MODAL
  // ===============================
  async function openEditModal(id) {
    const res = await fetch(PRODUCT_URL(id));
    const j = await res.json();

    if (!res.ok) {
      alert("Failed to fetch product");
      return;
    }

    document.getElementById("edit_id").value = j.id;
    document.getElementById("edit_title").value = j.title || "";
    document.getElementById("edit_description").value = j.description || "";
    document.getElementById("edit_price").value = j.price || "";
    document.getElementById("edit_main_category").value = j.main_category || "";
    document.getElementById("edit_categories").value = j.categories || "";
    document.getElementById("edit_product_url").value = j.product_url || "";
    document.getElementById("edit_context").value = j.context || "";

    // -------- FIXED PART --------
    const statusSelect = document.getElementById("edit_status");
    const allowed = [...statusSelect.options].map((o) => o.value);

    if (!allowed.includes(j.status)) {
      statusSelect.value = "pending";
    } else {
      statusSelect.value = j.status;
    }
    // ----------------------------

    editModal.classList.remove("hidden");
  }

  // ===============================
  // SAVE EDITED PRODUCT
  // ===============================
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

    if (!res.ok) {
      alert("Update failed: " + (j.detail || JSON.stringify(j)));
      return;
    }

    editModal.classList.add("hidden");
    loadProductsForSeller(sellerId);
  });

  // ===============================
  // CLOSE MODAL
  // ===============================
  closeEdit.addEventListener("click", () => {
    editModal.classList.add("hidden");
  });

  // ===============================
  // INITIAL LOAD
  // ===============================
  refreshBtn.addEventListener("click", () => {
    loadProductsForSeller(sellerId);
  });

  loadProductsForSeller(sellerId);
});
