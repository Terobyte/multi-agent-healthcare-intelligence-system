/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PUBLIC_URL?: string;
  readonly VITE_DEMO_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
