export type ProductErrorCategory = 'PARCEL' | 'PROVIDER' | 'ANALYSIS' | 'INTERNAL'

export interface ProductErrorDetail {
  schema_version: 'SITE_API_ERROR_V1'
  code: string
  category: ProductErrorCategory
  message: string
  retryable: boolean
}

export interface ParsedApiError {
  detail: ProductErrorDetail | null
  legacyMessage: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

function isProductErrorCategory(value: unknown): value is ProductErrorCategory {
  return value === 'PARCEL' || value === 'PROVIDER' || value === 'ANALYSIS' || value === 'INTERNAL'
}

function isProductErrorDetail(value: unknown): value is ProductErrorDetail {
  if (!isRecord(value)) return false
  return (
    value.schema_version === 'SITE_API_ERROR_V1' &&
    typeof value.code === 'string' &&
    value.code.trim().length > 0 &&
    isProductErrorCategory(value.category) &&
    typeof value.message === 'string' &&
    value.message.trim().length > 0 &&
    typeof value.retryable === 'boolean'
  )
}

export async function readApiError(response: Response): Promise<ParsedApiError> {
  try {
    const body: unknown = await response.json()
    if (!isRecord(body)) return { detail: null, legacyMessage: null }
    const detail = body.detail
    if (isProductErrorDetail(detail)) return { detail, legacyMessage: null }
    if (typeof detail === 'string' && detail.trim()) {
      return { detail: null, legacyMessage: detail.trim() }
    }
  } catch {
    // Fall through to the stable generic caller message.
  }
  return { detail: null, legacyMessage: null }
}

export class ProductApiError extends Error {
  readonly code: string | null
  readonly category: ProductErrorCategory | null
  readonly retryable: boolean | null
  readonly httpStatus: number

  constructor(message: string, httpStatus: number, detail: ProductErrorDetail | null = null) {
    super(message)
    this.name = 'ProductApiError'
    this.code = detail?.code ?? null
    this.category = detail?.category ?? null
    this.retryable = detail?.retryable ?? null
    this.httpStatus = httpStatus
  }
}
