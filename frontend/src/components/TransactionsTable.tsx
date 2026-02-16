import { useState, useEffect, useCallback } from 'react'
import { transactionsAPI } from '../services/api'
import type { Transaction } from '../types'
import './TransactionsTable.css'

export default function TransactionsTable() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('transaction_datetime')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [filterSource] = useState('all')
  const [filterSide] = useState('all')
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())

  const loadTransactions = useCallback(async () => {
    setLoading(true)
    try {
      const result = await transactionsAPI.getTransactions({
        search: searchTerm,
        sortBy,
        sortOrder,
      })
      let filtered = result.transactions
      if (filterSource !== 'all') {
        filtered = filtered.filter((t) => t.source === filterSource)
      }
      if (filterSide !== 'all') {
        filtered = filtered.filter((t) => t.side === filterSide)
      }
      setTransactions(filtered)
    } catch (error) {
      console.error('Failed to load transactions:', error)
    } finally {
      setLoading(false)
    }
  }, [searchTerm, sortBy, sortOrder, filterSource, filterSide])

  useEffect(() => {
    loadTransactions()
  }, [loadTransactions])

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('asc')
    }
  }

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
    currency: string,
    side: string
  ) => {
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'EUR',
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
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
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
                  onClick={() => handleSort('orig_amount')}
                  className="sortable"
                >
                  Amount (EUR){' '}
                  {sortBy === 'orig_amount' &&
                    (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th>L1 CAT</th>
                <th>L2 CAT</th>
                <th>L3 CAT</th>
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
                      transaction.orig_amount,
                      transaction.orig_currency,
                      transaction.side
                    )}
                  </td>
                  <td>{transaction.l1_category ?? '-'}</td>
                  <td>{transaction.l2_category ?? '-'}</td>
                  <td>{transaction.l3_category ?? '-'}</td>
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
    </div>
  )
}
