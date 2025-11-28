const API_BASE = "http://localhost:8000/search";

let selectedImageFile = null;

/* ================================
   IMAGE PREVIEW HANDLING
================================ */
document
  .getElementById("imageInput")
  .addEventListener("change", function (event) {
    const file = event.target.files[0];
    if (!file) return;

    selectedImageFile = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
      document.getElementById("imagePreview").src = e.target.result;
      document
        .getElementById("imagePreviewContainer")
        .classList.remove("hidden");
    };
    reader.readAsDataURL(file);

    updateWeightBoxVisibility();
  });

function removeImage() {
  selectedImageFile = null;
  document.getElementById("imageInput").value = "";
  document.getElementById("imagePreviewContainer").classList.add("hidden");

  updateWeightBoxVisibility();
}

/* ================================
   ENTER KEY = SEARCH
================================ */
document
  .getElementById("searchInput")
  .addEventListener("keydown", function (e) {
    if (e.key === "Enter") performSearch();
  });

document.addEventListener("keydown", function (e) {
  if (e.key === "Enter") performSearch();
});

/* ================================
   WEIGHT SLIDER LOGIC
================================ */
document.getElementById("weightSlider").addEventListener("input", function () {
  document.getElementById("weightValue").innerText = this.value;
});

function updateWeightBoxVisibility() {
  const text = document.getElementById("searchInput").value.trim();
  const weightBox = document.getElementById("weightBox");

  if (text && selectedImageFile) {
    weightBox.classList.remove("hidden");
  } else {
    weightBox.classList.add("hidden");
  }
}

// When user types, show/hide weight slider
document
  .getElementById("searchInput")
  .addEventListener("input", updateWeightBoxVisibility);

/* ================================
   UNIFIED SEARCH LOGIC
================================ */
async function performSearch() {
  const text = document.getElementById("searchInput").value.trim();

  // Nothing provided
  if (!text && !selectedImageFile) {
    alert("Please enter text or upload an image");
    return;
  }

  // TEXT ONLY
  if (text && !selectedImageFile) {
    const res = await fetch(
      `${API_BASE}/text?query=${encodeURIComponent(text)}&k=20`
    );
    return renderResults(await res.json());
  }

  // IMAGE ONLY
  if (!text && selectedImageFile) {
    const formData = new FormData();
    formData.append("image", selectedImageFile);

    const res = await fetch(`${API_BASE}/image?k=20`, {
      method: "POST",
      body: formData,
    });

    return renderResults(await res.json());
  }

  // HYBRID (both)
  const w_image = parseFloat(document.getElementById("weightSlider").value);
  const w_text = 1 - w_image;

  const formData = new FormData();
  formData.append("image", selectedImageFile);
  formData.append("text", text);
  formData.append("w_image", w_image);
  formData.append("w_text", w_text);

  const res = await fetch(`${API_BASE}/hybrid?k=20`, {
    method: "POST",
    body: formData,
  });

  return renderResults(await res.json());
}

/* ================================
   RENDER RESULTS
================================ */
function renderResults(list) {
  const container = document.getElementById("results");
  container.innerHTML = "";

  if (!list || list.length === 0) {
    container.innerHTML = "<p>No results found.</p>";
    return;
  }

  list.forEach((item) => {
    const div = document.createElement("div");
    div.className = "product-card";

    div.innerHTML = `
      <img src="${item.image_url}" alt="image">
      <div class="product-title">${item.title}</div>
      <div class="product-price">${item.price ?? "N/A"}</div>
      <div class="product-desc">${item.description ?? ""}</div>
    `;

    container.appendChild(div);
  });
}
