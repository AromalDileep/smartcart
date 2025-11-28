const API_BASE = "http://localhost:8000/search";

/* ================================
   🔍 TEXT SEARCH
================================ */
async function textSearch() {
  const query = document.getElementById("textQuery").value;
  if (!query) return alert("Enter search text");

  const res = await fetch(
    `${API_BASE}/text?query=${encodeURIComponent(query)}&k=20`
  );

  renderResults(await res.json());
}

/* ================================
   🖼️ IMAGE SEARCH
================================ */
async function imageSearch() {
  const file = document.getElementById("imageInput").files[0];
  if (!file) return alert("Select an image");

  const formData = new FormData();
  formData.append("image", file);

  const res = await fetch(`${API_BASE}/image?k=20`, {
    method: "POST",
    body: formData,
  });

  renderResults(await res.json());
}

/* ================================
   🧪 HYBRID SEARCH
================================ */
async function hybridSearch() {
  const file = document.getElementById("hybridImage").files[0];
  const text = document.getElementById("hybridText").value;

  if (!file && !text) return alert("Provide at least text or an image");

  const weight = parseFloat(document.getElementById("weightSlider").value);

  const formData = new FormData();
  formData.append("text", text);
  formData.append("image", file);
  formData.append("w_image", weight);
  formData.append("w_text", 1 - weight);

  const res = await fetch(`${API_BASE}/hybrid?k=20`, {
    method: "POST",
    body: formData,
  });

  renderResults(await res.json());
}

/* ================================
   🎨 RESULT RENDERING
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

/* Update weight label */
document.getElementById("weightSlider").oninput = function () {
  document.getElementById("weightValue").innerText = this.value;
};
