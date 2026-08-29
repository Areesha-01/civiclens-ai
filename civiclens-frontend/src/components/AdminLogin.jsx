import { useState } from 'react';

export default function AdminLogin({ apiUrl, onAuthed, onNavigate }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Login failed.');
      onAuthed(data.username);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>
      <div className="form-eyebrow">Government Access</div>
      <h2>Admin login</h2>
        <p className="form-sub">For authorized department staff only.</p>

      <label className="field-label" htmlFor="username">Username</label>
      <input id="username" className="text-input" value={username}
        onChange={(e) => setUsername(e.target.value)} />

      <label className="field-label" htmlFor="adminPassword">Password</label>
      <input id="adminPassword" type="password" className="text-input" value={password}
        onChange={(e) => setPassword(e.target.value)} />

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Please wait…' : 'Log in'}
      </button>
      <button type="button" className="btn-link" onClick={() => onNavigate('home')}>← Back to home</button>
    </form>
  );
}