class TemplateError(Exception):
    pass


class TemplateContextError(TemplateError):
    def __init__(self, context_var):
        self.context_var = context_var

    def __str__(self):
        return f"cannot resolve {self.context_var}"


class TemplateSyntaxError(TemplateError):
    def __init__(self, error_syntax):
        self.error_syntax = error_syntax

    def __str__(self):
        return f"{self.error_syntax} seems like invalid syntax"
