# Run: flatpak run org.blender.Blender -b --factory-startup --python tests/blender/make_scene.py -- OUT_DIR [case ...]
# Builds one 2x2 plane per test material, exports OUT_DIR/materials.glb through the RusticEngine Link
# add-on, and bakes each material's base colour with Cycles into OUT_DIR/bake/<case>.png (ground truth).
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "blender"))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else os.path.join(HERE, "out"))
ONLY = set(argv[1:])
BAKE = 128


def enable_addon():
    import rustic_link
    rustic_link.register()
    if "rustic_link" not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = "rustic_link"


def new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    return mat, nt, bsdf


def link(nt, a, out, b, inp):
    nt.links.new(a.outputs[out], b.inputs[inp])


def node(nt, kind, **settings):
    n = nt.nodes.new(kind)
    for k, v in settings.items():
        if k.startswith("in_"):
            n.inputs[k[3:].replace("_", " ")].default_value = v
        else:
            setattr(n, k, v)
    return n


# ---- test cases ------------------------------------------------------------------------------
def case_const():
    mat, nt, bsdf = new_material("const")
    bsdf.inputs["Base Color"].default_value = (0.2, 0.5, 0.8, 1.0)
    return mat


def case_noise_ramp():
    mat, nt, bsdf = new_material("noise_ramp")
    tc = node(nt, "ShaderNodeTexCoord")
    nz = node(nt, "ShaderNodeTexNoise", in_Scale=5.0, in_Detail=4.0, in_Roughness=0.55, in_Distortion=0.3)
    ramp = node(nt, "ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.35, (0.05, 0.1, 0.4, 1)
    els[1].position, els[1].color = 0.65, (0.9, 0.8, 0.3, 1)
    e = els.new(0.5)
    e.color = (0.8, 0.2, 0.1, 1)
    link(nt, tc, "Generated", nz, "Vector")
    link(nt, nz, "Fac", ramp, "Fac")
    link(nt, ramp, "Color", bsdf, "Base Color")
    return mat


def case_noise_color():
    mat, nt, bsdf = new_material("noise_color")
    tc = node(nt, "ShaderNodeTexCoord")
    nz = node(nt, "ShaderNodeTexNoise", in_Scale=3.0, in_Detail=2.5, in_Distortion=0.0)
    link(nt, tc, "Object", nz, "Vector")
    link(nt, nz, "Color", bsdf, "Base Color")
    return mat


def case_noise_2d():
    mat, nt, bsdf = new_material("noise_2d")
    tc = node(nt, "ShaderNodeTexCoord")
    nz = node(nt, "ShaderNodeTexNoise", noise_dimensions="2D", in_Scale=6.0, in_Detail=1.0)
    link(nt, tc, "UV", nz, "Vector")
    link(nt, nz, "Fac", bsdf, "Base Color")
    return mat


def case_checker_mapping():
    mat, nt, bsdf = new_material("checker_mapping")
    tc = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(30))
    mp.inputs["Scale"].default_value = (1.5, 1.0, 1.0)
    mp.inputs["Location"].default_value = (0.1, 0.0, 0.0)
    ck = node(nt, "ShaderNodeTexChecker", in_Scale=4.0)
    ck.inputs["Color1"].default_value = (0.9, 0.9, 0.85, 1)
    ck.inputs["Color2"].default_value = (0.1, 0.3, 0.2, 1)
    link(nt, tc, "UV", mp, "Vector")
    link(nt, mp, "Vector", ck, "Vector")
    link(nt, ck, "Color", bsdf, "Base Color")
    return mat


def case_gradient_math_mix():
    mat, nt, bsdf = new_material("gradient_math_mix")
    tc = node(nt, "ShaderNodeTexCoord")
    gr = node(nt, "ShaderNodeTexGradient", gradient_type="RADIAL")
    m = node(nt, "ShaderNodeMath", operation="POWER")
    m.inputs[1].default_value = 2.0
    mix = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="OVERLAY")
    mix.inputs["A"].default_value = (0.8, 0.3, 0.2, 1)
    mix.inputs["B"].default_value = (0.2, 0.6, 0.9, 1)
    link(nt, tc, "Object", gr, "Vector")
    link(nt, gr, "Fac", m, 0)
    link(nt, m, "Value", mix, "Factor")
    link(nt, mix, "Result", bsdf, "Base Color")
    return mat


def case_vector_math():
    mat, nt, bsdf = new_material("vector_math")
    tc = node(nt, "ShaderNodeTexCoord")
    vm = node(nt, "ShaderNodeVectorMath", operation="SINE")
    sc = node(nt, "ShaderNodeVectorMath", operation="SCALE")
    sc.inputs["Scale"].default_value = 6.0
    sep = node(nt, "ShaderNodeSeparateXYZ")
    comb = node(nt, "ShaderNodeCombineXYZ")
    mth = node(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    mth.inputs[1].default_value = 0.5
    mth.inputs[2].default_value = 0.5
    link(nt, tc, "UV", sc, "Vector")
    link(nt, sc, "Vector", vm, "Vector")
    link(nt, vm, "Vector", sep, "Vector")
    link(nt, sep, "X", mth, 0)
    link(nt, mth, "Value", comb, "X")
    link(nt, sep, "Y", comb, "Y")
    link(nt, comb, "Vector", bsdf, "Base Color")
    return mat


def case_image():
    mat, nt, bsdf = new_material("image")
    # 1:1 texels with the bake (filtering differences aside), shifted to exercise Mapping + repeat
    img = bpy.data.images.new("uv_grid", BAKE, BAKE)
    img.generated_type = "COLOR_GRID"
    it = node(nt, "ShaderNodeTexImage")
    it.image = img
    tc = node(nt, "ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.25, 0.5, 0.0)
    link(nt, tc, "UV", mp, "Vector")
    link(nt, mp, "Vector", it, "Vector")
    link(nt, it, "Color", bsdf, "Base Color")
    return mat


def case_bump_alpha():
    """Lit-only case: bump from noise into Normal, alpha from a gradient (no bake compare)."""
    mat, nt, bsdf = new_material("bump_alpha")
    mat["rustic_no_bake"] = True
    bsdf.inputs["Base Color"].default_value = (0.7, 0.6, 0.4, 1)
    nz = node(nt, "ShaderNodeTexNoise", in_Scale=8.0)
    bump = node(nt, "ShaderNodeBump", in_Strength=0.8)
    gr = node(nt, "ShaderNodeTexGradient")
    tc = node(nt, "ShaderNodeTexCoord")
    link(nt, nz, "Fac", bump, "Height")
    link(nt, bump, "Normal", bsdf, "Normal")
    link(nt, tc, "UV", gr, "Vector")
    link(nt, gr, "Fac", bsdf, "Alpha")
    mat.surface_render_method = "BLENDED"
    return mat


def case_mix_shader():
    """Lit-only case: Mix Shader of a Principled BSDF and an Emission, mixed by a checker."""
    mat, nt, bsdf = new_material("mix_shader")
    mat["rustic_no_bake"] = True
    bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1)
    em = node(nt, "ShaderNodeEmission", in_Strength=3.0)
    em.inputs["Color"].default_value = (0.1, 0.4, 1.0, 1)
    mix = node(nt, "ShaderNodeMixShader")
    ck = node(nt, "ShaderNodeTexChecker", in_Scale=3.0)
    out = nt.nodes["Material Output"]
    link(nt, ck, "Fac", mix, "Fac")
    link(nt, bsdf, "BSDF", mix, 1)
    link(nt, em, "Emission", mix, 2)
    link(nt, mix, "Shader", out, "Surface")
    return mat


def case_normal_map():
    """Lit-only case: an image through a Normal Map node, plus coat."""
    mat, nt, bsdf = new_material("normal_map")
    mat["rustic_no_bake"] = True
    img = bpy.data.images.new("nmap", 64, 64)
    img.generated_type = "BLANK"
    img.generated_color = (0.5, 0.5, 1.0, 1.0)
    img.colorspace_settings.name = "Non-Color"
    it = node(nt, "ShaderNodeTexImage")
    it.image = img
    nm = node(nt, "ShaderNodeNormalMap")
    link(nt, it, "Color", nm, "Color")
    link(nt, nm, "Normal", bsdf, "Normal")
    bsdf.inputs["Coat Weight"].default_value = 0.5
    bsdf.inputs["Metallic"].default_value = 0.6
    return mat


def _tex(name, kind, out="Color", coord="Generated", **settings):
    mat, nt, bsdf = new_material(name)
    tc = node(nt, "ShaderNodeTexCoord")
    tx = node(nt, kind, **settings)
    link(nt, tc, coord, tx, "Vector")
    link(nt, tx, out, bsdf, "Base Color")
    return mat


def case_voronoi_f1():
    return _tex("voronoi_f1", "ShaderNodeTexVoronoi", "Color", "Object", in_Scale=4.0)


def case_voronoi_edge():
    return _tex("voronoi_edge", "ShaderNodeTexVoronoi", "Distance", "UV", voronoi_dimensions="2D", feature="DISTANCE_TO_EDGE", in_Scale=6.0)


def case_voronoi_smooth():
    return _tex("voronoi_smooth", "ShaderNodeTexVoronoi", "Distance", "Generated", feature="SMOOTH_F1", normalize=True,
                in_Scale=4.0, in_Detail=2.5, in_Smoothness=0.6)


def case_voronoi_f2():
    return _tex("voronoi_f2", "ShaderNodeTexVoronoi", "Distance", "Generated", feature="F2", distance="MINKOWSKI",
                in_Scale=5.0, in_Exponent=1.5, in_Randomness=0.8)


def case_voronoi_radius():
    return _tex("voronoi_radius", "ShaderNodeTexVoronoi", "Radius", "UV", voronoi_dimensions="2D", feature="N_SPHERE_RADIUS", in_Scale=5.0)


def case_wave_rings():
    return _tex("wave_rings", "ShaderNodeTexWave", "Color", "Object", wave_type="RINGS", rings_direction="SPHERICAL", wave_profile="SAW",
                in_Scale=2.0, in_Distortion=4.0, in_Detail=3.0)


def case_wave_bands():
    return _tex("wave_bands", "ShaderNodeTexWave", "Fac", "Generated", bands_direction="DIAGONAL", wave_profile="TRI", in_Scale=3.0)


def case_brick():
    mat = _tex("brick", "ShaderNodeTexBrick", "Color", "UV", offset=0.4, squash=0.8, squash_frequency=3,
               in_Scale=4.0, in_Mortar_Smooth=0.3, in_Bias=0.1)
    tx = [n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeTexBrick"][0]
    tx.inputs["Color1"].default_value = (0.6, 0.2, 0.1, 1)
    tx.inputs["Color2"].default_value = (0.3, 0.15, 0.1, 1)
    return mat


def case_magic():
    return _tex("magic", "ShaderNodeTexMagic", "Color", "Generated", turbulence_depth=4, in_Scale=3.0, in_Distortion=2.0)


def case_noise_ridged():
    return _tex("noise_ridged", "ShaderNodeTexNoise", "Fac", "Generated", noise_type="RIDGED_MULTIFRACTAL", in_Scale=3.0, in_Detail=3.5,
                in_Offset=0.8, in_Gain=1.5)


def case_noise_hetero():
    return _tex("noise_hetero", "ShaderNodeTexNoise", "Color", "Object", noise_type="HETERO_TERRAIN", in_Scale=2.0, in_Detail=2.0,
                in_Offset=0.3, in_Roughness=0.4)


def case_noise_hybrid():
    return _tex("noise_hybrid", "ShaderNodeTexNoise", "Fac", "UV", noise_dimensions="2D", noise_type="HYBRID_MULTIFRACTAL",
                in_Scale=4.0, in_Detail=3.0, in_Offset=0.2, in_Gain=1.2)


def case_noise_multi():
    return _tex("noise_multi", "ShaderNodeTexNoise", "Fac", "Generated", noise_type="MULTIFRACTAL", in_Scale=3.0, in_Detail=2.0, in_Roughness=0.3)


def case_unsupported():
    mat, nt, bsdf = new_material("unsupported")
    wv = node(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="4D")
    link(nt, wv, "Color", bsdf, "Base Color")
    return mat


CASES = [case_const, case_noise_ramp, case_noise_color, case_noise_2d, case_checker_mapping,
         case_gradient_math_mix, case_vector_math, case_image, case_bump_alpha, case_mix_shader,
         case_normal_map, case_voronoi_f1, case_voronoi_edge, case_voronoi_smooth, case_voronoi_f2, case_voronoi_radius,
         case_wave_rings, case_wave_bands, case_brick, case_magic, case_noise_ridged, case_noise_hetero, case_noise_hybrid,
         case_noise_multi, case_unsupported]


def main():
    os.makedirs(os.path.join(OUT, "bake"), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    enable_addon()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.bake_type = "EMIT"
    scene.render.bake.margin = 0
    scene.view_settings.view_transform = "Standard"

    objects = []
    for i, fn in enumerate(c for c in CASES if not ONLY or c.__name__[5:] in ONLY):
        mat = fn()
        bpy.ops.mesh.primitive_plane_add(size=2.0, location=(i * 2.5, 0, 0))
        ob = bpy.context.active_object
        ob.name = mat.name
        ob.data.materials.append(mat)
        objects.append(ob)

    # ground truth: Cycles bake of the base colour, one image per material
    for ob in objects:
        mat = ob.active_material
        if mat.get("rustic_no_bake"):
            continue
        nt = mat.node_tree
        # Bake exactly what reaches Base Color: route it through an Emission shader for the bake.
        bsdf = nt.nodes["Principled BSDF"]
        out = nt.nodes["Material Output"]
        emit = nt.nodes.new("ShaderNodeEmission")
        base = bsdf.inputs["Base Color"]
        if base.is_linked:
            nt.links.new(base.links[0].from_socket, emit.inputs["Color"])
        else:
            emit.inputs["Color"].default_value = base.default_value
        surf = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(emit.outputs["Emission"], surf.inputs["Surface"])
        surf.is_active_output = True
        img = bpy.data.images.new("bake_" + mat.name, BAKE, BAKE, float_buffer=False)
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        mat.node_tree.nodes.active = tex
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(type="EMIT")
        img.filepath_raw = os.path.join(OUT, "bake", mat.name + ".png")
        img.file_format = "PNG"
        img.save()
        for n in (tex, emit, surf):                # keep the bake helpers out of the export
            nt.nodes.remove(n)
        out.is_active_output = True

    import rustic_link
    rustic_link.export_glb(os.path.join(OUT, "materials.glb"))
    print("RUSTIC_TEST_DONE", OUT, len(objects))


main()
