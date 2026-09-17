import { useEffect, useRef, useState } from 'react'
import type { ParcelCandidate, ParcelConfirmationResponse } from '../types/parcel'
import {
  candidateReferenceGeometryToMapGeometry,
  candidateToMapMarker,
  verifiedGeometryToMapGeometry,
} from './MapAdapter'

interface KakaoMapProps {
  candidates: ParcelCandidate[]
  selectedCandidate: ParcelCandidate | null
  confirmation: ParcelConfirmationResponse | null
  onCandidateSelect: (candidate: ParcelCandidate) => void
}

const DEFAULT_CENTER = { latitude: 37.5665, longitude: 126.978 }
const KAKAO_SDK_ID = 'kakao-maps-sdk'

export default function KakaoMap({ candidates, selectedCandidate, confirmation, onCandidateSelect }: KakaoMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<KakaoMap | null>(null)
  const markersRef = useRef<KakaoMarker[]>([])
  const candidatePolygonsRef = useRef<KakaoPolygon[]>([])
  const verifiedPolygonsRef = useRef<KakaoPolygon[]>([])
  const [sdkReady, setSdkReady] = useState(false)
  const [mapError, setMapError] = useState('')

  useEffect(() => {
    const appKey = import.meta.env.VITE_KAKAO_MAP_JAVASCRIPT_KEY
    if (!appKey) {
      setMapError('Kakao Maps JavaScript Key가 설정되지 않았습니다.')
      return
    }

    let cancelled = false

    loadKakaoMapsSdk(appKey)
      .then(() => {
        if (!cancelled) setSdkReady(true)
      })
      .catch((error) => {
        if (!cancelled) {
          setMapError(error instanceof Error ? error.message : 'Kakao Maps SDK를 불러오지 못했습니다.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!sdkReady || !containerRef.current || !window.kakao) return

    if (!mapRef.current) {
      mapRef.current = new window.kakao.maps.Map(containerRef.current, {
        center: new window.kakao.maps.LatLng(DEFAULT_CENTER.latitude, DEFAULT_CENTER.longitude),
        level: 4,
      })
    }

    mapRef.current.relayout()
  }, [sdkReady])

  useEffect(() => {
    const container = containerRef.current
    const map = mapRef.current
    if (!sdkReady || !container || !map || typeof ResizeObserver === 'undefined') return

    let frameId: number | null = null
    const observer = new ResizeObserver(() => {
      if (frameId !== null) window.cancelAnimationFrame(frameId)
      frameId = window.requestAnimationFrame(() => {
        map.relayout()
        if (confirmation) fitMapToConfirmation(map, confirmation)
        frameId = null
      })
    })

    observer.observe(container)

    return () => {
      observer.disconnect()
      if (frameId !== null) window.cancelAnimationFrame(frameId)
    }
  }, [confirmation, sdkReady])

  useEffect(() => {
    const kakao = window.kakao
    const map = mapRef.current
    if (!sdkReady || !kakao || !map) return

    markersRef.current.forEach((marker) => marker.setMap(null))
    markersRef.current = []
    candidatePolygonsRef.current.forEach((polygon) => polygon.setMap(null))
    candidatePolygonsRef.current = []

    const bounds = new kakao.maps.LatLngBounds()
    let hasBounds = false

    candidates.forEach((candidate) => {
      const markerInput = candidateToMapMarker(candidate)
      const position = new kakao.maps.LatLng(markerInput.position.latitude, markerInput.position.longitude)
      const marker = new kakao.maps.Marker({ map, position })
      const isSelected = selectedCandidate?.candidate_pnu === candidate.candidate_pnu

      marker.setOpacity(isSelected ? 1 : 0.72)
      marker.setZIndex(isSelected ? 10 : 1)
      kakao.maps.event.addListener(marker, 'click', () => onCandidateSelect(candidate))
      markersRef.current.push(marker)

      bounds.extend(position)
      hasBounds = true

      if (!confirmation && candidate.reference_geometry) {
        const referenceGeometry = candidateReferenceGeometryToMapGeometry(candidate.reference_geometry)
        referenceGeometry?.polygons.forEach((polygonRings) => {
          const path = polygonRings.map((ring) =>
            ring.map((point) => {
              const polygonPoint = new kakao.maps.LatLng(point.latitude, point.longitude)
              bounds.extend(polygonPoint)
              hasBounds = true
              return polygonPoint
            }),
          )

          const polygon = new kakao.maps.Polygon({
            map,
            path,
            strokeWeight: isSelected ? 3 : 1,
            strokeColor: isSelected ? '#315f45' : '#607568',
            strokeOpacity: isSelected ? 0.9 : 0.55,
            strokeStyle: 'solid',
            fillColor: isSelected ? '#8fb99d' : '#c8d5cc',
            fillOpacity: isSelected ? 0.2 : 0.08,
          })
          kakao.maps.event.addListener(polygon, 'click', () => onCandidateSelect(candidate))
          candidatePolygonsRef.current.push(polygon)
        })
      }
    })

    if (confirmation) return

    if (selectedCandidate) {
      const selectedReferenceGeometry = selectedCandidate.reference_geometry
        ? candidateReferenceGeometryToMapGeometry(selectedCandidate.reference_geometry)
        : null
      if (selectedReferenceGeometry) {
        fitMapToGeometry(map, selectedReferenceGeometry.polygons)
      } else {
        map.setCenter(new kakao.maps.LatLng(selectedCandidate.y, selectedCandidate.x))
      }
    } else if (hasBounds) {
      map.setBounds(bounds)
    }
  }, [candidates, selectedCandidate, confirmation, onCandidateSelect, sdkReady])

  useEffect(() => {
    const kakao = window.kakao
    const map = mapRef.current
    if (!sdkReady || !kakao || !map) return

    verifiedPolygonsRef.current.forEach((polygon) => polygon.setMap(null))
    verifiedPolygonsRef.current = []

    if (!confirmation) return

    const verifiedGeometry = verifiedGeometryToMapGeometry(confirmation.geometry)
    if (!verifiedGeometry) {
      setMapError('Backend가 반환한 검증 필지 경계를 지도 형식으로 변환하지 못했습니다.')
      return
    }

    const bounds = new kakao.maps.LatLngBounds()
    let hasBounds = false

    verifiedGeometry.polygons.forEach((polygonRings) => {
      const path = polygonRings.map((ring) =>
        ring.map((point) => {
          const position = new kakao.maps.LatLng(point.latitude, point.longitude)
          bounds.extend(position)
          hasBounds = true
          return position
        }),
      )

      const polygon = new kakao.maps.Polygon({
        map,
        path,
        strokeWeight: 3,
        strokeColor: '#172033',
        strokeOpacity: 0.9,
        strokeStyle: 'solid',
        fillColor: '#2f855a',
        fillOpacity: 0.22,
      })
      verifiedPolygonsRef.current.push(polygon)
    })

    if (hasBounds) map.setBounds(bounds)
  }, [confirmation, sdkReady])

  return (
    <section className="map-stage" aria-label="필지 지도">
      <div ref={containerRef} className="kakao-map" />
      {!mapError && sdkReady && candidates.length > 0 && !confirmation && (
        <div className="map-selection-guide">지도 마커 또는 옅은 필지 경계를 선택해 필지를 확인할 수 있습니다.</div>
      )}
      {mapError && (
        <div className="map-message map-message-error" role="alert">
          <strong>지도를 표시하지 못했습니다.</strong>
          <span>{mapError}</span>
        </div>
      )}
      {!mapError && !sdkReady && (
        <div className="map-message" role="status">
          <strong>지도를 불러오고 있습니다.</strong>
        </div>
      )}
      {!mapError && sdkReady && confirmation && (
        <div className="map-verification-badge">VERIFIED PARCEL</div>
      )}
    </section>
  )
}

function fitMapToGeometry(map: KakaoMap, polygons: { latitude: number; longitude: number }[][][]): void {
  const kakao = window.kakao
  if (!kakao) return

  const bounds = new kakao.maps.LatLngBounds()
  let hasBounds = false
  polygons.forEach((polygonRings) => {
    polygonRings.forEach((ring) => {
      ring.forEach((point) => {
        bounds.extend(new kakao.maps.LatLng(point.latitude, point.longitude))
        hasBounds = true
      })
    })
  })
  if (hasBounds) map.setBounds(bounds)
}

function fitMapToConfirmation(map: KakaoMap, confirmation: ParcelConfirmationResponse): void {
  const verifiedGeometry = verifiedGeometryToMapGeometry(confirmation.geometry)
  if (!verifiedGeometry) return
  fitMapToGeometry(map, verifiedGeometry.polygons)
}

function loadKakaoMapsSdk(appKey: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const finishLoading = () => {
      if (!window.kakao?.maps) {
        reject(new Error('Kakao Maps SDK 초기화에 실패했습니다.'))
        return
      }
      window.kakao.maps.load(resolve)
    }

    if (window.kakao?.maps) {
      finishLoading()
      return
    }

    const existingScript = document.getElementById(KAKAO_SDK_ID) as HTMLScriptElement | null
    if (existingScript) {
      existingScript.addEventListener('load', finishLoading, { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Kakao Maps SDK 요청에 실패했습니다.')), {
        once: true,
      })
      return
    }

    const script = document.createElement('script')
    script.id = KAKAO_SDK_ID
    script.async = true
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false`
    script.addEventListener('load', finishLoading, { once: true })
    script.addEventListener('error', () => reject(new Error('Kakao Maps SDK 요청에 실패했습니다.')), { once: true })
    document.head.appendChild(script)
  })
}
