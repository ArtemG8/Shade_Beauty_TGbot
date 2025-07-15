# db_utils.py
import sqlite3

DATABASE_NAME = 'salon_services.db'

def get_connection():
    """Устанавливает соединение с базой данных."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Позволяет получать строки как объекты, к которым можно обращаться по имени колонки
    return conn

def get_main_categories():
    """Возвращает список основных категорий (у которых нет родителя)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, title FROM categories WHERE parent_slug IS NULL ORDER BY title")
    categories = [{"id": row["id"], "slug": row["slug"], "title": row["title"]} for row in cursor.fetchall()]
    conn.close()
    return categories

def get_all_categories_flat():
    """Возвращает плоский список всех категорий для выбора (с id и title)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, title, parent_slug FROM categories ORDER BY title")
    categories = [{"id": row["id"], "slug": row["slug"], "title": row["title"], "parent_slug": row["parent_slug"]} for row in cursor.fetchall()]
    conn.close()
    return categories


def get_category_by_slug(slug: str):
    """Возвращает данные категории по ее slug."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, title, parent_slug FROM categories WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row) # Возвращаем как словарь
    return None

def get_category_by_id(category_id: int):
    """Возвращает данные категории по ее ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, title, parent_slug FROM categories WHERE id = ?", (category_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_subcategories(parent_slug: str):
    """Возвращает список подкатегорий для данной родительской категории."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, slug, title FROM categories WHERE parent_slug = ? ORDER BY title", (parent_slug,))
    subcategories = [{"id": row["id"], "slug": row["slug"], "title": row["title"]} for row in cursor.fetchall()]
    conn.close()
    return subcategories

def get_services_by_category_slug(category_slug: str):
    """Возвращает список услуг для данной категории/подкатегории (с ID)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, description FROM services WHERE category_slug = ? ORDER BY name", (category_slug,))
    services = []
    for row in cursor.fetchall():
        service = {"id": row["id"], "name": row["name"], "price": row["price"]}
        if row["description"]:
            service["description"] = row["description"]
        services.append(service)
    conn.close()
    return services

def get_service_by_id(service_id: int):
    """Возвращает данные услуги по ее ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, description, category_slug FROM services WHERE id = ?", (service_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


# --- Функции для админ-панели (CRUD) ---

def add_category(slug: str, title: str, parent_slug: str = None):
    """Добавляет новую категорию в БД."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (slug, title, parent_slug) VALUES (?, ?, ?)",
                       (slug, title, parent_slug))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # Если slug уже существует
        return False
    finally:
        conn.close()

def update_category(category_id: int, new_title: str):
    """Обновляет название категории по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE categories SET title = ? WHERE id = ?", (new_title, category_id))
    conn.commit()
    conn.close()

def delete_category(category_id: int):
    """Удаляет категорию по ID. Возвращает True при успехе, False если есть связанные услуги/подкатегории."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Проверяем, есть ли подкатегории, которые на нее ссылаются
        cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_slug = (SELECT slug FROM categories WHERE id = ?)", (category_id,))
        if cursor.fetchone()[0] > 0:
            return False # Есть дочерние подкатегории

        # Проверяем, есть ли услуги, которые на нее ссылаются
        cursor.execute("SELECT COUNT(*) FROM services WHERE category_slug = (SELECT slug FROM categories WHERE id = ?)", (category_id,))
        if cursor.fetchone()[0] > 0:
            return False # Есть связанные услуги

        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при удалении категории: {e}")
        return False
    finally:
        conn.close()

def add_service(name: str, price: str, category_slug: str, description: str = None):
    """Добавляет новую услугу в БД."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO services (name, price, description, category_slug) VALUES (?, ?, ?, ?)",
                   (name, price, description, category_slug))
    conn.commit()
    conn.close()

def update_service(service_id: int, name: str, price: str, description: str):
    """Обновляет услугу по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE services SET name = ?, price = ?, description = ? WHERE id = ?",
                   (name, price, description, service_id))
    conn.commit()
    conn.close()

def delete_service(service_id: int):
    """Удаляет услугу по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()

