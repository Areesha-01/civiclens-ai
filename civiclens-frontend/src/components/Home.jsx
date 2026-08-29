export default function Home({ onNavigate, citizenName }) {
  return (
    <div className="home-hero">
      <div className="form-eyebrow">Smart City Hackathon Lahore 2026</div>
      <h1>See something broken in your area? Report it in minutes.</h1>
      <p className="form-sub home-sub">
        CivicLens AI verifies your photo instantly and routes genuine issues
        straight to the map — no paperwork, no waiting.
      </p>
      <div className="home-actions">
        <button className="btn-primary" onClick={() => onNavigate(citizenName ? 'report' : 'login')}>
          Report an Issue
        </button>
        <button className="btn-secondary" onClick={() => onNavigate('map')}>
          View Reports Near You
        </button>
      </div>
      <button className="btn-link" onClick={() => onNavigate('adminLogin')}>
        Government login →
      </button>
    </div>
  );
}