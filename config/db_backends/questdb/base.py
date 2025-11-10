"""
Custom Django database backend for QuestDB.

QuestDB uses the PostgreSQL wire protocol but reports version 12.3 for
compatibility. Django 5.x requires PostgreSQL 14+, so we skip the version
check for QuestDB connections.
"""

from django.db.backends.postgresql import base


class DatabaseWrapper(base.DatabaseWrapper):
    """
    Custom PostgreSQL wrapper for QuestDB that skips version checking.
    """

    def check_database_version_supported(self):
        """
        Skip PostgreSQL version check for QuestDB.

        QuestDB reports PostgreSQL 12.3 for wire protocol compatibility,
        but Django 5.x requires PostgreSQL 14+. Since QuestDB supports
        the features we need, we skip this check.
        """
        pass
