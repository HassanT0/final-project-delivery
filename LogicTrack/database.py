"""
SQLite database manager for LogicTrack.

Tables
------
  - users         (id, email, password, role)
  - items         (id, name, sku, price, quantity, category, image_path,
                   last_restock, expires_on, min_stock_level, supplier_id)
  - suppliers     (id, name, contact, phone, email, address)
  - transactions  (id, item_id, change, reason, timestamp)

Every public method returns dataclass instances from `models.py` instead
of raw tuples, and every database operation is wrapped in a try/except
that logs the failure via the standard `logging` module. The first time
the app runs, the database is seeded with the sample data shown in the
design-document mockups.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import Iterator, List, Optional, Sequence, Tuple

from models import (
    Item,
    RestockSummary,
    SalesSummary,
    Supplier,
    Transaction,
    User,
)

# ---------------------------------------------------------------------------
# Logging — emit DB issues to the project-level logger so callers can see
# what happened without bringing the whole UI down.
# ---------------------------------------------------------------------------
log = logging.getLogger("logictrack.db")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    log.addHandler(handler)
log.setLevel(logging.INFO)


DB_FILE = "logictrack.db"


class DatabaseError(RuntimeError):
    """Wrapper raised when an internal sqlite3 error needs to bubble up."""


class Database:
    """Single point of access to the LogicTrack SQLite store."""

    def __init__(self, db_path: str = DB_FILE) -> None:
        self.db_path = db_path
        try:
            self._init_schema()
            self._migrate_items_schema()
            self._create_indexes()
            self._seed_if_empty()
        except sqlite3.Error as exc:
            log.exception("Failed to initialise database: %s", exc)
            raise DatabaseError(str(exc)) from exc

    # ------------------------------------------------------------------ helpers
    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        """Yield a cursor inside a connection that auto-closes."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn.cursor()
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------ schema
    def _init_schema(self) -> None:
        with self._cursor() as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    email    TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role     TEXT NOT NULL CHECK(role IN ('Admin','Manager','Staff'))
                );
                CREATE TABLE IF NOT EXISTS suppliers (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    name    TEXT NOT NULL,
                    contact TEXT,
                    phone   TEXT,
                    email   TEXT,
                    address TEXT
                );
                CREATE TABLE IF NOT EXISTS items (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT NOT NULL,
                    sku             TEXT UNIQUE NOT NULL,
                    price           REAL NOT NULL,
                    quantity        INTEGER NOT NULL,
                    category        TEXT,
                    image_path      TEXT,
                    last_restock    TEXT,
                    expires_on      DATE,
                    min_stock_level INTEGER DEFAULT 0,
                    supplier_id     INTEGER,
                    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
                        ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id   INTEGER NOT NULL,
                    change    INTEGER NOT NULL,
                    reason    TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
                );
                """
            )

    def _create_indexes(self) -> None:
        """Create indexes after migrations have ensured the columns exist.

        On legacy installs without supplier_id / expires_on the migration
        adds the columns first; only then is it safe to index them.
        """
        try:
            with self._cursor() as cur:
                cur.executescript(
                    """
                    CREATE INDEX IF NOT EXISTS idx_items_supplier
                        ON items(supplier_id);
                    CREATE INDEX IF NOT EXISTS idx_items_expires
                        ON items(expires_on);
                    """
                )
        except sqlite3.Error as exc:
            log.warning("Index creation skipped: %s", exc)

    def _migrate_items_schema(self) -> None:
        """Add expires_on / min_stock_level / supplier_id to existing DBs."""
        try:
            with self._cursor() as cur:
                cur.execute("PRAGMA table_info(items)")
                cols = {row[1] for row in cur.fetchall()}
                if "expires_on" not in cols:
                    cur.execute("ALTER TABLE items ADD COLUMN expires_on DATE")
                    log.info("Added column items.expires_on")
                if "min_stock_level" not in cols:
                    cur.execute(
                        "ALTER TABLE items ADD COLUMN min_stock_level INTEGER DEFAULT 0"
                    )
                    log.info("Added column items.min_stock_level")
                if "supplier_id" not in cols:
                    cur.execute(
                        "ALTER TABLE items ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"
                    )
                    log.info("Added column items.supplier_id")
        except sqlite3.Error as exc:
            log.exception("Items table migration failed: %s", exc)

    def _seed_if_empty(self) -> None:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                if cur.fetchone()[0] == 0:
                    cur.executemany(
                        "INSERT INTO users(email,password,role) VALUES (?,?,?)",
                        [
                            ("admin@logic.com",   "admin",   "Admin"),
                            ("manager@logic.com", "manager", "Manager"),
                            ("staff@logic.com",   "staff",   "Staff"),
                        ],
                    )
                cur.execute("SELECT COUNT(*) FROM suppliers")
                if cur.fetchone()[0] == 0:
                    cur.executemany(
                        "INSERT INTO suppliers(name,contact,phone,email,address) VALUES (?,?,?,?,?)",
                        [
                            ("Fresh Farms",  "John Doe",   "555-1234", "john@freshfarms.com",  "123 Farm Rd"),
                            ("Dairy Direct", "Jane Smith", "555-5678", "jane@dairydirect.com", "456 Dairy Ln"),
                        ],
                    )
                cur.execute("SELECT COUNT(*) FROM items")
                if cur.fetchone()[0] == 0:
                    today = date.today()
                    soon = (today + timedelta(days=10)).isoformat()
                    later = (today + timedelta(days=120)).isoformat()
                    cur.executemany(
                        """
                        INSERT INTO items(
                            name, sku, price, quantity, category, image_path,
                            last_restock, expires_on, min_stock_level, supplier_id
                        ) VALUES (?,?,?,?,?,?,?,?,?,?)
                        """,
                        [
                            ("Apples", "SKU001", 0.50, 23, "Produce", "assets/icons/apples.png", "04/01/26", soon,  10, 1),
                            ("Milk",   "SKU002", 3.99,  2, "Dairy",   "assets/icons/milk.png",   "03/28/26", soon,   5, 2),
                            ("Rice",   "SKU003", 2.50,  4, "Grains",  "assets/icons/rice.png",   "03/15/26", later, 12, 1),
                            ("Bread",  "SKU004", 2.99, 12, "Bakery",  "assets/icons/bread.png",  "04/10/26", soon,   8, 1),
                        ],
                    )
        except sqlite3.Error as exc:
            log.exception("Seeding failed: %s", exc)

    # ------------------------------------------------------------------ users
    def authenticate(self, identifier: str, password: str) -> Optional[User]:
        """Return a User if credentials match, else None.

        `identifier` may be the full email (admin@logic.com) or just the
        username portion before the @ (admin).
        """
        try:
            with self._cursor() as cur:
                if "@" in identifier:
                    cur.execute(
                        "SELECT id, email, role FROM users WHERE email=? AND password=?",
                        (identifier, password),
                    )
                else:
                    cur.execute(
                        "SELECT id, email, role FROM users "
                        "WHERE (email=? OR email LIKE ?) AND password=?",
                        (identifier, f"{identifier}@%", password),
                    )
                row = cur.fetchone()
                return User(id=row[0], email=row[1], role=row[2]) if row else None
        except sqlite3.Error as exc:
            log.exception("authenticate(%r) failed: %s", identifier, exc)
            return None

    def list_users(self) -> List[User]:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT id, email, role FROM users ORDER BY email")
                return [User(id=r[0], email=r[1], role=r[2]) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            log.exception("list_users failed: %s", exc)
            return []

    def add_user(self, email: str, password: str, role: str) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO users(email, password, role) VALUES (?,?,?)",
                    (email, password, role),
                )
            return True
        except sqlite3.Error as exc:
            log.exception("add_user(%r) failed: %s", email, exc)
            return False

    def email_exists(self, email: str) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE email=?", (email,))
                return cur.fetchone() is not None
        except sqlite3.Error as exc:
            log.exception("email_exists(%r) failed: %s", email, exc)
            return False

    # ------------------------------------------------------------------ items
    _ITEM_COLS = (
        "id, name, sku, price, quantity, category, image_path, last_restock, "
        "expires_on, min_stock_level, supplier_id"
    )

    @staticmethod
    def _row_to_item(row: Sequence) -> Item:
        return Item(
            id=row[0],
            name=row[1],
            sku=row[2],
            price=float(row[3] or 0),
            quantity=int(row[4] or 0),
            category=row[5],
            image_path=row[6],
            last_restock=row[7],
            expires_on=row[8] if len(row) > 8 else None,
            min_stock_level=int(row[9] or 0) if len(row) > 9 and row[9] is not None else 0,
            supplier_id=row[10] if len(row) > 10 else None,
        )

    def list_items(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Item]:
        try:
            sql = f"SELECT {self._ITEM_COLS} FROM items WHERE 1=1"
            args: List = []
            if search:
                sql += " AND (name LIKE ? OR sku LIKE ?)"
                args.extend([f"%{search}%", f"%{search}%"])
            if category and category != "All":
                sql += " AND category=?"
                args.append(category)
            sql += " ORDER BY name"
            with self._cursor() as cur:
                cur.execute(sql, args)
                return [self._row_to_item(r) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            log.exception("list_items failed: %s", exc)
            return []

    def get_item(self, item_id: int) -> Optional[Item]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT {self._ITEM_COLS} FROM items WHERE id=?", (item_id,),
                )
                row = cur.fetchone()
                return self._row_to_item(row) if row else None
        except sqlite3.Error as exc:
            log.exception("get_item(%r) failed: %s", item_id, exc)
            return None

    def sku_exists(self, sku: str, exclude_id: Optional[int] = None) -> bool:
        try:
            with self._cursor() as cur:
                if exclude_id is None:
                    cur.execute("SELECT 1 FROM items WHERE sku=?", (sku,))
                else:
                    cur.execute(
                        "SELECT 1 FROM items WHERE sku=? AND id<>?",
                        (sku, exclude_id),
                    )
                return cur.fetchone() is not None
        except sqlite3.Error as exc:
            log.exception("sku_exists(%r) failed: %s", sku, exc)
            return False

    def add_item(
        self,
        name: str,
        sku: str,
        price: float,
        quantity: int,
        category: Optional[str] = None,
        image_path: Optional[str] = None,
        expires_on: Optional[str] = None,
        min_stock_level: int = 0,
        supplier_id: Optional[int] = None,
    ) -> Optional[int]:
        try:
            today = datetime.now().strftime("%m/%d/%y")
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO items(
                        name, sku, price, quantity, category, image_path,
                        last_restock, expires_on, min_stock_level, supplier_id
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (name, sku, price, quantity, category, image_path,
                     today, expires_on, min_stock_level, supplier_id),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError as exc:
            log.warning("add_item(%r) conflict: %s", sku, exc)
            return None
        except sqlite3.Error as exc:
            log.exception("add_item(%r) failed: %s", sku, exc)
            return None

    def update_item(
        self,
        item_id: int,
        name: str,
        sku: str,
        price: float,
        quantity: int,
        category: Optional[str] = None,
        expires_on: Optional[str] = None,
        min_stock_level: Optional[int] = None,
        supplier_id: Optional[int] = None,
    ) -> bool:
        try:
            with self._cursor() as cur:
                if expires_on is None and min_stock_level is None and supplier_id is None:
                    cur.execute(
                        "UPDATE items SET name=?, sku=?, price=?, quantity=?, category=? "
                        "WHERE id=?",
                        (name, sku, price, quantity, category, item_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE items SET
                            name=?, sku=?, price=?, quantity=?, category=?,
                            expires_on=COALESCE(?, expires_on),
                            min_stock_level=COALESCE(?, min_stock_level),
                            supplier_id=COALESCE(?, supplier_id)
                        WHERE id=?
                        """,
                        (name, sku, price, quantity, category,
                         expires_on, min_stock_level, supplier_id, item_id),
                    )
            return True
        except sqlite3.Error as exc:
            log.exception("update_item(%r) failed: %s", item_id, exc)
            return False

    def delete_item(self, item_id: int) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute("DELETE FROM transactions WHERE item_id=?", (item_id,))
                cur.execute("DELETE FROM items WHERE id=?", (item_id,))
            return True
        except sqlite3.Error as exc:
            log.exception("delete_item(%r) failed: %s", item_id, exc)
            return False

    def adjust_stock(self, item_id: int, change: int, reason: str) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE items SET quantity = quantity + ? WHERE id=?",
                    (change, item_id),
                )
                if reason == "Restock":
                    cur.execute(
                        "UPDATE items SET last_restock=? WHERE id=?",
                        (datetime.now().strftime("%m/%d/%y"), item_id),
                    )
                cur.execute(
                    "INSERT INTO transactions(item_id, change, reason, timestamp) "
                    "VALUES (?,?,?,?)",
                    (item_id, change, reason, datetime.now().isoformat()),
                )
            return True
        except sqlite3.Error as exc:
            log.exception("adjust_stock(%r, %r, %r) failed: %s", item_id, change, reason, exc)
            return False

    def low_stock(self, threshold: int) -> List[Item]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT {self._ITEM_COLS} FROM items "
                    "WHERE quantity<=COALESCE(NULLIF(min_stock_level,0), ?) "
                    "ORDER BY quantity",
                    (threshold,),
                )
                return [self._row_to_item(r) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            log.exception("low_stock failed: %s", exc)
            return []

    def expiring_items(self, within_days: int = 30) -> List[Item]:
        try:
            cutoff = (date.today() + timedelta(days=within_days)).isoformat()
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT {self._ITEM_COLS} FROM items "
                    "WHERE expires_on IS NOT NULL AND expires_on <= ? "
                    "ORDER BY expires_on",
                    (cutoff,),
                )
                return [self._row_to_item(r) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            log.exception("expiring_items failed: %s", exc)
            return []

    def recent_restocks(self, limit: int = 5) -> List[RestockSummary]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT name, last_restock, quantity FROM items "
                    "WHERE last_restock IS NOT NULL "
                    "ORDER BY last_restock DESC LIMIT ?",
                    (limit,),
                )
                return [
                    RestockSummary(name=r[0], last_restock=r[1], quantity=int(r[2] or 0))
                    for r in cur.fetchall()
                ]
        except sqlite3.Error as exc:
            log.exception("recent_restocks failed: %s", exc)
            return []

    def total_items(self) -> int:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM items")
                return int(cur.fetchone()[0])
        except sqlite3.Error as exc:
            log.exception("total_items failed: %s", exc)
            return 0

    def categories(self) -> List[str]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT category FROM items WHERE category IS NOT NULL"
                )
                return [r[0] for r in cur.fetchall()]
        except sqlite3.Error as exc:
            log.exception("categories failed: %s", exc)
            return []

    # -------------------------------------------------------------- suppliers
    def list_suppliers(self, search: Optional[str] = None) -> List[Supplier]:
        try:
            sql = "SELECT id, name, contact, phone, email, address FROM suppliers"
            args: List = []
            if search:
                sql += " WHERE name LIKE ? OR CAST(id AS TEXT) LIKE ?"
                args.extend([f"%{search}%", f"%{search}%"])
            sql += " ORDER BY name"
            with self._cursor() as cur:
                cur.execute(sql, args)
                return [
                    Supplier(id=r[0], name=r[1], contact=r[2],
                             phone=r[3], email=r[4], address=r[5])
                    for r in cur.fetchall()
                ]
        except sqlite3.Error as exc:
            log.exception("list_suppliers failed: %s", exc)
            return []

    def get_supplier(self, supplier_id: int) -> Optional[Supplier]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT id, name, contact, phone, email, address "
                    "FROM suppliers WHERE id=?",
                    (supplier_id,),
                )
                r = cur.fetchone()
                if not r:
                    return None
                return Supplier(id=r[0], name=r[1], contact=r[2],
                                phone=r[3], email=r[4], address=r[5])
        except sqlite3.Error as exc:
            log.exception("get_supplier(%r) failed: %s", supplier_id, exc)
            return None

    def add_supplier(
        self,
        name: str,
        contact: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Optional[int]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO suppliers(name, contact, phone, email, address) "
                    "VALUES (?,?,?,?,?)",
                    (name, contact, phone, email, address),
                )
                return cur.lastrowid
        except sqlite3.Error as exc:
            log.exception("add_supplier(%r) failed: %s", name, exc)
            return None

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        contact: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE suppliers SET name=?, contact=?, phone=?, email=?, address=? "
                    "WHERE id=?",
                    (name, contact, phone, email, address, supplier_id),
                )
            return True
        except sqlite3.Error as exc:
            log.exception("update_supplier(%r) failed: %s", supplier_id, exc)
            return False

    def delete_supplier(self, supplier_id: int) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
            return True
        except sqlite3.Error as exc:
            log.exception("delete_supplier(%r) failed: %s", supplier_id, exc)
            return False

    # ----------------------------------------------------------- transactions
    def transactions_in_range(self, start_iso: str, end_iso: str) -> List[Tuple]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT t.id, i.name, t.change, t.reason, t.timestamp "
                    "FROM transactions t JOIN items i ON i.id = t.item_id "
                    "WHERE t.timestamp BETWEEN ? AND ? "
                    "ORDER BY t.timestamp DESC",
                    (start_iso, end_iso),
                )
                return cur.fetchall()
        except sqlite3.Error as exc:
            log.exception("transactions_in_range failed: %s", exc)
            return []

    def top_items_by_sales(
        self, limit: int = 10, ascending: bool = False
    ) -> List[SalesSummary]:
        """Total units sold (negative changes with reason='Sale') per item."""
        order = "ASC" if ascending else "DESC"
        try:
            with self._cursor() as cur:
                cur.execute(
                    f"SELECT i.name, COALESCE(SUM(-t.change), 0) AS units_sold "
                    f"FROM items i LEFT JOIN transactions t "
                    f"  ON t.item_id = i.id AND t.reason='Sale' "
                    f"GROUP BY i.id "
                    f"ORDER BY units_sold {order} LIMIT ?",
                    (limit,),
                )
                return [
                    SalesSummary(item_name=r[0], units_sold=int(r[1] or 0))
                    for r in cur.fetchall()
                ]
        except sqlite3.Error as exc:
            log.exception("top_items_by_sales failed: %s", exc)
            return []
