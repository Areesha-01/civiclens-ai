import { useState } from 'react';
import LocationPicker from './LocationPicker';
import { AREAS } from '../constants';

const CATEGORIES = [
  { id: 'pothole', label: 'Pothole / Road Damage' },
  { id: 'garbage', label: 'Garbage' },
  { id: 'streetlight', label: 'Broken Streetlight' },
  { id: 'water', label: 'Water / Sewerage' },
  { id: 'other', label: 'Other' },
];

export default function ReportForm({ onSubmit, submitting }) {
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('pothole');
  const [position, setPosition] = useState(null);
    const [area, setArea] = useState('');
  const [error, setError] = useState('');

  function handlePhotoChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!photo) return setError('Please attach a photo of the issue.');
    if (!description.trim()) return setError('Please add a short description.');
    if (!position) return setError('Please mark the location on the map.');
    if (!area) return setError('Please select your area.');
        onSubmit({ photo, description, category, area, position });
  }

  return (
    <form className="report-form" onSubmit={handleSubmit}>
      <div className="form-eyebrow">Step 1 of 1</div>
      <h2>Report a civic issue</h2>
      <p className="form-sub">
        Add a photo, describe what you see, and mark the spot. Our AI verifies
        and routes it to the right department.
      </p>

      <label className="field-label">Photo evidence</label>
      <label className="photo-drop">
        {photoPreview ? (
          <img src={photoPreview} alt="Preview" className="photo-preview" />
        ) : (
          <span className="photo-placeholder">
            <span className="photo-icon">+</span>
            Tap to attach a photo
          </span>
        )}
        <input type="file" accept="image/*" onChange={handlePhotoChange} hidden />
      </label>

      <label className="field-label">Issue type</label>
      <div className="chip-row">
        {CATEGORIES.map((c) => (
          <button
            type="button"
            key={c.id}
            className={`chip ${category === c.id ? 'chip-active' : ''}`}
            onClick={() => setCategory(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <label className="field-label" htmlFor="description">Description</label>
      <textarea
        id="description"
        placeholder="e.g. Large pothole near the main road, causing traffic slowdown"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={3}
      />
      <label className="field-label" htmlFor="area">Area</label>
      <select id="area" className="text-input" value={area} onChange={(e) => setArea(e.target.value)}>
        <option value="">Select your area</option>
        {AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
      </select>
      <label className="field-label">Location</label>
      <LocationPicker position={position} onPick={setPosition} />

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? 'Submitting…' : 'Submit report'}
      </button>
    </form>
  );
}
