import zope.interface


class IHandler(zope.interface.Interface):
    def handle(self, record):
        """Persist record to the handler"""


class IRetrieveCapable(zope.interface.Interface):
    def retrieve(self, rules_tree, limit=None):
        """Retrieve records matching conditions from the handler"""


class ICleanupCapable(zope.interface.Interface):
    def cleanup(self, rules_tree, older_than):
        """Delete records matching conditions and older than period from handler"""


class IRequiresHeartbeat(zope.interface.Interface):
    def heartbeat(self):
        """Will be called every second when there are no records"""
