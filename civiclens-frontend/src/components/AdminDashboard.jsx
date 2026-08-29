import { useEffect, useState } from 'react';

const STATUS_LABELS = { verified: 'Verified', pending_verification: 'Pending', rejected: 'Rejected' };

export default function AdminDashboard({ apiUrl, adminUsername, onLogout }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { fetchReports(); }, []);

  async function fetchReports() {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/reports`, { credentials: 'include' });
      if (!res.ok) throw new Error('Could not load reports.');
      setReports(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await fetch(`${apiUrl}/admin/logout`, { method: 'POST', credentials: 'include' });
    onLogout();
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Government Dashboard</h2>
          <p className="form-sub">Signed in as {adminUsername} · {reports.length} report(s) total</p>
        </div>
        <button className="btn-secondary" onClick={handleLogout}>Log out</button>
      </div>

      {error && <div className="form-error">{error}</div>}
      {loading ? <p className="form-sub">Loading…</p> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>#</th><th>Area</th><th>Category</th><th>Status</th>
                <th>Priority</th><th>Citizen</th><th>Phone</th><th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.area || '—'}</td>
                  <td>{r.ai_label || r.category}</td>
                  <td><span className={`popup-status status-${r.status}`}>{STATUS_LABELS[r.status] || r.status}</span></td>
                  <td>{r.ai_priority || '—'}</td>
                  <td>{r.citizen_name || '—'}</td>
                  <td>{r.citizen_phone || '—'}</td>
                  <td>{new Date(r.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}