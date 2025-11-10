class FeeFiFoFundsQuestDBRouter:
    """
    Database router for the feefifofunds app (hybrid approach).

    - Asset model: PostgreSQL (default database)
    - AssetPrice and Trade models: QuestDB (questdb database)

    Time-series models (AssetPrice, Trade) use managed=False and are created
    manually in QuestDB via setup_questdb_schema management command.
    """

    route_app_labels = {"feefifofunds"}
    questdb_models = {"assetprice", "trade"}

    def db_for_read(self, model, **hints):
        """Route read operations for time-series models to QuestDB."""
        if model._meta.app_label in self.route_app_labels:
            if model._meta.model_name in self.questdb_models:
                return "questdb"
        return None

    def db_for_write(self, model, **hints):
        """Route write operations for time-series models to QuestDB."""
        if model._meta.app_label in self.route_app_labels:
            if model._meta.model_name in self.questdb_models:
                return "questdb"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations within the same database.
        Note: AssetPrice and Trade don't have ForeignKey relationships due to QuestDB limitations.
        """
        if obj1._meta.app_label in self.route_app_labels or obj2._meta.app_label in self.route_app_labels:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Control migrations for feefifofunds app:
        - Asset model: Migrates to default database
        - AssetPrice and Trade models: Never migrate (managed=False, created manually in QuestDB)
        """
        if app_label in self.route_app_labels:
            # Time-series models are managed=False, never migrate them
            if model_name in self.questdb_models:
                return False
            # Asset model goes to default database
            if db == "default":
                return True
            return False
        # For non-feefifofunds apps, don't allow them on questdb
        return db != "questdb"
