/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HAYSTACK_API_URL: string
  readonly VITE_HAYSTACK_PROJECT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
