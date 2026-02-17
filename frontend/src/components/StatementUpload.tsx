import { useState } from 'react'
import { statementImportAPI } from '../services/api'
import type {
  StatementSource,
  ImportJobResult,
  ImportJobTransactionsResponse,
} from '../types'
import './StatementUpload.css'

export default function StatementUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [statementSource, setStatementSource] =
    useState<StatementSource>('swedbank')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<ImportJobResult | null>(null)
  const [jobStatus, setJobStatus] = useState<ImportJobResult | null>(null)
  const [transactions, setTransactions] = useState<
    ImportJobTransactionsResponse['transactions']
  >([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setUploadResult(null)
      setJobStatus(null)
      setTransactions([])
    }
  }

  const loadTransactions = async (jobId: string) => {
    setLoadingTransactions(true)
    try {
      const data = await statementImportAPI.getImportJobTransactions(jobId)
      setTransactions(data.transactions ?? [])
    } catch (error) {
      console.error('Failed to load transactions:', error)
    } finally {
      setLoadingTransactions(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 30
    let attempts = 0

    const poll = async () => {
      if (attempts >= maxAttempts) return

      try {
        const status = await statementImportAPI.getImportJobStatus(jobId)
        setJobStatus(status)

        if (status.import_job_status === 'completed') {
          loadTransactions(jobId)
        } else if (status.import_job_status === 'failed') {
          return
        } else {
          attempts++
          setTimeout(poll, 2000)
        }
      } catch (error) {
        console.error('Failed to check job status:', error)
      }
    }

    poll()
  }

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file')
      return
    }

    setUploading(true)
    setUploadResult(null)

    try {
      const result = await statementImportAPI.uploadStatement(
        file,
        statementSource
      )
      setUploadResult(result)
      setJobStatus(result)
      pollJobStatus(result.import_job_id)
    } catch (error) {
      alert('Upload failed: ' + (error instanceof Error ? error.message : ''))
    } finally {
      setUploading(false)
    }
  }

  const status =
    jobStatus?.import_job_status ?? uploadResult?.import_job_status

  return (
    <div className="statement-upload-container">
      <div className="statement-upload-card">
        <h2>Upload Statement</h2>
        <p className="subtitle">
          Upload a bank statement to import transactions
        </p>

        <div className="upload-form">
          <div className="form-group">
            <label htmlFor="statementSource">Statement Source</label>
            <select
              id="statementSource"
              value={statementSource}
              onChange={(e) =>
                setStatementSource(e.target.value as StatementSource)
              }
              className="form-select"
            >
              <option value="swedbank">Swedbank</option>
              <option value="revolut">Revolut</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="fileInput">Select File</label>
            <input
              id="fileInput"
              type="file"
              onChange={handleFileChange}
              accept=".csv,.xlsx,.pdf"
              className="file-input"
            />
            {file && (
              <div className="file-info">
                <span>Selected: {file.name}</span>
                <span className="file-size">
                  ({(file.size / 1024).toFixed(2)} KB)
                </span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="upload-button"
          >
            {uploading ? 'Uploading...' : 'Upload Statement'}
          </button>
        </div>

        {uploadResult && (
          <div className="upload-result">
            <h3>Upload Result</h3>
            <div className="result-info">
              <p>
                <strong>Job ID:</strong>{' '}
                <span className="result-value">{uploadResult.import_job_id}</span>
              </p>
              <p>
                <strong>Status:</strong>{' '}
                <span
                  className={`status-badge ${status?.toLowerCase() ?? ''}`}
                >
                  {status}
                </span>
              </p>
            </div>

            {status === 'completed' && (
              <div className="transactions-section">
                <h4>Imported Transactions</h4>
                {loadingTransactions ? (
                  <div className="loading">Loading transactions...</div>
                ) : transactions.length > 0 ? (
                  <div className="transactions-list">
                    {transactions.map((tx, idx) => (
                      <div key={tx.id ?? idx} className="transaction-item">
                        <div className="transaction-date">
                          {new Date(tx.transaction_datetime).toLocaleDateString()}
                        </div>
                        <div className="transaction-details">
                          <div className="transaction-counterparty">
                            {tx.counterparty}
                          </div>
                          <div className={`transaction-amount ${tx.side}`}>
                            {tx.side === 'debit' ? '-' : '+'}
                            {new Intl.NumberFormat('en-US', {
                              style: 'currency',
                              currency: tx.orig_currency ?? 'EUR',
                            }).format(Number(tx.orig_amount))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">No transactions found</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
