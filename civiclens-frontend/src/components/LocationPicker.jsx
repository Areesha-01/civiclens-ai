import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix default marker icon issue with bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Lahore city center as default view
const LAHORE_CENTER = [31.5497, 74.3436];

function ClickHandler({ onPick }) {
  useMapEvents({
    click(e) {
      onPick({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

export default function LocationPicker({ position, onPick }) {
  return (
    <div className="location-picker">
      <MapContainer
        center={LAHORE_CENTER}
        zoom={12}
        scrollWheelZoom={true}
        style={{ height: '260px', width: '100%', borderRadius: 'var(--radius)' }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickHandler onPick={onPick} />
        {position && <Marker position={[position.lat, position.lng]} />}
      </MapContainer>
      <p className="location-hint">
        {position
          ? `Pinned: ${position.lat.toFixed(4)}, ${position.lng.toFixed(4)}`
          : 'Tap the map to mark where the issue is'}
      </p>
    </div>
  );
}
