import zope.interface


class IPersister(zope.interface.Interface):
    def persist(self, record):
        """Persist record to the storage"""


class IRetriever(zope.interface.Interface):
    def retrieve(self, feed=None, limit=50):
        """Retrieve records matching conditions from the storage"""
