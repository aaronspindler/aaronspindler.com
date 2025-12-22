from django.db.backends.postgresql import base


class DatabaseWrapper(base.DatabaseWrapper):
    def check_database_version_supported(self):
        pass

    def _configure_timezone(self, connection):
        return False

    def init_connection_state(self):
        self.connection.autocommit = self.settings_dict.get("AUTOCOMMIT", True)
