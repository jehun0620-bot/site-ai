import type {
  ParcelCandidate,
  ParcelConfirmationGeometry,
  ParcelReferenceGeometry,
} from '../types/parcel'

export interface MapPoint {
  latitude: number
  longitude: number
}

export interface CandidateMapMarker {
  id: string
  position: MapPoint
}

export interface ParcelMapGeometry {
  type: 'Polygon' | 'MultiPolygon'
  polygons: MapPoint[][][]
}

export type CandidateReferenceMapGeometry = ParcelMapGeometry
export type VerifiedParcelMapGeometry = ParcelMapGeometry

export function candidateToMapMarker(candidate: ParcelCandidate): CandidateMapMarker {
  return {
    id: `${candidate.candidate_pnu}-${candidate.x}-${candidate.y}`,
    position: {
      latitude: candidate.y,
      longitude: candidate.x,
    },
  }
}

export function candidateReferenceGeometryToMapGeometry(
  geometry: ParcelReferenceGeometry,
): CandidateReferenceMapGeometry | null {
  return parcelGeometryToMapGeometry(geometry)
}

export function verifiedGeometryToMapGeometry(
  geometry: ParcelConfirmationGeometry,
): VerifiedParcelMapGeometry | null {
  return parcelGeometryToMapGeometry(geometry)
}

function parcelGeometryToMapGeometry(
  geometry: ParcelReferenceGeometry | ParcelConfirmationGeometry,
): ParcelMapGeometry | null {
  if (geometry.type === 'Polygon') {
    const polygon = parsePolygonCoordinates(geometry.coordinates)
    return polygon ? { type: 'Polygon', polygons: [polygon] } : null
  }

  const polygons = geometry.coordinates
    .map((coordinates) => parsePolygonCoordinates(coordinates))
    .filter((polygon): polygon is MapPoint[][] => polygon !== null)

  return polygons.length > 0 ? { type: 'MultiPolygon', polygons } : null
}

function parsePolygonCoordinates(value: unknown): MapPoint[][] | null {
  if (!Array.isArray(value)) return null

  const rings = value
    .map((ring) => parseRing(ring))
    .filter((ring): ring is MapPoint[] => ring !== null)

  return rings.length > 0 ? rings : null
}

function parseRing(value: unknown): MapPoint[] | null {
  if (!Array.isArray(value)) return null

  const points = value
    .map((coordinate) => parseCoordinate(coordinate))
    .filter((point): point is MapPoint => point !== null)

  return points.length >= 3 ? points : null
}

function parseCoordinate(value: unknown): MapPoint | null {
  if (!Array.isArray(value) || value.length < 2) return null

  const [longitude, latitude] = value
  if (typeof longitude !== 'number' || typeof latitude !== 'number') return null
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null
  if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return null

  return { latitude, longitude }
}
