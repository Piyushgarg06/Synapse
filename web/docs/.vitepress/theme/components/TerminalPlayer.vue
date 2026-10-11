<template>
  <div class="terminal-player" role="region" aria-label="Terminal Session Replay">
    <div class="terminal-header">
      <span class="terminal-title">{{ title || 'Terminal Session' }}</span>
      <div class="terminal-controls">
        <button type="button" @click="togglePlay" :aria-label="isPlaying ? 'Pause' : 'Play'">
          {{ isPlaying ? 'Pause' : 'Play' }}
        </button>
        <button type="button" @click="restart" aria-label="Restart">Restart</button>
        <button type="button" @click="toggleSpeed" aria-label="Toggle Speed">{{ speed }}x</button>
        <button type="button" @click="copyCommands" aria-label="Copy Commands">Copy</button>
      </div>
    </div>
    <div class="terminal-body" ref="terminalBody" aria-live="polite">
      {{ displayedText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

const defaultSession = `$ synapse init
Synapse initialized successfully (schema v1).

$ synapse index
Indexed 6 files, 9 symbols.
  Files processed: 6
  Symbols found: 9

$ synapse inspect UserService
Symbol: UserService (class)
  File:     backend/services/user_service.py:3-12
  ID:       57992df372a7a124
  Inherits from:
    - BaseService (backend/base.py:1)

$ synapse context get_user
# Synapse Repository Context: get_user

Found 1 item(s):
## Method: UserService.get_user
Path: backend/services/user_service.py (Lines 4-5)`

const props = withDefaults(defineProps<{
  transcript?: string
  title?: string
}>(), {
  transcript: defaultSession,
  title: 'Terminal Session'
})

const isPlaying = ref(false)
const displayedText = ref(props.transcript)
const speed = ref(1)
let timer: any = null
let charIndex = 0

function togglePlay() {
  if (isPlaying.value) {
    pause()
  } else {
    play()
  }
}

function play() {
  isPlaying.value = true
  if (charIndex >= props.transcript.length) {
    charIndex = 0
    displayedText.value = ''
  }
  const delay = Math.max(10, Math.floor(25 / speed.value))
  timer = setInterval(() => {
    if (charIndex < props.transcript.length) {
      charIndex += 4
      displayedText.value = props.transcript.slice(0, charIndex)
    } else {
      pause()
    }
  }, delay)
}

function pause() {
  isPlaying.value = false
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function restart() {
  pause()
  charIndex = 0
  displayedText.value = ''
  play()
}

function toggleSpeed() {
  speed.value = speed.value === 1 ? 2 : 1
  if (isPlaying.value) {
    pause()
    play()
  }
}

function copyCommands() {
  const lines = props.transcript
    .split('\n')
    .filter((l) => l.startsWith('$ '))
    .map((l) => l.slice(2))
    .join('\n')
  navigator.clipboard.writeText(lines || props.transcript)
}

onMounted(() => {
  // Check for reduced motion
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReduced) {
    displayedText.value = props.transcript
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
