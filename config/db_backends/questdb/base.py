"""
Custom Django database backend for QuestDB.

QuestDB uses the PostgreSQL wire protocol but reports version 12.3 for
compatibility. Django 5.x requires PostgreSQL 14+, and QuestDB doesn't
support all PostgreSQL functions (like set_config for timezone).

This backend skips unsupported operations while maintaining compatibility
for the features we actually use (SELECT, INSERT, basic queries).
"""

from django.db.backends.postgresql import base


class DatabaseWrapper(base.DatabaseWrapper):
    """
    Custom PostgreSQL wrapper for QuestDB that skips unsupported operations.
    """

    def check_database_version_supported(self):
        """
        Skip PostgreSQL version check for QuestDB.

        QuestDB reports PostgreSQL 12.3 for wire protocol compatibility,
        but Django 5.x requires PostgreSQL 14+. Since QuestDB supports
        the features we need, we skip this check.
        """
        pass

    def _configure_timezone(self, connection):
        """
        Skip timezone configuration for QuestDB.

        QuestDB doesn't support set_config() function used by Django
        to set the session timezone. QuestDB always uses UTC, which
        matches Django's default behavior, so this is safe to skip.
        """
        return False

    def init_connection_state(self):
        """
        Initialize connection state, skipping QuestDB-incompatible operations.
        """
        self.connection.autocommit = self.settings_dict.get("AUTOCOMMIT", True)
