import json
import xml.etree.ElementTree as ET

import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension


import wit_world
from wit_world.imports import host
from wit_world.imports.types import Context, Permission


class WitWorld(wit_world.WitWorld):
    def on_action(
        self,
        name: str,
        value: str,
        _context: Context | None,
        permission: Permission,
    ) -> str:
        if name == "config.save":
            if permission != Permission.EDIT:
                print("Trying to change field in non-edit mode")
                return ""
            action_value = json.loads(value)
            markdown_content = action_value["markdown_content"]
            header_start_level = (
                json.loads(host.get_field("header_start_level", None)) or 2
            )
            rendered_html = md2html(markdown_content, header_start_level - 1)
            host.set_field("markdown_content", json.dumps(markdown_content), None)
            host.set_field("rendered_html", json.dumps(rendered_html), None)
            host.send_event(
                "fields.change.markdown_content",
                json.dumps(markdown_content),
                None,
                Permission.EDIT,
            )
            host.send_event(
                "fields.change.rendered_html",
                json.dumps(rendered_html),
                None,
                Permission.EDIT,
            )
        return ""

    def get_state(
        self,
        _context: Context,
        permission: Permission,
    ) -> str:
        markdown_content = json.loads(host.get_field("markdown_content", None))
        rendered_html = json.loads(host.get_field("rendered_html", None))
        state = {"rendered_html": rendered_html}
        if permission == Permission.EDIT:
            state["markdown_content"] = markdown_content

        return json.dumps(state)


def md2html(md: str, offset: int) -> str:
    """
    Convert markdown to html with an offset in the heading levels. E.g: with offset=1,
    the top-level heading will be <h2>.
    """
    return markdown.markdown(md, extensions=[HeadingOffsetExtension(offset)])


class HeadingOffset(Treeprocessor):
    def __init__(self, md: markdown.Markdown, offset: int = 1) -> None:
        super().__init__(md)
        self.offset = offset

    def run(self, root: ET.Element) -> None:
        for el in root.iter():
            if el.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(el.tag[1]) + self.offset
                el.tag = f"h{min(level, 6)}"


class HeadingOffsetExtension(Extension):
    def __init__(self, offset: int) -> None:
        super().__init__()
        self.offset = offset

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        md.treeprocessors.register(
            HeadingOffset(md, offset=self.offset), "heading_offset", 0
        )
