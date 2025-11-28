const API_BASE = "http://localhost:8000/search";

async function textSearch() {
  const query = document.getElementById("textQuery").value;
  if (!query) return alert("Enter search text");

  const res = await fetch(
    `${API_BASE}/text?query=${encodeURIComponent(query)}&k=20`
  );
  const data = await res.json();
  renderResults(data);
}

function renderResults(list) {
  const container = document.getElementById("results");
  container.innerHTML = "";

  if (list.length === 0) {
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
            <div class="card-actions">
                <!-- Placeholder for future buttons -->
            </div>
        `;

    container.appendChild(div);
  });
}
