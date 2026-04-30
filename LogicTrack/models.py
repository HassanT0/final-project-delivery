"""
Domain data models for LogicTrack.

These dataclasses replace the raw tuple returns the database used to hand
back, so screens can refer to fields by name (item.quantity, user.role)
instead of magic indexes (row[3], row[2]). Type hints are used everywhere
so editors and static checkers can flag mistakes early.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional, Tuple, Iterable, List, Dict, Any


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class User:
    """A LogicTrack user account."""

    id: int
    email: str
    role: str                       # "Admin" | "Manager" | "Staff"
    password: Optional[str] = None  # never displayed; kept for completeness

    @property
    def display_name(self) -> str:
        return self.email.split("@", 1)[0]

    def is_admin(self) -> bool:
        return self.role == "Admin"

    def can_edit_inventory(self) -> bool:
        return self.role in ("Admin", "Manager")

    # Helps callers that still want to pattern-match on a tuple.
    def as_tuple(self) -> Tuple[int, str, str]:
        return (self.id, self.email, self.role)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
@dataclass
class Item:
    """A single tracked product (a row of the items table)."""

    id: int
    name: str
    sku: str
    price: float
    quantity: int
    category: Optional[str] = None
    image_path: Optional[str] = None
    last_restock: Optional[str] = None
    expires_on: Optional[str] = None        # ISO date string (YYYY-MM-DD)
    min_stock_level: int = 0
    supplier_id: Optional[int] = None

    # ----- derived helpers (not persisted) ---------------------------------
    @property
    def total_value(self) -> float:
        return float(self.price or 0) * int(self.quantity or 0)

    def is_low_stock(self, global_threshold: int) -> bool:
        threshold = max(self.min_stock_level or 0, int(global_threshold or 0))
        return self.quantity <= threshold

    def is_critical(self, global_threshold: int) -> bool:
        threshold = max(self.min_stock_level or 0, int(global_threshold or 0))
        return self.quantity <= max(1, threshold // 2)

    def expires_soon(self, within_days: int = 30) -> bool:
        if not self.expires_on:
            return False
        try:
            exp = date.fromisoformat(self.expires_on)
        except ValueError:
            return False
        return (exp - date.today()).days <= within_days


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
@dataclass
class Supplier:
    """Supplier / vendor record."""

    id: int
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


# ---------------------------------------------------------------------------
# Transactions / stock moves
# ---------------------------------------------------------------------------
@dataclass
class Transaction:
    """A single ledger entry against an item — sale, restock, damage."""

    id: int
    item_id: int
    change: int                # negative for sale/damage, positive for restock
    reason: str                # "Sale" | "Restock" | "Damaged"
    timestamp: str             # ISO 8601


# ---------------------------------------------------------------------------
# Aggregates returned by report queries
# ---------------------------------------------------------------------------
@dataclass
class SalesSummary:
    """A row in the top-selling / lowest-selling report."""

    item_name: str
    units_sold: int


@dataclass
class RestockSummary:
    """A row in the recent-restocks dashboard table."""

    name: str
    last_restock: Optional[str]
    quantity: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def items_total_value(items: Iterable[Item]) -> float:
    return sum(item.total_value for item in items)


def item_to_dict(item: Item) -> Dict[str, Any]:
    return asdict(item)


__all__ = [
    "User",
    "Item",
    "Supplier",
    "Transaction",
    "SalesSummary",
    "RestockSummary",
    "items_total_value",
    "item_to_dict",
]
