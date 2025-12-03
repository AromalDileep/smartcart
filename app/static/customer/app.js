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

    // Show preview with animation
    const reader = new FileReader();
    reader.onload = function (e) {
      document.getElementById("imagePreview").src = e.target.result;
      const container = document.getElementById("imagePreviewContainer");
      container.classList.remove("hidden");
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
    showNotification("Please enter text or upload an image", "warning");
    return;
  }

  // Show loading state
  showLoading();

  try {
    // TEXT ONLY
    if (text && !selectedImageFile) {
      const res = await fetch(
        `${API_BASE}/text?query=${encodeURIComponent(text)}&k=20`
      );
      const data = await res.json();
      return renderResults(data);
    }

    // IMAGE ONLY
    if (!text && selectedImageFile) {
      const formData = new FormData();
      formData.append("image", selectedImageFile);

      const res = await fetch(`${API_BASE}/image?k=20`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      return renderResults(data);
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

    const data = await res.json();
    return renderResults(data);
  } catch (error) {
    console.error("Search error:", error);
    showNotification(
      "An error occurred during search. Please try again.",
      "error"
    );
    document.getElementById("results").innerHTML = "";
  }
}

/* ================================
   LOADING STATE
================================ */
function showLoading() {
  const container = document.getElementById("results");
  container.innerHTML = '<div class="loading">Searching for products...</div>';
}

/* ================================
   NOTIFICATION SYSTEM
================================ */
function showNotification(message, type = "info") {
  // Create notification element
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${
      type === "error" ? "#f56565" : type === "warning" ? "#ed8936" : "#48bb78"
    };
    color: white;
    padding: 16px 24px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    z-index: 2000;
    animation: slideIn 0.3s ease;
    font-weight: 600;
  `;

  document.body.appendChild(notification);

  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.animation = "slideOut 0.3s ease";
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Add animation styles
const style = document.createElement("style");
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

/* ================================
   RENDER RESULTS
================================ */
function renderResults(list) {
  const container = document.getElementById("results");
  container.innerHTML = "";

  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: white;">
        <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
        <h3 style="font-size: 24px; margin-bottom: 8px;">No results found</h3>
        <p style="font-size: 16px; opacity: 0.9;">Try adjusting your search terms or filters</p>
      </div>
    `;
    return;
  }

  list.forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "product-card";
    div.style.animationDelay = `${index * 0.05}s`;

    div.innerHTML = `
      <img src="${item.image_url}" alt="product image" loading="lazy">
      <div class="product-title">${escapeHtml(item.title)}</div>
      <div class="product-price">${item.price ?? "N/A"}</div>
      <div class="product-desc">${escapeHtml(item.description ?? "")}</div>
      <button class="ask-btn" onclick="openChatModal(${item.id}, '${escapeHtml(
      item.title
    ).replace(/'/g, "\\'")}')">
        💬 Ask AI Assistant
      </button>
    `;

    container.appendChild(div);
  });
}

/* ================================
   UTILITY FUNCTION
================================ */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/* ================================
   CHAT MODAL SYSTEM
================================ */
let currentProductId = null;
let currentProductTitle = null;

const chatModal = document.getElementById("chatModal");
const chatCloseBtn = document.getElementById("chatCloseBtn");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const chatQuestion = document.getElementById("chatQuestion");
const chatProductTitle = document.getElementById("chatProductTitle");

// Open chat modal
function openChatModal(productId, title) {
  currentProductId = productId;
  currentProductTitle = title;

  // Update title
  chatProductTitle.textContent = `Ask about: ${title}`;

  // Clear chat history
  chatMessages.innerHTML = "";

  // Clear input
  chatQuestion.value = "";

  // Show modal
  chatModal.style.display = "flex";

  // Focus on input
  setTimeout(() => {
    chatQuestion.focus();
  }, 100);
}

// Close chat modal
function closeChatModal() {
  chatModal.style.display = "none";
  currentProductId = null;
  currentProductTitle = null;
}

// Close button click
chatCloseBtn.addEventListener("click", closeChatModal);

// Close on overlay click
chatModal
  .querySelector(".chat-overlay")
  .addEventListener("click", closeChatModal);

// Close on Escape key
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && chatModal.style.display === "flex") {
    closeChatModal();
  }
});

// Submit question form
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = chatQuestion.value.trim();
  if (!question) return;

  // Append user message
  appendMessage("You", question, "user");

  // Clear input
  chatQuestion.value = "";

  // Disable input and button
  chatQuestion.disabled = true;
  const submitBtn = chatForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  submitBtn.textContent = "Thinking...";

  try {
    const payload = {
      product_id: currentProductId,
      question: question,
    };

    const res = await fetch(`${API_BASE}/ask-question`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (data.error) {
      appendMessage("Assistant", "Error: " + data.error, "ai");
    } else {
      appendMessage(
        "Assistant",
        data.answer || "I couldn't find an answer to that question.",
        "ai"
      );
    }
  } catch (err) {
    console.error("Error fetching answer:", err);
    appendMessage(
      "Assistant",
      "I'm having trouble connecting right now. Please try again later.",
      "ai"
    );
  } finally {
    // Re-enable input and button
    chatQuestion.disabled = false;
    submitBtn.disabled = false;
    submitBtn.textContent = "Ask";
    chatQuestion.focus();
  }
});

// Append message helper
function appendMessage(sender, text, type) {
  const msgDiv = document.createElement("div");
  msgDiv.className = type === "user" ? "chat-msg user-msg" : "chat-msg ai-msg";

  // Format message with sender label
  const senderLabel = document.createElement("strong");
  senderLabel.textContent = sender + ": ";
  senderLabel.style.display = "block";
  senderLabel.style.marginBottom = "4px";
  senderLabel.style.fontSize = "0.85rem";
  senderLabel.style.opacity = "0.8";

  const messageText = document.createElement("span");
  messageText.textContent = text;

  msgDiv.appendChild(senderLabel);
  msgDiv.appendChild(messageText);

  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  });
});
