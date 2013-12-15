import zope.interface


class IPersister(zope.interface.Interface):
    def persist(self, record):
        """Persist record to the storage"""


class IRetriever(zope.interface.Interface):
    def retrieve(self, feed=None, limit=50):
        """Retrieve records matching conditions from the storage"""


class ICleaner(zope.interface.Interface):
    def cleanup(self, feed, older_than):
        """Delete records matching conditions and older than period from storage"""
