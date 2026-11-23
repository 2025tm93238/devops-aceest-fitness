"""Single source of truth for the application version.

Follows Semantic Versioning (MAJOR.MINOR.PATCH). The same value is used for the
git tag (``v<version>``) and the Docker image tag, so a running container can
always be traced back to the exact commit it was built from.
"""

__version__ = "3.0.1"
