import zope.interface


class IDisorderSeeker(zope.interface.Interface):
    def receive_record(self, record):
        """Receive record and probably return disorder(s)"""


class IReplayable(zope.interface.Interface):
    def retrieve_records(self, retriever):
        """Retrieve records to replay and restore disorder on application start"""
