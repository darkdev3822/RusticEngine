//! Understanding what the user brings into a project: images, 3D models, sounds, scenes, scripts.
//! Everything here reads file headers only (no image decoding libraries), so it stays fast and small.
use std::fs;
use std::path::Path;

use serde_json::Value;

pub fn mime_of(path: &str) -> Option<&'static str> {
    match ext(path).as_str() {
        "png" => Some("image/png"),
        "jpg" | "jpeg" => Some("image/jpeg"),
        "webp" => Some("image/webp"),
        "gif" => Some("image/gif"),
        _ => None,
    }
}

fn ext(path: &str) -> String {
    Path::new(path).extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase()
}

fn u16be(b: &[u8], i: usize) -> u32 { (b[i] as u32) << 8 | b[i + 1] as u32 }
fn u32be(b: &[u8], i: usize) -> u32 { u16be(b, i) << 16 | u16be(b, i + 2) }
fn u16le(b: &[u8], i: usize) -> u32 { b[i] as u32 | (b[i + 1] as u32) << 8 }
fn u32le(b: &[u8], i: usize) -> u32 { u16le(b, i) | u16le(b, i + 2) << 16 }

pub fn image_size(b: &[u8]) -> Option<(u32, u32)> {
    if b.len() > 24 && &b[1..4] == b"PNG" {
        return Some((u32be(b, 16), u32be(b, 20)));
    }
    if b.len() > 10 && &b[0..3] == b"GIF" {
        return Some((u16le(b, 6), u16le(b, 8)));
    }
    if b.len() > 30 && &b[0..4] == b"RIFF" && &b[8..12] == b"WEBP" {
        match &b[12..16] {
            b"VP8X" => return Some((1 + (u32le(b, 24) & 0xFFFFFF), 1 + (u32le(b, 27) & 0xFFFFFF))),
            b"VP8L" => {
                let n = u32le(b, 21);
                return Some((1 + (n & 0x3FFF), 1 + ((n >> 14) & 0x3FFF)));
            }
            b"VP8 " => return Some((u16le(b, 26) & 0x3FFF, u16le(b, 28) & 0x3FFF)),
            _ => return None,
        }
    }
    if b.len() > 4 && b[0] == 0xFF && b[1] == 0xD8 {
        let mut i = 2;
        while i + 9 < b.len() {
            if b[i] != 0xFF { i += 1; continue; }
            let m = b[i + 1];
            if (0xC0..=0xCF).contains(&m) && m != 0xC4 && m != 0xC8 && m != 0xCC {
                return Some((u16be(b, i + 7), u16be(b, i + 5)));
            }
            i += 2 + u16be(b, i + 2) as usize;
        }
    }
    None
}

/// A best guess at how an image would be used in a game.
fn image_hints(w: u32, h: u32, path: &str) -> String {
    let mut hints = vec![];
    let lower = path.to_lowercase();
    if lower.starts_with("design/") || lower.contains("concept") {
        hints.push("This is concept art: study it with look_at_image and keep its feel in mind. It isn't a game sprite.".to_string());
    }
    if w > h && h > 0 && w % h == 0 && w / h > 1 {
        hints.push(format!("Could be a sprite sheet: {} frames of {h}x{h} in one row (use Sprite2D with hframes = {}, or AnimatedSprite2D).", w / h, w / h));
    } else if h > w && w > 0 && h % w == 0 && h / w > 1 {
        hints.push(format!("Could be a sprite sheet: {} frames of {w}x{w} in one column (vframes = {}).", h / w, h / w));
    } else if w == h && w >= 64 && w % 16 == 0 && w <= 2048 && (lower.contains("tile") || lower.contains("sheet")) {
        hints.push(format!("Could be a tile set: a grid of {}x{} tiles of 16 px, or {}x{} of 32 px.", w / 16, h / 16, w / 32, h / 32));
    }
    if w <= 64 && h <= 64 {
        hints.push("Small pixel art: set texture_filter = 1 (nearest) on the Sprite2D so it stays crisp, and scale it up.".into());
    }
    if w >= 1024 && h >= 576 && !lower.starts_with("design/") {
        hints.push("Big enough for a background (the window is 1152x648).".into());
    }
    hints.join("\n")
}

fn glb_json(b: &[u8]) -> Option<Value> {
    if b.len() < 20 || &b[0..4] != b"glTF" { return None; }
    let len = u32le(b, 12) as usize;
    if &b[16..20] != b"JSON" || 20 + len > b.len() { return None; }
    serde_json::from_slice(&b[20..20 + len]).ok()
}

fn gltf_summary(v: &Value) -> String {
    let names = |k: &str| -> Vec<String> {
        v[k].as_array().map(|a| a.iter().enumerate()
            .map(|(i, x)| x["name"].as_str().map(String::from).unwrap_or_else(|| format!("#{i}"))).collect()).unwrap_or_default()
    };
    let list = |k: &str, max: usize| {
        let n = names(k);
        let more = if n.len() > max { format!(" (+{} more)", n.len() - max) } else { String::new() };
        format!("{} {k}: {}{more}", n.len(), n.into_iter().take(max).collect::<Vec<_>>().join(", "))
    };
    let mut out = vec![list("nodes", 25), list("meshes", 15), list("materials", 15), list("animations", 30)];
    let skins = v["skins"].as_array().map(|a| a.len()).unwrap_or(0);
    if skins > 0 { out.push(format!("{skins} skeleton(s): it can be animated.")); }
    out.push("Godot imports it as a scene: instance it with load::<PackedScene>(\"res://...\") or add it in a .tscn as an ExtResource \
              with type=\"PackedScene\" and `instance=ExtResource(\"id\")`. Animations play through its AnimationPlayer child.".into());
    out.join("\n")
}

fn wav_summary(b: &[u8]) -> Option<String> {
    if b.len() < 44 || &b[0..4] != b"RIFF" || &b[8..12] != b"WAVE" { return None; }
    let (mut i, mut rate, mut chans, mut bits) = (12, 0, 0, 0);
    while i + 8 <= b.len() {
        let id = &b[i..i + 4];
        let size = u32le(b, i + 4) as usize;
        if id == b"fmt " && i + 24 <= b.len() {
            chans = u16le(b, i + 10);
            rate = u32le(b, i + 12);
            bits = u16le(b, i + 22);
        } else if id == b"data" && rate > 0 && chans > 0 && bits > 0 {
            let secs = size as f64 / (rate as f64 * chans as f64 * (bits as f64 / 8.0));
            return Some(format!("WAV sound, {secs:.2} s, {rate} Hz, {}.", if chans == 1 { "mono" } else { "stereo" }));
        }
        i += 8 + size + (size & 1);
    }
    None
}

fn ogg_summary(b: &[u8]) -> Option<String> {
    if b.len() < 64 || &b[0..4] != b"OggS" { return None; }
    let (kind, rate) = if let Some(p) = b.windows(7).take(200).position(|w| w == b"\x01vorbis") {
        ("Ogg Vorbis", u32le(b, p + 12))
    } else if b.windows(8).take(200).any(|w| w == b"OpusHead") {
        ("Ogg Opus", 48000)
    } else {
        return Some("Ogg file.".into());
    };
    // The last page's granule position is the total number of samples.
    let last = b.windows(4).rposition(|w| w == b"OggS")?;
    if last + 14 > b.len() { return None; }
    let granule = u32le(b, last + 6) as u64 | (u32le(b, last + 10) as u64) << 32;
    let secs = granule as f64 / rate.max(1) as f64;
    Some(format!("{kind} sound, {secs:.1} s."))
}

/// Describe one file the user added. `rel` is the project-relative path.
pub fn info(full: &Path, rel: &str) -> Result<String, String> {
    if full.is_dir() {
        let mut items: Vec<String> = fs::read_dir(full).map_err(|e| e.to_string())?
            .filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().to_string())
            .filter(|n| !n.ends_with(".import")).collect();
        items.sort();
        return Ok(format!("Folder {rel} with {} items: {}", items.len(), items.join(", ")));
    }
    let b = fs::read(full).map_err(|e| format!("Can't read {rel}: {e}"))?;
    let kb = b.len() as f64 / 1024.0;
    let size = if kb > 1024.0 { format!("{:.1} MB", kb / 1024.0) } else { format!("{kb:.0} KB") };
    let e = ext(rel);
    let body = match e.as_str() {
        "png" | "jpg" | "jpeg" | "webp" | "gif" => match image_size(&b) {
            Some((w, h)) => format!("Image, {w}x{h} pixels.\n{}\nTo see what it shows, use look_at_image.", image_hints(w, h, rel)),
            None => "Image (couldn't read its size).".into(),
        },
        "svg" => {
            let t = String::from_utf8_lossy(&b);
            let vb = t.find("viewBox=\"").map(|i| t[i + 9..].split('"').next().unwrap_or("").to_string()).unwrap_or_default();
            format!("SVG vector image (viewBox {vb}). Godot imports it as a texture; it scales without blurring.")
        }
        "glb" => glb_json(&b).map(|v| format!("3D model (glTF binary).\n{}", gltf_summary(&v))).unwrap_or("3D model (couldn't read it).".into()),
        "gltf" => serde_json::from_slice::<Value>(&b).map(|v| format!("3D model (glTF).\n{}", gltf_summary(&v))).unwrap_or("glTF file (couldn't parse it).".into()),
        "fbx" | "obj" | "blend" | "dae" => format!("3D model ({e}). Godot imports it as a scene (.blend needs Blender installed). \
                                                    If it gives trouble, exporting it as .glb from the modelling program is the most reliable."),
        "wav" => wav_summary(&b).unwrap_or("WAV sound.".into()) + "\nPlay it with an AudioStreamPlayer (or AudioStreamPlayer2D for sound in the world).",
        "ogg" => ogg_summary(&b).unwrap_or("Ogg sound.".into()) + "\nGood for music (it can loop): AudioStreamPlayer with autoplay.",
        "mp3" => "MP3 sound. Play it with an AudioStreamPlayer.".into(),
        "ttf" | "otf" | "woff" | "woff2" => "Font. Use it on a Label with a LabelSettings or theme font override.".into(),
        "tscn" | "tres" | "rs" | "gd" | "gdshader" | "toml" | "json" | "md" | "txt" | "cfg" => {
            let t = String::from_utf8_lossy(&b);
            let mut s = format!("Text file, {} lines.", t.lines().count());
            if e == "tscn" {
                let nodes: Vec<String> = t.lines().filter(|l| l.starts_with("[node ")).map(|l| l.to_string()).take(30).collect();
                s += &format!("\nScene nodes:\n{}", nodes.join("\n"));
            } else if e == "gd" {
                s += "\nThis is GDScript. It still works in RusticEngine; it can stay as-is, or I can help rewrite it in Rust.";
            }
            s + "\nRead it with read_file."
        }
        _ => "No special support for this file type; Godot may still import it.".into(),
    };
    Ok(format!("{rel} ({size})\n{body}"))
}

/// What the design folder holds, for the system prompt.
pub fn design_context(root: &Path) -> String {
    let mut out = String::new();
    let vision = root.join("design/vision.md");
    match fs::read_to_string(&vision) {
        Ok(t) => {
            let t: String = t.chars().take(5000).collect();
            out += &format!("## The creator's design notes (design/vision.md)\n{t}\n");
        }
        Err(_) => out += "## The creator's design notes\nThere is no design/vision.md yet: you haven't talked about the game as a whole.\n",
    }
    let mut art = vec![];
    if let Ok(rd) = fs::read_dir(root.join("design/concept")) {
        for e in rd.flatten() {
            let n = e.file_name().to_string_lossy().to_string();
            if !n.ends_with(".import") { art.push(format!("design/concept/{n}")); }
        }
    }
    art.sort();
    if !art.is_empty() {
        out += &format!("\n## Concept art they shared\n{}\n", art.join("\n"));
    }
    if let Ok(t) = fs::read_to_string(root.join("design/assets.md")) {
        let t: String = t.chars().take(2000).collect();
        out += &format!("\n## Asset list (design/assets.md)\n{t}\n");
    }
    out
}
