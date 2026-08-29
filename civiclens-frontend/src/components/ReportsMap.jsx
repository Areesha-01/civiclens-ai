import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AREAS } from '../constants';

delete L.Icon.Default.prototype._getIconUrl;

const LAHORE_CENTER = [31.5497, 74.3436];

const STATUS_COLORS = {
  verified: '#2F7A54',
  pending_verification: '#D9A404',
  rejected: '#A63A26',
};

const CATEGORY_LABELS = {
  pothole: 'Pothole / Road Damage',
  garbage: 'Garbage',
  streetlight: 'Broken Streetlight',
  water: 'Water / Sewerage',
  other: 'Other',
};

function makeColoredIcon(color) {
  return L.divIcon({
    className: 'custom-pin',
    html: `<div style="
      width: 22px; height: 22px; border-radius: 50% 50% 50% 0;
      background: ${color}; transform: rotate(-45deg);
      border: 2px solid white; box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 22],
    popupAnchor: [0, -22],
  });
}

export default function ReportsMap({ apiUrl }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
    const [areaFilter, setAreaFilter] = useState('all');

  useEffect(() => {
    fetchReports();
    // Refresh every 15s so new reports show up without a manual reload
    const interval = setInterval(fetchReports, 15000);
    return () => clearInterval(interval);
  }, []);

  async function fetchReports() {
    try {
      const res = await fetch(`${apiUrl}/reports`);
      if (!res.ok) throw new Error('Could not load reports.');
      const data = await res.json();
      setReports(data);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

   const filteredReports = reports.filter((r) => {
    const statusOk = filter === 'all' || r.status === filter;
    const areaOk = areaFilter === 'all' || r.area === areaFilter;
    return statusOk && areaOk;
  });
  const counts = {
    all: reports.length,
    verified: reports.filter((r) => r.status === 'verified').length,
    pending_verification: reports.filter((r) => r.status === 'pending_verification').length,
    rejected: reports.filter((r) => r.status === 'rejected').length,
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Live Civic Reports</h2>
          <p className="form-sub">
            {loading ? 'Loading reports…' : `${filteredReports.length} report(s) shown`}
          </p>
        </div>
        <div className="filter-row">
          <button
            className={`filter-chip ${filter === 'all' ? 'filter-chip-active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({counts.all})
          </button>
          <button
            className={`filter-chip filter-verified ${filter === 'verified' ? 'filter-chip-active' : ''}`}
            onClick={() => setFilter('verified')}
          >
            Verified ({counts.verified})
          </button>
          <button
            className={`filter-chip filter-pending ${filter === 'pending_verification' ? 'filter-chip-active' : ''}`}
            onClick={() => setFilter('pending_verification')}
          >
            Pending ({counts.pending_verification})
          </button>
          <button
            className={`filter-chip filter-rejected ${filter === 'rejected' ? 'filter-chip-active' : ''}`}
            onClick={() => setFilter('rejected')}
          >
            Rejected ({counts.rejected})
          </button>
                    <select className="area-select" value={areaFilter} onChange={(e) => setAreaFilter(e.target.value)}>
            <option value="all">All areas</option>
            {AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="dashboard-map">
        <MapContainer
          center={LAHORE_CENTER}
          zoom={12}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {!loading && filteredReports.length === 0 && (
  <div className="empty-state">No reports match this filter yet.</div>
)}
          {!loading && filteredReports.length === 0 && (
            <div className="empty-state" style={{ position: 'absolute', zIndex: 400 }}>No reports match this filter yet.</div>
          )}
          {filteredReports.map((r) => (
            <Marker
              key={r.id}
              position={[r.lat, r.lng]}
              icon={makeColoredIcon(STATUS_COLORS[r.status] || '#52626D')}
            >
              <Popup>
                <div className="popup-content">
                  <img src={`${apiUrl}${r.image_url}`} alt={r.category} />
                  <div className="popup-category">
                    {CATEGORY_LABELS[r.ai_label] || CATEGORY_LABELS[r.category] || 'Other'}
                  </div>
                  <p className="popup-desc">{r.description}</p>
                  <div className="popup-meta">
                    <span className={`popup-status status-${r.status}`}>
                      {r.status.replace(/_/g, ' ')}
                    </span>
                    {r.ai_priority && (
                      <span className={`popup-priority priority-${r.ai_priority}`}>
                        {r.ai_priority} priority
                      </span>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
