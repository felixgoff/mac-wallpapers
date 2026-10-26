// The desktop app (src-tauri) runs this same page in real windows; these tell the page where it is
export const APP = '__TAURI_INTERNALS__' in window;
// Set by the Rust side when it opens the Quick Look window for a wallpaper
export const PREVIEW = APP ? (window.__PREVIEW__ ?? null) : null;
export const PLATFORM = /Mac/.test(navigator.userAgent) ? 'mac' : /Win/.test(navigator.userAgent) ? 'win' : 'linux';
export const SITE = 'https://felixgoff.github.io/mac-wallpapers/';
