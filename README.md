# SmartCart

**SmartCart** is a powerful **Semantic Search Engine** designed to be integrated into any existing e-commerce platform. It supercharges your online store with AI-powered search capabilities, allowing customers to find products using natural language ("something warm for winter") or by uploading images.

Unlike traditional keyword search, SmartCart uses OpenAI's **CLIP model** and **FAISS** vector database to understand the _context and meaning_ of user queries.

## Integration

SmartCart is built as a standalone microservice (API) that can easily plug into your existing e-commerce architecture (Shopify, WooCommerce, Magento, or custom builds).

- **Sync Products:** Push your product catalog to SmartCart's database.
- **Search API:** Add a "Search with Image" feature and integrate our smart search bar to query SmartCart's `/search` endpoints.
- **Results:** Receive ranked, semantically relevant product IDs to display on your frontend.

## Features

### AI Semantic Search

- **Hybrid Search:** Combines semantic understanding with traditional filtering.

### User Roles & Portals

- **Customer Portal:**
  - Browse and search products.
  - **AI Chat:** Ask questions about specific products (e.g., "Is this good for running?").
  - Responsive, modern UI.
- **Seller Dashboard:**
  - Register and Login.
  - Add new products with images.
  - Manage inventory (Edit/Delete products).
  - View product status (Pending/Approved).
- **Admin Dashboard:**
  - **Approval Workflow:** Review and approve/reject new products from sellers.
  - **Model Training:** "Train" the AI model (rebuild FAISS index) to include new products in search results.
  - **Maintenance:** Cleanup orphan images and permanently remove deleted products.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+)
- **Database:** PostgreSQL
- **AI/ML:**
  - **Model:** `openai/clip-vit-base-patch32` (via HuggingFace Transformers)
  - **Vector DB:** FAISS (Facebook AI Similarity Search)
- **Frontend:** Vanilla HTML/CSS/JavaScript (No complex build steps required)
- **Infrastructure:** Docker & Docker Compose

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** installed on your machine.

### Option 1: Run with Docker (Recommended)

This is the easiest way to run the full stack (App + DB + pgAdmin).

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd smartcart
    ```

2.  **Create a `.env` file:**
    Copy the sample configuration file:

    ```bash
    cp .env.example .env
    ```

    Then update the values (passwords, API keys) in `.env` as needed.

3.  **Start the application:**

    ```bash
    docker compose up -d --build
    ```

4.  **Access the App:**
    - **Customer UI:** [http://localhost:8000](http://localhost:8000)
    - **Seller UI:** [http://localhost:8000/static/seller/login.html](http://localhost:8000/static/seller/login.html)
    - **Admin UI:** [http://localhost:8000/static/admin/index.html](http://localhost:8000/static/admin/index.html)
    - **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
    - **pgAdmin (DB GUI):** [http://localhost:5050](http://localhost:5050)

### Option 2: Run Locally (For Development)

1.  **Set up Python Environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Run PostgreSQL:**
    You still need a database. You can use the Docker DB:

    ```bash
    docker compose up -d db
    ```

3.  **Configure Environment:**
    Update your `.env` file to point to localhost:

    ```bash
    POSTGRES_HOST=localhost
    ```

4.  **Run the Server:**
    ```bash
    uvicorn app.main:app --reload
    ```

## 🧪 Testing

The project uses `pytest` for automated testing.

1.  **Install Test Dependencies:**
    (Included in `requirements.txt`)

    ```bash
    pip install pytest httpx
    ```

2.  **Run Tests:**
    ```bash
    python3 -m pytest
    ```
    - Runs tests for Admin, Seller, Search, and Main endpoints.
    - **Note:** Tests are configured to run locally (connecting to `localhost` DB).

## 📂 Project Structure

```
smartcart/
├── app/
│   ├── core/           # Config and settings
│   ├── db/             # Database connection and models
│   ├── routers/        # API Endpoints (admin, seller, search, etc.)
│   ├── schemas/        # Pydantic models (Request/Response schemas)
│   ├── services/       # Business logic (AI, Product, Auth)
│   ├── static/         # Frontend files (HTML/CSS/JS)
│   ├── utils/          # Helper functions
│   └── main.py         # App entry point
├── tests/              # Automated tests
├── docker-compose.yml  # Docker services config
├── Dockerfile          # API container definition
├── requirements.txt    # Python dependencies
└── README.md           # You are here!
```

## 🛡️ Admin Access

- **Admin ID:** Configured in `.env` (Default: `12345`).
- Use this ID to log in to the Admin Dashboard.

## 🤝 Contributing

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.
