import json

class AppConfig:
    def __init__(self, filename):
        self.filename = filename
        self.config = self.load_config()

    def load_config(self):
        with open(self.filename, 'r', encoding='utf-8') as file:
            return json.load(file)

# Usage
app_config = AppConfig('config.json')
print(app_config.config)
