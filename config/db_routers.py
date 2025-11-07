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
        """
        if app_label in self.route_app_labels:
            return db == "timescaledb"
        return db != "timescaledb"
