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

/// For .glb files from the RusticEngine Link Blender add-on: what happened to each Blender material on import,
/// from the report the editor writes to .godot/rustic/blender/<path with / as _, no extension>.json.
fn blender_explain(full: &Path, rel: &str, v: &Value) -> String {
    let from_blender = v["extensionsUsed"].as_array().map(|a| a.iter().any(|x| x == "RUSTIC_blender_nodes")).unwrap_or(false);
    if !from_blender { return String::new(); }
    let rel_clean = rel.trim_start_matches("res://").trim_start_matches('/');
    let mut root = full.to_path_buf();
    for _ in Path::new(rel_clean).components() { root.pop(); }
    let stem = rel_clean.rsplit_once('.').map(|(a, _)| a).unwrap_or(rel_clean).replace('/', "_");
    let report = root.join(".godot/rustic/blender").join(format!("{stem}.json"));
    let mut out = String::from("\nMade in Blender with the RusticEngine Link add-on: its material node graphs travel inside the file \
        and the editor rebuilds them as real shaders, so procedural textures stay procedural.");
    let Some(r) = fs::read(&report).ok().and_then(|b| serde_json::from_slice::<Value>(&b).ok()) else {
        return out + " The editor hasn't imported it yet (open the project in the editor), so there's no material report.";
    };
    out += &format!("\nMaterials: {} rebuilt from Blender nodes, {} kept as the plain standard version.",
        r["translated"].as_i64().unwrap_or(0), r["kept_standard"].as_i64().unwrap_or(0));
    for m in r["materials"].as_array().into_iter().flatten() {
        let name = m["material"].as_str().unwrap_or("?");
        let list = |k: &str| m[k].as_array().map(|a| a.iter().filter_map(|x| x.as_str()).collect::<Vec<_>>().join("; ")).unwrap_or_default();
        if m["result"] == "translated" {
            out += &format!("\n- {name}: rebuilt ({} nodes).", m["nodes"].as_i64().unwrap_or(0));
            let notes = list("notes");
            if !notes.is_empty() { out += &format!(" Approximations: {notes}"); }
        } else {
            out += &format!("\n- {name}: NOT rebuilt, so it shows only its base settings (no procedural detail). Why: {}", list("problems"));
        }
    }
    if r["kept_standard"].as_i64().unwrap_or(0) > 0 {
        out += "\nTo fix a material that wasn't rebuilt: in Blender, replace the node named in 'Why' with a supported one \
                (Noise, Checker, Gradient, Image, Color Ramp, Math, Mix and similar), or bake that material to an image texture. \
                With Live Link on, saving in Blender re-imports it.";
    }
    out
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
/// A model made in the Studio's 3D modeler (.rmodel, JSON): size, shape and colors, in words a beginner can use.
fn rmodel_summary(v: &Value, rel: &str) -> String {
    let verts: Vec<[f64; 3]> = v["vertices"].as_array().map(|a| a.iter().filter_map(|p| {
        let p = p.as_array()?;
        Some([p.first()?.as_f64()?, p.get(1)?.as_f64()?, p.get(2)?.as_f64()?])
    }).collect()).unwrap_or_default();
    let faces = v["faces"].as_array().cloned().unwrap_or_default();
    let mirror = v["mirror_x"].as_bool().unwrap_or(false);
    let mut colors: Vec<(String, usize)> = vec![];
    let (mut tris, mut quads, mut ngons) = (0, 0, 0);
    for f in &faces {
        match f["v"].as_array().map(|a| a.len()).unwrap_or(0) { 3 => tris += 1, 4 => quads += 1, _ => ngons += 1 }
        let c = f["color"].as_str().unwrap_or("#b0b0b0").to_string();
        match colors.iter_mut().find(|(k, _)| *k == c) { Some(e) => e.1 += 1, None => colors.push((c, 1)) }
    }
    colors.sort_by(|a, b| b.1.cmp(&a.1));
    let (mut lo, mut hi) = ([f64::MAX; 3], [f64::MIN; 3]);
    for p in &verts {
        for k in 0..3 { lo[k] = lo[k].min(p[k]); hi[k] = hi[k].max(p[k]); }
    }
    if mirror { lo[0] = lo[0].min(-hi[0]); }
    let size = if verts.is_empty() { "empty".to_string() } else {
        format!("{:.2} wide (X) x {:.2} tall (Y) x {:.2} deep (Z) units (1 unit is about 1 meter)", hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    };
    let palette: Vec<String> = colors.iter().take(8).map(|(c, n)| format!("{c} on {n} faces")).collect();
    let stem = rel.trim_end_matches(".rmodel");
    let name = stem.rsplit('/').next().unwrap_or(stem);
    format!("Studio 3D model (made in RusticEngine's Studio tab). {} vertices, {} faces ({tris} triangles, {quads} quads, {ngons} larger), {}.\n\
             Size: {size}.\nColors: {}.\n\
             The game uses {stem}.glb (exported on every save). A picture from the last save is at design/studio/{name}.png (use look_at_image).",
        verts.len(), faces.len(), if mirror { "mirrored on X (one half is modeled, the other copies it)" } else { "not mirrored" },
        if palette.is_empty() { "none".into() } else { palette.join(", ") })
}

/// A sound made in the Studio's Sound Effects maker (.rsfx, JSON): what it's made of, in sound-design words.
fn rsfx_summary(v: &Value, rel: &str) -> String {
    let f = |k: &str| v[k].as_f64().unwrap_or(0.0);
    let mut parts = vec![format!("{} wave", v["wave"].as_str().unwrap_or("square"))];
    let len = f("attack") + f("sustain") + f("decay");
    parts.push(format!("{len:.2} s long (attack {:.2}, sustain {:.2}, decay {:.2} s{})", f("attack"), f("sustain"), f("decay"),
        if f("punch") > 0.01 { format!(", punch {:.2}", f("punch")) } else { String::new() }));
    parts.push(format!("starts at {:.0} Hz", f("freq")));
    if f("slide").abs() > 0.01 { parts.push(format!("pitch slides {} {:.1} octaves/s", if f("slide") > 0.0 { "up" } else { "down" }, f("slide").abs())); }
    if f("freq_min") > 0.0 && f("slide") < 0.0 { parts.push(format!("stops when the pitch falls below {:.0} Hz", f("freq_min"))); }
    if f("arp_time") > 0.0 && f("arp_semitones") != 0.0 { parts.push(format!("pitch jumps {:+.0} semitones after {:.2} s", f("arp_semitones"), f("arp_time"))); }
    if f("vibrato_depth") > 0.0 && f("vibrato_speed") > 0.0 { parts.push(format!("vibrato {:.1} semitones at {:.0} Hz", f("vibrato_depth"), f("vibrato_speed"))); }
    if f("repeat") > 0.005 { parts.push(format!("repeats every {:.2} s", f("repeat"))); }
    if f("lowpass") > 0.0 { parts.push(format!("low-pass at {:.0} Hz", f("lowpass"))); }
    if f("highpass") > 0.0 { parts.push(format!("high-pass at {:.0} Hz", f("highpass"))); }
    if f("phaser_ms") > 0.0 { parts.push("phaser".into()); }
    parts.push(format!("volume {:.2}", f("volume")));
    let stem = rel.trim_end_matches(".rsfx");
    format!("Studio sound effect (made in RusticEngine's Studio tab, Sound Effects). {}.\n\
             The game uses {stem}.wav (exported on every save). Its controls: wave, Attack/Sustain/Punch/Decay, Start pitch, Slide, Slide curve, \
             Stop below, Vibrato depth/speed, Pitch jump/Jump after, Repeat every, Square duty/Duty sweep, Phaser/Phaser sweep, Low-pass/Low-pass sweep, High-pass, Volume.",
        parts.join(", "))
}

/// A sprite made in the Studio's Pixel Art painter (.rpix, JSON): size, palette use, symmetry and
/// animation, in pixel-art words, plus the first frame itself when it's small enough to read.
fn rpix_summary(v: &Value, rel: &str) -> String {
    const CH: &str = ".123456789abcdefghijklmnopqrstuv";
    let (w, h) = (v["width"].as_u64().unwrap_or(16) as usize, v["height"].as_u64().unwrap_or(16) as usize);
    let fps = v["fps"].as_u64().unwrap_or(8);
    let palette: Vec<String> = v["palette"].as_array().map(|a| a.iter().map(|c| c.as_str().unwrap_or("").to_string()).collect()).unwrap_or_default();
    let frames: Vec<Vec<String>> = v["frames"].as_array().map(|a| a.iter().map(|f| {
        let rows: Vec<String> = f.as_array().map(|r| r.iter().map(|x| x.as_str().unwrap_or("").to_string()).collect()).unwrap_or_default();
        (0..h).map(|y| { let r = rows.get(y).cloned().unwrap_or_default(); (0..w).map(|x| r.chars().nth(x).unwrap_or('.')).collect() }).collect()
    }).collect()).unwrap_or_default();
    if frames.is_empty() { return "Studio sprite with no frames.".into(); }
    let mut count = vec![0usize; CH.len()];
    for f in &frames { for r in f { for c in r.chars() { if let Some(i) = CH.find(c) { count[i] += 1; } } } }
    let total = w * h * frames.len();
    let drawn: usize = count[1..].iter().sum();
    let mut used: Vec<(usize, usize)> = (1..count.len()).filter(|&i| count[i] > 0).map(|i| (i, count[i])).collect();
    used.sort_by(|a, b| b.1.cmp(&a.1));
    let colors: Vec<String> = used.iter().take(10).map(|(i, n)| format!("slot {} {} ({}%)", CH.as_bytes()[*i] as char,
        palette.get(*i).map(String::as_str).unwrap_or("?"), n * 100 / drawn.max(1))).collect();
    // Symmetry and position of frame 1.
    let f0 = &frames[0];
    let (mut same, mut pairs) = (0, 0);
    let (mut x0, mut y0, mut x1, mut y1) = (w, h, 0, 0);
    for (y, r) in f0.iter().enumerate() {
        let b: Vec<char> = r.chars().collect();
        for x in 0..w {
            if b[x] != '.' { x0 = x0.min(x); y0 = y0.min(y); x1 = x1.max(x); y1 = y1.max(y); }
            if x < w / 2 && (b[x] != '.' || b[w - 1 - x] != '.') { pairs += 1; if b[x] == b[w - 1 - x] { same += 1; } }
        }
    }
    let mut parts = vec![format!("{w}x{h} pixels, {} frame{} at {fps} fps", frames.len(), if frames.len() == 1 { "" } else { "s" }),
        format!("{} of {} palette colors used, {}% of pixels drawn", used.len(), palette.len().saturating_sub(1), drawn * 100 / total.max(1))];
    if x0 > x1 { parts.push("frame 1 is empty".into()); } else {
        parts.push(format!("frame 1 art spans x {x0}-{x1}, y {y0}-{y1}"));
        parts.push(format!("left/right symmetry {}%", same * 100 / pairs.max(1)));
    }
    if frames.len() > 1 {
        let diffs: Vec<String> = (0..frames.len()).map(|i| {
            let (a, b) = (&frames[i], &frames[(i + 1) % frames.len()]);
            let n: usize = a.iter().zip(b).map(|(r, s)| r.chars().zip(s.chars()).filter(|(p, q)| p != q).count()).sum();
            format!("{}->{}: {n}", i + 1, (i + 1) % frames.len() + 1)
        }).collect();
        parts.push(format!("pixels changing between frames {}", diffs.join(", ")));
    }
    let stem = rel.trim_end_matches(".rpix");
    let name = stem.rsplit('/').next().unwrap_or(stem);
    let mut out = format!("Studio pixel art sprite (made in RusticEngine's Studio tab, Pixel Art). {}.\nColors: {}.\n\
        The game uses {stem}.png (exported on every save, frames side by side). A bigger picture from the last save is at design/studio/{name}.png (use look_at_image).",
        parts.join(", "), if colors.is_empty() { "none".into() } else { colors.join(", ") });
    if w <= 32 && h <= 32 && x0 <= x1 {
        out += &format!("\nFrame 1, one character per pixel ('.' = transparent, others = palette slot):\n{}", f0.join("\n"));
    }
    out
}

/// A song made in the Studio's Music maker (.rmusic, JSON): tempo, key, scale, and what each track plays.
fn rmusic_summary(v: &Value, rel: &str) -> String {
    const KEYS: [&str; 12] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const DRUMS: [&str; 4] = ["kick", "snare", "hi-hat", "clap"];
    let bpm = v["bpm"].as_f64().unwrap_or(110.0);
    let bars = v["bars"].as_i64().unwrap_or(2);
    let key = KEYS[(v["key"].as_i64().unwrap_or(0).rem_euclid(12)) as usize];
    let scale = v["scale"].as_str().unwrap_or("Major");
    let mut tracks = vec![];
    for t in v["tracks"].as_array().cloned().unwrap_or_default() {
        let name = t["name"].as_str().unwrap_or("Track");
        let notes = t["notes"].as_array().cloned().unwrap_or_default();
        let muted = if t["muted"].as_bool().unwrap_or(false) { " (muted)" } else { "" };
        if t["kind"].as_str() == Some("drums") {
            let mut count = [0usize; 4];
            for n in &notes {
                if let Some(r) = n.get(1).and_then(|r| r.as_u64()) { if (r as usize) < 4 { count[r as usize] += 1; } }
            }
            let hits: Vec<String> = (0..4).filter(|&d| count[d] > 0).map(|d| format!("{} {}", count[d], DRUMS[d])).collect();
            tracks.push(format!("{name}{muted}: {}", if hits.is_empty() { "no hits".into() } else { hits.join(", ") }));
        } else {
            let steps: Vec<i64> = notes.iter().filter_map(|n| n.get(0).and_then(|x| x.as_i64())).collect();
            let rows: Vec<i64> = notes.iter().filter_map(|n| n.get(1).and_then(|x| x.as_i64())).collect();
            let range = match (rows.iter().min(), rows.iter().max()) { (Some(a), Some(b)) => format!(", rows {a}-{b}"), _ => String::new() };
            let first = steps.iter().min().map(|s| format!(", starts at step {s}")).unwrap_or_default();
            tracks.push(format!("{name}{muted}: {} wave, octave {}, {} notes{range}{first}, attack {:.2} s, release {:.2} s{}, volume {:.2}",
                t["wave"].as_str().unwrap_or("square"), t["octave"].as_i64().unwrap_or(4), notes.len(),
                t["attack"].as_f64().unwrap_or(0.0), t["release"].as_f64().unwrap_or(0.0),
                if t["cutoff"].as_f64().unwrap_or(0.0) > 0.0 { format!(", filter {:.0} Hz", t["cutoff"].as_f64().unwrap_or(0.0)) } else { String::new() },
                t["volume"].as_f64().unwrap_or(0.5)));
        }
    }
    let secs = bars as f64 * 16.0 * 60.0 / bpm.max(1.0) / 4.0;
    let stem = rel.trim_end_matches(".rmusic");
    format!("Studio song (made in RusticEngine's Studio tab, Music). {bpm:.0} BPM, {key} {scale}, {bars} bars ({secs:.1} s loop){}.\nTracks: {}.\n\
             Grid rows are notes of the scale (row 0 = the track's home note, +7 rows = one octave up in 7-note scales); 16 steps per bar.\n\
             The game uses {stem}.wav (exported on every save; it loops seamlessly).",
        if v["swing"].as_f64().unwrap_or(0.0) > 0.01 { ", with swing" } else { "" }, tracks.join("; "))
}

/// A sky made in the Studio's Sky maker (.rsky, JSON).
fn rsky_summary(v: &Value, rel: &str) -> String {
    let f = |k: &str| v[k].as_f64().unwrap_or(0.0);
    let hour = f("hour");
    let elev = 65.0 * ((hour - 6.0) / 12.0 * std::f64::consts::PI).sin();
    let phase = if elev < -6.0 { "night" } else if elev < 0.0 { "twilight" } else if elev < 10.0 { "sunrise/sunset" } else if elev < 25.0 { "low golden sun" } else { "daylight" };
    let colors = if v["auto_colors"].as_bool().unwrap_or(true) { "colors follow the time of day".to_string() }
        else { format!("custom colors: sky {}, horizon {}, ground {}, sunlight {}", v["top"].as_str().unwrap_or("?"), v["horizon"].as_str().unwrap_or("?"), v["ground"].as_str().unwrap_or("?"), v["sun"].as_str().unwrap_or("?")) };
    let stem = rel.trim_end_matches(".rsky");
    let name = stem.rsplit('/').next().unwrap_or(stem);
    format!("Studio sky (made in RusticEngine's Studio tab, Sky). Time {:02}:{:02} ({phase}, sun {elev:.0}° up), {colors}. Sun size {:.1}°, glow {:.2}; clouds {:.0}% (softness {:.2}, size {:.2}, drift {:.3}); stars {:.0}%; fog {:.3}; sky light {:.2}.\n\
             The game uses {stem}.tscn (WorldEnvironment + Sun; drop it into a 3D scene). A preview picture is at design/studio/{name}.png (use look_at_image).",
        hour.floor() as i64 % 24, ((hour.fract()) * 60.0).round() as i64 % 60, f("sun_size"), f("sun_glow"), f("cloud_coverage") * 100.0, f("cloud_softness"),
        f("cloud_scale"), f("cloud_speed"), f("stars") * 100.0, f("fog"), f("ambient"))
}

/// A UI kit made in the Studio's UI Kit maker (.rui, JSON), with its contrast check.
fn rui_summary(v: &Value, rel: &str) -> String {
    fn lum(hex: &str) -> f64 {
        let h = hex.trim_start_matches('#');
        let ch = |i: usize| u8::from_str_radix(h.get(i..i + 2).unwrap_or("00"), 16).unwrap_or(0) as f64 / 255.0;
        let lin = |c: f64| if c <= 0.03928 { c / 12.92 } else { ((c + 0.055) / 1.055).powf(2.4) };
        0.2126 * lin(ch(0)) + 0.7152 * lin(ch(2)) + 0.0722 * lin(ch(4))
    }
    fn contrast(a: &str, b: &str) -> f64 {
        let (x, y) = (lum(a), lum(b));
        (x.max(y) + 0.05) / (x.min(y) + 0.05)
    }
    let c = |k: &str| v[k].as_str().unwrap_or("#000000").to_string();
    let f = |k: &str| v[k].as_f64().unwrap_or(0.0);
    let (ct, cb) = (contrast(&c("text"), &c("panel")), contrast(&c("button_text"), &c("accent")));
    let verdict = |x: f64| if x >= 4.5 { "readable" } else if x >= 3.0 { "big text only" } else { "TOO LOW" };
    let stem = rel.trim_end_matches(".rui");
    let name = stem.rsplit('/').next().unwrap_or(stem);
    format!("Studio UI kit (made in RusticEngine's Studio tab, UI Kit). Accent {}, panel {}, text {}, button text {}; corners {:.0} px, border {:.0} px, padding {:.0} px, font {:.0} px, shadow {:.0} px (offset {:.0}), state change {:.2}.\n\
             Contrast: text on panel {ct:.1}:1 ({}), text on buttons {cb:.1}:1 ({}).\n\
             The game uses {stem}_theme.tres (a Theme: set it on the UI's root Control) and 9-slice button pictures in {stem}_9slice/. A preview picture is at design/studio/{name}.png.",
        c("accent"), c("panel"), c("text"), c("button_text"), f("corner_radius"), f("border_width"), f("padding"), f("font_size"), f("shadow_size"), f("shadow_offset"), f("state_strength"),
        verdict(ct), verdict(cb))
}

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
        "glb" => glb_json(&b).map(|v| format!("3D model (glTF binary).\n{}{}", gltf_summary(&v), blender_explain(full, rel, &v))).unwrap_or("3D model (couldn't read it).".into()),
        "gltf" => serde_json::from_slice::<Value>(&b).map(|v| format!("3D model (glTF).\n{}", gltf_summary(&v))).unwrap_or("glTF file (couldn't parse it).".into()),
        "rmodel" => serde_json::from_slice::<Value>(&b).map(|v| rmodel_summary(&v, rel)).unwrap_or("Studio model (couldn't parse it).".into()),
        "rsfx" => serde_json::from_slice::<Value>(&b).map(|v| rsfx_summary(&v, rel)).unwrap_or("Studio sound (couldn't parse it).".into()),
        "rpix" => serde_json::from_slice::<Value>(&b).map(|v| rpix_summary(&v, rel)).unwrap_or("Studio sprite (couldn't parse it).".into()),
        "rmusic" => serde_json::from_slice::<Value>(&b).map(|v| rmusic_summary(&v, rel)).unwrap_or("Studio song (couldn't parse it).".into()),
        "rsky" => serde_json::from_slice::<Value>(&b).map(|v| rsky_summary(&v, rel)).unwrap_or("Studio sky (couldn't parse it).".into()),
        "rui" => serde_json::from_slice::<Value>(&b).map(|v| rui_summary(&v, rel)).unwrap_or("Studio UI kit (couldn't parse it).".into()),
        "blend" => "Blender file. RusticEngine doesn't import .blend files directly: keep them OUTSIDE the project and send the scene \
                     with the RusticEngine Link add-on in Blender (File > Export > RusticEngine, or turn on Live Link so every save updates the game). \
                     That keeps Blender's procedural materials.".into(),
        "fbx" | "obj" | "dae" => format!("3D model ({e}). Godot imports it as a scene. \
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
    if let Ok(t) = fs::read_to_string(root.join("design/path.md")) {
        out += &format!("\n{}\n", t.replace("# Game Path", "## Their Game Path (open the current step with game_path)"));
    }
    if let Ok(t) = fs::read_to_string(root.join("design/art_path.md")) {
        out += &format!("\n{}\n", t.replace("# Art Path", "## Their Art Path (open the current step with game_path)"));
    }
    let entries = journal_entries(root);
    if !entries.is_empty() {
        out += "\n## Concept Journal (design/journal/: the creator's ideas; read an entry before relying on it)\n";
        for (path, title, preview, words) in entries.iter().take(40) {
            out += &format!("- {path}: \"{title}\" ({words} words) {preview}\n");
        }
    }
    if let Ok(t) = fs::read_to_string(root.join("design/assets.md")) {
        let t: String = t.chars().take(2000).collect();
        out += &format!("\n## Asset list (design/assets.md)\n{t}\n");
    }
    out
}

/// (path, title, preview, word count) for each journal entry, newest first.
pub fn journal_entries(root: &Path) -> Vec<(String, String, String, usize)> {
    let mut out = vec![];
    let Ok(rd) = fs::read_dir(root.join("design/journal")) else { return out };
    let mut files: Vec<_> = rd.flatten().filter(|e| e.path().extension().is_some_and(|x| x == "md")).collect();
    files.sort_by_key(|e| std::cmp::Reverse(e.metadata().and_then(|m| m.modified()).ok()));
    for e in files {
        let Ok(t) = fs::read_to_string(e.path()) else { continue };
        let name = e.file_name().to_string_lossy().to_string();
        let mut lines = t.lines().filter(|l| !l.trim().is_empty());
        let title = lines.next().unwrap_or(&name).trim_start_matches('#').trim().to_string();
        let preview: String = lines.collect::<Vec<_>>().join(" ").chars().take(110).collect();
        out.push((format!("design/journal/{name}"), title, preview, t.split_whitespace().count()));
    }
    out
}

/// Search the journal for entries mentioning any of the words in `query`.
pub fn journal_search(root: &Path, query: &str) -> String {
    let words: Vec<String> = query.to_lowercase().split_whitespace().filter(|w| w.len() > 2).map(String::from).collect();
    let mut hits = vec![];
    for (path, title, _, _) in journal_entries(root) {
        let Ok(t) = fs::read_to_string(root.join(&path)) else { continue };
        let lower = t.to_lowercase();
        let score = words.iter().filter(|w| lower.contains(w.as_str())).count();
        if score == 0 { continue; }
        // Show the lines that mention the query, with a little context.
        let lines: Vec<&str> = t.lines().collect();
        let mut keep = vec![false; lines.len()];
        for (i, l) in lines.iter().enumerate() {
            if words.iter().any(|w| l.to_lowercase().contains(w.as_str())) {
                for k in i.saturating_sub(1)..(i + 2).min(lines.len()) { keep[k] = true; }
            }
        }
        let mut snippets = vec![];
        let mut cur: Vec<&str> = vec![];
        for (i, l) in lines.iter().enumerate() {
            if keep[i] { cur.push(l); } else if !cur.is_empty() { snippets.push(cur.join("\n")); cur.clear(); }
        }
        if !cur.is_empty() { snippets.push(cur.join("\n")); }
        snippets.truncate(6);
        hits.push((score, format!("## {title} ({path})\n{}", snippets.join("\n...\n"))));
    }
    hits.sort_by(|a, b| b.0.cmp(&a.0));
    if hits.is_empty() { return format!("Nothing in the journal mentions {query}."); }
    hits.into_iter().take(4).map(|h| h.1).collect::<Vec<_>>().join("\n\n")
}
