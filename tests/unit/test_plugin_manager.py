import unittest
from flask import Flask
from app.core.plugins import PluginManager, Plugin

class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test'
        self.plugin_manager = PluginManager()
        # Reset plugins for each test
        PluginManager._plugins = {}

    def test_register_plugin(self):
        from flask import Blueprint
        bp = Blueprint('test_plugin', __name__)
        plugin = Plugin('test_plugin', bp)
        self.plugin_manager.register(plugin)
        self.assertIn('test_plugin', self.plugin_manager._plugins)

    def test_discover_plugins(self):
        # This is harder to test without actual folders, but we can check if it runs
        self.plugin_manager.discover_plugins(self.app)
        # Should at least not crash

if __name__ == '__main__':
    unittest.main()
