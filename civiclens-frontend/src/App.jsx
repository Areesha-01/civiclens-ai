import { useEffect, useState } from 'react';
import ReportForm from './components/ReportForm';
import ReportsMap from './components/ReportsMap';
import Home from './components/Home';
import CitizenAuth from './components/CitizenAuth';
import AdminLogin from './components/AdminLogin';
import AdminDashboard from './components/AdminDashboard';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function App() {
  const [view, setView] = useState('home');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState('');
  const [citizenName, setCitizenName] = useState(null);
  const [adminUsername, setAdminUsername] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/citizen/me`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => { if (d.logged_in) setCitizenName(d.full_name); });
    fetch(`${API_URL}/admin/me`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => { if (d.logged_in) setAdminUsername(d.username); });
  }, []);

  async function handleSubmit({ photo, description, category, area, position }) {
    setSubmitting(true);
    setSubmitError('');
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('photo', photo);
      formData.append('description', description);
      formData.append('category', category);
      formData.append('area', area);
      formData.append('lat', position.lat);
      formData.append('lng', position.lng);

      const res = await fetch(`${API_URL}/submit-report`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.error || 'Server error, please try again.');
      setResult(data);
    } catch (err) {
      setSubmitError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCitizenLogout() {
    await fetch(`${API_URL}/citizen/logout`, { method: 'POST', credentials: 'include' });
    setCitizenName(null);
    setView('home');
  }

  function renderView() {
    if (view === 'map') return <ReportsMap apiUrl={API_URL} />;
    if (view === 'login') return <CitizenAuth apiUrl={API_URL} onNavigate={setView}
      onAuthed={(name) => { setCitizenName(name); setView('report'); }} />;
    if (view === 'adminLogin') return <AdminLogin apiUrl={API_URL} onNavigate={setView}
      onAuthed={(name) => { setAdminUsername(name); setView('adminDashboard'); }} />;
    if (view === 'adminDashboard') return <AdminDashboard apiUrl={API_URL} adminUsername={adminUsername}
      onLogout={() => { setAdminUsername(null); setView('home'); }} />;
    if (view === 'report') {
      if (!citizenName) { setView('login'); return null; }
      if (result) {
        return (
          <div className="result-card">
            <div className={`stamp ${result.status === 'rejected' ? 'stamp-rejected' : result.status === 'pending_verification' ? 'stamp-pending' : ''}`}>
              {result.status === 'verified' ? 'Verified' : result.status === 'rejected' ? 'Not Verified' : 'Under Review'}
            </div>
            <h2>Thank you — your report is in.</h2>
            <p>
              {result.status === 'verified'
                ? "Our AI verified this photo and confirmed it's a genuine civic issue. It now appears on the public map."
                : result.status === 'rejected'
                ? 'Our AI could not confirm this photo shows a genuine civic issue, so it was not published. Feel free to submit again with a clearer photo.'
                : 'Our AI is reviewing the photo. Verified reports appear on the public map for government departments.'}
            </p>
            <div className="result-meta">
              <div><span className="meta-label">Report ID</span><span className="meta-value">#{result.id ?? '—'}</span></div>
              <div><span className="meta-label">Status</span>
                <span className={`meta-value status-badge status-${result.status}`}>{(result.status ?? 'pending_verification').replace(/_/g, ' ')}</span>
              </div>
            </div>
            <button className="btn-secondary" onClick={() => setResult(null)}>Submit another report</button>
            {result.status === 'verified' && (
              <button className="btn-link" onClick={() => setView('map')}>View it on the live map →</button>
            )}
          </div>
        );
      }
      return <ReportForm onSubmit={handleSubmit} submitting={submitting} />;
    }
    return <Home onNavigate={setView} citizenName={citizenName} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => setView('home')}>
          <span className="brand-mark">CL</span>
          <div>
            <div className="brand-name">CivicLens AI</div>
            <div className="brand-tag">Lahore Civic Intelligence</div>
          </div>
        </div>
        <nav className="nav-tabs">
          <button className={`nav-tab ${view === 'home' ? 'nav-tab-active' : ''}`} onClick={() => setView('home')}>Home</button>
          <button className={`nav-tab ${view === 'report' ? 'nav-tab-active' : ''}`} onClick={() => setView(citizenName ? 'report' : 'login')}>Report an Issue</button>
          <button className={`nav-tab ${view === 'map' ? 'nav-tab-active' : ''}`} onClick={() => setView('map')}>Live Map</button>
          {view !== 'adminDashboard' && view !== 'adminLogin' && citizenName && (
            <button className="nav-tab" onClick={handleCitizenLogout}>Log out ({citizenName})</button>
          )}
        </nav>
      </header>
      <main className="main-content">
        {renderView()}
        {submitError && <div className="form-error page-error">{submitError}</div>}
      </main>
      <footer className="footer">Smart City Hackathon Lahore 2026 — Theme: City Intelligence</footer>
    </div>
  );
}

export default App;