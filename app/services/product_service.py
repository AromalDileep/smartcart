from app.db.database import get_connection
from app.schemas.product_schema import ProductCreate, ProductUpdate


# -----------------------------------
# CREATE PRODUCT (Seller uploads)
# -----------------------------------
def create_product(product: ProductCreate):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products 
        (title, description, price, image, status, main_category, categories, features, details, product_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        product.title,
        product.description,
        product.price,
        product.image,
        "pending",
        product.main_category,
        product.categories,
        product.features,
        product.details,
        product.product_url
    ))

    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


# -----------------------------------
# GET PRODUCT BY ID
# -----------------------------------
def get_product(product_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id = %s;", (product_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row


# -----------------------------------
# GET ALL PRODUCTS
# -----------------------------------
def get_all_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY id ASC;")
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows


# -----------------------------------
# UPDATE PRODUCT
# -----------------------------------
def update_product(product_id: int, product: ProductUpdate):
    conn = get_connection()
    cur = conn.cursor()

    updates = []
    values = []

    fields = {
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "image": product.image,
        "main_category": product.main_category,
        "categories": product.categories,
        "features": product.features,
        "details": product.details,
        "product_url": product.product_url,
        "status": product.status
    }

    for key, value in fields.items():
        if value is not None:
            updates.append(f"{key} = %s")
            values.append(value)

    if not updates:
        return False

    values.append(product_id)
    query = f"UPDATE products SET {', '.join(updates)} WHERE id = %s;"
    cur.execute(query, tuple(values))

    conn.commit()
    cur.close()
    conn.close()
    return True


# -----------------------------------
# DELETE PRODUCT
# -----------------------------------
def delete_product(product_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id = %s;", (product_id,))
    conn.commit()

    cur.close()
    conn.close()
    return True
