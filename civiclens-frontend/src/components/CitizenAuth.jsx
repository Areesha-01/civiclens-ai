import { useState } from 'react';

export default function CitizenAuth({ apiUrl, onAuthed, onNavigate }) {
  const [mode, setMode] = useState('login');
  const [fullName, setFullName] = useState('');
  const [cnic, setCnic] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const endpoint = mode === 'login' ? '/citizen/login' : '/citizen/signup';
      const body = mode === 'login'
        ? { cnic, password }
        : { full_name: fullName, cnic, phone, password };

      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Something went wrong.');
      onAuthed(data.full_name);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>
      <div className="form-eyebrow">Citizen Account</div>
      <h2>{mode === 'login' ? 'Log in to report an issue' : 'Create your account'}</h2>
      <p className="form-sub">
        {mode === 'login'
          ? 'Use your CNIC and password to continue.'
          : 'Your CNIC is used only to prevent duplicate accounts and is never stored in plain text.'}
      </p>

      {mode === 'signup' && (
        <>
          <label className="field-label" htmlFor="fullName">Full name</label>
          <input id="fullName" className="text-input" value={fullName}
            onChange={(e) => setFullName(e.target.value)} placeholder="Areesha Chaudhry" />
        </>
      )}

      <label className="field-label" htmlFor="cnic">CNIC</label>
      <input id="cnic" className="text-input" value={cnic}
        onChange={(e) => setCnic(e.target.value)} placeholder="35202-1234567-1" />

      {mode === 'signup' && (
        <>
          <label className="field-label" htmlFor="phone">Phone number</label>
          <input id="phone" className="text-input" value={phone}
            onChange={(e) => setPhone(e.target.value)} placeholder="03XX-XXXXXXX" />
        </>
      )}

      <label className="field-label" htmlFor="password">Password</label>
      <input id="password" type="password" className="text-input" value={password}
        onChange={(e) => setPassword(e.target.value)} placeholder="At least 6 characters" />

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
      </button>
      <button type="button" className="btn-link"
        onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}>
        {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Log in'}
      </button>
      <button type="button" className="btn-link" onClick={() => onNavigate('home')}>← Back to home</button>
    </form>
  );
}