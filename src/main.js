import './app.css';
import { mount } from 'svelte';
import { openUrl } from '@tauri-apps/plugin-opener';
import App from './App.svelte';
import Preview from './Preview.svelte';
import { APP, PREVIEW, PLATFORM } from './lib/desktop.js';

if (APP) {
  document.documentElement.classList.add('app', `app-${PLATFORM}`, ...(PREVIEW ? ['preview'] : []));
  // The app's windows only show the gallery: web links open in the browser
  document.addEventListener('click', e => {
    const a = e.target.closest?.('a[href^="http"]');
    if (!a || e.defaultPrevented) return;
    e.preventDefault();
    openUrl(a.href);
  });
}

mount(PREVIEW ? Preview : App, { target: document.getElementById('app') });

// Fade out the loading screen from index.html now that the app is on screen
const splash = document.getElementById('splash');
splash.classList.add('done');
setTimeout(() => splash.remove(), 600); // after the .5s fade; a timer, as background tabs may never animate
