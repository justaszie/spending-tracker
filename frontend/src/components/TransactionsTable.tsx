import { useState, useEffect, useCallback } from 'react'
import { transactionsAPI } from '../services/api'
import type { Transaction } from '../types'
import './TransactionsTable.css'

const PAGE_SIZE = 20

export default function TransactionsTable() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('transaction_datetime')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [filterSource] = useState('all')
  const [untaggedOnly, setUntaggedOnly] = useState(false)
  const [debitOnly, setDebitOnly] = useState(false)
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState<number | undefined>(undefined)

  const loadTransactions = useCallback(async () => {
    setLoading(true)
    try {
      const result = await transactionsAPI.getTransactions({
        page,
        size: PAGE_SIZE,
        search: searchTerm,
        sortBy,
        sortOrder,
        untaggedOnly: untaggedOnly || undefined,
        side: debitOnly ? ['debit'] : undefined,
      })
      let filtered = result.transactions
      if (filterSource !== 'all') {
        filtered = filtered.filter((t) => t.source === filterSource)
      }
      setTransactions(filtered)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to load transactions:', error)
    } finally {
      setLoading(false)
    }
  }, [page, searchTerm, sortBy, sortOrder, filterSource, untaggedOnly, debitOnly])

  useEffect(() => {
    loadTransactions()
  }, [loadTransactions])

  const handleSort = (column: string) => {
    setPage(1)
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('asc')
    }
  }

  const totalPages = total !== undefined ? Math.ceil(total / PAGE_SIZE) : undefined
  const hasNextPage =
    totalPages !== undefined ? page < totalPages : transactions.length >= PAGE_SIZE
  const hasPrevPage = page > 1

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const month = date.toLocaleDateString('en-US', { month: 'short' })
    const day = date.getDate().toString().padStart(2, '0')
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${month} ${day} ${hours}:${minutes}`
  }

  const formatAmount = (
    amount: string,
    side: string
  ) => {
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
    }).format(Math.abs(Number(amount)))
    return side === 'debit' ? `-${formatted}` : `+${formatted}`
  }

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedRows(new Set(transactions.map((t) => t.id)))
    } else {
      setSelectedRows(new Set())
    }
  }

  const handleSelectRow = (id: string) => {
    const newSelected = new Set(selectedRows)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedRows(newSelected)
  }

  const isAllSelected =
    transactions.length > 0 && selectedRows.size === transactions.length
  const isIndeterminate =
    selectedRows.size > 0 && selectedRows.size < transactions.length

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
            setSearchTerm(e.target.value)
            setPage(1)
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
              setUntaggedOnly(e.target.checked)
              setPage(1)
            }}
          />
          <span>Untagged Only</span>
        </label>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={debitOnly}
            onChange={(e) => {
              setDebitOnly(e.target.checked)
              setPage(1)
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
                      if (input) input.indeterminate = isIndeterminate
                    }}
                    onChange={handleSelectAll}
                  />
                </th>
                <th>ID</th>
                <th
                  onClick={() => handleSort('transaction_datetime')}
                  className="sortable"
                >
                  Date{' '}
                  {sortBy === 'transaction_datetime' &&
                    (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('counterparty')}
                  className="sortable"
                >
                  COUNTERPARTY{' '}
                  {sortBy === 'counterparty' &&
                    (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('side')} className="sortable">
                  SIDE {sortBy === 'side' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th
                  onClick={() => handleSort('eur_amount')}
                  className="sortable"
                >
                  Amount (EUR){' '}
                  {sortBy === 'eur_amount' &&
                    (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('spending_category')} className="sortable">
                  CATEGORY {sortBy === 'spending_category' && (sortOrder === 'asc' ? '↑' : '↓')}
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
                    <span
                      className={`badge badge-${transaction.side}`}
                    >
                      {transaction.side.toUpperCase()}
                    </span>
                  </td>
                  <td
                    className={
                      transaction.side === 'debit'
                        ? 'amount-debit'
                        : 'amount-credit'
                    }
                  >
                    {formatAmount(
                      transaction.eur_amount,
                      transaction.side
                    )}
                  </td>
                  <td>{transaction.spending_category ?? '-'}</td>
                  <td>{transaction.note ?? '-'}</td>
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
    </div>
  )
}
