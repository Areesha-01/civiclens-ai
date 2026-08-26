import { useState } from 'react';
import ReportForm from './components/ReportForm';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function App() {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState('');

  async function handleSubmit({ photo, description, category, position }) {
    setSubmitting(true);
    setSubmitError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('photo', photo);
      formData.append('description', description);
      formData.append('category', category);
      formData.append('lat', position.lat);
      formData.append('lng', position.lng);

      const res = await fetch(`${API_URL}/submit-report`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Server error, please try again.');
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setSubmitError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">CL</span>
          <div>
            <div className="brand-name">CivicLens AI</div>
            <div className="brand-tag">Lahore Civic Intelligence</div>
          </div>
        </div>
      </header>

      <main className="main-content">
        {result ? (
          <div className="result-card">
            <div className="stamp">Report Received</div>
            <h2>Thank you — your report is in.</h2>
            <p>
              Our AI is reviewing the photo to verify the issue and assign a
              priority level. Verified reports appear on the public map for
              government departments to act on.
            </p>
            <div className="result-meta">
              <div>
                <span className="meta-label">Report ID</span>
                <span className="meta-value">#{result.id ?? '—'}</span>
              </div>
              <div>
                <span className="meta-label">Status</span>
                <span className="meta-value status-pending">
                  {result.status ?? 'Pending verification'}
                </span>
              </div>
            </div>
            <button className="btn-secondary" onClick={() => setResult(null)}>
              Submit another report
            </button>
          </div>
        ) : (
          <ReportForm onSubmit={handleSubmit} submitting={submitting} />
        )}
        {submitError && <div className="form-error page-error">{submitError}</div>}
      </main>

      <footer className="footer">
        Smart City Hackathon Lahore 2026 — Theme: City Intelligence
      </footer>
    </div>
  );
}

export default App;
