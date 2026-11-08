#!/usr/bin/env bash
# Build every RusticEngine branding asset from logo-pipe-gear.svg into branding/export/.
#   app_icon.png (128)        -> engine/main/app_icon.png        (window/taskbar icon)
#   splash.png (800x600)      -> engine/main/splash.png          (boot splash, editor + games)
#   Logo.svg (187x69)         -> engine/editor/icons/Logo.svg    (project manager / about header)
#   DefaultProjectIcon.svg    -> engine/editor/icons/DefaultProjectIcon.svg (icon.svg of new projects)
#   rusticengine-<N>.png      -> hicolor icon theme sizes for the desktop launcher
# Godot's SVG renderer (ThorVG) has no filter support, so the rusted artwork is embedded as PNG.
set -euo pipefail
cd "$(dirname "$0")"
SRC=logo-pipe-gear.svg
OUT=export; mkdir -p "$OUT"
FONT=$(fc-match -f '%{file}' 'Fira Sans Condensed:weight=205')   # ExtraBold
BG='#1b1715'; RUST='#c8692e'; ASH='#e8d4a2'
python3 make_logo_pipe.py "$SRC" >/dev/null

png() { rsvg-convert -w "$1" -h "$1" "$SRC" -o "$2"; }
b64() { base64 -w0 "$1"; }

# icons
for n in 16 24 32 48 64 128 256 512; do png "$n" "$OUT/rusticengine-$n.png"; done
cp "$OUT/rusticengine-128.png" "$OUT/app_icon.png"

# wordmark: "Rustic" in rust, "Engine" in ash
wordmark() {  # height out.png
  local h=$1 pt=$(( $1 * 82 / 100 ))
  magick -background none -font "$FONT" -pointsize "$pt" -kerning 1 \
    \( -fill "$RUST" label:Rustic \) \( -fill "$ASH" label:Engine \) +append \
    -trim +repage "$2"
}

# splash 800x600: logo over wordmark on a dark vignette
png 300 "$OUT/_logo300.png"; wordmark 64 "$OUT/_wm64.png"
magick -size 800x600 radial-gradient:'#2a221e'-"$BG" \
  \( "$OUT/_logo300.png" \) -gravity center -geometry +0-60 -composite \
  \( "$OUT/_wm64.png" \) -gravity center -geometry +0+150 -composite \
  -define png:color-type=6 "$OUT/splash.png"

# editor header logo (187x69 at 2x): icon + wordmark side by side
png 138 "$OUT/_logo138.png"; wordmark 66 "$OUT/_wm66.png"
magick -size 374x138 xc:none \
  "$OUT/_logo138.png" -gravity west -geometry +0+0 -composite \
  \( "$OUT/_wm66.png" -resize 222x \) -gravity west -geometry +148+4 -composite \
  -trim +repage -background none -gravity west -extent 374x138 "$OUT/_header.png"
cat > "$OUT/Logo.svg" <<EOF
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="187" height="69"><image width="187" height="69" xlink:href="data:image/png;base64,$(b64 "$OUT/_header.png")"/></svg>
EOF

# default icon for new projects (128x128, 256px raster for HiDPI)
cat > "$OUT/DefaultProjectIcon.svg" <<EOF
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="128" height="128"><image width="128" height="128" xlink:href="data:image/png;base64,$(b64 "$OUT/rusticengine-256.png")"/></svg>
EOF

# title-bar logo (100x24 at 4x): used by the project manager and the editor's top-left menu
png 96 "$OUT/_logo96.png"; wordmark 64 "$OUT/_wm64b.png"
magick -size 400x96 xc:none \
  "$OUT/_logo96.png" -gravity west -geometry +0+0 -composite \
  \( "$OUT/_wm64b.png" -resize 280x56 \) -gravity west -geometry +106+2 -composite "$OUT/_title.png"
cat > "$OUT/TitleBarLogo.svg" <<EOF2
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="24"><image width="100" height="24" xlink:href="data:image/png;base64,$(b64 "$OUT/_title.png")"/></svg>
EOF2

rm -f "$OUT"/_*.png
ls -la "$OUT"
