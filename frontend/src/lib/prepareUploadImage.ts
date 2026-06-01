import { MAX_FILE_BYTES } from '../constants'

const MAX_LONG_EDGE = 2048
const JPEG_QUALITY = 0.85
const JPEG_QUALITY_RETRY = 0.75
const JPEG_QUALITY_EXIF_ONLY = 0.92
const ANALYSIS_LONG_EDGE = 512
const INK_THRESHOLD = 200
const FLIP_MIN_SCORE_DELTA = 500
const BOTTOM_TOP_WEIGHT = 0.25

export type PrepareImageErrorCode = 'not_image' | 'file_too_large' | 'file_read_error'

export class PrepareImageError extends Error {
  constructor(readonly code: PrepareImageErrorCode) {
    super(code)
    this.name = 'PrepareImageError'
  }
}

/** Read JPEG EXIF orientation (1–8). Non-JPEG or missing tag → 1. */
export async function getExifOrientation(file: File): Promise<number> {
  const buf = await file.slice(0, 65536).arrayBuffer()
  const view = new DataView(buf)
  if (view.byteLength < 2 || view.getUint16(0, false) !== 0xffd8) return 1

  let offset = 2
  while (offset + 4 < view.byteLength) {
    const marker = view.getUint16(offset, false)
    offset += 2
    if (marker === 0xffe1) {
      const tiff = offset + 2
      if (tiff + 8 > view.byteLength) return 1
      const little = view.getUint16(tiff, false) === 0x4949
      const ifd0 = tiff + view.getUint32(tiff + 4, little)
      if (ifd0 + 2 > view.byteLength) return 1
      const entries = view.getUint16(ifd0, little)
      for (let i = 0; i < entries; i++) {
        const entry = ifd0 + 2 + i * 12
        if (entry + 12 > view.byteLength) return 1
        if (view.getUint16(entry, little) === 0x0112) {
          return view.getUint16(entry + 8, little) || 1
        }
      }
      return 1
    }
    if ((marker & 0xff00) !== 0xff00) break
    const size = view.getUint16(offset, false)
    if (size < 2) break
    offset += size
  }
  return 1
}

function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new PrepareImageError('file_read_error'))
    }
    img.src = url
  })
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = String(ev.target?.result ?? '')
      if (!dataUrl) {
        reject(new PrepareImageError('file_read_error'))
        return
      }
      resolve(dataUrl)
    }
    reader.onerror = () => reject(new PrepareImageError('file_read_error'))
    reader.readAsDataURL(file)
  })
}

function orientedSize(
  width: number,
  height: number,
  orientation: number,
): { width: number; height: number } {
  if (orientation >= 5 && orientation <= 8) {
    return { width: height, height: width }
  }
  return { width, height }
}

function applyExifTransform(
  ctx: CanvasRenderingContext2D,
  orientation: number,
  width: number,
  height: number,
) {
  switch (orientation) {
    case 2:
      ctx.transform(-1, 0, 0, 1, width, 0)
      break
    case 3:
      ctx.transform(-1, 0, 0, -1, width, height)
      break
    case 4:
      ctx.transform(1, 0, 0, -1, 0, height)
      break
    case 5:
      ctx.transform(0, 1, 1, 0, 0, 0)
      break
    case 6:
      ctx.transform(0, 1, -1, 0, height, 0)
      break
    case 7:
      ctx.transform(0, -1, -1, 0, height, width)
      break
    case 8:
      ctx.transform(0, -1, 1, 0, 0, width)
      break
    default:
      break
  }
}

function canvasToJpegBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new PrepareImageError('file_read_error'))
          return
        }
        resolve(blob)
      },
      'image/jpeg',
      quality,
    )
  })
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = String(ev.target?.result ?? '')
      if (!dataUrl) {
        reject(new PrepareImageError('file_read_error'))
        return
      }
      resolve(dataUrl)
    }
    reader.onerror = () => reject(new PrepareImageError('file_read_error'))
    reader.readAsDataURL(blob)
  })
}

function inkProfile(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const { data } = ctx.getImageData(0, 0, w, h)
  const rows = new Array<number>(h).fill(0)
  for (let y = 0; y < h; y++) {
    let sum = 0
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4
      const lum = 0.299 * data[i]! + 0.587 * data[i + 1]! + 0.114 * data[i + 2]!
      if (lum < INK_THRESHOLD) sum++
    }
    rows[y] = sum
  }
  const mean = rows.reduce((a, b) => a + b, 0) / h
  const variance =
    rows.reduce((acc, r) => acc + (r - mean) ** 2, 0) / h || 0
  const third = Math.floor(h / 3)
  const top = rows.slice(0, third).reduce((a, b) => a + b, 0)
  const bottom = rows.slice(2 * third).reduce((a, b) => a + b, 0)
  return { variance, bottomTop: bottom - top }
}

function drawOrientedThumb(
  img: HTMLImageElement,
  exifOrientation: number,
  flip180: 0 | 180,
): { ctx: CanvasRenderingContext2D; w: number; h: number } | null {
  const { width, height } = orientedSize(
    img.naturalWidth,
    img.naturalHeight,
    exifOrientation,
  )
  const longEdge = Math.max(width, height)
  const scale = longEdge > ANALYSIS_LONG_EDGE ? ANALYSIS_LONG_EDGE / longEdge : 1
  const w = Math.max(1, Math.round(width * scale))
  const h = Math.max(1, Math.round(height * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, w, h)
  if (flip180 === 180) {
    ctx.translate(w, h)
    ctx.rotate(Math.PI)
  }
  applyExifTransform(ctx, exifOrientation, w, h)
  ctx.drawImage(img, 0, 0, w, h)
  return { ctx, w, h }
}

/** 180° correction when EXIF is normal but the page is physically upside down. */
function detectUpsideDown(
  img: HTMLImageElement,
  exifOrientation: number,
): 0 | 180 {
  const a = drawOrientedThumb(img, exifOrientation, 0)
  const b = drawOrientedThumb(img, exifOrientation, 180)
  if (!a || !b) return 0
  const profile0 = inkProfile(a.ctx, a.w, a.h)
  const profile180 = inkProfile(b.ctx, b.w, b.h)
  const score0 = profile0.variance + BOTTOM_TOP_WEIGHT * profile0.bottomTop
  const score180 = profile180.variance + BOTTOM_TOP_WEIGHT * profile180.bottomTop
  if (Math.abs(score180 - score0) < FLIP_MIN_SCORE_DELTA) return 0
  return score180 > score0 ? 180 : 0
}

function rotateCanvas180(source: HTMLCanvasElement): HTMLCanvasElement {
  const out = document.createElement('canvas')
  out.width = source.width
  out.height = source.height
  const ctx = out.getContext('2d')
  if (!ctx) throw new PrepareImageError('file_read_error')
  ctx.translate(out.width, out.height)
  ctx.rotate(Math.PI)
  ctx.drawImage(source, 0, 0)
  return out
}

async function encodeCanvas(
  canvas: HTMLCanvasElement,
  compressForSize: boolean,
): Promise<string> {
  const qualities = compressForSize
    ? [JPEG_QUALITY, JPEG_QUALITY_RETRY]
    : [JPEG_QUALITY_EXIF_ONLY]

  for (const quality of qualities) {
    const blob = await canvasToJpegBlob(canvas, quality)
    if (blob.size <= MAX_FILE_BYTES) {
      return blobToDataUrl(blob)
    }
  }
  throw new PrepareImageError('file_too_large')
}

async function renderToDataUrl(
  img: HTMLImageElement,
  orientation: number,
  compressForSize: boolean,
  flip180: 0 | 180,
): Promise<string> {
  const naturalW = img.naturalWidth
  const naturalH = img.naturalHeight
  if (!naturalW || !naturalH) {
    throw new PrepareImageError('file_read_error')
  }

  const { width: orientedW, height: orientedH } = orientedSize(
    naturalW,
    naturalH,
    orientation,
  )

  const oriented = document.createElement('canvas')
  oriented.width = orientedW
  oriented.height = orientedH
  const octx = oriented.getContext('2d')
  if (!octx) throw new PrepareImageError('file_read_error')

  applyExifTransform(octx, orientation, orientedW, orientedH)
  octx.drawImage(img, 0, 0)

  let source = oriented
  if (flip180 === 180) {
    source = rotateCanvas180(oriented)
  }

  let targetW = source.width
  let targetH = source.height
  if (compressForSize) {
    const longEdge = Math.max(source.width, source.height)
    if (longEdge > MAX_LONG_EDGE) {
      const scale = MAX_LONG_EDGE / longEdge
      targetW = Math.round(source.width * scale)
      targetH = Math.round(source.height * scale)
    }
  }

  if (targetW === source.width && targetH === source.height) {
    return encodeCanvas(source, compressForSize)
  }

  const scaled = document.createElement('canvas')
  scaled.width = targetW
  scaled.height = targetH
  const sctx = scaled.getContext('2d')
  if (!sctx) throw new PrepareImageError('file_read_error')
  sctx.drawImage(source, 0, 0, source.width, source.height, 0, 0, targetW, targetH)
  return encodeCanvas(scaled, compressForSize)
}

/**
 * Normalize upload images: EXIF orientation, 180° upright when needed; resize/compress over cap.
 */
export async function prepareUploadImage(file: File): Promise<{ dataUrl: string }> {
  if (!file.type.startsWith('image/')) {
    throw new PrepareImageError('not_image')
  }

  const orientation = await getExifOrientation(file)
  const compressForSize = file.size > MAX_FILE_BYTES
  const img = await loadImageFromFile(file)
  const flip180 = detectUpsideDown(img, orientation)
  const needsCanvas =
    orientation !== 1 || compressForSize || flip180 === 180

  if (!needsCanvas) {
    const dataUrl = await readFileAsDataUrl(file)
    return { dataUrl }
  }

  const dataUrl = await renderToDataUrl(img, orientation, compressForSize, flip180)
  return { dataUrl }
}
