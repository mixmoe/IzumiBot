"""
Template Engine for OneBot v11 Specification

Referenced Project: https://github.com/alexmic/microtemplates
"""
from .base import Template  # noqa:F401


def template_rend(template: str, **kwargs) -> str:
    return Template(template).render(**kwargs)
