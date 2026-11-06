from app import db

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @staticmethod
    def get_value(key, default=None):
        setting = SystemSetting.query.get(key)
        return setting.value if setting else default

    @staticmethod
    def set_value(key, value, description=None):
        setting = SystemSetting.query.get(key)
        if not setting:
            setting = SystemSetting(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        db.session.commit()
        return setting
