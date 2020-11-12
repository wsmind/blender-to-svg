import bpy
from bpy.types import Operator

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


def transform_vertex(co):
    scale = 0.01

    x = co.x * scale + co.y * scale * 0.2
    y = co.z * scale + co.y * scale * 0.2

    return (x * 100 + 256, -y * 100 + 256)


class PlopTest(Operator):
    bl_idname = "blender_to_svg.export"
    bl_label = "Plop Test"

    def execute(self, context):
        mesh = context.active_object.data
        vertices = mesh.vertices

        with open("D:/tests/blender-to-svg/plop.svg", "wt") as f:
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


def register():
    bpy.utils.register_class(PlopTest)


def unregister():
    bpy.utils.unregister_class(PlopTest)
