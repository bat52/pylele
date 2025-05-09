#!/usr/bin/env python3

from __future__ import annotations
import bpy
import bmesh
import copy
from math import ceil, pi
from mathutils import Vector
import os
from pathlib import Path
import sys
from typing import Union

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from b13d.api.core import Shape, ShapeAPI, test_api
from b13d.api.utils import (
    dimXY,
    file_ensure_extension,
    isPathCounterClockwise,
    lineSplineXY,
    radians,
    simplifyLineSpline,
)


"""
    Encapsulate Blender implementation specific calls
"""


def gen_box_points(x: float, y: float, z: float) -> list[tuple[float, float, float]]:
    return [
        (0, 0, 0),
        (x, 0, 0),
        (x, y, 0),
        (0, y, 0),
        (0, 0, z),
        (x, 0, z),
        (x, y, z),
        (0, y, z),
    ]

class BlenderShapeAPI(ShapeAPI):

    def export(self, shape: BlenderShape, path: Union[str, Path],fmt=".stl") -> None:
        assert fmt in [".stl",".glb"]
        
        # shape.repairMesh()
        
        bpy.ops.object.select_all(action="DESELECT")
        shape.solid.select_set(True)
        bpy.context.view_layer.objects.active = shape.solid
        
        if fmt == ".stl":
            stl_fname=file_ensure_extension(path, ".stl")
            if bpy.app.version <= (4, 1, 0):
                bpy.ops.export_mesh.stl(
                filepath=stl_fname, use_selection=True
                )
            else:
                bpy.ops.wm.stl_export(
                filepath=stl_fname, export_selected_objects=True
                )                
        elif fmt == ".glb":
            bpy.ops.export_scene.gltf(
            filepath=file_ensure_extension(path, ".glb"), use_selection=True
            )
        else:
            assert False

    def export_best(self, shape: BlenderShape, path: Union[str, Path]) -> None:
        self.export(shape=shape,path=path,fmt=".glb")

    def export_stl(self, shape: BlenderShape, path: Union[str, Path]) -> None:
        self.export(shape=shape,path=path,fmt=".stl")

    def export_best_multishapes(
        self,
        shapes: list[BlenderShape],
        assembly_name: str,
        path: Union[str, Path],
    ) -> None:
        bpy.ops.object.select_all(action="DESELECT")

        # Function to assign color to a solid
        def add_material(obj: bpy.types.Object, name: str, color: tuple[int, int, int]):
            mat = bpy.data.materials.new(name=f"{name}_Material")
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (
                color[0]/255,
                color[1]/255,
                color[2]/255,
                1.0,
            )
            obj.data.materials.append(mat)

        # Add shapes to the assembly with assigned colors
        for s in shapes:
            bpy.context.view_layer.objects.active = s.solid
            s.solid.name = s.name
            add_material(s.solid, s.name, s.color)
            s.solid.select_set(True)

        output_file = file_ensure_extension(path, 'GLB')
        bpy.ops.export_scene.gltf(filepath=output_file, export_format='GLB', use_selection=True)

    def sphere(self, r: float) -> BlenderShape:
        return BlenderBall(r, self)

    def box(self, l: float, wth: float, ht: float, center: bool = True) -> BlenderShape:
        if True:
            # bpy.ops operation are supposedly slower than bpy.data
            retval = BlenderBoxOps(l, wth, ht, self)
        else:
            retval = BlenderBoxData(l, wth, ht, self)
        if center:
            return retval
        return retval.mv(-l / 2, -wth / 2, -ht / 2)

    def cone_x(self, h: float, r1: float, r2: float) -> BlenderShape:
        return BlenderConeX(h, r1, r2, self).mv(h / 2, 0, 0)

    def cone_y(self, h: float, r1: float, r2: float) -> BlenderShape:
        return BlenderConeY(h, r1, r2, self).mv(0, h / 2, 0)

    def cone_z(self, h: float, r1: float, r2: float) -> BlenderShape:
        return BlenderConeZ(h, r1, r2, self).mv(0, 0, h / 2)

    def regpoly_extrusion_x(self, ln: float, rad: float, sides: int) -> BlenderShape:
        return BlenderPolyRodX(ln, rad, sides, self)

    def regpoly_extrusion_y(self, ln: float, rad: float, sides: int) -> BlenderShape:
        return BlenderPolyRodY(ln, rad, sides, self)

    def regpoly_extrusion_z(self, ln: float, rad: float, sides: int) -> BlenderShape:
        return BlenderPolyRodZ(ln, rad, sides, self)

    def cylinder_x(self, l: float, rad: float) -> BlenderShape:
        return BlenderRodX(l, rad, self)

    def cylinder_y(self, l: float, rad: float) -> BlenderShape:
        return BlenderRodY(l, rad, self)

    def cylinder_z(self, l: float, rad: float) -> BlenderShape:
        return BlenderRodZ(l, rad, self)
    
    def cylinder_rounded_x(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        stemLen = l - 2 * rad * domeRatio
        rod = self.cylinder_x(stemLen, rad)
        for bx in [stemLen / 2, -stemLen / 2]:
            ball = self.sphere(rad).scale(domeRatio, 1, 1)
            ball <<= (bx, 0, 0)
            rod += ball
        return rod

    def cylinder_rounded_y(self, l: float, rad: float, domeRatio: float = 1) -> Shape:
        stemLen = l - 2 * rad * domeRatio
        rod = self.cylinder_y(stemLen, rad)
        for by in [stemLen / 2, -stemLen / 2]:
            ball = self.sphere(rad).scale(1, domeRatio, 1)
            ball <<= (0, by, 0)
            rod += ball
        return rod
        
    def polygon_extrusion(
        self, path: list[tuple[float, float]], ht: float
    ) -> BlenderShape:
        return BlenderPolyExtrusionZ(path, ht, self)

    def spline_extrusion(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        ht: float,
    ) -> BlenderShape:
        if ht < 0:
            return BlenderLineSplineExtrusionZ(start, path, abs(ht), self).mv(
                0, 0, -abs(ht)
            )
        return BlenderLineSplineExtrusionZ(start, path, ht, self)

    def spline_revolve(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, float, float, float]]],
        deg: float,
    ) -> BlenderShape:
        return BlenderLineSplineRevolveX(start, path, deg, self)

    def regpoly_sweep(
        self, rad: float, path: list[tuple[float, float, float]]
    ) -> BlenderShape:
        return BlenderCirclePolySweep(rad, path, self)

    def text(
        self, txt: str, fontSize: float, tck: float, font: str
    ) -> BlenderShape:
        return BlenderTextZ(txt, fontSize, tck, font, self)

    def genImport(self, infile: str, extrude: float = None) -> BlenderShape:
        return BlenderImport(infile, extrude=extrude)

class BlenderShape(Shape):

    # MAX_DIM = 10000 # for max and min dimensions
    REPAIR_MIN_REZ = 0.005
    REPAIR_LOOPS = 2

    def __init__(self, api: BlenderShapeAPI):
        super().__init__(api)
        self.solid: bpy.types.Object = None

    def findBounds(self) -> tuple[float, float, float, float, float, float]:
        """
        Returns the bounding box of a Blender object in world space as a tuple:
        (minX, maxX, minY, maxY, minZ, maxZ)

        Parameters:
        obj (bpy.types.Object): The Blender object.

        Returns:
        tuple: A tuple with the bounding box limits (minX, maxX, minY, maxY, minZ, maxZ).
        """
        if self.solid.type not in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            raise ValueError(
                f"Object type {self.solid.type} does not support bounding boxes."
            )

        # Get the bounding box in local space
        bbox = self.solid.bound_box

        # Convert to world space by applying the object's transformation matrix
        bbox_world = [self.solid.matrix_world @ Vector(corner) for corner in bbox]

        # Extract the min/max values from the bounding box in world space
        min_x = min([v[0] for v in bbox_world])
        max_x = max([v[0] for v in bbox_world])
        min_y = min([v[1] for v in bbox_world])
        max_y = max([v[1] for v in bbox_world])
        min_z = min([v[2] for v in bbox_world])
        max_z = max([v[2] for v in bbox_world])

        return (min_x, max_x, min_y, max_y, min_z, max_z)

    def cut(self, cutter: BlenderShape) -> BlenderShape:
        if cutter is None:
            return self
        bpy.context.view_layer.objects.active = self.solid
        mod = self.solid.modifiers.new(name="Diff", type="BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter.solid
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.context.view_layer.update()
        return self.repairMesh()

    def dup(self) -> BlenderShape:
        duplicate = copy.copy(self)
        self.solid.select_set(True)
        bpy.context.view_layer.objects.active = self.solid
        bpy.ops.object.duplicate()
        bpy.ops.object.select_all(action="DESELECT")
        duplicate.solid = bpy.context.object
        duplicate.solid.select_set(True)
        return duplicate

    def extrudeZ(self, tck: float) -> BlenderShape:
        if tck <= 0:
            return self
        bpy.ops.object.select_all(action="DESELECT")
        self.solid.select_set(True)
        # origin = self.solid.location
        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.solidify(thickness=tck)
        bpy.ops.object.mode_set(mode="OBJECT")
        # self.solid.location.z = tck
        return self.repairMesh()

    def findNearestEdgeIndex(self, point: tuple[float, float, float]) -> int:
        mesh = self.solid.data
        nearestIdx = -1
        minDist = float("inf")
        pv = Vector(point)
        for edge in mesh.edges:
            v1 = self.solid.matrix_world @ mesh.vertices[edge.vertices[0]].co
            v2 = self.solid.matrix_world @ mesh.vertices[edge.vertices[1]].co
            diff = v2 - v1
            if diff.length == 0:
                continue
            closestPtOnEdge = v1 + diff.normalized() * (
                (pv - v1).dot(diff) / diff.length_squared
            )
            distance = (pv - closestPtOnEdge).length
            if distance < minDist:
                minDist = distance
                nearestIdx = edge.index
        return nearestIdx

    def fillet(
        self,
        nearestPts: list[tuple[float, float, float]],
        rad: float,
    ) -> BlenderShape:
        if rad <= 0:
            return self
        segs = self._smoothing_segments(rad/4)
        bpy.context.view_layer.objects.active = self.solid
        if nearestPts is None or len(nearestPts) == 0:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="EDGE")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.bevel(offset=rad/4, segments=segs)
            bpy.ops.object.mode_set(mode="OBJECT")
        else:
            for p in nearestPts:
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="DESELECT")
                bpy.ops.mesh.select_mode(type="EDGE")
                bpy.ops.object.mode_set(mode="OBJECT")
                idx = self.findNearestEdgeIndex(p)
                if idx >= 0:
                    self.solid.data.edges[idx].select = True
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.bevel(offset=rad/4, segments=segs)
                    bpy.ops.object.mode_set(mode="OBJECT")
        return self.repairMesh()

    def join(self, joiner: BlenderShape) -> BlenderShape:
        if joiner is None:
            return self
        bpy.context.view_layer.objects.active = self.solid
        bpy.ops.object.mode_set(mode="OBJECT")
        mod = self.solid.modifiers.new(name="Union", type="BOOLEAN")
        mod.operation = "UNION"
        mod.object = joiner.solid
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.context.view_layer.update()
        # joiner._remove()
        return self.repairMesh()

    def intersection(self, intersector: BlenderShape) -> BlenderShape:
        if intersector is None:
            return self
        bpy.context.view_layer.objects.active = self.solid
        bpy.ops.object.mode_set(mode="OBJECT")
        mod = self.solid.modifiers.new(name="Intersect", type="BOOLEAN")
        mod.operation = "INTERSECT"
        mod.object = intersector.solid
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.context.view_layer.update()
        # intersector._remove()
        return self.repairMesh()

    def mirror(self, plane: tuple[bool, bool, bool] = (False, True, False)) -> BlenderShape:

        cp = copy.copy(self)
        cp.solid.select_set(True)
        bpy.context.view_layer.objects.active = cp.solid
        bpy.ops.object.duplicate()
        bpy.ops.object.select_all(action="DESELECT")
        dup = bpy.context.object
        dup.select_set(True)

        # shift to one side to avoid cross mirroring
        shift = (
            self.solid.dimensions.x if plane[0] else 0,
            self.solid.dimensions.y if plane[1] else 0,
            self.solid.dimensions.z if plane[2] else 0,
        )
        # dup.location = dup.location + shift
        bpy.ops.transform.translate(
            value=shift,
            use_accurate=True,
            use_automerge_and_split=True,
        )

        bpy.context.view_layer.objects.active = dup
        mirror = bpy.data.objects.new("MirrorAtOrigin", None)
        mirror.location = (0, 0, 0)
        mod = dup.modifiers.new(name="Mirror", type="MIRROR")
        mod.mirror_object = mirror
        mod.use_axis = plane
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.context.view_layer.update()
        cp.solid = dup

        cp = cp.half(plane)  # cut out the original half

        # recover from shift
        # cp.solid.location = cp.solid.location + shift
        dup.select_set(True)
        bpy.ops.transform.translate(
            value=shift,
            use_accurate=True,
            use_automerge_and_split=True,
        )
        return cp.repairMesh()

    def mv(self, x: float, y: float, z: float) -> BlenderShape:
        if x == 0 and y == 0 and z == 0:
            return self
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.ops.transform.translate(
            value=(x, y, z),
            use_accurate=True,
            use_automerge_and_split=True,
        )
        return self

    def _remove(self) -> None:
        bpy.ops.object.select_all(action="DESELECT")
        self.solid.select_set(True)
        bpy.ops.object.delete()

    def repairMesh(self) -> BlenderShape:
        minRez = self.REPAIR_MIN_REZ
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bm = bmesh.from_edit_mesh(self.solid.data)
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        loop = 0
        while non_manifold_edges and loop < self.REPAIR_LOOPS:
            print(
                f"Loop {loop}: found {len(non_manifold_edges)} non-manifold edges. Attempting to fix..."
            )
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.remove_doubles(
                threshold=minRez,
                use_sharp_edge_from_normals=True,
                use_unselected=True,
            )
            bpy.ops.mesh.fill_holes(sides=0)  # 'sides=0' fills all holes
            bpy.ops.mesh.dissolve_degenerate(threshold=minRez)
            bpy.ops.mesh.delete_loose(use_faces=True, use_edges=True, use_verts=True)
            bpy.ops.mesh.normals_make_consistent(inside=True)
            bm = bmesh.from_edit_mesh(self.solid.data)
            non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
            minRez *= 1.4
            loop += 1
        bpy.ops.object.mode_set(mode="OBJECT")
        return self

    def rotate_x(self, ang: float) -> BlenderShape:
        if ang == 0:
            return self
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.ops.transform.rotate(
            value=radians(ang),  # Rotation angle in radians
            orient_axis="X",  # Rotation axis
            constraint_axis=(True, False, False),  # Constrain to X-axis
            orient_type="GLOBAL",  # Orientation type
            use_accurate=True,
        )
        return self

    def rotate_y(self, ang: float) -> BlenderShape:
        if ang == 0:
            return self
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.ops.transform.rotate(
            value=radians(ang),  # Rotation angle in radians
            orient_axis="Y",  # Rotation axis
            constraint_axis=(False, True, False),  # Constrain to Y-axis
            orient_type="GLOBAL",  # Orientation type
            use_accurate=True,
        )
        return self

    def rotate_z(self, ang: float) -> BlenderShape:
        if ang == 0:
            return self
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.ops.transform.rotate(
            value=radians(ang),  # Rotation angle in radians
            orient_axis="Z",  # Rotation axis
            constraint_axis=(False, False, True),  # Constrain to Z-axis
            orient_type="GLOBAL",  # Orientation type
            use_accurate=True,
        )
        return self

    def scale(self, x: float, y: float, z: float) -> BlenderShape:
        if x == 1 and y == 1 and z == 1:
            return self
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        bpy.context.scene.tool_settings.transform_pivot_point = "CURSOR"
        bpy.ops.transform.resize(
            value=(x, y, z),
            constraint_axis=(True, True, True),
            use_accurate=True,
        )
        return self.repairMesh()

    def show(self):
        self.updateMesh()
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)

    def _smoothing_segments(self, dim: float) -> int:
        return ceil(abs(dim) ** 0.5 * self.api.fidelity.smoothing_segments())

    def bbox(self) -> tuple[float, float, float, float, float, float]:
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)

        obj = bpy.context.active_object

        # Get world-space bounding box corners
        world_bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

        # Compute min and max in world space
        minx = min(v.x for v in world_bbox_corners)
        miny = min(v.y for v in world_bbox_corners)
        minz = min(v.z for v in world_bbox_corners)

        maxx = max(v.x for v in world_bbox_corners)
        maxy = max(v.y for v in world_bbox_corners)
        maxz = max(v.z for v in world_bbox_corners)

        return (minx, maxx, miny, maxy, minz, maxz)

class BlenderBall(BlenderShape):
    def __init__(
        self,
        rad: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        segs = ceil(self._smoothing_segments(2 * pi * rad)/2)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rad, segments=segs, ring_count=segs)
        self.solid = bpy.context.object


class BlenderBoxOps(BlenderShape):
    def __init__(
        self,
        ln: float,
        wth: float,
        ht: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        bpy.ops.mesh.primitive_cube_add(size=1)
        self.solid = bpy.context.object
        self.scale(ln, wth, ht)

class BlenderBoxData(BlenderShape):
    def __init__(
        self,
        ln: float,
        wth: float,
        ht: float,
        api: BlenderShapeAPI,
    ):
        """
        Create a box (cube) in Blender using bpy.data interface.

        Args:
            name (str): The name of the box object.
            location (tuple): The (x, y, z) coordinates for the box's location.
            x (float): The width of the box along the X-axis.
            y (float): The depth of the box along the Y-axis.
            z (float): The height of the box along the Z-axis.
        """

        super().__init__(api)

        # Create a new mesh and object
        name="Box"
        mesh = bpy.data.meshes.new(name + "_mesh")
        box_object = bpy.data.objects.new(name, mesh)
        
        # Link the object to the scene collection
        bpy.context.collection.objects.link(box_object)
        
        # Define the vertices and faces of a cube
        half_x, half_y, half_z = ln / 2, wth / 2, ht / 2
        vertices = [
            (-half_x, -half_y, -half_z),  # 0: Bottom-left-back
            (half_x, -half_y, -half_z),  # 1: Bottom-right-back
            (half_x, half_y, -half_z),   # 2: Bottom-right-front
            (-half_x, half_y, -half_z),  # 3: Bottom-left-front
            (-half_x, -half_y, half_z),  # 4: Top-left-back
            (half_x, -half_y, half_z),   # 5: Top-right-back
            (half_x, half_y, half_z),    # 6: Top-right-front
            (-half_x, half_y, half_z),   # 7: Top-left-front
        ]
        faces = [
            (3, 2, 1, 0),  # Bottom face (clockwise)
            (4, 5, 6, 7),  # Top face (clockwise)
            (0, 1, 5, 4),  # Back face (clockwise)
            (1, 2, 6, 5),  # Right face (clockwise)
            (2, 3, 7, 6),  # Front face (clockwise)
            (3, 0, 4, 7),  # Left face (clockwise)
        ]
        edges = []
        # Create the mesh from the defined vertices and faces
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()
        
        # Set the location of the object
        box_object.location = (0, 0, 0)
        # show both sides of the faces
        box_object.data.use_fake_user = True
        self.solid = box_object

class BlenderConeZ(BlenderShape):
    def __init__(
        self,
        ln: float,
        r1: float,
        r2: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        verts = self._smoothing_segments(2 * pi * max(r1, r2))
        bpy.ops.mesh.primitive_cone_add(
            radius1=r1, radius2=r2, depth=ln, vertices=verts
        )
        self.solid = bpy.context.object


class BlenderConeX(BlenderShape):
    def __init__(
        self,
        ln: float,
        r1: float,
        r2: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderConeZ(ln, r1, r2, api).rotate_y(90).solid


class BlenderConeY(BlenderShape):
    def __init__(
        self,
        ln: float,
        r1: float,
        r2: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderConeZ(ln, r1, r2, api).rotate_x(90).solid


class BlenderPolyRodZ(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        sides: int,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        bpy.ops.mesh.primitive_cylinder_add(radius=rad, depth=ln, vertices=sides)
        self.solid = bpy.context.object


class BlenderPolyRodX(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        sides: int,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderPolyRodZ(ln, rad, sides, api).rotate_y(90).solid


class BlenderPolyRodY(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        sides: int,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderPolyRodZ(ln, rad, sides, api).rotate_x(90).solid


class BlenderRodZ(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        verts = self._smoothing_segments(2 * pi * rad)
        bpy.ops.mesh.primitive_cylinder_add(radius=rad, depth=ln, vertices=verts)
        self.solid = bpy.context.object


class BlenderRodX(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderRodZ(ln, rad, api).rotate_y(90).solid


class BlenderRodY(BlenderShape):
    def __init__(
        self,
        ln: float,
        rad: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        self.solid = BlenderRodZ(ln, rad, api).rotate_x(90).solid


class BlenderRod3D(BlenderShape):
    def __init__(
        self,
        start: tuple[float, float, float],
        stop: tuple[float, float, float],
        rad: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        segs = self._smoothing_segments(2 * pi * rad)
        startPt = Vector(start)
        endPt = Vector(stop)
        vec = endPt - startPt
        length = vec.length
        midpoint = (startPt + endPt) / 2
        bpy.ops.mesh.primitive_cylinder_add(
            radius=rad, depth=length, location=midpoint, vertices=segs
        )
        cylinder = bpy.context.object
        z_axis = Vector((0, 0, 1))
        rotation_quat = z_axis.rotation_difference(vec)
        cylinder.rotation_mode = "QUATERNION"
        cylinder.rotation_quaternion = rotation_quat
        bpy.context.view_layer.update()
        self.solid = cylinder


class BlenderPolyExtrusionZ(BlenderShape):
    def __init__(
        self,
        path: list[tuple[float, float]],
        ht: float,
        api: BlenderShapeAPI,
        checkWinding: bool = True,
    ):
        super().__init__(api)
        if checkWinding and not isPathCounterClockwise(path):
            path.reverse()

        mesh = bpy.data.meshes.new(name="Polygon")
        bpy.ops.object.select_all(action="DESELECT")
        bm = bmesh.new()
        for v in path:
            bm.verts.new((v[0], v[1], 0))
        bm.faces.new(bm.verts)
        bm.to_mesh(mesh)
        self.solid = bpy.data.objects.new(name="Polygon_Object", object_data=mesh)
        bpy.context.collection.objects.link(self.solid)
        mesh.update()

        bpy.context.view_layer.objects.active = self.solid
        self.extrudeZ(ht)


class BlenderLineSplineExtrusionZ(BlenderShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, ...]]],
        ht: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        # optimization:instead of detecting winding direction of polypath, detect the winding direction of input line-spline
        polyPath = lineSplineXY(start, path, self._smoothing_segments)
        if not isPathCounterClockwise(simplifyLineSpline(start, path)):
            polyPath.reverse()
        polyExt = BlenderPolyExtrusionZ(polyPath, ht, api, checkWinding=False)
        self.solid = polyExt.solid


class BlenderLineSplineRevolveX(BlenderShape):
    def __init__(
        self,
        start: tuple[float, float],
        path: list[tuple[float, float] | list[tuple[float, ...]]],
        deg: float,
        api: BlenderShapeAPI,
    ):
        super().__init__(api)
        polyPath = lineSplineXY(start, path, self._smoothing_segments)

        mesh = bpy.data.meshes.new(name="Polygon")
        bpy.ops.object.select_all(action="DESELECT")
        bm = bmesh.new()
        for v in polyPath:
            bm.verts.new((v[0], v[1], 0))
        bm.faces.new(bm.verts)
        bm.to_mesh(mesh)
        polyObj = bpy.data.objects.new(name="Polygon_Object", object_data=mesh)

        _, dimY = dimXY(start, path)
        segs = self._smoothing_segments(abs(2 * pi * dimY * min(abs(deg), 360) / 360))
        bpy.ops.object.select_all(action="DESELECT")
        self.solid = polyObj
        bpy.context.collection.objects.link(self.solid)
        bpy.context.view_layer.objects.active = self.solid
        self.solid.select_set(True)
        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        # HACK: spin only produce correct mesh when axis and deg are opposite sign, so forcing it here
        bpy.ops.mesh.spin(axis=(1, 0, 0), angle=radians(-abs(deg)), steps=segs)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        if deg < 0:  # HACK: since spin hack above, mirror if deg is negative
            self.solid = self.mirror((False, False, True)).solid

        self.repairMesh()


class BlenderCirclePolySweep(BlenderShape):
    def __init__(
        self,
        rad: float,
        path: list[tuple[float, float, float]],
        api: BlenderShapeAPI,
    ):
        super().__init__(api)

        # Deselect all existing objects
        bpy.ops.object.select_all(action="DESELECT")

        if len(path) >= 2:

            # Create a curve object for the path
            curve_data = bpy.data.curves.new("sweep_path", type="CURVE")
            curve_data.dimensions = "3D"
            spline = curve_data.splines.new(type="POLY")
            spline.points.add(len(path) - 1)

            # Set the path points
            for i, (x, y, z) in enumerate(path):
                spline.points[i].co = (x, y, z, 1)

            # Create a curve object in the scene
            path_obj = bpy.data.objects.new("SweepPath", curve_data)
            bpy.context.collection.objects.link(path_obj)

            # Create a circle to be used as the profile (bevel object)
            bpy.ops.curve.primitive_bezier_circle_add(radius=rad)
            circle_obj = bpy.context.object
            circle_obj.name = "CircleProfile"

            # Assign the circle as the bevel object for the path
            path_obj.data.bevel_object = circle_obj
            path_obj.data.use_fill_caps = True  # To cap the ends

            # Set the resolution of the circle and the path
            path_obj.data.bevel_resolution = self._smoothing_segments(2 * pi * rad)
            path_obj.data.resolution_u = 1

            # Important: Set curve bevel mode and size
            path_obj.data.bevel_mode = "OBJECT"  # Use the object (circle) as a bevel
            path_obj.data.bevel_depth = 0.0  # Disable default bevel depth

            # Optionally, hide the profile object (Circle)
            circle_obj.hide_set(True)

            bpy.ops.object.mode_set(mode="OBJECT")
            # Make the path object active and selected for conversion
            bpy.context.view_layer.objects.active = path_obj
            path_obj.select_set(True)
            bpy.ops.object.convert(target="MESH")

            # Update the scene to show the result
            bpy.context.view_layer.update()

        self.solid = path_obj
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

        self.repairMesh()


class BlenderTextZ(BlenderShape):
    def __init__(
        self, txt: str, fontSize: float, tck: float, fontName: str, api: BlenderShapeAPI
    ):
        super().__init__(api)
        bpy.ops.object.text_add()
        self.solid = bpy.context.object
        self.solid.data.body = txt
        self.solid.data.size = fontSize
        fontPath = self.api.getFontPath(fontName)
        if fontPath is not None:
            font = bpy.data.fonts.load(filepath=fontPath)
            self.solid.data.font = font
        else:
            print("WARN: font ${fontName} not found, use blender default")
        self.extrudeZ(tck)
        (minX, maxX, minY, maxY, _, _) = self.findBounds()
        self.mv(-(minX + maxX) / 2, -(minY + maxY) / 2, tck)
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

class BlenderImport(BlenderShape):
    def __init__(
        self,
        infile: str,
        extrude: float = None,
        api: BlenderShapeAPI = BlenderShapeAPI,
    ):
        super().__init__(api)
        assert os.path.isfile(infile) or os.path.isdir(
            infile
        ), f"ERROR: file/directory {infile} does not exist!"
        self.infile = infile

        _, fext = os.path.splitext(infile)

        assert (
            fext in ['.stl','.ply','.svg']
        ), f"ERROR: file extension {fext} not supported!"

        if fext in [".stl",".ply"]:
            if bpy.app.version <= (4, 1, 0):
                bpy.ops.import_mesh.stl(filepath=infile)
            else:
                if fext == ".stl":
                    bpy.ops.wm.stl_import(filepath=infile)
                elif fext == ".ply":
                    bpy.ops.wm.ply_import(filepath=infile)
                    
            self.solid = bpy.context.object

        elif fext in [".svg"]:
            bpy.ops.import_curve.svg(filepath=infile)
            self.solid = bpy.context.object
            self.extrudeZ(extrude)

if __name__ == "__main__":
    test_api("blender")
