# InvisibleRoommates の部屋を Blender でゼロから組み立てて assets/room.glb に書き出す。
#
# 使い方（バックグラウンド実行）:
#   blender -b --factory-startup --python blender/build_room.py
#
# 座標の決まり:
#   このスクリプトの中の寸法・位置はすべて three.js の座標（Y が上、+Z が手前）で書く。
#   Blender へは (x, y, z)three -> (x, -z, y)blender に変換して置く。glTF は +Y up で書き出すので、
#   読み込んだ three 側では元の座標に戻る。
#
# 動く部品は独立したオブジェクトにして、原点を回転軸（蝶番）に置く。回転・拡縮は既定値（0 / 1）のまま。
# 光る面はマテリアル名で探せるように、専用のマテリアルを当てる。

import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEX = os.path.join(ROOT, 'assets', 'textures')
OUT_GLB = os.path.join(ROOT, 'assets', 'room.glb')
OUT_BLEND = os.path.join(ROOT, 'blender', 'room.blend')

random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
SCN = bpy.context.scene

# three -> blender の変換行列
C3 = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def V(x, y, z):
    return Vector((x, -z, y))


def lin(c):
    """'#rrggbb'（sRGB）を線形の RGB に"""
    c = c.lstrip('#')
    out = []
    for i in range(3):
        s = int(c[i * 2:i * 2 + 2], 16) / 255
        out.append(s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# ---------------------------------------------------------------- マテリアル
_imgs = {}


def load_img(fname, noncolor):
    if fname not in _imgs:
        im = bpy.data.images.load(os.path.join(TEX, fname))
        im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
        _imgs[fname] = im
    return _imgs[fname]


def gltf_output_group():
    ng = bpy.data.node_groups.get('glTF Material Output')
    if ng:
        return ng
    ng = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
    ng.interface.new_socket(name='Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    ng.nodes.new('NodeGroupInput')
    return ng


class M:
    pass


MATS = {}


def mat(name, color='#ffffff', rough=0.6, metal=0.0, tex=None, res='1k', uv=1.0, nstr=1.0):
    """PBR マテリアル。tex を渡すと diff / nor / arm（AO・粗さ・金属）の JPG を貼る。uv は 1m あたりの繰り返し数"""
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['IOR'].default_value = 1.5
    col = lin(color)
    if tex:
        d = nt.nodes.new('ShaderNodeTexImage')
        d.image = load_img(f'{tex}_diff_{res}.jpg', False)
        if color.lower() != '#ffffff':
            mix = nt.nodes.new('ShaderNodeMix')
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs[0].default_value = 1.0
            nt.links.new(d.outputs['Color'], mix.inputs[6])
            mix.inputs[7].default_value = (*col, 1)
            nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
        else:
            nt.links.new(d.outputs['Color'], bsdf.inputs['Base Color'])
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = load_img(f'{tex}_nor_{res}.jpg', True)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = nstr
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        a = nt.nodes.new('ShaderNodeTexImage')
        a.image = load_img(f'{tex}_arm_{res}.jpg', True)
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(a.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
        g = nt.nodes.new('ShaderNodeGroup')
        g.node_tree = gltf_output_group()
        nt.links.new(sep.outputs['Red'], g.inputs['Occlusion'])
    else:
        bsdf.inputs['Base Color'].default_value = (*col, 1)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal
    o = M()
    o.mat = m
    o.uv = uv
    MATS[name] = o
    return o


# 部屋
mat('Floor', tex='laminate_floor_02', res='2k', uv=0.42, nstr=0.8)
mat('Wall', '#f4ede2', tex='plastered_wall_04', res='2k', uv=0.45, nstr=0.5)
mat('Slab', '#a9a299', tex='plastered_wall_04', res='2k', uv=0.45, nstr=0.5)
mat('Trim', '#e9e1d4', rough=0.45)
mat('Baseboard', '#cdbfa9', rough=0.5)
mat('SwitchPlate', '#f6f3ee', rough=0.35)
mat('SwitchToggle', '#ebe6dc', rough=0.3)
# 玄関
mat('DoorSteel', '#5e6b78', rough=0.42, metal=0.35)
mat('Brass', '#cfc3a2', rough=0.28, metal=0.9)
mat('Chrome', '#d9dbde', rough=0.16, metal=1.0)
mat('Tataki', '#b9b6b0', tex='granite_tile', uv=1.6)
mat('Kamachi', '#ffffff', tex='kitchen_wood', uv=1.4)
# 浴室
mat('BathWall', '#ffffff', tex='long_white_tiles', uv=1.1, nstr=0.8)
mat('BathFloor', '#c8ccd0', tex='granite_tile', uv=2.4)
mat('BathDoor', '#ece4d6', rough=0.4)
mat('Towel', '#e8b4a0', tex='cotton_jersey', uv=4.0)
mat('Plastic', '#f0eee9', rough=0.3)
# キッチン
mat('CabinetDoor', '#ffffff', tex='oak_veneer_01', uv=1.1)
mat('CabinetBody', '#e4ddd0', rough=0.5)
mat('WallCabinet', '#f7f3ec', tex='oak_veneer_01', uv=1.1)
mat('Stainless', '#ffffff', tex='Metal012', uv=1.4, nstr=0.6)
mat('Backsplash', '#ffffff', tex='long_white_tiles', uv=0.8, nstr=0.8)
mat('StoveTop', '#141416', rough=0.12, metal=0.0)
mat('CastIron', '#2b2b2d', rough=0.65, metal=0.5)
mat('Burner', '#5b5c60', rough=0.4, metal=0.7)
mat('Knob', '#2e2e31', rough=0.4)
mat('Kettle', '#d6cdb8', rough=0.32, metal=0.35)
mat('BlackPlastic', '#1d1d20', rough=0.45)
# 冷蔵庫
mat('FridgeBody', '#f3f1ec', rough=0.3)
mat('FridgeInner', '#f4f7f8', rough=0.45)
mat('Gasket', '#d4d2cb', rough=0.85)
mat('FoodWhite', '#f2f2f2', rough=0.5)
mat('FoodYellow', '#e6c56a', rough=0.4)
mat('FoodGreen', '#5f9a5a', rough=0.15)
mat('FoodRed', '#d98f8f', rough=0.4)
mat('FoodCream', '#e8d8a0', rough=0.3)
mat('MagnetRed', '#e07a5f', rough=0.3)
mat('MagnetBlue', '#5fa8d3', rough=0.3)
# ベッド・窓
mat('BedFrame', '#ffffff', tex='kitchen_wood', uv=1.3)
mat('Mattress', '#f4f1ea', tex='cotton_jersey', uv=3.0, nstr=0.7)
mat('Pillow', '#ffffff', tex='cotton_jersey', uv=3.0, nstr=0.7)
mat('Blanket', '#ffffff', tex='fabric_pattern_05', uv=1.4)
mat('Curtain', '#ffffff', tex='rough_linen', uv=2.2)
mat('CurtainRail', '#8a7a68', rough=0.4, metal=0.2)
mat('WindowFrame', '#c4c7cb', rough=0.35, metal=0.65)
mat('NightSky', '#1e2c4f', rough=1.0)
mat('Moon', '#f5ecc8', rough=1.0)
# 机まわり
mat('Desk', '#ffffff', tex='oak_veneer_01', uv=1.1)
mat('ChairWood', '#ffffff', tex='wood_table_001', uv=1.6)
mat('ChairSeat', '#6f8f9f', tex='cotton_jersey', uv=4.0)
mat('LaptopBody', '#b9bcc2', rough=0.3, metal=0.75)
mat('LaptopKeys', '#2a2b2e', rough=0.5)
mat('LaptopScreen', '#0a0b0e', rough=0.2)
mat('LampMetal', '#333438', rough=0.38, metal=0.5)
mat('LampBulb', '#4a4740', rough=0.2)
mat('BookRed', '#c86b5a', rough=0.55)
mat('BookBlue', '#5a7ec8', rough=0.55)
mat('BookPages', '#efe9dc', rough=0.8)
# テレビまわり
mat('Rug', '#cbbfd8', tex='Carpet016', uv=1.6)
mat('TVStand', '#8a7464', tex='kitchen_wood', uv=1.2)
mat('TVBody', '#1b1b1f', rough=0.32, metal=0.2)
mat('TVScreen', '#08080a', rough=0.1)
mat('LowTable', '#ffffff', tex='kitchen_wood', uv=1.0)
mat('Mug', '#f2ece0', rough=0.18)
mat('Remote', '#2b2b30', rough=0.45)
mat('RemoteButton', '#6a6a72', rough=0.5)
mat('RemoteRed', '#c0453a', rough=0.4)
mat('Cushion0', '#f0c860', tex='cotton_jersey', uv=3.0)
mat('Cushion1', '#8cc0b0', tex='cotton_jersey', uv=3.0)
mat('Cushion2', '#e49a9a', tex='cotton_jersey', uv=3.0)
mat('Thread', '#3a3430', rough=0.8)


# ---------------------------------------------------------------- 形を作る道具（すべて three 座標）
def box_uv(bm, s, rot=False):
    uvl = bm.loops.layers.uv.verify()
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            p = lp.vert.co
            if ax == 0:
                u, v = p.z, p.y
            elif ax == 1:
                u, v = p.x, p.z
            else:
                u, v = p.x, p.y
            if rot:
                u, v = v, u
            lp[uvl].uv = (u * s, v * s)


def bm_box(x0, x1, y0, y1, z0, z1, bm=None):
    bm = bm or bmesh.new()
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = Vector((x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else y1, z0 if v.co.z < 0 else z1))
    return bm


def bm_cyl(p0, p1, r0, r1=None, seg=24, bm=None, caps=True):
    """p0 から p1 へ伸びる円柱（円錐台）"""
    bm = bm or bmesh.new()
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    mtx = Matrix.Translation((p0 + p1) / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r0,
                          radius2=r0 if r1 is None else r1, depth=d.length, matrix=mtx)
    return bm


def bm_lathe(profile, center=(0, 0, 0), seg=32, bm=None, cap_bottom=False, cap_top=False):
    """(半径, 高さ) の列を Y 軸まわりに回す"""
    bm = bm or bmesh.new()
    cx, cy, cz = center
    rings = []
    for r, y in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((cx, cy + y, cz))])
        else:
            rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * i / seg), cy + y,
                                        cz + r * math.sin(2 * math.pi * i / seg))) for i in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[j], b[i]))
            elif len(b) == 1:
                bm.faces.new((a[i], a[j], b[0]))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_tube(points, r, seg=12, bm=None, caps=True):
    """折れ線に沿った管（取っ手・蛇口・スタンドの腕など）"""
    bm = bm or bmesh.new()
    pts = [Vector(p) for p in points]
    tangents = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tangents.append((b - a).normalized())
    up = Vector((0, 1, 0)) if abs(tangents[0].y) < 0.9 else Vector((1, 0, 0))
    n = tangents[0].cross(up).normalized()
    rings = []
    for i, p in enumerate(pts):
        t = tangents[i]
        n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * r)
                      for k in range(seg)])
    for a, c in zip(rings, rings[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((a[k], a[j], c[j], c[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def arc_pts(center, radius, a0, a1, n, plane='xy'):
    cx, cy, cz = center
    out = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        if plane == 'xy':
            out.append((cx + radius * math.cos(a), cy + radius * math.sin(a), cz))
        elif plane == 'zy':
            out.append((cx, cy + radius * math.sin(a), cz + radius * math.cos(a)))
        else:
            out.append((cx + radius * math.cos(a), cy, cz + radius * math.sin(a)))
    return out


def bm_superellipsoid(center, a, b, c, e_v=0.5, e_h=0.3, nu=16, nv=40, bm=None, flat_bottom=None):
    """丸みのある箱（座布団・枕・マットレス）。e が小さいほど角ばる"""
    bm = bm or bmesh.new()
    cx, cy, cz = center

    def sc(w, m):
        cw = math.cos(w)
        return math.copysign(abs(cw) ** m, cw)

    def ss(w, m):
        sw = math.sin(w)
        return math.copysign(abs(sw) ** m, sw)

    rings = []
    for i in range(1, nu):
        u = -math.pi / 2 + math.pi * i / nu
        ring = []
        for j in range(nv):
            v = -math.pi + 2 * math.pi * j / nv
            y = b * ss(u, e_v)
            if flat_bottom is not None:
                y = max(y, -flat_bottom)
            ring.append(bm.verts.new((cx + a * sc(u, e_v) * sc(v, e_h), cy + y, cz + c * sc(u, e_v) * ss(v, e_h))))
        rings.append(ring)
    bot = bm.verts.new((cx, cy - (b if flat_bottom is None else min(b, flat_bottom)), cz))
    top = bm.verts.new((cx, cy + b, cz))
    for ra, rb in zip(rings, rings[1:]):
        for j in range(nv):
            k = (j + 1) % nv
            bm.faces.new((ra[j], ra[k], rb[k], rb[j]))
    for j in range(nv):
        k = (j + 1) % nv
        bm.faces.new((bot, rings[0][k], rings[0][j]))
        bm.faces.new((rings[-1][j], rings[-1][k], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_grid(fn, nu, nv, bm=None):
    """fn(s, t) -> (x, y, z)。s, t は 0..1"""
    bm = bm or bmesh.new()
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    return bm


GROUPS = {}


def part(group, bm, matname, bevel=0.0, seg=3, smooth=False, sharp=35, uvrot=False, solidify=0.0, subsurf=0):
    m = MATS[matname]
    box_uv(bm, m.uv, uvrot)
    bmesh.ops.transform(bm, matrix=C3, verts=bm.verts)
    me = bpy.data.meshes.new(group)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m.mat)
    ob = bpy.data.objects.new(group, me)
    SCN.collection.objects.link(ob)
    if solidify:
        md = ob.modifiers.new('solid', 'SOLIDIFY')
        md.thickness = solidify
        md.offset = -1
    if subsurf:
        md = ob.modifiers.new('sub', 'SUBSURF')
        md.levels = subsurf
        md.render_levels = subsurf
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL')
        md.width = bevel
        md.segments = seg
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(40)
        md.harden_normals = True
        me.shade_smooth()
    elif smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
    GROUPS.setdefault(group, []).append(ob)
    return ob


def boxp(group, matname, x0, x1, y0, y1, z0, z1, bevel=0.004, seg=2, uvrot=False):
    return part(group, bm_box(x0, x1, y0, y1, z0, z1), matname, bevel=bevel, seg=seg, uvrot=uvrot)


def apply_mods(ob):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob],
                                   selected_editable_objects=[ob]):
        for md in list(ob.modifiers):
            bpy.ops.object.modifier_apply(modifier=md.name)


def finalize(group, name=None, pivot=(0, 0, 0)):
    objs = GROUPS.pop(group)
    for ob in objs:
        apply_mods(ob)
    target = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=target, object=target, selected_objects=objs,
                                       selected_editable_objects=objs):
            bpy.ops.object.join()
    name = name or group
    target.name = name
    target.data.name = name
    pv = V(*pivot)
    target.data.transform(Matrix.Translation(-pv))
    target.location = pv
    return target


def parent_to(child, parent):
    w = child.location.copy()
    child.parent = parent
    child.location = w - parent.location


H = 2.9

# ================================================================ 箱庭の箱（床・壁）
boxp('Shell', 'Slab', -4.2, 4.2, -0.4, -0.02, -3.2, 3.2, bevel=0.03, seg=3)
part('Shell', bm_box(-4.0, 4.2, -0.04, 0, -3.0, 3.2), 'Floor', bevel=0.004, seg=2)


def wall_with_holes(x0, x1, z0, z1, holes):
    w = part('Shell', bm_box(x0, x1, 0, H, z0, z1), 'Wall')
    for i, (hx0, hx1, hy0, hy1, hz0, hz1) in enumerate(holes):
        cut = part('_cut', bm_box(hx0, hx1, hy0, hy1, hz0, hz1), 'Wall')
        md = w.modifiers.new(f'hole{i}', 'BOOLEAN')
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
        md.object = cut
    md = w.modifiers.new('bev', 'BEVEL')
    md.width = 0.006
    md.segments = 2
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(40)
    md.harden_normals = True
    w.data.shade_smooth()
    return w


# 奥の壁（浴室のドアと窓の穴）
wall_with_holes(-4.2, 4.2, -3.2, -3.0, [(-3.6, -2.7, -0.1, 2.1, -3.3, -2.9), (2.5, 3.7, 1.2, 2.3, -3.3, -2.9)])
# 左の壁（玄関の穴）
wall_with_holes(-4.2, -4.0, -3.0, 3.2, [(-4.3, -3.9, -0.1, 2.1, 1.7, 2.6)])
for ob in GROUPS['Shell']:
    apply_mods(ob)
for ob in GROUPS.pop('_cut'):
    bpy.data.objects.remove(ob)

# 幅木
boxp('Shell', 'Baseboard', -2.7, 2.3, 0, 0.07, -3.0, -2.985)
boxp('Shell', 'Baseboard', -4.0, -3.985, 0, 0.07, -3.0, 1.7)
boxp('Shell', 'Baseboard', -4.0, -3.985, 0, 0.07, 2.6, 3.2)
# 入口まわりの枠（部屋側）
for (z0, z1) in [(1.64, 1.7), (2.6, 2.66)]:
    boxp('Shell', 'Trim', -4.0, -3.975, 0, 2.16, z0, z1, bevel=0.006)
boxp('Shell', 'Trim', -4.0, -3.975, 2.1, 2.16, 1.64, 2.66, bevel=0.006)
boxp('Shell', 'Trim', -4.2, -4.0, 2.08, 2.1, 1.7, 2.6, bevel=0.002)  # 上枠の下面
# 浴室の入口の枠
for (x0, x1) in [(-3.66, -3.6), (-2.7, -2.64)]:
    boxp('Shell', 'Trim', x0, x1, 0, 2.16, -3.0, -2.975, bevel=0.006)
boxp('Shell', 'Trim', -3.66, -2.64, 2.1, 2.16, -3.0, -2.975, bevel=0.006)
boxp('Shell', 'Trim', -3.6, -2.7, 0, 0.02, -3.2, -2.99, bevel=0.004)  # 敷居
finalize('Shell', 'Room')

# ================================================================ 玄関
boxp('Entrance', 'Tataki', -4.0, -3.24, 0, 0.015, 1.7, 2.6, bevel=0.003)
boxp('Entrance', 'Kamachi', -3.25, -3.19, 0, 0.03, 1.7, 2.6, bevel=0.006, uvrot=True)
# 照明スイッチのプレート（枠と中のくぼみ）
boxp('Entrance', 'SwitchPlate', -4.0, -3.988, 1.12, 1.3, 1.38, 1.5, bevel=0.004)
boxp('Entrance', 'BlackPlastic', -3.989, -3.986, 1.16, 1.26, 1.408, 1.472, bevel=0.001)
finalize('Entrance')

# 照明スイッチのトグル（原点＝回転軸）
boxp('SwitchToggle', 'SwitchToggle', -3.991, -3.976, 1.17, 1.25, 1.413, 1.467, bevel=0.004, seg=3)
part('SwitchToggle', bm_cyl((-3.9765, 1.235, 1.44), (-3.9755, 1.235, 1.44), 0.0025, seg=8), 'Brass', smooth=True)
finalize('SwitchToggle', pivot=(-3.9825, 1.21, 1.44))

# 玄関ドア（外開き。原点＝蝶番 (-4.1, 0, 1.72)）
PX, PZ = -4.1, 1.72
boxp('EntranceDoor', 'DoorSteel', PX - 0.03, PX + 0.03, 0.0, 2.08, PZ, PZ + 0.86, bevel=0.008, seg=3)
# 室内側の化粧パネル（細い溝で囲む）
for (y0, y1) in [(0.12, 0.13), (1.95, 1.96)]:
    boxp('EntranceDoor', 'BlackPlastic', PX + 0.029, PX + 0.032, y0, y1, PZ + 0.1, PZ + 0.76, bevel=0.0)
for (z0, z1) in [(0.1, 0.11), (0.75, 0.76)]:
    boxp('EntranceDoor', 'BlackPlastic', PX + 0.029, PX + 0.032, 0.12, 1.96, PZ + z0, PZ + z1, bevel=0.0)
# レバーハンドル
hz = PZ + 0.76
part('EntranceDoor', bm_cyl((PX + 0.03, 1.0, hz), (PX + 0.04, 1.0, hz), 0.032, seg=28), 'Chrome', smooth=True)
part('EntranceDoor', bm_cyl((PX + 0.04, 1.0, hz), (PX + 0.075, 1.0, hz), 0.011, seg=16), 'Chrome', smooth=True)
part('EntranceDoor', bm_tube([(PX + 0.075, 1.0, hz), (PX + 0.078, 1.0, hz - 0.03), (PX + 0.076, 0.998, hz - 0.08),
                              (PX + 0.07, 0.996, hz - 0.12)], 0.011, seg=14), 'Chrome', smooth=True)
# サムターン
part('EntranceDoor', bm_cyl((PX + 0.03, 1.17, hz), (PX + 0.038, 1.17, hz), 0.028, seg=24), 'Chrome', smooth=True)
boxp('EntranceDoor', 'Chrome', PX + 0.038, PX + 0.05, 1.15, 1.19, hz - 0.006, hz + 0.006, bevel=0.003)
# ドアスコープ
part('EntranceDoor', bm_cyl((PX + 0.03, 1.5, PZ + 0.43), (PX + 0.036, 1.5, PZ + 0.43), 0.012, seg=16), 'Chrome', smooth=True)
part('EntranceDoor', bm_cyl((PX + 0.036, 1.5, PZ + 0.43), (PX + 0.037, 1.5, PZ + 0.43), 0.006, seg=12), 'BlackPlastic', smooth=True)
# 新聞受け
boxp('EntranceDoor', 'Chrome', PX + 0.03, PX + 0.045, 0.78, 0.84, PZ + 0.28, PZ + 0.58, bevel=0.004)
# 外側の取っ手
part('EntranceDoor', bm_tube([(PX - 0.03, 0.9, hz), (PX - 0.07, 0.92, hz), (PX - 0.07, 1.08, hz), (PX - 0.03, 1.1, hz)],
                             0.01, seg=12), 'Chrome', smooth=True)
door = finalize('EntranceDoor', pivot=(PX, 0, PZ))

# ================================================================ 浴室（壁の向こう。ドアのすき間から見える）
part('Bathroom', bm_box(-3.85, -2.45, 0, 2.2, -4.1, -4.05), 'BathWall', bevel=0.0)
part('Bathroom', bm_box(-3.9, -3.85, 0, 2.2, -4.1, -3.2), 'BathWall', bevel=0.0)
part('Bathroom', bm_box(-2.45, -2.4, 0, 2.2, -4.1, -3.2), 'BathWall', bevel=0.0)
part('Bathroom', bm_box(-3.9, -2.4, -0.03, 0.001, -4.1, -3.2), 'BathFloor', bevel=0.0)
# タオル掛けとタオル（ドアの開く範囲をよけて奥の壁に）
TWX = -0.5
part('Bathroom', bm_tube([(-2.98 + TWX, 1.52, -4.05), (-2.98 + TWX, 1.52, -4.01), (-2.57 + TWX, 1.52, -4.01), (-2.57 + TWX, 1.52, -4.05)],
                         0.008, seg=10), 'Chrome', smooth=True)


def towel_fn(s, t):
    x = -2.95 + TWX + 0.35 * s
    y = 1.53 - 0.52 * t
    z = -4.012 + 0.006 * math.sin(s * 9.0) + 0.004 * t
    return (x, y, z)


part('Bathroom', bm_grid(towel_fn, 16, 12), 'Towel', smooth=True, solidify=0.008)
# 洗面ボウル
part('Bathroom', bm_lathe([(0.0, 0.0), (0.16, 0.0), (0.2, 0.08), (0.21, 0.13), (0.19, 0.13), (0.15, 0.04), (0.0, 0.04)],
                          center=(-2.66, 0.72, -3.82), seg=32), 'Plastic', smooth=True)
part('Bathroom', bm_cyl((-2.66, 0.0, -3.82), (-2.66, 0.72, -3.82), 0.05, 0.07, seg=20), 'Plastic', smooth=True)
finalize('Bathroom')

# 浴室ドア（原点＝蝶番 (-3.58, 0, -3.1)）
BX, BZ = -3.58, -3.1
boxp('BathDoor', 'BathDoor', BX, BX + 0.86, 0.0, 2.08, BZ - 0.025, BZ + 0.025, bevel=0.008, seg=3)
# 下のガラリ（換気の羽根）
boxp('BathDoor', 'Plastic', BX + 0.2, BX + 0.66, 0.08, 0.34, BZ + 0.024, BZ + 0.03, bevel=0.003)
for i in range(8):
    y = 0.1 + i * 0.029
    boxp('BathDoor', 'Plastic', BX + 0.22, BX + 0.64, y, y + 0.012, BZ + 0.026, BZ + 0.036, bevel=0.002)
# 縦長のすりガラス風パネル（光らせない。くぼみだけ）
boxp('BathDoor', 'Plastic', BX + 0.3, BX + 0.56, 1.0, 1.85, BZ + 0.024, BZ + 0.028, bevel=0.003)
# 座金（表・裏）
part('BathDoor', bm_cyl((BX + 0.76, 1.0, BZ + 0.025), (BX + 0.76, 1.0, BZ + 0.035), 0.028, seg=24), 'Chrome', smooth=True)
part('BathDoor', bm_cyl((BX + 0.76, 1.0, BZ - 0.025), (BX + 0.76, 1.0, BZ - 0.035), 0.028, seg=24), 'Chrome', smooth=True)
bath_door = finalize('BathDoor', pivot=(BX, 0, BZ))

# 浴室ドアのレバー（原点＝回転軸。ドアの子）
LX, LY, LZ = BX + 0.76, 1.0, BZ + 0.05
part('BathLever', bm_cyl((LX, LY, LZ - 0.015), (LX, LY, LZ + 0.012), 0.01, seg=14), 'Chrome', smooth=True)
part('BathLever', bm_tube([(LX, LY, LZ + 0.012), (LX - 0.03, LY, LZ + 0.02), (LX - 0.08, LY, LZ + 0.022),
                           (LX - 0.11, LY - 0.002, LZ + 0.018)], 0.009, seg=12), 'Chrome', smooth=True)
lever = finalize('BathLever', pivot=(LX, LY, LZ))
parent_to(lever, bath_door)

# ================================================================ キッチン
# 流し台の本体（扉・台輪）
boxp('Kitchen', 'CabinetBody', -2.4, 0.7, 0.08, 0.7, -3.0, -2.43, bevel=0.003)
boxp('Kitchen', 'CabinetBody', -2.4, 0.7, 0.7, 0.86, -2.47, -2.43, bevel=0.003)
for (x0, x1) in [(-2.4, -2.37), (0.67, 0.7)]:
    boxp('Kitchen', 'CabinetBody', x0, x1, 0.7, 0.86, -3.0, -2.43, bevel=0.003)
boxp('Kitchen', 'BlackPlastic', -2.39, 0.69, 0.0, 0.08, -2.98, -2.48, bevel=0.002)
doors = [(-2.4, -1.78), (-1.78, -1.16), (-1.16, -0.54), (-0.54, 0.08), (0.08, 0.7)]
for i, (x0, x1) in enumerate(doors):
    boxp('Kitchen', 'CabinetDoor', x0 + 0.004, x1 - 0.004, 0.09, 0.83, -2.43, -2.41, bevel=0.004, uvrot=True)
    hx = x1 - 0.14 if i % 2 == 0 else x0 + 0.04
    part('Kitchen', bm_tube([(hx, 0.74, -2.41), (hx, 0.74, -2.385), (hx + 0.1, 0.74, -2.385), (hx + 0.1, 0.74, -2.41)],
                            0.006, seg=10), 'Stainless', smooth=True)
# ステンレスの天板（シンクの穴あき）
top = part('Kitchen', bm_box(-2.42, 0.72, 0.86, 0.92, -3.0, -2.36), 'Stainless', bevel=0.0)
cut = part('_cut', bm_box(-1.85, -1.15, 0.8, 1.0, -2.88, -2.48), 'Stainless')
md = top.modifiers.new('sink', 'BOOLEAN')
md.operation = 'DIFFERENCE'
md.solver = 'EXACT'
md.object = cut
md = top.modifiers.new('bev', 'BEVEL')
md.width = 0.006
md.segments = 3
md.limit_method = 'ANGLE'
md.angle_limit = math.radians(40)
md.harden_normals = True
top.data.shade_smooth()
apply_mods(top)
bpy.data.objects.remove(GROUPS.pop('_cut')[0])
# シンクの槽（内側だけの箱）
sink = bmesh.new()
bm_box(-1.85, -1.15, 0.72, 0.92, -2.88, -2.48, sink)
bmesh.ops.delete(sink, geom=[f for f in sink.faces if f.calc_center_median().y > 0.91], context='FACES')
bmesh.ops.reverse_faces(sink, faces=sink.faces)
part('Kitchen', sink, 'Stainless', bevel=0.02, seg=3)
part('Kitchen', bm_cyl((-1.5, 0.721, -2.68), (-1.5, 0.724, -2.68), 0.035, seg=24), 'Chrome', smooth=True)
# 壁のタイル（流し台と吊戸棚の間）
boxp('Kitchen', 'Backsplash', -2.4, 0.7, 0.92, 1.75, -3.0, -2.994, bevel=0.0)
# 吊戸棚
boxp('Kitchen', 'CabinetBody', -2.4, 0.7, 1.75, 2.4, -3.0, -2.7, bevel=0.003)
for (x0, x1) in [(-2.4, -1.78), (-1.78, -1.16), (-1.16, -0.54), (-0.54, 0.08), (0.08, 0.7)]:
    boxp('Kitchen', 'WallCabinet', x0 + 0.004, x1 - 0.004, 1.754, 2.396, -2.7, -2.68, bevel=0.004, uvrot=True)
# レンジフード
boxp('Kitchen', 'Stainless', -0.7, 0.4, 1.6, 1.75, -3.0, -2.55, bevel=0.01)
boxp('Kitchen', 'BlackPlastic', -0.66, 0.36, 1.598, 1.6, -2.98, -2.6, bevel=0.0)
boxp('Kitchen', 'BlackPlastic', -0.08, 0.2, 1.62, 1.66, -2.552, -2.548, bevel=0.002)
# 蛇口（シングルレバー）
part('Kitchen', bm_cyl((-1.5, 0.92, -2.9), (-1.5, 0.94, -2.9), 0.03, seg=24), 'Chrome', smooth=True)
part('Kitchen', bm_cyl((-1.5, 0.94, -2.9), (-1.5, 1.08, -2.9), 0.02, 0.018, seg=20), 'Chrome', smooth=True)
spout = [(-1.5, 1.07, -2.9)] + [(-1.5, 1.07 + 0.07 * math.sin(a), -2.83 - 0.07 * math.cos(a))
                                for a in [math.pi * k / 16 for k in range(1, 9)]] + [(-1.5, 1.14, -2.76), (-1.5, 1.13, -2.738)]
part('Kitchen', bm_tube(spout, 0.012, seg=14), 'Chrome', smooth=True)
part('Kitchen', bm_cyl((-1.5, 1.1, -2.9), (-1.5, 1.1, -2.98), 0.008, seg=10), 'Chrome', smooth=True)
part('Kitchen', bm_tube([(-1.5, 1.1, -2.98), (-1.5, 1.13, -3.0)], 0.006, seg=8), 'Chrome', smooth=True)
# 洗剤とスポンジ
part('Kitchen', bm_lathe([(0, 0), (0.03, 0), (0.032, 0.12), (0.025, 0.15), (0.01, 0.16), (0.01, 0.18), (0, 0.18)],
                         center=(-2.1, 0.92, -2.85), seg=20), 'FoodGreen', smooth=True)
boxp('Kitchen', 'FoodYellow', -1.98, -1.88, 0.92, 0.95, -2.9, -2.84, bevel=0.01)
finalize('Kitchen')

# コンロ（2口のガステーブル）
boxp('Stove', 'StoveTop', -0.65, 0.35, 0.92, 0.95, -2.9, -2.45, bevel=0.008)
boxp('Stove', 'Stainless', -0.65, 0.35, 0.88, 0.92, -2.46, -2.44, bevel=0.004)
for kx in (-0.4, 0.1):
    part('Stove', bm_cyl((kx, 0.9, -2.44), (kx, 0.9, -2.41), 0.018, seg=20), 'Knob', smooth=True)
    boxp('Stove', 'Knob', kx - 0.004, kx + 0.004, 0.885, 0.915, -2.42, -2.405, bevel=0.002)
for bx in (-0.4, 0.1):
    bz = -2.67
    part('Stove', bm_lathe([(0.0, 0.0), (0.1, 0.0), (0.1, 0.004), (0.085, 0.006), (0.085, 0.012), (0.07, 0.014), (0.07, 0.016),
                            (0.03, 0.016), (0.028, 0.022), (0.0, 0.024)], center=(bx, 0.95, bz), seg=32), 'Burner', smooth=True)
    # 五徳（放射状の爪）
    part('Stove', bm_lathe([(0.115, 0.0), (0.125, 0.0), (0.125, 0.008), (0.115, 0.008)], center=(bx, 0.95, bz), seg=32,
                           cap_bottom=False), 'CastIron', smooth=True)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        ca, sa = math.cos(a), math.sin(a)
        part('Stove', bm_tube([(bx + ca * 0.12, 0.954, bz + sa * 0.12), (bx + ca * 0.12, 0.97, bz + sa * 0.12),
                               (bx + ca * 0.085, 0.97, bz + sa * 0.085)], 0.005, seg=6), 'CastIron', smooth=True)
finalize('Stove')

# やかん（原点＝底の中心）
KX, KY, KZ = -0.4, 0.97, -2.67
part('Kettle', bm_lathe([(0.0, 0.0), (0.088, 0.0), (0.096, 0.008), (0.1, 0.03), (0.098, 0.07), (0.088, 0.105),
                         (0.07, 0.122), (0.058, 0.128), (0.058, 0.132), (0.0, 0.132)],
                        center=(KX, KY, KZ), seg=40), 'Kettle', smooth=True)
part('Kettle', bm_tube([(KX + 0.08, KY + 0.05, KZ), (KX + 0.11, KY + 0.075, KZ), (KX + 0.135, KY + 0.11, KZ),
                        (KX + 0.155, KY + 0.135, KZ)], 0.013, seg=14, caps=False), 'Kettle', smooth=True)
handle = [(KX, KY + 0.12, KZ - 0.075)] + [(KX, KY + 0.15 + 0.06 * math.sin(a), KZ - 0.07 * math.cos(a))
                                           for a in [math.pi * k / 12 for k in range(13)]] + [(KX, KY + 0.12, KZ + 0.075)]
part('Kettle', bm_tube(handle, 0.008, seg=10), 'BlackPlastic', smooth=True)
kettle = finalize('Kettle', pivot=(KX, KY, KZ))
# やかんのフタ（原点＝フタの中心。やかんの子）
part('KettleLid', bm_lathe([(0.0, -0.008), (0.056, -0.008), (0.06, 0.0), (0.05, 0.008), (0.02, 0.012), (0.0, 0.012)],
                           center=(KX, KY + 0.14, KZ), seg=32), 'Kettle', smooth=True)
part('KettleLid', bm_superellipsoid((KX, KY + 0.16, KZ), 0.016, 0.01, 0.016, 0.6, 1.0, nu=8, nv=16), 'BlackPlastic', smooth=True)
klid = finalize('KettleLid', pivot=(KX, KY + 0.14, KZ))
parent_to(klid, kettle)

# ================================================================ 冷蔵庫
boxp('Fridge', 'FridgeBody', 0.95, 0.99, 0.0, 1.7, -3.0, -2.34, bevel=0.008)
boxp('Fridge', 'FridgeBody', 1.71, 1.75, 0.0, 1.7, -3.0, -2.34, bevel=0.008)
boxp('Fridge', 'FridgeBody', 0.95, 1.75, 1.66, 1.7, -3.0, -2.34, bevel=0.008)
boxp('Fridge', 'BlackPlastic', 0.97, 1.73, 0.0, 0.08, -2.98, -2.36, bevel=0.004)
# 庫内（光る内張り）
inner = bmesh.new()
# 本体の側板・天板・下の黒い台の面と同じ位置に重ねると、実機の GPU でちらつく網目（Z ファイティング）になるので、
# 内張りは内側へ 3mm 離す（three 側の polygonOffset で押し出すと、側板の外側に点線が透けた）
bm_box(0.993, 1.707, 0.083, 1.657, -2.99, -2.34, inner)
bmesh.ops.delete(inner, geom=[f for f in inner.faces if f.calc_center_median().z > -2.35], context='FACES')
bmesh.ops.reverse_faces(inner, faces=inner.faces)
part('Fridge', inner, 'FridgeInner', bevel=0.02, seg=2)
for y in (0.55, 1.08):
    boxp('Fridge', 'FridgeInner', 0.995, 1.705, y, y + 0.02, -2.96, -2.45, bevel=0.004)
# 野菜室のケース
boxp('Fridge', 'FridgeInner', 1.0, 1.7, 0.085, 0.1, -2.96, -2.45, bevel=0.003)
boxp('Fridge', 'FridgeInner', 1.0, 1.7, 0.085, 0.3, -2.47, -2.45, bevel=0.004)
# 中身
boxp('Fridge', 'FoodWhite', 1.05, 1.15, 0.57, 0.76, -2.8, -2.7, bevel=0.004)  # 牛乳パック
roof = bmesh.new()
v = [roof.verts.new(p) for p in [(1.05, 0.76, -2.8), (1.15, 0.76, -2.8), (1.15, 0.76, -2.7), (1.05, 0.76, -2.7),
                                  (1.05, 0.8, -2.75), (1.15, 0.8, -2.75)]]
roof.faces.new((v[0], v[1], v[5], v[4]))
roof.faces.new((v[3], v[4], v[5], v[2]))
roof.faces.new((v[0], v[4], v[3]))
roof.faces.new((v[1], v[2], v[5]))
bmesh.ops.recalc_face_normals(roof, faces=roof.faces)
part('Fridge', roof, 'FoodWhite')
boxp('Fridge', 'FoodYellow', 1.2, 1.38, 0.57, 0.64, -2.85, -2.6, bevel=0.012)
boxp('Fridge', 'Plastic', 1.195, 1.385, 0.64, 0.66, -2.855, -2.595, bevel=0.008)
part('Fridge', bm_lathe([(0, 0), (0.035, 0), (0.036, 0.13), (0.03, 0.17), (0.013, 0.2), (0.013, 0.22), (0, 0.22)],
                        center=(1.55, 0.57, -2.75), seg=24), 'FoodGreen', smooth=True)
boxp('Fridge', 'FoodRed', 1.1, 1.45, 1.1, 1.2, -2.9, -2.6, bevel=0.015)
part('Fridge', bm_lathe([(0, 0), (0.03, 0), (0.03, 0.15), (0.026, 0.16), (0.026, 0.18), (0, 0.18)],
                        center=(1.6, 1.1, -2.8), seg=20), 'FoodCream', smooth=True)
finalize('Fridge')

# 冷蔵庫の扉（原点＝蝶番 (1.75, 0, -2.34)）
FX, FZ = 1.75, -2.34
boxp('FridgeDoor', 'FridgeBody', FX - 0.8, FX, 0.08, 1.7, FZ, FZ + 0.05, bevel=0.015, seg=3)
# パッキンは扉の角の丸み（bevel 0.015）より内側に収める。はみ出すと扉の表に四角い線が透ける
boxp('FridgeDoor', 'Gasket', FX - 0.78, FX - 0.02, 0.1, 1.68, FZ - 0.012, FZ, bevel=0.004)
boxp('FridgeDoor', 'Gasket', FX - 0.8, FX, 1.077, 1.083, FZ + 0.049, FZ + 0.052, bevel=0.0)
part('FridgeDoor', bm_tube([(FX - 0.745, 0.75, FZ + 0.05), (FX - 0.745, 0.76, FZ + 0.075), (FX - 0.745, 1.34, FZ + 0.075),
                            (FX - 0.745, 1.35, FZ + 0.05)], 0.011, seg=12), 'Plastic', smooth=True)
part('FridgeDoor', bm_cyl((FX - 0.3, 1.4, FZ + 0.05), (FX - 0.3, 1.4, FZ + 0.062), 0.03, seg=24), 'MagnetRed', smooth=True)
part('FridgeDoor', bm_cyl((FX - 0.45, 1.3, FZ + 0.05), (FX - 0.45, 1.3, FZ + 0.062), 0.025, seg=24), 'MagnetBlue', smooth=True)
boxp('FridgeDoor', 'FoodWhite', FX - 0.52, FX - 0.36, 1.18, 1.38, FZ + 0.05, FZ + 0.052, bevel=0.0)  # メモ
# 扉ポケット（内側）
for y in (0.35, 0.8, 1.3):
    boxp('FridgeDoor', 'FridgeInner', FX - 0.72, FX - 0.08, y, y + 0.012, FZ - 0.085, FZ - 0.012, bevel=0.003)
    boxp('FridgeDoor', 'FridgeInner', FX - 0.72, FX - 0.08, y, y + 0.08, FZ - 0.09, FZ - 0.082, bevel=0.003)
for i, bx in enumerate((-0.65, -0.57, -0.49)):
    part('FridgeDoor', bm_lathe([(0, 0), (0.03, 0), (0.03, 0.16), (0.012, 0.2), (0.012, 0.22), (0, 0.22)],
                                center=(FX + bx, 0.362, FZ - 0.048), seg=16),
         ['FoodGreen', 'FoodWhite', 'FoodCream'][i], smooth=True)
finalize('FridgeDoor', pivot=(FX, 0, FZ))

# ================================================================ ベッド
boxp('Bed', 'BedFrame', 2.3, 3.9, 0.06, 0.32, -2.92, -0.95, bevel=0.012, uvrot=True)
for (x, z) in [(2.34, -0.99), (3.86, -0.99), (2.34, -2.9), (3.86, -2.9)]:
    boxp('Bed', 'BedFrame', x - 0.04, x + 0.04, 0.0, 0.08, z - 0.04, z + 0.04, bevel=0.008)
boxp('Bed', 'BedFrame', 2.3, 3.9, 0.0, 0.85, -3.0, -2.92, bevel=0.012)
boxp('Bed', 'BedFrame', 2.28, 3.92, 0.85, 0.88, -3.0, -2.9, bevel=0.01)
part('Bed', bm_superellipsoid((3.1, 0.42, -1.96), 0.74, 0.1, 0.96, 0.25, 0.08, nu=12, nv=48), 'Mattress', smooth=True, sharp=70)
part('Bed', bm_superellipsoid((3.1, 0.58, -2.66), 0.4, 0.065, 0.17, 0.55, 0.35, nu=14, nv=40, flat_bottom=0.055),
     'Pillow', smooth=True, sharp=80)
finalize('Bed')


# 掛け布団（原点 (3.1, 0.555, -1.72)。両脇と足元に垂れる）
def drape(s, flat, r, drop):
    a = abs(s)
    arc = math.pi / 2 * r
    if a <= flat:
        return s, 0.0
    if a <= flat + arc:
        th = (a - flat) / r
        return math.copysign(flat + r * math.sin(th), s), -r * (1 - math.cos(th))
    return math.copysign(flat + r, s), -r - min(drop, a - flat - arc)


BLX, BLY, BLZ = 3.1, 0.555, -1.72
SX = 0.74 + math.pi / 2 * 0.05 + 0.13
SZ = 0.72 + math.pi / 2 * 0.05 + 0.12


def blanket_fn(s, t):
    u = -SX + 2 * SX * s
    w = -0.75 + (0.75 + SZ) * t
    x, dy1 = drape(u, 0.72, 0.05, 0.13)
    if w > 0:
        z, dy2 = drape(w, 0.70, 0.05, 0.12)
    else:
        z, dy2 = w, 0.0
    puff = 0.0
    if dy1 == 0 and dy2 == 0:
        puff = 0.008 * (math.cos(x * 2 * math.pi / 0.36) * math.cos(z * 2 * math.pi / 0.36)) + 0.006
        puff += 0.006 * math.sin(x * 7 + z * 3)
    return (BLX + x, BLY + 0.035 + dy1 + dy2 + puff, BLZ + z)


part('Blanket', bm_grid(blanket_fn, 48, 44), 'Blanket', smooth=True, sharp=80, solidify=0.05)
blanket = finalize('Blanket', pivot=(BLX, BLY, BLZ))
# 折り返し（原点はその中心。掛け布団の子）
part('BlanketFold', bm_superellipsoid((BLX, BLY + 0.06, BLZ - 0.55), 0.79, 0.03, 0.175, 0.6, 0.12, nu=10, nv=48),
     'Blanket', smooth=True, sharp=80)
fold = finalize('BlanketFold', pivot=(BLX, BLY + 0.06, BLZ - 0.55))
parent_to(fold, blanket)

# ================================================================ 窓とカーテン
part('Window', bm_box(2.45, 3.75, 1.15, 2.35, -3.16, -3.15), 'NightSky', bevel=0.0)
part('Window', bm_cyl((3.45, 2.05, -3.149), (3.45, 2.05, -3.145), 0.08, seg=32), 'Moon', smooth=True)
# アルミサッシ
for (y0, y1) in [(1.2, 1.24), (2.26, 2.3)]:
    boxp('Window', 'WindowFrame', 2.5, 3.7, y0, y1, -3.1, -2.97, bevel=0.004)
for (x0, x1) in [(2.5, 2.54), (3.66, 3.7)]:
    boxp('Window', 'WindowFrame', x0, x1, 1.2, 2.3, -3.1, -2.97, bevel=0.004)
# 引き違いの障子（左は手前、右は奥）
for (x0, x1, z0, z1) in [(2.54, 3.13, -3.04, -3.01), (3.07, 3.66, -3.08, -3.05)]:
    for (y0, y1) in [(1.24, 1.28), (2.22, 2.26)]:
        boxp('Window', 'WindowFrame', x0, x1, y0, y1, z0, z1, bevel=0.003)
    for (a, b) in [(x0, x0 + 0.035), (x1 - 0.035, x1)]:
        boxp('Window', 'WindowFrame', a, b, 1.24, 2.26, z0, z1, bevel=0.003)
boxp('Window', 'WindowFrame', 3.118, 3.13, 1.65, 1.75, -3.012, -3.0, bevel=0.002)  # クレセント
boxp('Window', 'Trim', 2.46, 3.74, 1.16, 1.2, -3.0, -2.95, bevel=0.006)  # 窓台
# カーテンレール
boxp('Window', 'CurtainRail', 2.33, 3.87, 2.42, 2.45, -2.93, -2.9, bevel=0.006)
for x in (2.45, 3.75):
    boxp('Window', 'CurtainRail', x - 0.015, x + 0.015, 2.42, 2.47, -3.0, -2.92, bevel=0.004)
for x in (2.33, 3.87):
    part('Window', bm_cyl((x, 2.435, -2.915), (x + (0.012 if x > 3 else -0.012), 2.435, -2.915), 0.018, seg=16),
         'CurtainRail', smooth=True)
finalize('Window')


def make_curtain(name, pivot_x, d):
    def fn(s, t):
        x = pivot_x + d * 0.7 * s
        y = 1.02 + 1.38 * t
        z = -2.88 + 0.022 * math.sin(s * 2 * math.pi * 7) * (0.6 + 0.4 * t) + 0.004 * math.sin(t * 9 + s * 4)
        return (x, y, z)
    part(name, bm_grid(fn, 84, 20), 'Curtain', smooth=True, sharp=80, solidify=0.006)
    for k in range(8):
        x = pivot_x + d * 0.7 * (k + 0.5) / 8
        part(name, bm_cyl((x, 2.4, -2.88), (x, 2.425, -2.88), 0.006, seg=8), 'Plastic', smooth=True)
    return finalize(name, pivot=(pivot_x, 0, -2.88))


make_curtain('CurtainL', 2.4, 1)
make_curtain('CurtainR', 3.8, -1)

# ================================================================ 机・椅子・ノートPC・スタンド
boxp('Desk', 'Desk', 3.1, 3.9, 0.72, 0.77, 0.7, 2.1, bevel=0.008, seg=3, uvrot=True)
for (x, z) in [(3.14, 0.74), (3.86, 0.74), (3.14, 2.06), (3.86, 2.06)]:
    boxp('Desk', 'Desk', x - 0.022, x + 0.022, 0.0, 0.72, z - 0.022, z + 0.022, bevel=0.005)
boxp('Desk', 'Desk', 3.13, 3.15, 0.64, 0.72, 0.76, 2.04, bevel=0.003, uvrot=True)
boxp('Desk', 'Desk', 3.85, 3.87, 0.64, 0.72, 0.76, 2.04, bevel=0.003, uvrot=True)
boxp('Desk', 'Desk', 3.16, 3.84, 0.64, 0.72, 0.73, 0.75, bevel=0.003)
boxp('Desk', 'Desk', 3.16, 3.84, 0.64, 0.72, 2.05, 2.07, bevel=0.003)
# 本
boxp('Desk', 'BookRed', 3.5, 3.8, 0.77, 0.81, 1.8, 2.02, bevel=0.004)
boxp('Desk', 'BookPages', 3.505, 3.79, 0.774, 0.806, 1.79, 2.012, bevel=0.002)
boxp('Desk', 'BookBlue', 3.52, 3.78, 0.81, 0.84, 1.82, 2.0, bevel=0.004)
boxp('Desk', 'BookPages', 3.525, 3.77, 0.813, 0.837, 1.812, 1.992, bevel=0.002)
finalize('Desk')

# ノートPC の本体
boxp('Laptop', 'LaptopBody', 3.3, 3.56, 0.77, 0.785, 1.24, 1.62, bevel=0.005, seg=3)
for i in range(6):
    for j in range(13):
        x0 = 3.425 + i * 0.019
        z0 = 1.3 + j * 0.0195
        boxp('Laptop', 'LaptopKeys', x0, x0 + 0.015, 0.785, 0.7865, z0, z0 + 0.016, bevel=0.0)
boxp('Laptop', 'LaptopKeys', 3.33, 3.405, 0.785, 0.7855, 1.37, 1.49, bevel=0.0)
finalize('Laptop')
# ノートPC のふた（原点＝蝶番 (3.56, 0.785, 1.43)）
boxp('LaptopLid', 'LaptopBody', 3.3, 3.56, 0.785, 0.797, 1.24, 1.62, bevel=0.005, seg=3)
part('LaptopLid', bm_box(3.31, 3.545, 0.7844, 0.7848, 1.26, 1.6), 'LaptopKeys', bevel=0.0)
part('LaptopLid', bm_box(3.315, 3.54, 0.7838, 0.7842, 1.265, 1.595), 'LaptopScreen', bevel=0.0)
finalize('LaptopLid', pivot=(3.56, 0.785, 1.43))

# スタンド
part('Lamp', bm_lathe([(0, 0), (0.08, 0), (0.08, 0.012), (0.07, 0.022), (0.02, 0.026), (0, 0.026)],
                      center=(3.72, 0.77, 0.92), seg=32), 'LampMetal', smooth=True)
part('Lamp', bm_tube([(3.72, 0.79, 0.92), (3.72, 1.22, 0.92), (3.71, 1.245, 0.92), (3.695, 1.25, 0.92)], 0.008, seg=10),
     'LampMetal', smooth=True)
ax = Vector((-0.5, -0.866, 0.0))
sc = Vector((3.66, 1.2, 0.92))
shade = bm_lathe([(0.012, -0.06), (0.03, -0.05), (0.06, -0.01), (0.09, 0.06), (0.088, 0.06), (0.058, -0.008),
                  (0.028, -0.046), (0.01, -0.056)], seg=32)
rot = Vector((0, 1, 0)).rotation_difference(ax).to_matrix().to_4x4()
bmesh.ops.transform(shade, matrix=Matrix.Translation(sc) @ rot, verts=shade.verts)
part('Lamp', shade, 'LampMetal', smooth=True, sharp=60)
part('Lamp', bm_superellipsoid((3.64, 1.17, 0.92), 0.028, 0.028, 0.028, 1.0, 1.0, nu=12, nv=20), 'LampBulb', smooth=True)
finalize('Lamp')

# 椅子（原点 (2.72, 0, 1.4)。座る人は +x を向く）
CX, CZ = 2.72, 1.4
for (dx, dz) in [(-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)]:
    part('Chair', bm_cyl((CX + dx * 1.04, 0.0, CZ + dz * 1.04), (CX + dx, 0.44, CZ + dz), 0.014, 0.017, seg=14),
         'ChairWood', smooth=True)
for dz in (-0.18, 0.18):
    part('Chair', bm_cyl((CX - 0.19, 0.44, CZ + dz), (CX - 0.215, 0.92, CZ + dz), 0.016, 0.013, seg=14), 'ChairWood', smooth=True)
part('Chair', bm_cyl((CX - 0.185, 0.16, CZ - 0.18), (CX - 0.185, 0.16, CZ + 0.18), 0.009, seg=10), 'ChairWood', smooth=True)
part('Chair', bm_cyl((CX + 0.185, 0.16, CZ - 0.18), (CX + 0.185, 0.16, CZ + 0.18), 0.009, seg=10), 'ChairWood', smooth=True)
boxp('Chair', 'ChairWood', CX - 0.22, CX + 0.22, 0.42, 0.45, CZ - 0.22, CZ + 0.22, bevel=0.008)
part('Chair', bm_superellipsoid((CX + 0.005, 0.462, CZ), 0.205, 0.016, 0.205, 0.4, 0.15, nu=10, nv=40), 'ChairSeat',
     smooth=True, sharp=80)
# 背もたれ（ゆるく曲げた板）


def back_fn(s, t):
    z = CZ - 0.2 + 0.4 * s
    y = 0.7 + 0.18 * t
    x = CX - 0.205 - 0.04 * (1 - ((s - 0.5) * 2) ** 2) * 0.6 - 0.012 * t
    return (x, y, z)


part('Chair', bm_grid(back_fn, 16, 4), 'ChairWood', smooth=True, sharp=80, solidify=0.018)
finalize('Chair', pivot=(CX, 0, CZ))

# ================================================================ テレビ・ローテーブル・座布団
part('Rug', bm_superellipsoid((-2.0, 0.005, -0.3), 1.1, 0.006, 0.85, 0.2, 0.06, nu=6, nv=64), 'Rug', smooth=True, sharp=50)
finalize('Rug')

# テレビ台（前面は +x）
boxp('TVStand', 'TVStand', -4.0, -3.55, 0.05, 0.08, -1.15, 0.35, bevel=0.004)
boxp('TVStand', 'TVStand', -4.0, -3.55, 0.42, 0.45, -1.15, 0.35, bevel=0.006, uvrot=True)
for z0 in (-1.15, -0.67, 0.0, 0.32):
    boxp('TVStand', 'TVStand', -4.0, -3.55, 0.08, 0.42, z0, z0 + 0.03, bevel=0.003)
boxp('TVStand', 'TVStand', -4.0, -3.99, 0.08, 0.42, -1.15, 0.35, bevel=0.0)
for (z0, z1) in [(-1.12, -0.67), (0.03, 0.32)]:
    boxp('TVStand', 'TVStand', -3.57, -3.55, 0.085, 0.415, z0 + 0.004, z1 - 0.004, bevel=0.004)
    boxp('TVStand', 'BlackPlastic', -3.55, -3.535, 0.33, 0.345, (z0 + z1) / 2 - 0.06, (z0 + z1) / 2 + 0.06, bevel=0.004)
for (x, z) in [(-3.96, -1.11), (-3.59, -1.11), (-3.96, 0.31), (-3.59, 0.31)]:
    part('TVStand', bm_cyl((x, 0.0, z), (x, 0.05, z), 0.018, seg=12), 'BlackPlastic', smooth=True)
# 中の段：レコーダー
boxp('TVStand', 'BlackPlastic', -3.95, -3.6, 0.08, 0.15, -0.6, -0.12, bevel=0.005)
boxp('TVStand', 'FoodGreen', -3.6, -3.599, 0.11, 0.113, -0.2, -0.19, bevel=0.0)
finalize('TVStand')

# テレビ
boxp('TV', 'TVBody', -3.9, -3.75, 0.45, 0.462, -0.62, -0.18, bevel=0.005)
boxp('TV', 'TVBody', -3.86, -3.83, 0.46, 0.6, -0.44, -0.36, bevel=0.005)
boxp('TV', 'TVBody', -3.86, -3.8, 0.47, 1.13, -1.0, 0.2, bevel=0.006, seg=3)
boxp('TV', 'TVBody', -3.9, -3.86, 0.55, 1.05, -0.8, 0.0, bevel=0.02)
part('TV', bm_box(-3.7955, -3.795, 0.5, 1.1, -0.96, 0.16), 'TVScreen', bevel=0.0)
finalize('TV')

# ローテーブル
boxp('LowTable', 'LowTable', -2.5, -1.5, 0.33, 0.39, -0.65, 0.05, bevel=0.012, seg=3, uvrot=True)
for (x, z) in [(-2.42, -0.57), (-1.58, -0.57), (-2.42, -0.03), (-1.58, -0.03)]:
    boxp('LowTable', 'LowTable', x - 0.03, x + 0.03, 0.0, 0.33, z - 0.03, z + 0.03, bevel=0.006)
boxp('LowTable', 'LowTable', -2.44, -1.56, 0.27, 0.33, -0.6, -0.58, bevel=0.003)
boxp('LowTable', 'LowTable', -2.44, -1.56, 0.27, 0.33, -0.02, 0.0, bevel=0.003)
boxp('LowTable', 'LowTable', -2.44, -2.42, 0.27, 0.33, -0.58, -0.02, bevel=0.003)
boxp('LowTable', 'LowTable', -1.58, -1.56, 0.27, 0.33, -0.58, -0.02, bevel=0.003)
# マグカップ
part('LowTable', bm_lathe([(0, 0.002), (0.034, 0.0), (0.038, 0.005), (0.04, 0.09), (0.036, 0.09), (0.034, 0.012), (0, 0.012)],
                          center=(-2.25, 0.39, -0.45), seg=32), 'Mug', smooth=True)
part('LowTable', bm_tube([(-2.25 + 0.038, 0.39 + 0.072, -0.45)] +
                         [(-2.25 + 0.04 + 0.025 * math.sin(a), 0.39 + 0.045 + 0.027 * math.cos(a), -0.45)
                          for a in [math.pi * k / 8 for k in range(1, 8)]] + [(-2.25 + 0.038, 0.39 + 0.018, -0.45)],
                         0.006, seg=10), 'Mug', smooth=True)
finalize('LowTable')

# リモコン（原点＝中心 (-1.72, 0.402, -0.12)）
RX, RY, RZ = -1.72, 0.402, -0.12
part('Remote', bm_superellipsoid((RX, RY, RZ), 0.025, 0.011, 0.085, 0.5, 0.2, nu=10, nv=32), 'Remote', smooth=True, sharp=70)
part('Remote', bm_cyl((RX, RY + 0.009, RZ - 0.06), (RX, RY + 0.0125, RZ - 0.06), 0.006, seg=12), 'RemoteRed', smooth=True)
for i in range(4):
    for j in range(3):
        part('Remote', bm_cyl((RX - 0.012 + j * 0.012, RY + 0.009, RZ - 0.03 + i * 0.016),
                              (RX - 0.012 + j * 0.012, RY + 0.0118, RZ - 0.03 + i * 0.016), 0.0045, seg=10),
             'RemoteButton', smooth=True)
part('Remote', bm_cyl((RX, RY + 0.009, RZ + 0.05), (RX, RY + 0.012, RZ + 0.05), 0.012, seg=20), 'RemoteButton', smooth=True)
finalize('Remote', pivot=(RX, RY, RZ))

# 座布団（原点＝中心）
for i, (x, z) in enumerate([(-1.15, -0.35), (-2.0, 0.42), (-2.0, -1.02)]):
    name = f'Cushion{i}'
    cb = bm_superellipsoid((x, 0.04, z), 0.25, 0.04, 0.25, 0.45, 0.12, nu=14, nv=48, flat_bottom=0.036)
    # 真ん中を少しへこませる（綴じ）
    for v in cb.verts:
        r = math.hypot(v.co.x - x, v.co.z - z)
        if v.co.y > 0.04:
            v.co.y -= 0.012 * math.exp(-(r / 0.05) ** 2)
    part(name, cb, name, smooth=True, sharp=80)
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.4
        part(name, bm_tube([(x, 0.07, z), (x + 0.012 * math.cos(a), 0.074, z + 0.012 * math.sin(a)),
                            (x + 0.02 * math.cos(a), 0.072, z + 0.02 * math.sin(a))], 0.0025, seg=6), 'Thread', smooth=True)
    finalize(name, pivot=(x, 0.04, z))

assert not GROUPS, GROUPS.keys()

# ---------------------------------------------------------------- 書き出し
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format='GLB',
    export_yup=True,
    export_apply=True,
    export_image_format='AUTO',
    export_materials='EXPORT',
    export_cameras=False,
    export_lights=False,
    export_extras=False,
    export_animations=False,
)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in SCN.objects:
    if ob.type == 'MESH':
        me = ob.evaluated_get(dg).data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
print('OBJECTS', sorted(o.name for o in SCN.objects))
print('TRIS', tris)
print('GLB', OUT_GLB, os.path.getsize(OUT_GLB))
