import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const src = path.resolve(__dirname, '../docs/.vitepress/dist')
const targets = [
  path.resolve(__dirname, '../dist'),
  path.resolve(__dirname, '../.vitepress/dist')
]

for (const target of targets) {
  try {
    fs.mkdirSync(target, { recursive: true })
    fs.cpSync(src, target, { recursive: true })
    console.log(`Successfully mirrored build output to ${target}`)
  } catch (err) {
    console.error(`Failed to mirror to ${target}:`, err)
  }
}
