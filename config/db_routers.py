class FeeFiFoFundsQuestDBRouter:
    route_app_labels = {"feefifofunds"}
    questdb_models = {"assetprice", "trade"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            if model._meta.model_name in self.questdb_models:
                return "questdb"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            if model._meta.model_name in self.questdb_models:
                return "questdb"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label in self.route_app_labels or obj2._meta.app_label in self.route_app_labels:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            if model_name in self.questdb_models:
                return False
            if db == "default":
                return True
            return False
        return db != "questdb"
