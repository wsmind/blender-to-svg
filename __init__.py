import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, PointerProperty

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
        bpy.types.Scene.svg_export = PointerProperty(
            name="SVG Export Data",
            type=cls,
        )

    @classmethod
    def unregister(cls):
        del bpy.types.Scene.svg_export


def transform_vertex(co):
    scale = 0.01

    x = co.x * scale + co.y * scale * 0.2
    y = co.z * scale + co.y * scale * 0.2

    return (x * 100 + 256, -y * 100 + 256)


class SvgExportMesh(Operator):
    bl_idname = "blender_to_svg.export"
    bl_label = "Export selected mesh as SVG"
    bl_description = "Projects the selected mesh to 2D from the given camera point of view, and render it as SVG"

    def execute(self, context):
        export_data = context.scene.svg_export

        if export_data.output_path == "":
            self.report({"ERROR"}, "No output path specified")
            return {"CANCELLED"}

        if not context.active_object.select_get():
            self.report({"ERROR"}, "Please select the object to export")
            return {"CANCELLED"}

        if context.active_object.type != "MESH":
            self.report({"ERROR"}, "Active object is not a mesh")
            return {"CANCELLED"}

        mesh = context.active_object.data
        vertices = mesh.vertices

        with open(export_data.output_path, "wt") as f:
            f.write("<?xml version=\"1.0\"?>\n")
            f.write(
                "<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">\n")

            f.write(
                "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\">\n")
            for edge in mesh.edges:
                if edge.use_edge_sharp:
                    v0 = vertices[edge.vertices[0]]
                    v1 = vertices[edge.vertices[1]]

                    v0 = transform_vertex(v0.co)
                    v1 = transform_vertex(v1.co)

                    f.write(
                        f"<line x1=\"{v0[0]}\" y1=\"{v0[1]}\" x2=\"{v1[0]}\" y2=\"{v1[1]}\" style=\"stroke:rgb(0, 0, 0);stroke-width:2\" />\n")
            f.write("</svg>\n")

        return {"FINISHED"}


class SvgExportPanel(Panel):
    bl_label = "SVG Export"
    bl_idname = "SCENE_PT_SvgExport"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        export_data = context.scene.svg_export
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
