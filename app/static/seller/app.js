// app/static/seller/app.js
const UPLOAD_URL = "/seller/upload-image";
const CREATE_URL = "/seller/create-product";
const LIST_URL = "/seller/products";
const PRODUCT_URL = (id) => `/seller/products/${id}`;

document.addEventListener("DOMContentLoaded", () => {
  const sellerIdInput = document.getElementById("sellerId");
  const refreshBtn = document.getElementById("refreshBtn");
  const uploadForm = document.getElementById("uploadForm");
  const imageFileInput = document.getElementById("imageFile");
  const imagePreview = document.getElementById("imagePreview");
  const uploadStatus = document.getElementById("uploadStatus");

  const productsTableBody = document.querySelector("#productsTable tbody");

  const editModal = document.getElementById("editModal");
  const closeEdit = document.getElementById("closeEdit");
  const editForm = document.getElementById("editForm");

  // Preview selected image
  imageFileInput.addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) {
      imagePreview.innerHTML = "";
      return;
    }
    const url = URL.createObjectURL(f);
    imagePreview.innerHTML = `<img src="${url}" alt="preview" style="max-width:150px;" />`;
  });

  // Upload image helper
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

  // Create product
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    uploadStatus.textContent = "Processing...";
    try {
      const seller_id = parseInt(sellerIdInput.value || "1", 10);
      const title = document.getElementById("title").value;
      const description = document.getElementById("description").value;
      const price = parseFloat(document.getElementById("price").value || "0");
      const main_category = document.getElementById("main_category").value;
      const categories = document.getElementById("categories").value;
      const product_url = document.getElementById("product_url").value;
      const context = document.getElementById("context").value;

      // If user selected a file, upload it first
      let filename = null;
      const file = imageFileInput.files[0];
      if (file) {
        const up = await uploadImage(file);
        filename = up.filename;
      }

      const payload = {
        seller_id,
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
      loadProductsForSeller(seller_id);
    } catch (err) {
      uploadStatus.textContent = `Error: ${err.message}`;
      console.error(err);
    }
  });

  // Load products
  async function loadProductsForSeller(seller_id) {
    productsTableBody.innerHTML = "<tr><td colspan='6'>Loading...</td></tr>";
    try {
      const res = await fetch(`${LIST_URL}?seller_id=${seller_id}`);
      const rows = await res.json();
      if (!res.ok) throw new Error(rows.detail || "Failed to fetch");

      if (!rows.length) {
        productsTableBody.innerHTML =
          "<tr><td colspan='6'>No products</td></tr>";
        return;
      }

      productsTableBody.innerHTML = "";
      for (const r of rows) {
        const tr = document.createElement("tr");

        const imgTag = r.image
          ? `<img src="/images/${r.image
              .split("/")
              .pop()}" style="max-width:80px;">`
          : "";

        tr.innerHTML = `
          <td>${r.id}</td>
          <td>${imgTag}</td>
          <td>${r.title || ""}</td>
          <td>${r.price != null ? r.price : ""}</td>
          <td>${r.status || ""}</td>
          <td>
            <button class="editBtn" data-id="${r.id}">Edit</button>
            <button class="deleteBtn" data-id="${r.id}">Delete</button>
          </td>
        `;
        productsTableBody.appendChild(tr);
      }

      // attach actions
      document.querySelectorAll(".editBtn").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          const id = ev.currentTarget.dataset.id;
          openEditModal(id);
        });
      });

      document.querySelectorAll(".deleteBtn").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          const id = ev.currentTarget.dataset.id;
          if (!confirm("Delete this product? This cannot be undone.")) return;
          await deleteProduct(id);
          loadProductsForSeller(parseInt(sellerIdInput.value || "1", 10));
        });
      });
    } catch (err) {
      productsTableBody.innerHTML = `<tr><td colspan='6'>Error: ${err.message}</td></tr>`;
    }
  }

  // Delete product
  async function deleteProduct(id) {
    const res = await fetch(PRODUCT_URL(id), { method: "DELETE" });
    const j = await res.json();
    if (!res.ok) throw new Error(j.detail || JSON.stringify(j));
    return j;
  }

  // Open edit modal
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
    document.getElementById("edit_status").value = j.status || "pending";

    editModal.classList.remove("hidden");
  }

  // Handle edit form submit
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
    loadProductsForSeller(parseInt(sellerIdInput.value || "1", 10));
  });

  closeEdit.addEventListener("click", () => {
    editModal.classList.add("hidden");
  });

  // initial load
  refreshBtn.addEventListener("click", () => {
    loadProductsForSeller(parseInt(sellerIdInput.value || "1", 10));
  });

  // load products on start
  loadProductsForSeller(parseInt(sellerIdInput.value || "1", 10));
});
