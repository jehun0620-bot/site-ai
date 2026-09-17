interface Window {
  kakao?: KakaoNamespace
}

interface KakaoNamespace {
  maps: KakaoMapsNamespace
}

interface KakaoMapsNamespace {
  load(callback: () => void): void
  Map: new (container: HTMLElement, options: KakaoMapOptions) => KakaoMap
  LatLng: new (latitude: number, longitude: number) => KakaoLatLng
  LatLngBounds: new () => KakaoLatLngBounds
  Marker: new (options: KakaoMarkerOptions) => KakaoMarker
  Polygon: new (options: KakaoPolygonOptions) => KakaoPolygon
}

interface KakaoMapOptions {
  center: KakaoLatLng
  level?: number
}

interface KakaoMap {
  setBounds(bounds: KakaoLatLngBounds): void
  setCenter(position: KakaoLatLng): void
  relayout(): void
}

interface KakaoLatLng {}

interface KakaoLatLngBounds {
  extend(position: KakaoLatLng): void
}

interface KakaoMarkerOptions {
  map?: KakaoMap
  position: KakaoLatLng
}

interface KakaoMarker {
  setMap(map: KakaoMap | null): void
}

interface KakaoPolygonOptions {
  map?: KakaoMap
  path: KakaoLatLng[] | KakaoLatLng[][]
  strokeWeight?: number
  strokeColor?: string
  strokeOpacity?: number
  strokeStyle?: string
  fillColor?: string
  fillOpacity?: number
}

interface KakaoPolygon {
  setMap(map: KakaoMap | null): void
}
