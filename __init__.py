import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, PointerProperty

from mathutils import Vector

bl_info = {
    "name": "blender-to-svg",
    "author": "Rémi Papillié",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic"
}


class SvgExportSceneData(PropertyGroup):
    output_path: StringProperty(
        name="Output File",
        subtype='FILE_PATH',
        default=""
    )

    @classmethod
    def register(cls):
        bpy.types.Scene.blender_to_svg = PointerProperty(
            name="SVG Export Data",
            type=cls,
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.blender_to_svg


def transform_vertex(render, mvp, co):
    projected_vertex = mvp @ Vector((co.x, co.y, co.z, 1))

    clip_space_vertex = (projected_vertex.x / projected_vertex.w,
                         projected_vertex.y / projected_vertex.w,
                         projected_vertex.z / projected_vertex.w)

    half_width = render.resolution_x * 0.5
    half_height = render.resolution_y * 0.5

    return (
        clip_space_vertex[0] * half_width + half_width,
        -clip_space_vertex[1] * half_height + half_height,
        clip_space_vertex[2],
    )


class Face:
    def __init__(self, points, color):
        self.points = points
        self.color = color
        self.occluders = []

        self.min_bound = list(points[0])
        self.max_bound = list(points[0])
        self.centroid = list(points[0])

        for point in points:
            self.min_bound[0] = min(self.min_bound[0], point[0])
            self.min_bound[1] = min(self.min_bound[1], point[1])
            self.min_bound[2] = min(self.min_bound[2], point[2])
            self.max_bound[0] = max(self.max_bound[0], point[0])
            self.max_bound[1] = max(self.max_bound[1], point[1])
            self.max_bound[2] = max(self.max_bound[2], point[2])

            self.centroid[0] += point[0]
            self.centroid[1] += point[1]
            self.centroid[2] += point[2]

        self.centroid[0] /= len(points)
        self.centroid[1] /= len(points)
        self.centroid[2] /= len(points)

    def compare_depth(self, face):
        # 2D intersection test
        if self.min_bound[0] > face.max_bound[0]:
            return
        if self.max_bound[0] < face.min_bound[0]:
            return
        if self.min_bound[1] > face.max_bound[1]:
            return
        if self.max_bound[1] < face.min_bound[1]:
            return

        # the following should be replaced with a 2D triangle intersection test,
        # non-linear depth interpolation and compare

        # depth compare
        if self.min_bound[2] > face.max_bound[2]:
            self.occluders.append(face)
            return
        if self.max_bound[2] < face.min_bound[2]:
            face.occluders.append(self)
            return

        # bounding boxes intersect, finer heuristic
        if self.centroid[2] > face.centroid[2]:
            self.occluders.append(face)
        else:
            face.occluders.append(self)
        # if self.min_bound[2] > face.min_bound[2]:
        #     self.occluders.append(face)
        # else:
        #     face.occluders.append(self)

    def relative_depth(self):
        # prevent cycles
        known_occluders = set()

        new_occluders = set(self.occluders) - known_occluders
        while len(new_occluders) > 0:
            occluder = new_occluders.pop()
            if occluder == self:
                print("Occlusion cycle detected, output order will be wrong")
                continue
            known_occluders.add(occluder)
            new_occluders |= set(occluder.occluders) - known_occluders

        return len(known_occluders)

    def to_svg(self):
        points = map(
            lambda point: f"{point[0]},{point[1]}", self.points)
        points = " ".join(points)

        # intensity = 255 / (self.relative_depth() * 0.1 + 1)
        # color = (intensity, intensity, intensity)

        color = self.color

        return f"<polygon points=\"{points}\" style=\"fill:rgb({color[0]}, {color[1]}, {color[2]})\" />\n"


class SvgExportMesh(Operator):
    bl_idname = "blender_to_svg.export"
    bl_label = "Export selected mesh as SVG"
    bl_description = "Projects the selected mesh to 2D from the scene camera point of view, and render it as SVG"

    def execute(self, context):
        export_data = context.scene.blender_to_svg
        camera = context.scene.camera

        if export_data.output_path == "":
            self.report({"ERROR"}, "No output path specified")
            return {"CANCELLED"}

        if not context.active_object.select_get():
            self.report({"ERROR"}, "Please select the object to export")
            return {"CANCELLED"}

        if context.active_object.type != "MESH":
            self.report({"ERROR"}, "Active object is not a mesh")
            return {"CANCELLED"}

        if not camera:
            self.report({"ERROR"}, "No active camera found in the scene")
            return {"CANCELLED"}

        render = context.scene.render
        depsgraph = context.scene.view_layers[0].depsgraph

        view_matrix = camera.matrix_world.inverted()
        projection_matrix = camera.calc_matrix_camera(
            depsgraph,
            x=render.resolution_x,
            y=render.resolution_y,
            scale_x=render.pixel_aspect_x,
            scale_y=render.pixel_aspect_y,
        )

        camera_direction = camera.matrix_world @ Vector((0, 0, -1, 0))

        light_direction = Vector((1, -0.4, 0.5))
        light_direction.normalize()

        mvp = projection_matrix @ view_matrix @ context.active_object.matrix_world

        mesh = context.active_object.data
        vertices = mesh.vertices

        projected_vertices = list(map(
            lambda v: transform_vertex(render, mvp, v.co), vertices))

        output_path = bpy.path.abspath(export_data.output_path)
        with open(output_path, "wt") as f:
            f.write("<?xml version=\"1.0\"?>\n")
            f.write(
                "<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">\n")

            f.write(
                f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{render.resolution_x}\" height=\"{render.resolution_y}\">\n")

            for edge in mesh.edges:
                if edge.use_edge_sharp:
                    v0 = projected_vertices[edge.vertices[0]]
                    v1 = projected_vertices[edge.vertices[1]]

                    f.write(
                        f"<line x1=\"{v0[0]}\" y1=\"{v0[1]}\" x2=\"{v1[0]}\" y2=\"{v1[1]}\" style=\"stroke:rgb(0, 0, 0);stroke-width:2\" />\n")

            def make_face(poly):
                points = []
                for loop_index in poly.loop_indices:
                    loop = mesh.loops[loop_index]
                    points.append(projected_vertices[loop.vertex_index])

                diffuse = max(poly.normal.dot(light_direction), 0)
                color = (80 * diffuse, 200 * diffuse, 150 * diffuse)

                return Face(points, color)

            all_faces = []

            for poly in mesh.polygons:
                if poly.normal.dot(camera_direction) > 0:
                    continue

                face = make_face(poly)
                all_faces.append(face)

            for i in range(len(all_faces) - 1):
                for j in range(i + 1, len(all_faces)):
                    all_faces[i].compare_depth(all_faces[j])

            all_faces.sort(key=lambda face: -face.relative_depth())

            for face in all_faces:
                f.write(face.to_svg())

            f.write("</svg>\n")

        return {"FINISHED"}


class SvgExportPanel(Panel):
    bl_label = "SVG Export"
    bl_idname = "SCENE_PT_SvgExport"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        export_data = context.scene.blender_to_svg
        layout = self.layout

        layout.prop(export_data, "output_path")
        layout.operator("blender_to_svg.export")


def register():
    bpy.utils.register_class(SvgExportMesh)
    bpy.utils.register_class(SvgExportSceneData)
    bpy.utils.register_class(SvgExportPanel)


def unregister():
    bpy.utils.unregister_class(SvgExportMesh)
    bpy.utils.unregister_class(SvgExportSceneData)
    bpy.utils.unregister_class(SvgExportPanel)
