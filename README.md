# Mac Wallpapers

Every Mac wallpaper in one place, in a page that looks like a macOS window: the macOS aerials,
the current Desktop Pictures, Apple's extra wallpapers and an archive going back to Mac OS X 10.0.
Browse by category or by macOS release, preview with Quick Look (double-click or Space) and download.
Every wallpaper has a share link (Quick Look › Copy Link, e.g. `…/mac-wallpapers/w/macos-tahoe/`) that shows the
wallpaper's name and picture in chats and opens straight into it. `scripts/share-pages.js` writes those pages after `vite build`.

**Live site:** https://felixgoff.github.io/mac-wallpapers/

Built with [Svelte](https://svelte.dev) and [Vite](https://vite.dev) as a static site. Every push to
`main` is tested, built and deployed to GitHub Pages by `.github/workflows/deploy.yml`; every Monday
`.github/workflows/check-links.yml` checks that all download links still work (`node scripts/check-links.js` runs it locally).

## Wallpaper Engine packages

Every wallpaper that moves or changes has a **Wallpaper Engine** button next to the normal download. It builds a
ready-to-import Wallpaper Engine web wallpaper (`project.json`, a page that switches with the clock and crossfades,
a preview, a README and an installer):

- **Still dynamic wallpapers** (Tahoe, Sonoma, Big Sur, The Lake, hello, …): light/dark or dawn/day/dusk/night
  images that the page loads from the web while it runs, so the package is tiny and builds in any browser.
- **Aerial sets** filmed at several times of day (Tahoe, Golden Gate, Sequoia): Apple's videos go inside the
  package; copy the zip to your PC.
- **Single aerials**: the video, looping.

Grid, Motion and Iridescence have no light/dark copies anywhere, so the page takes both images out of Apple's HEIC
while it builds the package (below) and puts them inside. Macintosh is drawn live by macOS and has no file, so it
only links to a recording on the Steam Workshop.

## Full-size pictures

Quick Look shows each picture at full size. Apple's catalog only offers zipped HEIC files, so for those the page
fetches the zip through the proxy, takes out the HEIC (`unzipFile` in `src/lib/zip.js`) and decodes it
(`src/lib/heic.js`): Safari natively, other browsers with [libheif](https://github.com/catdad-experiments/libheif-js),
a 2 MB decoder that loads the first time it's needed. An activity panel at the bottom right shows every download,
decode and package build with its progress and a Cancel button.

The repo holds no full-size images or videos: macOS Sonoma's videos, which Apple only ships inside macOS, are files
on the [media release](https://github.com/felixgoff/mac-wallpapers/releases/tag/media) (`build_data.py` uploads
them the first time).

## App

`src-tauri/` wraps the same page in a [Tauri](https://tauri.app) desktop app for macOS, Windows and Linux. The real
window is the Finder window: on a Mac it has the system's traffic lights and sidebar material; on Windows and Linux
it's frameless and the page's traffic lights close, minimize and zoom it. Quick Look opens in a second window. The app
downloads straight from Apple's and the other servers (no proxy) into Downloads, installs Wallpaper Engine packages
straight into Wallpaper Engine (Windows; elsewhere the package folder goes to Downloads), and **Set as Wallpaper**
makes a picture the desktop picture (on a Mac Apple's own HEIC, so dynamic ones keep following the time of day).

```sh
npm run icons       # Tauri's icons from public/icon.png, into src-tauri/icons/ (not committed)
npm run tauri dev   # the app, with the page hot-reloading
npm run tauri build # installers in src-tauri/target/release/bundle/
```

`.github/workflows/app.yml` builds the installers on macOS (universal), Windows and Linux: pushing a tag like
`app-v1.0.0` publishes them as a GitHub Release, a manual run keeps them as workflow artifacts. The builds aren't
signed, so the first time macOS's Gatekeeper refuses the app (right-click it › Open, or System Settings › Privacy &
Security › Open Anyway) and Windows SmartScreen warns (More info › Run anyway).

## Develop

```sh
npm install
npm run dev     # local server with hot reload
npm test        # filtering and grouping tests
npm run build   # static site in dist/
```

## Updating the wallpaper list

The site reads `src/data.json` and the thumbnails in `public/thumbs/`. Both are generated on a Mac
(it reads `/System/Library/Desktop Pictures` and uses `sips`) and committed:

```sh
cp ~/Downloads/entries.json scripts/cache/   # Apple's aerial manifest
curl -o scripts/cache/catalog.xml https://mesu.apple.com/assets/macos/com_apple_MobileAsset_DesktopPicture/com_apple_MobileAsset_DesktopPicture.xml
python3 scripts/bag.py           # Apple's wallpapers republished by Basic Apple Guy
python3 scripts/fetch_album.py   # the "macOS Wallpapers" Google Photos album
python3 scripts/build_data.py    # writes src/data.json and public/thumbs/
```

`scripts/cache/` holds the downloaded inputs and isn't committed.

## Sources

- **Aerials:** Apple's aerial manifest; the videos stream from Apple's servers.
- **Desktop Pictures:** Apple's desktop-picture catalog (`mesu.apple.com`); downloads come from Apple as zipped HEIC files.
- **Apple Extras:** Apple's own wallpapers as republished by [Basic Apple Guy](https://basicappleguy.com) — some are
  frames from Apple's videos that he upscaled; each one says so and links to his post.
- **macOS Archive:** the "macOS Wallpapers" Google Photos album shared by Евгений Богун.
- **Tahoe, Sequoia and other light/dark images:** [LAYTAT/macOS-Wallpapers](https://github.com/LAYTAT/macOS-Wallpapers) on GitHub.

All wallpapers are © Apple Inc. This is an unofficial fan project and isn't affiliated with Apple.

## Known limits

- Only Safari trusts the certificate of Apple's aerial server. Other browsers preview and download aerials through a
  Cloudflare Worker proxy (`dry-dawn-9e3c.felixmgoff.workers.dev`, see `src/lib/proxy.js`). Firefox can't
  play Apple's HEVC videos, so aerial previews show the still picture there; downloads still work.
- Wallpaper Engine packages contain Apple's original 4K HEVC videos; they're untested in Wallpaper Engine itself, and some PCs need Microsoft's HEVC Video Extensions to play them.
- macOS versions for archive items follow the album's order and are best guesses in places.
