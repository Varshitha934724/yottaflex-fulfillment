import { useEffect, useMemo, useState } from 'react'
import './App.css'

async function loadCSV(file) {
  const response = await fetch(`/data/${file}`)
  if (!response.ok) throw new Error(`Unable to load ${file}`)

  const text = await response.text()
  const lines = text.trim().split(/\r?\n/)
  const headers = lines[0].split(',')

  return lines.slice(1).filter(Boolean).map(line => {
    const values = line.split(',')
    return Object.fromEntries(
      headers.map((header, index) => [header, values[index] ?? ''])
    )
  })
}

export default function App() {
  const [orders, setOrders] = useState([])
  const [lines, setLines] = useState([])
  const [results, setResults] = useState([])
  const [nodes, setNodes] = useState([])
  const [activeTab, setActiveTab] = useState('Orders')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)

  useEffect(() => {
    Promise.all([
      loadCSV('orders.csv'),
      loadCSV('order_lines.csv'),
      loadCSV('allocation_results.csv'),
      loadCSV('fulfillment_nodes.csv'),
    ])
      .then(([o, l, r, n]) => {
        setOrders(o)
        setLines(l)
        setResults(r)
        setNodes(n)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const linesByOrder = useMemo(() => {
    const grouped = {}
    lines.forEach(line => {
      if (!grouped[line.order_id]) grouped[line.order_id] = []
      grouped[line.order_id].push(line)
    })
    return grouped
  }, [lines])

  const resultByLine = useMemo(
    () => Object.fromEntries(results.map(row => [row.order_line_id, row])),
    [results]
  )

  const allocated = results.filter(r => r.status === 'ALLOCATED').length
  const exceptions = results.filter(r => r.status !== 'ALLOCATED').length

  const filteredOrders = orders.filter(order =>
    order.order_id.toLowerCase().includes(search.toLowerCase())
  )

  const pageSize = 50
  const visibleOrders = filteredOrders.slice(page * pageSize, (page + 1) * pageSize)

  if (loading) return <main className="app"><h1>Loading fulfillment data...</h1></main>
  if (error) return <main className="app"><h1>Data loading error</h1><p>{error}</p><p>Check the CSV files inside public/data.</p></main>

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">YOTTAFLEX AI · OPERATIONS PLATFORM</div>
          <h1>Fulfillment Control Center</h1>
          <p>Inventory-aware allocation and delivery promise planning</p>
        </div>
        <span className="live"><span /> GENERATED DATASET</span>
      </header>

      <nav className="tabs">
        {['Orders', 'Fulfillment Nodes', 'Decisions'].map(tab => (
          <button key={tab} className={activeTab === tab ? 'tab active' : 'tab'} onClick={() => { setActiveTab(tab); setPage(0) }}>
            {tab}
          </button>
        ))}
      </nav>

      <section className="metrics">
        <article className="metric"><span>Total Orders</span><strong>{orders.length.toLocaleString('en-IN')}</strong><small>Generated orders</small></article>
        <article className="metric"><span>Allocated Lines</span><strong>{allocated.toLocaleString('en-IN')}</strong><small>Successful allocations</small></article>
        <article className="metric"><span>Exceptions</span><strong>{exceptions.toLocaleString('en-IN')}</strong><small>Lines requiring attention</small></article>
        <article className="metric"><span>Fulfillment Nodes</span><strong>{nodes.length}</strong><small>Available locations</small></article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{activeTab === 'Orders' ? 'Order Queue' : activeTab === 'Fulfillment Nodes' ? 'Fulfillment Nodes' : 'Allocation Decisions'}</h2>
            <p>Validated allocation output from the generated dataset.</p>
          </div>
        </div>

        {activeTab === 'Orders' && (
          <>
            <div style={{ padding: '12px 0' }}>
              <input
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(0) }}
                placeholder="Search order ID..."
                style={{ padding: 10, width: 'min(100%, 320px)' }}
              />
              <p>Showing {visibleOrders.length} of {filteredOrders.length.toLocaleString('en-IN')} matching orders</p>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Order ID</th><th>SKU</th><th>Qty</th><th>Zone</th><th>Allocation Status</th></tr></thead>
                <tbody>
                  {visibleOrders.flatMap(order =>
                    (linesByOrder[order.order_id] || []).map(line => {
                      const result = resultByLine[line.order_line_id]
                      return (
                        <tr key={line.order_line_id}>
                          <td className="id">{order.order_id}</td>
                          <td>{line.sku_id}</td>
                          <td>{line.quantity}</td>
                          <td>{order.destination_zone}</td>
                          <td><span className={'badge ' + (result?.status === 'ALLOCATED' ? 'success' : 'danger')}>{result?.status || 'Pending'}</span></td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
            <div className="actions" style={{ padding: 16 }}>
              <button className="secondary" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</button>
              <span>Page {page + 1} of {Math.max(1, Math.ceil(filteredOrders.length / pageSize))}</span>
              <button className="primary" disabled={(page + 1) * pageSize >= filteredOrders.length} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          </>
        )}

        {activeTab === 'Fulfillment Nodes' && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Node ID</th><th>Node Name</th><th>Zone</th><th>Daily Capacity</th></tr></thead>
              <tbody>{nodes.map(node => (
                <tr key={node.node_id}><td className="id">{node.node_id}</td><td>{node.node_name}</td><td>{node.zone}</td><td>{Number(node.daily_capacity).toLocaleString('en-IN')}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}

        {activeTab === 'Decisions' && (
          <>
            <p style={{ padding: 12 }}>Showing the first 100 allocation decisions.</p>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Order ID</th><th>Order Line</th><th>Status</th><th>Selected Node</th><th>Carrier</th><th>Promise Date</th></tr></thead>
                <tbody>{results.slice(0, 100).map(result => (
                  <tr key={result.order_line_id}>
                    <td className="id">{result.order_id}</td>
                    <td>{result.order_line_id}</td>
                    <td><span className={'badge ' + (result.status === 'ALLOCATED' ? 'success' : 'danger')}>{result.status}</span></td>
                    <td>{result.node_id || '—'}</td>
                    <td>{result.carrier_id || '—'}</td>
                    <td>{result.promised_delivery_date || '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <footer>YottaFlex Fulfillment Planner · Synthetic demonstration data · No live orders</footer>
    </main>
  )
}