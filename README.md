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

Dynamic wallpapers have a **Wallpaper Engine** button next to the normal download. It builds a ready-to-import
Wallpaper Engine web wallpaper (`project.json`, a page that switches with the clock and crossfades, a preview and
a README) that follows the time of day:

- **Still dynamic wallpapers** (Tahoe, Sonoma, Big Sur, The Lake, hello, …): light/dark or dawn/day/dusk/night
  images that the page loads from the web while it runs, so the package is tiny and builds in any browser.
- **Aerial sets** filmed at several times of day (Tahoe, Golden Gate, Sequoia): Apple's videos go inside the
  package; copy the zip to your PC.

Grid, Motion, Iridescence and Macintosh have no public light/dark images, so they don't get the button.

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
  Cloudflare Worker proxy (`dry-dawn-9e3c.felixmgoff.workers.dev`, see `src/lib/downloads.svelte.js`). Firefox can't
  play Apple's HEVC videos, so aerial previews show the still picture there; downloads still work.
- Wallpaper Engine packages contain Apple's original 4K HEVC videos; they're untested in Wallpaper Engine itself, and some PCs need Microsoft's HEVC Video Extensions to play them.
- macOS versions for archive items follow the album's order and are best guesses in places.
