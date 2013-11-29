import zope.interface


class IReceiver(zope.interface.Interface):
    def receive(self):
        """Yield Record's"""
