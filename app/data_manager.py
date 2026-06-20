"""
data_manager.py
----------------
A generic, table-agnostic CSV data layer. One DataManager instance wraps
one CSV file (driven by a TableConfig) and provides:

    - load()                       read CSV into memory (list[dict])
    - save()                       write memory back to CSV (with backup)
    - all_rows() / get(key)        read access
    - add_row(data)                create, with required-field + uniqueness validation
    - update_row(key, data)        update, with validation
    - delete_row(key)              delete
    - search(text, columns)        simple case-insensitive substring search
    - sort(rows, column, reverse)  sort a list of rows by a column
    - suggest_next_id()            propose the next sequential ID for new records
    - row_count()

No external dependencies - uses only the standard library `csv` module so
the whole application runs with nothing but Python + Tk.
"""

import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

from app.config import BACKUP_DIR, MAX_BACKUPS_PER_TABLE


class ValidationError(Exception):
    """Raised when a record fails required-field or uniqueness checks."""


class DataManager:
    def __init__(self, table_config):
        self.config = table_config
        self.columns = table_config.column_names()
        self.rows = []  # list[dict[str, str]]
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------
    def load(self):
        path = Path(self.config.csv_path)
        self.rows = []
        if not path.exists():
            self._loaded = True
            return
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            file_columns = reader.fieldnames or []
            for raw in reader:
                row = {}
                for col in self.columns:
                    row[col] = (raw.get(col) or "").strip()
                self.rows.append(row)
            # If the file has extra columns we don't know about, keep schema
            # as configured (we never silently drop the user's columns on
            # save, since save() writes out exactly self.columns).
            self._file_had_unknown_columns = any(c not in self.columns for c in file_columns)
        self._loaded = True

    def _backup_existing_file(self):
        path = Path(self.config.csv_path)
        if not path.exists():
            return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{path.stem}_{stamp}.csv"
        shutil.copy2(path, backup_path)
        # prune old backups for this table, keep most recent N
        backups = sorted(
            BACKUP_DIR.glob(f"{path.stem}_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[MAX_BACKUPS_PER_TABLE:]:
            try:
                old.unlink()
            except OSError:
                pass

    def save(self):
        path = Path(self.config.csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_existing_file()
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({col: row.get(col, "") for col in self.columns})
        tmp_path.replace(path)

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------
    def _key_of(self, row):
        return tuple(row.get(k, "") for k in self.config.key_fields)

    def find_index(self, key_values):
        """key_values: tuple matching self.config.key_fields order."""
        for i, row in enumerate(self.rows):
            if self._key_of(row) == tuple(key_values):
                return i
        return -1

    def get(self, key_values):
        idx = self.find_index(key_values)
        return self.rows[idx] if idx >= 0 else None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def _validate_field_types(self, data, field_map):
        """Per-field required/type checks (no key-uniqueness check here - that
        differs between single-row edits and bulk replace, so callers handle
        it separately). Returns a list of error strings."""
        errors = []
        for fname, spec in field_map.items():
            value = (data.get(fname) or "").strip()
            if spec.required and not value:
                errors.append(f"'{spec.label}' is required.")
                continue
            if value and spec.type == "int":
                try:
                    int(float(value))
                except ValueError:
                    errors.append(f"'{spec.label}' must be a whole number.")
            elif value and spec.type == "float":
                try:
                    float(value)
                except ValueError:
                    errors.append(f"'{spec.label}' must be a number.")
            elif value and spec.type == "date":
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                    errors.append(f"'{spec.label}' must be in YYYY-MM-DD format.")
            elif value and spec.type == "datetime":
                if not re.match(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$", value):
                    errors.append(f"'{spec.label}' must be in YYYY-MM-DD HH:MM format.")
            elif value and spec.type == "email":
                if "@" not in value or "." not in value.split("@")[-1]:
                    errors.append(f"'{spec.label}' doesn't look like a valid email.")
        return errors

    def _validate(self, data, exclude_key=None):
        errors = self._validate_field_types(data, self.config.field_map())

        key_values = tuple(data.get(k, "").strip() for k in self.config.key_fields)
        if any(key_values):
            existing_idx = self.find_index(key_values)
            if existing_idx >= 0 and key_values != exclude_key:
                key_label = " / ".join(self.config.key_fields)
                errors.append(
                    f"A record with {key_label} = {' / '.join(key_values)} already exists."
                )

        if errors:
            raise ValidationError("\n".join(errors))

    def add_row(self, data):
        clean = {col: (data.get(col) or "").strip() for col in self.columns}
        self._validate(clean, exclude_key=None)
        self.rows.append(clean)
        self.save()
        return clean

    def update_row(self, original_key_values, data):
        idx = self.find_index(original_key_values)
        if idx < 0:
            raise ValidationError("Record no longer exists (it may have been deleted).")
        clean = {col: (data.get(col) or "").strip() for col in self.columns}
        self._validate(clean, exclude_key=tuple(original_key_values))
        self.rows[idx] = clean
        self.save()
        return clean

    def delete_row(self, key_values):
        idx = self.find_index(key_values)
        if idx < 0:
            return False
        del self.rows[idx]
        self.save()
        return True

    def delete_rows(self, list_of_key_values):
        keys = set(tuple(k) for k in list_of_key_values)
        before = len(self.rows)
        self.rows = [r for r in self.rows if self._key_of(r) not in keys]
        removed = before - len(self.rows)
        if removed:
            self.save()
        return removed

    def replace_all(self, new_rows):
        """
        Validates and replaces the ENTIRE table with new_rows in one shot -
        for bulk/grid-style editors (e.g. a web data-editor widget) where
        many rows may have been added, edited, or removed at once.

        Unlike add_row/update_row, this checks for duplicate keys WITHIN
        new_rows itself (not against the table's previous state). Raises
        ValidationError, leaving the table untouched, if anything fails -
        never partially saves. On success, saves exactly once.
        """
        field_map = self.config.field_map()
        errors = []
        seen_keys = {}
        cleaned = []

        for i, raw in enumerate(new_rows, start=1):
            clean = {col: str(raw.get(col, "") or "").strip() for col in self.columns}
            cleaned.append(clean)

            for err in self._validate_field_types(clean, field_map):
                errors.append(f"Row {i}: {err}")

            key_values = tuple(clean.get(k, "") for k in self.config.key_fields)
            if not any(key_values):
                errors.append(f"Row {i}: missing required key field(s) {' / '.join(self.config.key_fields)}.")
            elif key_values in seen_keys:
                key_label = " / ".join(self.config.key_fields)
                errors.append(
                    f"Row {i}: duplicate key {key_label} = {' / '.join(key_values)} "
                    f"(also used by row {seen_keys[key_values]})."
                )
            else:
                seen_keys[key_values] = i

        if errors:
            raise ValidationError("\n".join(errors))

        self.rows = cleaned
        self.save()
        return len(cleaned)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def all_rows(self):
        return self.rows

    def row_count(self):
        return len(self.rows)

    def search(self, text, columns=None):
        if not text:
            return list(self.rows)
        text = text.lower().strip()
        cols = columns or self.config.search_fields
        results = []
        for row in self.rows:
            for c in cols:
                if text in (row.get(c, "") or "").lower():
                    results.append(row)
                    break
        return results

    @staticmethod
    def sort_rows(rows, column, reverse=False, field_type="text"):
        def sort_key(row):
            val = row.get(column, "")
            if field_type in ("int", "float"):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return float("-inf")
            return (val or "").lower()

        return sorted(rows, key=sort_key, reverse=reverse)

    # ------------------------------------------------------------------
    # ID suggestion
    # ------------------------------------------------------------------
    def suggest_next_id(self):
        """Suggest the next sequential ID for tables with a numeric-suffix
        id pattern like CUST-000123 or ITM-000045. Falls back to a
        timestamp-based suggestion if no pattern is detected."""
        cfg = self.config
        if not cfg.id_field or not cfg.id_prefix:
            return ""
        prefix = cfg.id_prefix
        max_num = 0
        width = 6
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        for row in self.rows:
            val = row.get(cfg.id_field, "")
            m = pattern.match(val)
            if m:
                digits = m.group(1)
                width = max(width, len(digits))
                max_num = max(max_num, int(digits))
        if max_num == 0 and not any(pattern.match(row.get(cfg.id_field, "")) for row in self.rows):
            # No existing pattern matched at all -> fall back to a safe default
            return f"{prefix}{1:0{width}d}"
        return f"{prefix}{max_num + 1:0{width}d}"

    def suggest_next_order_number(self, year=None):
        """Special-case helper for the Orders table: SO-YYYY-NNNNNN."""
        year = year or datetime.now().year
        pattern = re.compile(r"^SO-(\d{4})-(\d+)$")
        max_num = 0
        for row in self.rows:
            m = pattern.match(row.get("order_number", ""))
            if m:
                max_num = max(max_num, int(m.group(2)))
        return f"SO-{year}-{max_num + 1:06d}"
