import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { transactionsAPI } from "../services/api";
import type { Transaction } from "../types";
import "./TransactionsTable.css";

const PAGE_SIZE = 20;
const CATEGORY_MAX_LENGTH = 50;

export default function TransactionsTable() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("transaction_datetime");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [filterSource] = useState("all");
  const [untaggedOnly, setUntaggedOnly] = useState(false);
  const [debitOnly, setDebitOnly] = useState(false);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState<number | undefined>(undefined);

  const [categoryPopoverId, setCategoryPopoverId] = useState<string | null>(null);
  const [categorySearchQuery, setCategorySearchQuery] = useState("");
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [patchLoadingId, setPatchLoadingId] = useState<string | null>(null);
  const categoryPopoverRef = useRef<HTMLDivElement>(null);
  const categorySearchInputRef = useRef<HTMLInputElement>(null);

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    try {
      const result = await transactionsAPI.getTransactions({
        page,
        size: PAGE_SIZE,
        search: searchTerm,
        sortBy,
        sortOrder,
        untaggedOnly: untaggedOnly || undefined,
        side: debitOnly ? ["debit"] : undefined,
      });
      let filtered = result.transactions;
      if (filterSource !== "all") {
        filtered = filtered.filter((t) => t.source === filterSource);
      }
      setTransactions(filtered);
      setTotal(result.total);
    } catch (error) {
      console.error("Failed to load transactions:", error);
    } finally {
      setLoading(false);
    }
  }, [
    page,
    searchTerm,
    sortBy,
    sortOrder,
    filterSource,
    untaggedOnly,
    debitOnly,
  ]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  useEffect(() => {
    if (categories.length === 0 && !categoriesLoading) {
      setCategoriesLoading(true);
      transactionsAPI
        .getSpendingCategories()
        .then(setCategories)
        .catch(console.error)
        .finally(() => setCategoriesLoading(false));
    }
  }, [categories.length, categoriesLoading]);

  useEffect(() => {
    if (categoryPopoverId) {
      setCategorySearchQuery("");
      const t = setTimeout(() => categorySearchInputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
  }, [categoryPopoverId]);

  useEffect(() => {
    if (!categoryPopoverId) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCategoryPopoverId(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [categoryPopoverId]);

  useEffect(() => {
    if (!categoryPopoverId) return;
    const onMouseDown = (e: MouseEvent) => {
      if (
        categoryPopoverRef.current &&
        !categoryPopoverRef.current.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest(".category-cell-trigger")
      ) {
        setCategoryPopoverId(null);
      }
    };
    window.addEventListener("mousedown", onMouseDown);
    return () => window.removeEventListener("mousedown", onMouseDown);
  }, [categoryPopoverId]);

  const openCategoryPopover = (e: React.MouseEvent, transactionId: string) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setAnchorRect(rect);
    setCategoryPopoverId(transactionId);
  };

  const applyCategory = async (transactionId: string, value: string) => {
    const trimmed = value.trim().slice(0, CATEGORY_MAX_LENGTH);
    if (!trimmed) return;
    setPatchLoadingId(transactionId);
    try {
      const updated = await transactionsAPI.patchTransaction(transactionId, {
        spending_category: trimmed,
      });
      setTransactions((prev) =>
        prev.map((t) => (t.id === transactionId ? updated : t)),
      );
      setCategoryPopoverId(null);
    } catch (err) {
      console.error("Failed to update category:", err);
    } finally {
      setPatchLoadingId(null);
    }
  };

  const popoverTransaction = categoryPopoverId
    ? transactions.find((t) => t.id === categoryPopoverId)
    : null;
  const query = categorySearchQuery.trim().toLowerCase();
  const matchingCategories = query
    ? categories.filter((c) => c.toLowerCase().includes(query))
    : categories;
  const canCreateNew =
    query.length > 0 && !categories.some((c) => c.toLowerCase() === query);

  const handleSort = (column: string) => {
    setPage(1);
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  };

  const totalPages =
    total !== undefined ? Math.ceil(total / PAGE_SIZE) : undefined;
  const hasNextPage =
    totalPages !== undefined
      ? page < totalPages
      : transactions.length >= PAGE_SIZE;
  const hasPrevPage = page > 1;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const year = date.getFullYear().toString();
    const month = date.toLocaleDateString("en-US", { month: "short" });
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${day} ${month} ${year}, ${hours}:${minutes}`;
  };

  const formatAmount = (amount: string, side: string) => {
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 2,
    }).format(Math.abs(Number(amount)));
    return side === "debit" ? `-${formatted}` : `+${formatted}`;
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedRows(new Set(transactions.map((t) => t.id)));
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleSelectRow = (id: string) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedRows(newSelected);
  };

  const isAllSelected =
    transactions.length > 0 && selectedRows.size === transactions.length;
  const isIndeterminate =
    selectedRows.size > 0 && selectedRows.size < transactions.length;

  return (
    <div className="transactions-container">
      <div className="transactions-header">
        <h1>Transactions</h1>
        <p className="transactions-subtitle">
          Manage your financial ledger, categorize entries, and handle
          reimbursements.
        </p>
      </div>

      <div className="transactions-search">
        <input
          type="text"
          placeholder="Filter counterparties..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setPage(1);
          }}
          className="search-input"
        />
      </div>

      <div className="transactions-filters">
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={untaggedOnly}
            onChange={(e) => {
              setUntaggedOnly(e.target.checked);
              setPage(1);
            }}
          />
          <span>Untagged Only</span>
        </label>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={debitOnly}
            onChange={(e) => {
              setDebitOnly(e.target.checked);
              setPage(1);
            }}
          />
          <span>Debit Only</span>
        </label>
      </div>

      {loading ? (
        <div className="loading">Loading transactions...</div>
      ) : transactions.length === 0 ? (
        <div className="empty-state">No transactions found</div>
      ) : (
        <div className="table-wrapper">
          <table className="transactions-table">
            <thead>
              <tr>
                <th className="checkbox-column">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    ref={(input) => {
                      if (input) input.indeterminate = isIndeterminate;
                    }}
                    onChange={handleSelectAll}
                  />
                </th>
                <th>ID</th>
                <th
                  onClick={() => handleSort("transaction_datetime")}
                  className="sortable"
                >
                  Date{" "}
                  {sortBy === "transaction_datetime" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th
                  onClick={() => handleSort("counterparty")}
                  className="sortable"
                >
                  COUNTERPARTY{" "}
                  {sortBy === "counterparty" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th onClick={() => handleSort("side")} className="sortable">
                  SIDE {sortBy === "side" && (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th
                  onClick={() => handleSort("eur_amount")}
                  className="sortable"
                >
                  Amount (EUR){" "}
                  {sortBy === "eur_amount" && (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th
                  onClick={() => handleSort("spending_category")}
                  className="sortable"
                >
                  CATEGORY{" "}
                  {sortBy === "spending_category" &&
                    (sortOrder === "asc" ? "↑" : "↓")}
                </th>
                <th>NOTE</th>
                <th className="actions-column"></th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="checkbox-column">
                    <input
                      type="checkbox"
                      checked={selectedRows.has(transaction.id)}
                      onChange={() => handleSelectRow(transaction.id)}
                    />
                  </td>
                  <td className="id-cell">{transaction.id}</td>
                  <td className="date-cell">
                    {formatDate(transaction.transaction_datetime)}
                  </td>
                  <td>{transaction.counterparty}</td>
                  <td>
                    <span className={`badge badge-${transaction.side}`}>
                      {transaction.side.toUpperCase()}
                    </span>
                  </td>
                  <td
                    className={
                      transaction.side === "debit"
                        ? "amount-debit"
                        : "amount-credit"
                    }
                  >
                    {formatAmount(transaction.eur_amount, transaction.side)}
                  </td>
                  <td className="category-cell">
                    <button
                      type="button"
                      className="category-cell-trigger"
                      onClick={(e) => openCategoryPopover(e, transaction.id)}
                      disabled={patchLoadingId === transaction.id}
                    >
                      {transaction.spending_category ?? "Select category…"}
                    </button>
                  </td>
                  <td>{transaction.note ?? "-"}</td>
                  <td className="actions-column">
                    <button type="button" className="actions-button">
                      ⋯
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && transactions.length > 0 && (
        <div className="pagination">
          <span className="pagination-info">
            Page {page}
            {totalPages !== undefined && ` of ${totalPages}`}
          </span>
          <div className="pagination-buttons">
            <button
              type="button"
              className="pagination-btn"
              disabled={!hasPrevPage}
              onClick={() => setPage((p) => p - 1)}
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              type="button"
              className="pagination-btn"
              disabled={!hasNextPage}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {categoryPopoverId &&
        popoverTransaction &&
        anchorRect &&
        (() => {
          const viewportPadding = 24;
          const spaceBelow =
            typeof window !== "undefined"
              ? window.innerHeight - anchorRect.bottom - viewportPadding
              : 320;
          const spaceAbove =
            typeof window !== "undefined"
              ? anchorRect.top - viewportPadding
              : 320;
          const openAbove = spaceBelow < 240;
          const maxHeight = Math.min(
            320,
            Math.max(120, openAbove ? spaceAbove : spaceBelow),
          );
          return createPortal(
            <div
              ref={categoryPopoverRef}
              className="category-popover"
              style={{
                position: "fixed",
                ...(openAbove
                  ? {
                      bottom: window.innerHeight - anchorRect.top + 4,
                      top: "auto",
                    }
                  : { top: anchorRect.bottom + 4 }),
                left: anchorRect.left,
                minWidth: Math.max(anchorRect.width, 280),
                maxHeight,
              }}
              role="dialog"
              aria-label="Select spending category"
            >
            <div className="category-popover-search">
              <span className="category-popover-search-icon" aria-hidden>🔍</span>
              <input
                ref={categorySearchInputRef}
                type="text"
                value={categorySearchQuery}
                onChange={(e) => setCategorySearchQuery(e.target.value)}
                placeholder="Search categories…"
                className="category-popover-input"
              />
            </div>
            {canCreateNew && (
              <div className="category-popover-section">
                <div className="category-popover-section-title">New Category</div>
                <button
                  type="button"
                  className="category-popover-option category-popover-create"
                  onClick={() =>
                    applyCategory(
                      categoryPopoverId,
                      categorySearchQuery.trim().slice(0, CATEGORY_MAX_LENGTH),
                    )
                  }
                >
                  + Create &quot;{categorySearchQuery.trim().slice(0, 50)}&quot;
                </button>
              </div>
            )}
            <div className="category-popover-section">
              <div className="category-popover-section-title">Categories</div>
              <ul className="category-popover-list">
                {matchingCategories.length === 0 ? (
                  <li className="category-popover-empty">No matching categories</li>
                ) : (
                  matchingCategories.map((cat) => (
                    <li key={cat}>
                      <button
                        type="button"
                        className="category-popover-option"
                        onClick={() => applyCategory(categoryPopoverId, cat)}
                      >
                        <span className="category-popover-dot" />
                        {cat}
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>,
            document.body,
          );
        })()}
    </div>
  );
}
