# Mac Wallpapers

Every Mac wallpaper in one place, in a page that looks like a macOS window: the macOS aerials,
the current Desktop Pictures, Apple's extra wallpapers and an archive going back to Mac OS X 10.0.
Browse by category or by macOS release, preview with Quick Look (double-click or Space) and download.

**Live site:** https://felixgoff.github.io/mac-wallpapers/

Built with [Svelte](https://svelte.dev) and [Vite](https://vite.dev) as a static site. Every push to
`main` is tested, built and deployed to GitHub Pages by `.github/workflows/deploy.yml`.

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

All wallpapers are © Apple Inc. This is an unofficial fan project and isn't affiliated with Apple.

## Known limits

- Apple's aerial server uses a certificate Chrome doesn't trust, so aerial videos preview and download in Safari only.
- macOS versions for archive items follow the album's order and are best guesses in places.
