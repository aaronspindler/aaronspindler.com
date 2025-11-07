class FeeFiFoFundsRouter:
    """
    Database router for the feefifofunds app.
    Routes all feefifofunds models to the 'timescaledb' database.
    """

    route_app_labels = {"feefifofunds"}

    def db_for_read(self, model, **hints):
        """Route read operations for feefifofunds models to timescaledb."""
        if model._meta.app_label in self.route_app_labels:
            return "timescaledb"
        return None

    def db_for_write(self, model, **hints):
        """Route write operations for feefifofunds models to timescaledb."""
        if model._meta.app_label in self.route_app_labels:
            return "timescaledb"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both models are in the feefifofunds app.
        Prevent cross-database relations.
        """
        if obj1._meta.app_label in self.route_app_labels or obj2._meta.app_label in self.route_app_labels:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure feefifofunds models are only migrated to timescaledb database,
        and other models are not migrated to timescaledb.

        Raises an error if someone attempts to migrate feefifofunds to the wrong database
        to prevent silent failures.
        """
        if app_label in self.route_app_labels:
            if db == "timescaledb":
                return True
            elif db == "default":
                from django.core.management.base import CommandError

                raise CommandError(
                    f"\n❌ ERROR: Cannot migrate '{app_label}' to the '{db}' database!\n"
                    f"   The '{app_label}' app uses TimescaleDB and must be migrated to the 'timescaledb' database.\n\n"
                    f"   Please use one of these commands instead:\n"
                    f"   • python manage.py migrate {app_label} --database=timescaledb\n"
                    f"   • python manage.py migrate --database=timescaledb  (for all apps)\n"
                )
            return False
        # For non-feefifofunds apps, don't allow them on timescaledb
        return db != "timescaledb"
