from typing import List, Optional, Type

from . import syntax
from .exceptions import TemplateError, TemplateSyntaxError


class Compiler(object):
    def __init__(self, template_string: str):
        self.template_string = template_string

    @property
    def fragments(self):
        return [
            syntax.Fragment(fragment)
            for fragment in filter(
                lambda text: text,
                syntax.TOKEN_SEPERATOR.split(self.template_string),
            )
        ]

    def compile(self):
        root = syntax.Root()
        scope_stack: List[syntax.Node] = [root]
        for fragment in self.fragments:
            if not scope_stack:
                raise TemplateError("nesting issues")
            *_, parent_scope = scope_stack
            if fragment.type is syntax.FragmentType.CLOSE_BLOCK:
                parent_scope.exit_scope()
                scope_stack.pop()
                continue
            new_node = self.create_node(fragment, parent_scope)
            parent_scope.children.append(new_node)
            if new_node.creates_scope:
                scope_stack.append(new_node)
                new_node.enter_scope()
        return root

    def create_node(
        self,
        fragment: syntax.Fragment,
        parent: Optional[syntax.Node] = None,
    ) -> syntax.Node:
        node_class: Optional[Type[syntax.Node]] = None
        if fragment.type is syntax.FragmentType.TEXT:
            node_class = syntax.Text
        elif fragment.type is syntax.FragmentType.VAR:
            node_class = syntax.Variable
        elif fragment.type is syntax.FragmentType.OPEN_BLOCK:
            cmd, *_ = fragment.clean.split()
            if cmd == "each":
                node_class = syntax.Each
            elif cmd == "if":
                node_class = syntax.If
            elif cmd == "else":
                node_class = syntax.Else
            elif cmd == "call":
                node_class = syntax.Call
        if node_class is None:
            raise TemplateSyntaxError(fragment)
        return node_class(fragment, parent=parent)


class Template(object):
    def __init__(
        self,
        contents: str,
        filters: Optional[List[syntax.T_Filter]] = None,
        default_filter: Optional[str] = None,
    ):
        self.contents = contents
        self.root = Compiler(contents).compile()
        self.configs: syntax.RootContext = {
            "_filters": {filter.__name__: filter for filter in (filters or [])},
            "_default_filter": default_filter,
        }

    def render(self, **kwargs):
        context: syntax.RootContext = {**kwargs, **self.configs}  # type:ignore
        return self.root.render(context)
