import './app.css';
import { mount } from 'svelte';
import App from './App.svelte';

mount(App, { target: document.getElementById('app') });

// Fade out the loading screen from index.html now that the app is on screen
const splash = document.getElementById('splash');
splash.classList.add('done');
setTimeout(() => splash.remove(), 600); // after the .5s fade; a timer, as background tabs may never animate
