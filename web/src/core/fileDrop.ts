/**
 * Recursive file & folder reader for browser drag-and-drop and FileList inputs.
 */

import type { CsvInputFile } from './parser'

interface WebkitFileSystemEntry {
  isFile: boolean
  isDirectory: boolean
  name: string
  fullPath: string
  file?: (cb: (f: File) => void, err?: (e: unknown) => void) => void
  createReader?: () => {
    readEntries: (cb: (entries: WebkitFileSystemEntry[]) => void, err?: (e: unknown) => void) => void
  }
}

async function readEntryRecursively(entry: WebkitFileSystemEntry): Promise<CsvInputFile[]> {
  if (entry.isFile && entry.file) {
    const file = await new Promise<File>((resolve, reject) => {
      entry.file!(resolve, reject)
    })
    const buf = new Uint8Array(await file.arrayBuffer())
    return [
      {
        name: file.name,
        relativePath: entry.fullPath.replace(/^\/+/, '') || file.name,
        content: buf,
      },
    ]
  }

  if (entry.isDirectory && entry.createReader) {
    const reader = entry.createReader()
    const allEntries: WebkitFileSystemEntry[] = []
    // DirectoryReader returns batches up to 100 entries until an empty array
    while (true) {
      const batch = await new Promise<WebkitFileSystemEntry[]>((resolve, reject) => {
        reader.readEntries(resolve, reject)
      })
      if (batch.length === 0) break
      allEntries.push(...batch)
    }
    const nested = await Promise.all(allEntries.map((child) => readEntryRecursively(child)))
    return nested.flat()
  }

  return []
}

export async function readFileListToCsvInputs(fileList: FileList | File[]): Promise<CsvInputFile[]> {
  const files = Array.from(fileList)
  return Promise.all(
    files.map(async (f) => {
      const rel = (f as File & { webkitRelativePath?: string }).webkitRelativePath
      const buf = new Uint8Array(await f.arrayBuffer())
      return {
        name: f.name,
        relativePath: rel && rel.length > 0 ? rel : f.name,
        content: buf,
      }
    }),
  )
}

export async function readDropDataTransfer(dt: DataTransfer): Promise<CsvInputFile[]> {
  const items = Array.from(dt.items ?? [])
  const entries: WebkitFileSystemEntry[] = []
  for (const item of items) {
    const getter = (item as DataTransferItem & { webkitGetAsEntry?: () => WebkitFileSystemEntry | null })
      .webkitGetAsEntry
    if (typeof getter === 'function') {
      const entry = getter.call(item)
      if (entry) entries.push(entry)
    }
  }
  if (entries.length > 0) {
    const results = await Promise.all(entries.map((e) => readEntryRecursively(e)))
    return results.flat()
  }
  return readFileListToCsvInputs(dt.files)
}
