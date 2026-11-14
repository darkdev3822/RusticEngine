# SPDX-License-Identifier: GPL-3.0-or-later
"""Ports Blender's Voronoi GLSL (2D + 3D, fractal) to Godot's shading language.

Usage: python3 port_voronoi.py BLENDER_SHADER_DIR > voronoi.glsl.inc
BLENDER_SHADER_DIR holds gpu_shader_material_voronoi.glsl and gpu_shader_material_fractal_voronoi.glsl
from blender/source/blender/gpu/shaders/material (branch blender-v5.2-release).
The output is pasted into engine/modules/rustic/blender/blender_glsl.h as VORONOI.
Godot has no function overloading, so each function gets a _2d/_3d suffix; Blender's float2/int2
types, 'f' literals and int/float loop compares are rewritten.
"""
import os
import re
import sys

src = sys.argv[1]
vor = open(os.path.join(src, "gpu_shader_material_voronoi.glsl")).read()
frac = open(os.path.join(src, "gpu_shader_material_fractal_voronoi.glsl")).read()

FUNCS = ["voronoi_distance", "voronoi_position", "voronoi_f1", "voronoi_smooth_f1", "voronoi_f2",
         "voronoi_distance_to_edge", "voronoi_n_sphere_radius", "fractal_voronoi_x_fx", "fractal_voronoi_distance_to_edge"]


def section(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def functions_for(text, typ):
    """Every top-level function whose parameter list mentions `typ coord` or `typ a`."""
    out = []
    for m in re.finditer(r"^\w[\w ]*\s(\w+)\(([^)]*)\)\n\{", text, re.M):
        params = m.group(2)
        if re.search(rf"\b{typ} (coord|a)\b", params):
            # find the matching closing brace
            depth, i = 0, m.end() - 1
            while True:
                if text[i] == "{": depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0: break
                i += 1
            out.append(text[m.start():i + 1])
    return "\n\n".join(out)


macro = section(frac, "#define FRACTAL_VORONOI_DISTANCE_TO_EDGE_FUNCTION(T)", "\n\n")
macro = macro.split("\n", 1)[1].replace("\\\n", "\n")


def port(code, suffix):
    for f in sorted(FUNCS, key=len, reverse=True):
        code = re.sub(rf"\b{f}\(", f"b_{f}_{suffix}(", code)
    code = re.sub(r"\bfloat2\b", "vec2", code)
    code = re.sub(r"\bfloat3\b", "vec3", code)
    code = re.sub(r"\bfloat4\b", "vec4", code)
    code = re.sub(r"\bint2\b", "ivec2", code)
    code = re.sub(r"\bint3\b", "ivec3", code)
    code = re.sub(r"(\d+\.\d*|\.\d+)f\b", r"\1", code)
    code = re.sub(r"\bvec4\(0\)", "vec4(0.0)", code)
    code = re.sub(r"\bivec2\(0\)", "ivec2(0)", code)
    code = code.replace("FLT_MAX", "3.402823466e+38")
    code = code.replace("i <= ceil(params.detail)", "i <= int(ceil(params.detail))")
    code = code.replace("i <= params.detail", "params.detail >= float(i)")
    code = re.sub(r"\bfloat distance = ", "float dist = ", code)
    code = re.sub(r"(?<![\w.])distance = ", "dist = ", code)
    code = re.sub(r"min\(distance, ", "min(dist, ", code)
    code = re.sub(r"mix\(distance, ", "mix(dist, ", code)
    code = re.sub(r"distance /= ", "dist /= ", code)
    code = re.sub(r"return distance;", "return dist;", code)
    code = code.replace("hash_int2_to_vec2(", "b_hash_int2_to_vec2(").replace("hash_int3_to_vec3(", "b_hash_int3_to_vec3(")
    code = code.replace("hash_int2_to_vec3(", "b_hash_int2_to_vec3(")
    code = code.replace("safe_divide(", "b_safe_divide4(")
    for k, v in {"SHD_VORONOI_EUCLIDEAN": "0", "SHD_VORONOI_MANHATTAN": "1", "SHD_VORONOI_CHEBYCHEV": "2", "SHD_VORONOI_MINKOWSKI": "3",
                 "SHD_VORONOI_F1": "0", "SHD_VORONOI_F2": "1", "SHD_VORONOI_SMOOTH_F1": "2"}.items():
        code = re.sub(rf"\b{k}\b", v, code)
    code = re.sub(r"\bVoronoiParams\b", "BVoronoiParams", code)
    code = re.sub(r"\bVoronoiOutput\b", "BVoronoiOutput", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    code = re.sub(r"[ \t]+\n", "\n", code)
    code = re.sub(r"\n{3,}", "\n\n", code)
    return code


out = ["""struct BVoronoiParams {
	float scale; float detail; float roughness; float lacunarity; float smoothness; float exponent;
	float randomness; float max_distance; bool normalize; int feature; int metric;
};
struct BVoronoiOutput { float Distance; vec3 Color; vec4 Position; };
ivec2 b_hash_pcg2d_i(ivec2 v) {
	v = v * 1664525 + 1013904223; v.x += v.y * 1664525; v.y += v.x * 1664525; v = v ^ (v >> 16);
	v.x += v.y * 1664525; v.y += v.x * 1664525; return v;
}
ivec3 b_hash_pcg3d_i(ivec3 v) {
	v = v * 1664525 + 1013904223; v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y; v = v ^ (v >> 16);
	v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y; return v;
}
vec2 b_hash_int2_to_vec2(ivec2 k) { ivec2 h = b_hash_pcg2d_i(k); return vec2(h & ivec2(2147483647)) * (1.0 / 2147483647.0); }
vec3 b_hash_int3_to_vec3(ivec3 k) { ivec3 h = b_hash_pcg3d_i(k); return vec3(h & ivec3(2147483647)) * (1.0 / 2147483647.0); }
vec3 b_hash_int2_to_vec3(ivec2 k) { return b_hash_int3_to_vec3(ivec3(k.x, k.y, 0)); }
vec4 b_safe_divide4(vec4 a, float b) { return (b != 0.0) ? (a / b) : vec4(0.0); }
"""]
for typ, suf in (("float2", "2d"), ("float3", "3d")):
    body = functions_for(vor, typ) + "\n\n" + functions_for(frac, typ) + "\n\n" + macro.replace("T coord", f"{typ} coord")
    out.append(port(body, suf))
print("\n".join(out))
