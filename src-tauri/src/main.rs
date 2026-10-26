// Mac Wallpapers as a desktop app: the gallery in a real window styled like macOS, plus what a web page
// can't do — download straight from any server, install into Wallpaper Engine, and set the desktop picture.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::ipc::{Channel, InvokeBody, Request};
use tauri::{AppHandle, Emitter, Manager, State, WebviewUrl, WebviewWindowBuilder};

/// Running jobs (downloads, installs) by the page's job key, so the page can cancel them
#[derive(Default)]
struct Jobs(Mutex<HashMap<String, Arc<AtomicBool>>>);
static STAGED: AtomicU64 = AtomicU64::new(0);

/// One file to save: downloaded from `url`, or moved from a file `stage` wrote
#[derive(Deserialize)]
struct FileSpec {
    name: String,
    url: Option<String>,
    staged: Option<String>,
}

#[derive(Clone, Serialize)]
struct Progress {
    file: usize,
    files: usize,
    got: u64,
    total: u64,
}

#[derive(Serialize)]
struct Saved {
    path: String,
    /// true when the files went into Wallpaper Engine's projects folder
    installed: bool,
}

#[derive(Deserialize)]
#[serde(rename_all = "kebab-case")]
enum Dest {
    Downloads,
    WallpaperEngine,
    Wallpapers,
}

fn err(e: impl std::fmt::Display) -> String {
    e.to_string()
}

/// A file or folder name from the page, made safe to use as a single path component
fn clean(name: &str) -> String {
    let s: String = name.chars().map(|c| if "/\\:*?\"<>|".contains(c) || c.is_control() { '-' } else { c }).collect();
    let s = s.trim().trim_matches('.').trim();
    if s.is_empty() { "Untitled".into() } else { s.into() }
}

fn staging(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_cache_dir().map_err(err)?.join("staged");
    fs::create_dir_all(&dir).map_err(err)?;
    Ok(dir)
}

fn wallpapers(app: &AppHandle) -> Result<PathBuf, String> {
    Ok(app.path().app_data_dir().map_err(err)?.join("wallpapers"))
}

/// Bytes the page made (package files, pictures decoded from HEIC) are written here first; `save` moves them into place
#[tauri::command]
fn stage(app: AppHandle, request: Request<'_>) -> Result<String, String> {
    let InvokeBody::Raw(bytes) = request.body() else { return Err("expected raw bytes".into()) };
    let path = staging(&app)?.join(format!("{}-{}", std::process::id(), STAGED.fetch_add(1, Ordering::Relaxed)));
    fs::write(&path, bytes).map_err(err)?;
    Ok(path.to_string_lossy().into())
}

/// Saves files into Downloads, Wallpaper Engine's projects folder (Downloads when it isn't installed),
/// or the app's own wallpapers folder; `folder` puts them in a subfolder. Returns the file, or the folder for several.
#[tauri::command]
async fn save(app: AppHandle, jobs: State<'_, Jobs>, job: String, dest: Dest, folder: Option<String>,
              files: Vec<FileSpec>, on_progress: Channel<Progress>) -> Result<Saved, String> {
    let downloads = app.path().download_dir().map_err(err)?;
    let (base, installed) = match dest {
        Dest::Downloads => (downloads, false),
        Dest::Wallpapers => (wallpapers(&app)?, false),
        Dest::WallpaperEngine => match wallpaper_engine() {
            Some(projects) => (projects, true),
            None => (downloads, false),
        },
    };
    let dir = match &folder { Some(f) => base.join(clean(f)), None => base };
    let staged = staging(&app)?;
    let cancel = Arc::new(AtomicBool::new(false));
    jobs.0.lock().unwrap().insert(job.clone(), cancel.clone());
    let result = tauri::async_runtime::spawn_blocking(move || write_all(&dir, &files, &staged, &cancel, &on_progress)).await;
    jobs.0.lock().unwrap().remove(&job);
    Ok(Saved { path: result.map_err(err)??.to_string_lossy().into(), installed })
}

fn write_all(dir: &Path, files: &[FileSpec], staged: &Path, cancel: &AtomicBool, progress: &Channel<Progress>) -> Result<PathBuf, String> {
    fs::create_dir_all(dir).map_err(err)?;
    let mut last = dir.to_path_buf();
    for (i, f) in files.iter().enumerate() {
        let target = dir.join(clean(&f.name));
        last = match (&f.url, &f.staged) {
            (_, Some(s)) => {
                let s = PathBuf::from(s);
                if s.parent() != Some(staged) {
                    return Err("not a staged file".into());
                }
                // rename fails across disks; copy then
                fs::rename(&s, &target).or_else(|_| fs::copy(&s, &target).and_then(|_| fs::remove_file(&s))).map_err(err)?;
                target
            }
            (Some(url), None) => {
                // the page's job ends with the window, so a closed window cancels the download
                let report = |got, total| progress.send(Progress { file: i, files: files.len(), got, total }).is_ok();
                download(url, target, cancel, report)?
            }
            (None, None) => return Err(format!("nothing to save for {}", f.name)),
        };
    }
    Ok(if files.len() == 1 { last } else { dir.to_path_buf() })
}

const EXTENSIONS: [&str; 15] = ["jpg", "jpeg", "png", "heic", "webp", "gif", "tif", "tiff", "zip", "mov", "mp4", "json", "html", "txt", "bat"];

/// The extension for a file the server describes as `content_type`, for names that come without one (Google Photos links)
fn extension_for(content_type: &str) -> Option<&'static str> {
    Some(match content_type.split(';').next()?.trim() {
        "image/jpeg" => "jpg",
        "image/png" => "png",
        "image/heic" | "image/heif" => "heic",
        "image/webp" => "webp",
        "image/gif" => "gif",
        "image/tiff" => "tiff",
        "application/zip" => "zip",
        "video/quicktime" => "mov",
        "video/mp4" => "mp4",
        _ => return None,
    })
}

fn download(url: &str, target: PathBuf, cancel: &AtomicBool, mut report: impl FnMut(u64, u64) -> bool) -> Result<PathBuf, String> {
    if !url.starts_with("https://") && !url.starts_with("http://") {
        return Err(format!("not a web address: {url}"));
    }
    let mut res = ureq::get(url).call().map_err(err)?;
    let header = |h| res.headers().get(h).and_then(|v| v.to_str().ok()).map(str::to_owned);
    let total = header("content-length").and_then(|v| v.parse().ok()).unwrap_or(0);
    let known = target.extension().and_then(|e| e.to_str()).is_some_and(|e| EXTENSIONS.contains(&e.to_lowercase().as_str()));
    let target = match header("content-type").as_deref().and_then(extension_for) {
        Some(ext) if !known => PathBuf::from(format!("{}.{ext}", target.display())),
        _ => target,
    };
    let part = PathBuf::from(format!("{}.part", target.display()));
    let copied = (|| {
        let mut out = fs::File::create(&part).map_err(err)?;
        let mut body = res.body_mut().as_reader();
        let (mut buf, mut got, mut last) = (vec![0; 1 << 16], 0u64, Instant::now());
        loop {
            if cancel.load(Ordering::Relaxed) {
                return Err("cancelled".to_string());
            }
            let n = body.read(&mut buf).map_err(err)?;
            if n == 0 {
                break;
            }
            out.write_all(&buf[..n]).map_err(err)?;
            got += n as u64;
            if last.elapsed() > Duration::from_millis(120) {
                last = Instant::now();
                if !report(got, total) {
                    return Err("cancelled".to_string());
                }
            }
        }
        report(got, total);
        out.flush().map_err(err)
    })();
    if let Err(e) = copied {
        let _ = fs::remove_file(&part);
        return Err(e);
    }
    fs::rename(&part, &target).map_err(err)?;
    Ok(target)
}

#[tauri::command]
fn cancel(jobs: State<'_, Jobs>, job: String) {
    if let Some(flag) = jobs.0.lock().unwrap().get(&job) {
        flag.store(true, Ordering::Relaxed);
    }
}

/// Sets a picture `save` put in the app's wallpapers folder as the desktop picture
#[tauri::command]
async fn set_wallpaper(app: AppHandle, path: String) -> Result<(), String> {
    if Path::new(&path).parent() != Some(wallpapers(&app)?.as_path()) {
        return Err("not one of the app's wallpapers".into());
    }
    tauri::async_runtime::spawn_blocking(move || wallpaper::set_from_path(&path).map_err(err)).await.map_err(err)?
}

/// The Steam library folders listed in steamapps/libraryfolders.vdf
fn library_paths(vdf: &str) -> Vec<PathBuf> {
    vdf.lines()
        .filter_map(|l| l.trim().strip_prefix("\"path\""))
        .map(|rest| PathBuf::from(rest.trim().trim_matches('"').replace("\\\\", "\\")))
        .collect()
}

/// Wallpaper Engine's projects/myprojects folder, in whichever Steam library it's installed
#[cfg(windows)]
fn wallpaper_engine() -> Option<PathBuf> {
    use winreg::{enums::HKEY_CURRENT_USER, RegKey};
    let steam: String = RegKey::predef(HKEY_CURRENT_USER).open_subkey(r"Software\Valve\Steam").ok()?.get_value("SteamPath").ok()?;
    let steam = PathBuf::from(steam.replace('/', "\\"));
    let mut libraries = vec![steam.clone()];
    libraries.extend(library_paths(&fs::read_to_string(steam.join(r"steamapps\libraryfolders.vdf")).unwrap_or_default()));
    let we = libraries.into_iter().map(|l| l.join(r"steamapps\common\wallpaper_engine")).find(|p| p.is_dir())?;
    Some(we.join(r"projects\myprojects"))
}

/// Wallpaper Engine only runs on Windows
#[cfg(not(windows))]
fn wallpaper_engine() -> Option<PathBuf> {
    None
}

/// Real windows dressed like macOS: the system's own traffic lights and sidebar material on a Mac,
/// and on Windows and Linux a frameless window whose traffic lights the page draws
fn mac_window<'a, R: tauri::Runtime, M: Manager<R>>(b: WebviewWindowBuilder<'a, R, M>) -> WebviewWindowBuilder<'a, R, M> {
    let b = b.transparent(true);
    #[cfg(target_os = "macos")]
    let b = {
        use tauri::window::{Effect, EffectState, EffectsBuilder};
        b.title_bar_style(tauri::TitleBarStyle::Overlay)
            .hidden_title(true)
            .traffic_light_position(tauri::LogicalPosition::new(20.0, 20.0))
            .effects(EffectsBuilder::new().effect(Effect::Sidebar).state(EffectState::FollowsWindowActiveState).build())
    };
    #[cfg(windows)]
    let b = {
        use tauri::window::{Effect, EffectsBuilder};
        b.decorations(false).shadow(true).effects(EffectsBuilder::new().effect(Effect::Mica).build())
    };
    #[cfg(target_os = "linux")]
    let b = b.decorations(false);
    b
}

/// Quick Look in its own window; a second click shows the new wallpaper in the same window
#[tauri::command]
fn open_preview(app: AppHandle, id: String) -> Result<(), String> {
    if id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
        return Err("not a wallpaper id".into());
    }
    if let Some(w) = app.get_webview_window("preview") {
        app.emit_to("preview", "show", &id).map_err(err)?;
        let _ = w.unminimize();
        return w.set_focus().map_err(err);
    }
    mac_window(WebviewWindowBuilder::new(&app, "preview", WebviewUrl::default()))
        .initialization_script(format!("window.__PREVIEW__ = {id:?};"))
        .title("Quick Look")
        .inner_size(980.0, 640.0)
        .min_inner_size(480.0, 340.0)
        .build()
        .map_err(err)?;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(Jobs::default())
        .invoke_handler(tauri::generate_handler![stage, save, cancel, set_wallpaper, open_preview])
        .setup(|app| {
            let _ = fs::remove_dir_all(staging(app.handle())?); // leftovers from a run that quit mid-save
            mac_window(WebviewWindowBuilder::new(app, "main", WebviewUrl::default()))
                .title("Mac Wallpapers")
                .inner_size(1180.0, 800.0)
                .min_inner_size(720.0, 480.0)
                .build()?;
            Ok(())
        })
        .on_window_event(|w, e| {
            if w.label() == "main" && matches!(e, tauri::WindowEvent::Destroyed) {
                w.app_handle().exit(0); // the Quick Look window goes with the gallery
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Mac Wallpapers");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn names_from_the_page_stay_one_path_component() {
        assert_eq!(clean("Tahoe Day/Night (Dynamic)"), "Tahoe Day-Night (Dynamic)");
        assert_eq!(clean("../../etc/passwd"), "-..-etc-passwd");
        assert_eq!(clean(".."), "Untitled");
        assert_eq!(clean("macOS 10.15.jpg"), "macOS 10.15.jpg");
    }

    #[test]
    fn steam_libraries_come_from_libraryfolders_vdf() {
        let vdf = "\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\"C:\\\\Program Files (x86)\\\\Steam\"\n\t}\n\t\"1\"\n\t{\n\t\t\"path\"\t\t\"D:\\\\SteamLibrary\"\n\t\t\"label\"\t\t\"\"\n\t}\n}";
        assert_eq!(library_paths(vdf), [PathBuf::from("C:\\Program Files (x86)\\Steam"), PathBuf::from("D:\\SteamLibrary")]);
    }

    #[test]
    fn missing_extensions_come_from_the_content_type() {
        assert_eq!(extension_for("image/jpeg; charset=binary"), Some("jpg"));
        assert_eq!(extension_for("text/html"), None);
    }
}
