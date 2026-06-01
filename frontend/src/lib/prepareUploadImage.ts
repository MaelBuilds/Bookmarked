import { MAX_FILE_BYTES } from '../constants'

const MAX_LONG_EDGE = 2048
const JPEG_QUALITY = 0.85
const JPEG_QUALITY_RETRY = 0.75
const JPEG_QUALITY_EXIF_ONLY = 0.92

export type PrepareImageErrorCode = 'not_image' | 'file_too_large' | 'file_read_error'

export class PrepareImageError extends Error {
  constructor(readonly code: PrepareImageErrorCode) {
    super(code)
    this.name = 'PrepareImageError'
  }
}

/** Read JPEG EXIF orientation (1–8). Non-JPEG or missing tag → 1. */
export async function getExifOrientation(file: File): Promise<number> {
  if (!file.type.includes('jpeg') && !file.type.includes('jpg')) {
    const name = file.name.toLowerCase()
    if (!name.endsWith('.jpg') && !name.endsWith('.jpeg')) return 1
  }

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

  let targetW = orientedW
  let targetH = orientedH
  if (compressForSize) {
    const longEdge = Math.max(orientedW, orientedH)
    if (longEdge > MAX_LONG_EDGE) {
      const scale = MAX_LONG_EDGE / longEdge
      targetW = Math.round(orientedW * scale)
      targetH = Math.round(orientedH * scale)
    }
  }

  if (targetW === orientedW && targetH === orientedH) {
    return encodeCanvas(oriented, compressForSize)
  }

  const scaled = document.createElement('canvas')
  scaled.width = targetW
  scaled.height = targetH
  const sctx = scaled.getContext('2d')
  if (!sctx) throw new PrepareImageError('file_read_error')
  sctx.drawImage(oriented, 0, 0, orientedW, orientedH, 0, 0, targetW, targetH)
  return encodeCanvas(scaled, compressForSize)
}

/**
 * Normalize upload images: EXIF orientation when needed; resize/compress only over cap.
 */
export async function prepareUploadImage(file: File): Promise<{ dataUrl: string }> {
  if (!file.type.startsWith('image/')) {
    throw new PrepareImageError('not_image')
  }

  const orientation = await getExifOrientation(file)
  const compressForSize = file.size > MAX_FILE_BYTES
  const needsCanvas = orientation !== 1 || compressForSize

  if (!needsCanvas) {
    const dataUrl = await readFileAsDataUrl(file)
    return { dataUrl }
  }

  const img = await loadImageFromFile(file)
  const dataUrl = await renderToDataUrl(img, orientation, compressForSize)
  return { dataUrl }
}
