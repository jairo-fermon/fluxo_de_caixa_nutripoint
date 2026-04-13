import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "app.db"


RECEIVE_METHODS_SEED = [
    ("Alelo", 0.08),
    ("Amex", 0.0283),
    ("Boleto", 0.0),
    ("Dinheiro", 0.0),
    ("Elo Crédito", 0.0259),
    ("Elo Débito", 0.0122),
    ("Ifood", 0.32),
    ("Master Crédito", 0.0205),
    ("Master Débito", 0.0092),
    ("Pix Banco", 0.0),
    ("Pix Stone", 0.005),
    ("Sodexo", 0.08),
    ("Ticket", 0.08),
    ("Vale Refeição", 0.08),
    ("Visa Crédito", 0.0205),
    ("Visa Débito", 0.0092),
]


PAYMENT_METHODS_SEED = [
    ("Empresarial Crédito", 0.0),
    ("Empresarial Débito", 0.0),
    ("PIX", 0.0),
    ("Reserva banco", 0.0),
    ("Boleto", 0.0),
]


CATEGORY_SEED = [
    ("Alimentos", "RECEITA", "RECEITA"),
    ("Cursos", "RECEITA", "RECEITA"),
    ("Diversos", "RECEITA", "RECEITA"),
    ("Agua mineral", "DESPESA", "CUSTOS DIRETOS"),
    ("Carne Bovina", "DESPESA", "CUSTOS DIRETOS"),
    ("Embalagem/Etiqueta", "DESPESA", "CUSTOS DIRETOS"),
    ("Filé Mignon", "DESPESA", "CUSTOS DIRETOS"),
    ("Frango", "DESPESA", "CUSTOS DIRETOS"),
    ("Matéria prima", "DESPESA", "CUSTOS DIRETOS"),
    ("Peixe", "DESPESA", "CUSTOS DIRETOS"),
    ("Salmão", "DESPESA", "CUSTOS DIRETOS"),
    ("Comissão", "DESPESA", "DESPESAS VENDAS"),
    ("Frete", "DESPESA", "DESPESAS VENDAS"),
    ("Imposto", "DESPESA", "DESPESAS VENDAS"),
    ("Taxa Cartão", "DESPESA", "DESPESAS VENDAS"),
    ("Taxa Ifood", "DESPESA", "DESPESAS VENDAS"),
    ("Aluguel", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Aluguel Maquina", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Cagece", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Caju", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Contador", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Depreciação", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Energia", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("FGTS", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Gás", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("INSS", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Internet", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("IPTU", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Manutenção", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Marketing", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Plano de Saúde", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Provisões de salários", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Registro marca", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Salários", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Seguro Predio", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Sistema ERP", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Uniformes e EPIs", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Utensílios", "DESPESA", "DESPESAS OPERACIONAIS"),
    ("Despesa Diversa", "DESPESA", "DESPESAS DIVERSAS"),
    ("Juros e multas", "DESPESA", "DESPESAS DIVERSAS"),
    ("Outras despesas", "DESPESA", "DESPESAS DIVERSAS"),
    ("Tarifas bancárias", "DESPESA", "DESPESAS DIVERSAS"),
    ("Transferência de Lucro", "DESPESA", "TRANSFERÊNCIA DE LUCRO"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_value: str) -> bool:
    salt_hex, digest_hex = stored_value.split(":")
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(candidate, expected)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def expires_at(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def month_start(value: str | None) -> str | None:
    if not value:
        return None
    parsed = date.fromisoformat(value)
    return parsed.replace(day=1).isoformat()


def add_column_if_missing(cur, table: str, column: str, ddl: str):
    current = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in current:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def dedupe_named_table(cur, table: str):
    ids_to_keep = [
        row["id"]
        for row in cur.execute(f"SELECT MIN(id) AS id FROM {table} GROUP BY name").fetchall()
    ]
    if not ids_to_keep:
        return
    placeholders = ",".join("?" for _ in ids_to_keep)
    cur.execute(f"DELETE FROM {table} WHERE id NOT IN ({placeholders})", ids_to_keep)


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            active INTEGER NOT NULL DEFAULT 1,
            approved INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(cur, "users", "approved", "approved INTEGER NOT NULL DEFAULT 1")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            user_email TEXT,
            user_role TEXT,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            entry_type TEXT NOT NULL CHECK(entry_type IN ('RECEITA', 'DESPESA')),
            dre_group TEXT NOT NULL
        )
        """
    )
    add_column_if_missing(cur, "categories", "type", "type TEXT")
    add_column_if_missing(cur, "categories", "entry_type", "entry_type TEXT")
    add_column_if_missing(cur, "categories", "dre_group", "dre_group TEXT")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            fee_percent REAL NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS receive_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            fee_percent REAL NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cash_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_date TEXT,
            entry_type TEXT,
            category_name TEXT,
            dre_group TEXT,
            payment_method TEXT,
            gross_amount REAL NOT NULL DEFAULT 0,
            fee_percent REAL NOT NULL DEFAULT 0,
            fee_amount REAL NOT NULL DEFAULT 0,
            net_amount REAL NOT NULL DEFAULT 0,
            payment_date TEXT,
            competence_month TEXT,
            notes TEXT,
            consider_dre INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'planejado',
            created_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            description TEXT,
            amount REAL,
            kind TEXT,
            due_date TEXT,
            category_id INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """
    )

    # Migration support from the first MVP.
    add_column_if_missing(cur, "cash_entries", "fact_date", "fact_date TEXT")
    add_column_if_missing(cur, "cash_entries", "entry_type", "entry_type TEXT")
    add_column_if_missing(cur, "cash_entries", "category_name", "category_name TEXT")
    add_column_if_missing(cur, "cash_entries", "dre_group", "dre_group TEXT")
    add_column_if_missing(cur, "cash_entries", "payment_method", "payment_method TEXT")
    add_column_if_missing(cur, "cash_entries", "gross_amount", "gross_amount REAL NOT NULL DEFAULT 0")
    add_column_if_missing(cur, "cash_entries", "fee_percent", "fee_percent REAL NOT NULL DEFAULT 0")
    add_column_if_missing(cur, "cash_entries", "fee_amount", "fee_amount REAL NOT NULL DEFAULT 0")
    add_column_if_missing(cur, "cash_entries", "net_amount", "net_amount REAL NOT NULL DEFAULT 0")
    add_column_if_missing(cur, "cash_entries", "payment_date", "payment_date TEXT")
    add_column_if_missing(cur, "cash_entries", "competence_month", "competence_month TEXT")
    add_column_if_missing(cur, "cash_entries", "consider_dre", "consider_dre INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(cur, "cash_entries", "updated_at", "updated_at TEXT")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conciliation_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL,
            expected_amount REAL NOT NULL,
            matched_amount REAL,
            status TEXT NOT NULL DEFAULT 'pendente',
            created_at TEXT NOT NULL
        )
        """
    )

    users_count = cur.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    if not users_count:
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, role, active, approved, created_at)
            VALUES (?, ?, ?, 'admin', 1, 1, ?)
            """,
            ("Administrador", "admin@nutripoint.local", hash_password("admin123"), now_utc()),
        )

    for name, percent in RECEIVE_METHODS_SEED:
        cur.execute(
            "INSERT OR IGNORE INTO receive_methods (name, fee_percent) VALUES (?, ?)",
            (name, percent),
        )

    for name, percent in PAYMENT_METHODS_SEED:
        cur.execute(
            "INSERT OR IGNORE INTO payment_methods (name, fee_percent) VALUES (?, ?)",
            (name, percent),
        )

    for name, entry_type, dre_group in CATEGORY_SEED:
        cur.execute(
            "INSERT OR IGNORE INTO categories (name, type, entry_type, dre_group) VALUES (?, ?, ?, ?)",
            (name, entry_type.lower(), entry_type, dre_group),
        )

    dedupe_named_table(cur, "categories")
    dedupe_named_table(cur, "payment_methods")
    dedupe_named_table(cur, "receive_methods")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_unique ON categories(name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_methods_name_unique ON payment_methods(name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_receive_methods_name_unique ON receive_methods(name)")

    cur.execute(
        """
        UPDATE categories
        SET entry_type = CASE
            WHEN entry_type IS NOT NULL AND entry_type <> '' THEN entry_type
            WHEN lower(COALESCE(type, '')) = 'receita' THEN 'RECEITA'
            ELSE 'DESPESA'
        END
        """
    )
    cur.execute(
        """
        UPDATE categories
        SET dre_group = COALESCE(NULLIF(dre_group, ''), CASE
            WHEN entry_type = 'RECEITA' THEN 'RECEITA'
            ELSE 'DESPESAS OPERACIONAIS'
        END)
        """
    )
    cur.execute("DELETE FROM categories WHERE name = 'DIVERSOS' AND EXISTS (SELECT 1 FROM categories c2 WHERE c2.name = 'Diversos')")
    cur.execute("UPDATE categories SET name = 'Diversos' WHERE name = 'DIVERSOS'")
    cur.execute("DELETE FROM categories WHERE name IN ('Vendas', 'Serviços', 'Fornecedores', 'Despesas Operacionais')")
    dedupe_named_table(cur, "categories")

    cur.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('opening_balance', '0')"
    )
    cur.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('reference_model_version', '0')"
    )

    # Normalize old MVP rows into the richer structure and remove the validation row.
    cur.execute("DELETE FROM cash_entries WHERE description = 'Teste inicial'")
    cur.execute(
        """
        UPDATE cash_entries
        SET fact_date = COALESCE(fact_date, due_date),
            payment_date = COALESCE(payment_date, due_date),
            competence_month = COALESCE(competence_month, substr(COALESCE(due_date, date('now')), 1, 7) || '-01'),
            entry_type = COALESCE(entry_type, CASE WHEN kind = 'entrada' THEN 'RECEITA' ELSE 'DESPESA' END),
            category_name = COALESCE(category_name, description, 'Sem categoria'),
            dre_group = COALESCE(dre_group, CASE WHEN kind = 'entrada' THEN 'RECEITA' ELSE 'DESPESAS OPERACIONAIS' END),
            payment_method = COALESCE(payment_method, 'Pix Banco'),
            gross_amount = CASE WHEN gross_amount = 0 THEN COALESCE(amount, 0) ELSE gross_amount END,
            net_amount = CASE WHEN net_amount = 0 THEN COALESCE(amount, 0) ELSE net_amount END,
            description = COALESCE(description, category_name)
        """
    )

    version = cur.execute("SELECT value FROM settings WHERE key = 'reference_model_version'").fetchone()["value"]
    if version != "2":
        receive_names = [name for name, _ in RECEIVE_METHODS_SEED]
        payment_names = [name for name, _ in PAYMENT_METHODS_SEED]
        category_names = [name for name, _, _ in CATEGORY_SEED]
        cur.execute(
            f"DELETE FROM receive_methods WHERE name NOT IN ({','.join('?' for _ in receive_names)})",
            receive_names,
        )
        cur.execute(
            f"DELETE FROM payment_methods WHERE name NOT IN ({','.join('?' for _ in payment_names)})",
            payment_names,
        )
        cur.execute(
            f"DELETE FROM categories WHERE name NOT IN ({','.join('?' for _ in category_names)})",
            category_names,
        )
        cur.execute("UPDATE settings SET value = '2' WHERE key = 'reference_model_version'")

    conn.commit()
    conn.close()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO sessions (user_id, session_token, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, token, expires_at(), now_utc()),
    )
    conn.commit()
    conn.close()
    return token


def delete_session(token: str):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_session(token: str):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT users.*
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.session_token = ?
          AND sessions.expires_at > ?
          AND users.active = 1
          AND users.approved = 1
        """,
        (token, now_utc()),
    ).fetchone()
    conn.close()
    return row


def list_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, email, role, active, approved, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def create_user(name: str, email: str, password: str, role: str, approved: int = 1):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO users (name, email, password_hash, role, active, approved, created_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (name, email, hash_password(password), role, approved, now_utc()),
    )
    conn.commit()
    conn.close()


def register_user(name: str, email: str, password: str):
    create_user(name, email, password, "user", approved=0)


def count_pending_users() -> int:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS total FROM users WHERE approved = 0").fetchone()["total"]
    conn.close()
    return int(total or 0)


def approve_user(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET approved = 1, active = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def delete_user(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user_password(user_id: int, password: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id))
    conn.commit()
    conn.close()


def update_user_name(user_id: int, name: str):
    conn = get_connection()
    conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    conn.commit()
    conn.close()


def update_user_role(user_id: int, role: str):
    conn = get_connection()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()


def create_audit_log(
    action: str,
    entity: str,
    *,
    user=None,
    entity_id: int | None = None,
    details: str = "",
    ip_address: str = "",
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO audit_logs (
            user_id, user_name, user_email, user_role, action, entity, entity_id, details, ip_address, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"] if user else None,
            user["name"] if user else "",
            user["email"] if user else "",
            user["role"] if user else "",
            action,
            entity,
            entity_id,
            details,
            ip_address,
            now_utc(),
        ),
    )
    conn.commit()
    conn.close()


def list_audit_logs(limit: int = 300):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, user_name, user_email, user_role, action, entity, entity_id, details, ip_address, created_at
        FROM audit_logs
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def set_opening_balance(value: str):
    conn = get_connection()
    conn.execute("UPDATE settings SET value = ? WHERE key = 'opening_balance'", (value,))
    conn.commit()
    conn.close()


def get_opening_balance() -> float:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = 'opening_balance'").fetchone()
    conn.close()
    return float(row["value"]) if row else 0.0


def dashboard_metrics(date_from: str | None = None, date_to: str | None = None):
    conn = get_connection()
    where = " WHERE 1=1 "
    params = []
    if date_from:
        where += " AND payment_date >= ?"
        params.append(date_from)
    if date_to:
        where += " AND payment_date <= ?"
        params.append(date_to)
    revenue = conn.execute(
        f"SELECT COALESCE(SUM(net_amount), 0) AS total FROM cash_entries {where} AND entry_type = 'RECEITA'",
        params,
    ).fetchone()["total"]
    expenses = conn.execute(
        f"SELECT COALESCE(SUM(net_amount), 0) AS total FROM cash_entries {where} AND entry_type = 'DESPESA'",
        params,
    ).fetchone()["total"]
    pending = conn.execute(
        "SELECT COUNT(*) AS total FROM conciliation_items WHERE status = 'pendente'"
    ).fetchone()["total"]
    total_entries = conn.execute(
        f"SELECT COUNT(*) AS total FROM cash_entries {where}",
        params,
    ).fetchone()["total"]
    users_total = conn.execute("SELECT COUNT(*) AS total FROM users WHERE active = 1").fetchone()["total"]
    chart_rows = conn.execute(
        f"""
        SELECT payment_date,
               SUM(CASE WHEN entry_type = 'RECEITA' THEN net_amount ELSE 0 END) AS entradas,
               SUM(CASE WHEN entry_type = 'DESPESA' THEN net_amount ELSE 0 END) AS saidas
        FROM cash_entries
        {where}
        GROUP BY payment_date
        ORDER BY payment_date
        """,
        params,
    ).fetchall()
    conn.close()
    timeline = [
        {
            "date": row["payment_date"],
            "entradas": row["entradas"] or 0,
            "saidas": row["saidas"] or 0,
        }
        for row in chart_rows
        if row["payment_date"]
    ]
    return {
        "revenue": revenue,
        "expenses": expenses,
        "balance": get_opening_balance() + revenue - expenses,
        "pending_conciliation": pending,
        "users_total": users_total,
        "total_entries": total_entries,
        "opening_balance": get_opening_balance(),
        "timeline": timeline,
        "filters": {"date_from": date_from or "", "date_to": date_to or ""},
    }


def list_categories(entry_type: str | None = None):
    conn = get_connection()
    if entry_type:
        rows = conn.execute(
            "SELECT * FROM categories WHERE entry_type = ? ORDER BY name",
            (entry_type,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM categories ORDER BY entry_type, dre_group, name").fetchall()
    conn.close()
    return rows


def get_category_by_id(category_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    conn.close()
    return row


def list_payment_methods():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM payment_methods ORDER BY name").fetchall()
    conn.close()
    return rows


def list_receive_methods():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM receive_methods ORDER BY name").fetchall()
    conn.close()
    return rows


def get_payment_method_by_id(payment_method_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM payment_methods WHERE id = ?", (payment_method_id,)).fetchone()
    conn.close()
    return row


def get_receive_method_by_id(receive_method_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM receive_methods WHERE id = ?", (receive_method_id,)).fetchone()
    conn.close()
    return row


def get_payment_method(name: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM payment_methods WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row


def get_receive_method(name: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM receive_methods WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row


def get_category(name: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row


def create_category(name: str, entry_type: str, dre_group: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO categories (name, type, entry_type, dre_group) VALUES (?, ?, ?, ?)",
        (name, entry_type.lower(), entry_type, dre_group),
    )
    conn.commit()
    conn.close()


def update_category(category_id: int, name: str, entry_type: str, dre_group: str):
    conn = get_connection()
    conn.execute(
        """
        UPDATE categories
        SET name = ?, type = ?, entry_type = ?, dre_group = ?
        WHERE id = ?
        """,
        (name, entry_type.lower(), entry_type, dre_group, category_id),
    )
    conn.commit()
    conn.close()


def delete_category(category_id: int):
    conn = get_connection()
    row = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.execute("UPDATE cash_entries SET category_name = 'Sem categoria' WHERE category_name = ?", (row["name"],))
    conn.commit()
    conn.close()


def create_payment_method(name: str, fee_percent: float):
    conn = get_connection()
    conn.execute(
        "INSERT INTO payment_methods (name, fee_percent) VALUES (?, ?)",
        (name, fee_percent),
    )
    conn.commit()
    conn.close()


def create_receive_method(name: str, fee_percent: float):
    conn = get_connection()
    conn.execute(
        "INSERT INTO receive_methods (name, fee_percent) VALUES (?, ?)",
        (name, fee_percent),
    )
    conn.commit()
    conn.close()


def update_payment_method(payment_method_id: int, name: str, fee_percent: float):
    conn = get_connection()
    previous = conn.execute("SELECT name FROM payment_methods WHERE id = ?", (payment_method_id,)).fetchone()
    conn.execute(
        """
        UPDATE payment_methods
        SET name = ?, fee_percent = ?
        WHERE id = ?
        """,
        (name, fee_percent, payment_method_id),
    )
    if previous:
        conn.execute("UPDATE cash_entries SET payment_method = ? WHERE payment_method = ?", (name, previous["name"]))
    conn.commit()
    conn.close()


def update_receive_method(receive_method_id: int, name: str, fee_percent: float):
    conn = get_connection()
    previous = conn.execute("SELECT name FROM receive_methods WHERE id = ?", (receive_method_id,)).fetchone()
    conn.execute(
        """
        UPDATE receive_methods
        SET name = ?, fee_percent = ?
        WHERE id = ?
        """,
        (name, fee_percent, receive_method_id),
    )
    if previous:
        conn.execute("UPDATE cash_entries SET payment_method = ? WHERE payment_method = ?", (name, previous["name"]))
    conn.commit()
    conn.close()


def delete_payment_method(payment_method_id: int):
    conn = get_connection()
    row = conn.execute("SELECT name FROM payment_methods WHERE id = ?", (payment_method_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM payment_methods WHERE id = ?", (payment_method_id,))
        conn.execute("UPDATE cash_entries SET payment_method = 'Pix Banco' WHERE payment_method = ?", (row["name"],))
    conn.commit()
    conn.close()


def delete_receive_method(receive_method_id: int):
    conn = get_connection()
    row = conn.execute("SELECT name FROM receive_methods WHERE id = ?", (receive_method_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM receive_methods WHERE id = ?", (receive_method_id,))
        conn.execute("UPDATE cash_entries SET payment_method = 'Pix Banco' WHERE payment_method = ?", (row["name"],))
    conn.commit()
    conn.close()


def calculate_entry_values(entry_type: str, payment_method: str, gross_amount: float):
    fee_percent = 0.0
    if entry_type == "RECEITA":
        payment = get_receive_method(payment_method)
        if payment:
            fee_percent = float(payment["fee_percent"])
    fee_amount = round(gross_amount * fee_percent, 2)
    net_amount = round(gross_amount - fee_amount, 2)
    return fee_percent, fee_amount, net_amount


def list_cash_entries(filters: dict | None = None):
    filters = filters or {}
    conn = get_connection()
    sql = """
        SELECT id, fact_date, entry_type, category_name, dre_group, payment_method,
               gross_amount, fee_percent, fee_amount, net_amount, payment_date,
               competence_month, notes, consider_dre, status, created_at
        FROM cash_entries
        WHERE 1=1
    """
    params = []
    if filters.get("entry_type"):
        sql += " AND entry_type = ?"
        params.append(filters["entry_type"])
    if filters.get("category_name"):
        sql += " AND category_name = ?"
        params.append(filters["category_name"])
    if filters.get("date_from"):
        sql += " AND fact_date >= ?"
        params.append(filters["date_from"])
    if filters.get("date_to"):
        sql += " AND fact_date <= ?"
        params.append(filters["date_to"])
    sql += " ORDER BY fact_date DESC, created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_cash_entry(entry_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM cash_entries WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    return row


def save_cash_entry(data: dict, user_id: int, entry_id: int | None = None):
    category = get_category(data["category_name"])
    dre_group = category["dre_group"] if category else data.get("dre_group", "RECEITA")
    fee_percent, fee_amount, net_amount = calculate_entry_values(
        data["entry_type"],
        data["payment_method"],
        float(data["gross_amount"]),
    )
    payload = (
        data["fact_date"],
        data["entry_type"],
        data["category_name"],
        dre_group,
        data["payment_method"],
        float(data["gross_amount"]),
        fee_percent,
        fee_amount,
        net_amount,
        data["payment_date"] or data["fact_date"],
        month_start(data["competence_month"] or data["fact_date"]),
        data.get("notes", ""),
        1,
        data.get("status", "planejado"),
        user_id,
        data["category_name"],
        float(data["gross_amount"]),
        "entrada" if data["entry_type"] == "RECEITA" else "saida",
        data["payment_date"] or data["fact_date"],
    )
    conn = get_connection()
    if entry_id is None:
        cursor = conn.execute(
            """
            INSERT INTO cash_entries (
                fact_date, entry_type, category_name, dre_group, payment_method,
                gross_amount, fee_percent, fee_amount, net_amount, payment_date,
                competence_month, notes, consider_dre, status, created_by,
                description, amount, kind, due_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload + (now_utc(),),
        )
        saved_id = cursor.lastrowid
    else:
        conn.execute(
            """
            UPDATE cash_entries
            SET fact_date = ?, entry_type = ?, category_name = ?, dre_group = ?, payment_method = ?,
                gross_amount = ?, fee_percent = ?, fee_amount = ?, net_amount = ?, payment_date = ?,
                competence_month = ?, notes = ?, consider_dre = ?, status = ?, created_by = ?,
                description = ?, amount = ?, kind = ?, due_date = ?, updated_at = ?
            WHERE id = ?
            """,
            payload + (now_utc(), entry_id),
        )
        saved_id = entry_id
    conn.commit()
    conn.close()
    return saved_id


def delete_cash_entry(entry_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM cash_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def cash_flow_summary(start_date: str | None, opening_balance: float, days: int = 30):
    conn = get_connection()
    if not start_date:
        start_date = date.today().isoformat()
    start = date.fromisoformat(start_date)
    end = start + timedelta(days=max(days - 1, 0))
    daily = conn.execute(
        """
        SELECT payment_date AS flow_date,
               SUM(CASE WHEN entry_type = 'RECEITA' THEN net_amount ELSE 0 END) AS entradas,
               SUM(CASE WHEN entry_type = 'DESPESA' THEN net_amount ELSE 0 END) AS saidas
        FROM cash_entries
        WHERE payment_date >= ? AND payment_date <= ?
        GROUP BY payment_date
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    conn.close()

    grouped = {
        row["flow_date"]: {
            "entradas": row["entradas"] or 0,
            "saidas": row["saidas"] or 0,
        }
        for row in daily
    }
    balance = opening_balance
    rows = []
    for offset in range(days):
        current_date = start + timedelta(days=offset)
        current_key = current_date.isoformat()
        entradas = grouped.get(current_key, {}).get("entradas", 0)
        saidas = grouped.get(current_key, {}).get("saidas", 0)
        final_balance = balance + entradas - saidas
        rows.append(
            {
                "date": current_key,
                "opening": balance,
                "entradas": entradas,
                "saidas": saidas,
                "closing": final_balance,
            }
        )
        balance = final_balance
    return rows


def dre_summary(competence_month: str | None = None):
    conn = get_connection()
    params = []
    where = " WHERE 1=1 "
    if competence_month:
        where += " AND competence_month = ?"
        params.append(f"{competence_month}-01")

    rows = conn.execute(
        f"""
        SELECT
            SUM(CASE WHEN entry_type = 'RECEITA' THEN gross_amount ELSE 0 END) AS gross_revenue,
            SUM(CASE WHEN entry_type = 'DESPESA' AND category_name = 'Imposto' THEN gross_amount ELSE 0 END) AS taxes,
            SUM(CASE WHEN dre_group = 'CUSTOS DIRETOS' THEN gross_amount ELSE 0 END) AS direct_costs,
            SUM(CASE WHEN entry_type = 'RECEITA' THEN fee_amount ELSE 0 END) AS selling_expenses,
            SUM(CASE WHEN dre_group = 'DESPESAS OPERACIONAIS' THEN gross_amount ELSE 0 END) AS operating_expenses,
            SUM(CASE WHEN entry_type = 'RECEITA' AND category_name = 'Diversos' THEN gross_amount ELSE 0 END) AS other_revenue,
            SUM(CASE WHEN dre_group = 'DESPESAS DIVERSAS' THEN gross_amount ELSE 0 END) AS other_expenses,
            SUM(CASE WHEN dre_group = 'TRANSFERÊNCIA DE LUCRO' THEN gross_amount ELSE 0 END) AS profit_transfer
        FROM cash_entries
        {where}
        """,
        params,
    ).fetchone()
    conn.close()

    gross_revenue = rows["gross_revenue"] or 0
    taxes = rows["taxes"] or 0
    net_revenue = gross_revenue - taxes
    direct_costs = rows["direct_costs"] or 0
    gross_profit = net_revenue - direct_costs
    selling_expenses = rows["selling_expenses"] or 0
    operating_expenses = rows["operating_expenses"] or 0
    operating_profit = gross_profit - selling_expenses - operating_expenses
    diverse_result = (rows["other_revenue"] or 0) - (rows["other_expenses"] or 0)
    pre_transfer = operating_profit + diverse_result
    profit_transfer = rows["profit_transfer"] or 0

    return {
        "gross_revenue": gross_revenue,
        "taxes": taxes,
        "net_revenue": net_revenue,
        "direct_costs": direct_costs,
        "gross_profit": gross_profit,
        "selling_expenses": selling_expenses,
        "operating_expenses": operating_expenses,
        "operating_profit": operating_profit,
        "diverse_result": diverse_result,
        "pre_transfer": pre_transfer,
        "profit_transfer": profit_transfer,
        "net_result": pre_transfer - profit_transfer,
    }


def list_conciliation_items():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM conciliation_items ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def conciliation_summary(filters: dict | None = None):
    filters = filters or {}
    conn = get_connection()
    sql = """
        SELECT
            id,
            competence_month,
            entry_type,
            payment_method,
            payment_date,
            fact_date,
            category_name,
            net_amount
        FROM cash_entries
        WHERE 1=1
    """
    params = []
    if filters.get("competence_month"):
        sql += " AND competence_month = ?"
        params.append(f"{filters['competence_month']}-01")
    if filters.get("entry_type"):
        sql += " AND entry_type = ?"
        params.append(filters["entry_type"])
    if filters.get("payment_method"):
        sql += " AND payment_method = ?"
        params.append(filters["payment_method"])
    sql += " ORDER BY payment_date DESC, fact_date DESC, created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    total = sum(float(item["net_amount"] or 0) for item in rows)
    conn.close()
    return {"rows": rows, "total_net_amount": total}
