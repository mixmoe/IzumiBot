"""
Template Engine for chatbot message serialization

Referenced Project: https://github.com/alexmic/microtemplates
"""
from .base import Template


def template_rend(template: str, **kwargs) -> str:
    return Template(template).render(**kwargs)
