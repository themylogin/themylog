import os
import glob
import zlib
import pickle
import struct
import logging
from time import time as _time
from Queue import Empty, Full
from collections import namedtuple, deque

log = logging.getLogger(__name__)


class SafeQueueQueue(object):
    """Create a queue object with a given maximum size.
    If maxsize is <= 0, the queue size is infinite.
    A copy of Python's Queue.Queue with changes that guarantee locks will
    always be released, even if unexpected exceptions are raised (also, it
    inherits from ``object``).
    """
    def __init__(self, maxsize=0):
        import threading
        self.maxsize = maxsize
        self._init(maxsize)
        # mutex must be held whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the three conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self.mutex = threading.Lock()
        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self.not_empty = threading.Condition(self.mutex)
        # Notify not_full whenever an item is removed from the queue;
        # a thread waiting to put is notified then.
        self.not_full = threading.Condition(self.mutex)
        # Notify all_tasks_done whenever the number of unfinished tasks
        # drops to zero; thread waiting to join() is notified to resume
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.
        Used by Queue consumer threads.  For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.
        If a join() is currently blocking, it will resume when all items
        have been processed (meaning that a task_done() call was received
        for every item that had been put() into the queue).
        Raises a ValueError if called more times than there were items
        placed in the queue.
        """
        self.all_tasks_done.acquire()
        try:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished
        finally:
            self.all_tasks_done.release()

    def join(self):
        """Blocks until all items in the Queue have been gotten and processed.
        The count of unfinished tasks goes up whenever an item is added to the
        queue. The count goes down whenever a consumer thread calls task_done()
        to indicate the item was retrieved and all work on it is complete.
        When the count of unfinished tasks drops to zero, join() unblocks.
        """
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                self.all_tasks_done.wait()
        finally:
            self.all_tasks_done.release()

    def qsize(self):
        """Return the approximate size of the queue (not reliable!)."""
        with self.mutex:
            return self._qsize()

    def empty(self):
        """Return True if the queue is empty, False otherwise (not reliable!)."""
        with self.mutex:
            return not self._qsize()

    def full(self):
        """Return True if the queue is full, False otherwise (not reliable!)."""
        with self.mutex:
            return 0 < self.maxsize == self._qsize()

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.
        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until a free slot is available. If 'timeout' is
        a positive number, it blocks at most 'timeout' seconds and raises
        the Full exception if no free slot was available within that time.
        Otherwise ('block' is false), put an item on the queue if a free slot
        is immediately available, else raise the Full exception ('timeout'
        is ignored in that case).
        """
        self.not_full.acquire()
        try:
            if self.maxsize > 0:
                if not block:
                    if self._qsize() == self.maxsize:
                        raise Full
                elif timeout is None:
                    while self._qsize() == self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                else:
                    endtime = _time() + timeout
                    while self._qsize() == self.maxsize:
                        remaining = endtime - _time()
                        if remaining <= 0.0:
                            raise Full
                        self.not_full.wait(remaining)
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()
        finally:
            self.not_full.release()

    def put_nowait(self, item):
        """Put an item into the queue without blocking.
        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the Full exception.
        """
        return self.put(item, False)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.
        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a positive number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        self.not_empty.acquire()
        try:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a positive number")
            else:
                endtime = _time() + timeout
                while not self._qsize():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._get()
            self.not_full.notify()
            return item
        finally:
            self.not_empty.release()

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.
        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        """
        return self.get(False)

    # Override these methods to implement other queue organizations
    # (e.g. stack or priority queue).
    # These will only be called with appropriate locks held

    # Initialize the queue representation
    def _init(self, maxsize):
        self.queue = deque()

    def _qsize(self, len=len):
        return len(self.queue)

    # Put a new item in the queue
    def _put(self, item):
        self.queue.append(item)

    # Get an item from the queue
    def _get(self):
        return self.queue.popleft()


class ThreadsafeQueueBase(SafeQueueQueue):
    def peek(self, block=True, timeout=None):
        """Return an item from the queue without removing it.
        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until an item is available. If 'timeout' is
        a positive number, it blocks at most 'timeout' seconds and raises
        the Empty exception if no item was available within that time.
        Otherwise ('block' is false), return an item if one is immediately
        available, else raise the Empty exception ('timeout' is ignored
        in that case).
        """
        self.not_empty.acquire()
        try:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a positive number")
            else:
                endtime = _time() + timeout
                while not self._qsize():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._peek()
            self.not_full.notify()
            return item
        finally:
            self.not_empty.release()

    def peek_nowait(self):
        """Return an item from the queue without removing it.
        Only get an item if one is immediately available. Otherwise
        raise the Empty exception.
        """
        return self.peek(False)

    def _init(self, maxsize):
        # Queue.Queue's ``_init`` creates a deque, which we don't necessarily
        # want.
        pass

    def _qsize(self, len=len):
        raise NotImplemented

    def _put(self, item):
        raise NotImplemented

    def _get(self):
        raise NotImplemented


def pack_int(int):
    return struct.pack("!i", int)

def unpack_int(bytes):
    return struct.unpack("!i", bytes)[0]

def pack_uint(uint):
    assert uint >= 0, "%r < 0" %(uint, )
    return struct.pack("!I", uint)

def unpack_uint(bytes):
    return struct.unpack("!I", bytes)[0]


class QueueError(Exception):
    pass


PQRecord = namedtuple("PQRecord", "queue start end type data error")


class JournaledPersistentQueue(object):
    """ A queue that is persisted to a journal file.
        Properties:
        - *Not* thread safe (intended to be used through ``PersistentQueue``,
          which handles thread safety).
        - Records all operations (puts, gets) to a journal file (which will
          only grow).
        - Loading the journal will require time proportional to the number
          of records.
        - Optimized for durability, not throughput
        - Uses the ``_nowait`` suffix on public methods to make sure that
          they are never used in a context where blocking is expected.
        - Each record has the format::
            char type (either ``RECORD_TYPE_JOURNAL`` or ``RECORD_TYPE_ITEM``)
            uint length (of the ``data``)
            char[length] data (see below)
            int crc32 (the ``crc32`` checksum of ``type . length . data``)
          The ``data`` is either a pickled object (when the ``type`` is
          ``RECORD_TYPE_ITEM``) or when the ``type`` is
          ``RECORD_TYPE_JOURNAL``, a ``uint`` which is a reference to the end
          of the last "read" item record.
        - If an error (truncated record or checksum failure) is encountered
          while reading from the journal, a ``log.warning`` message will be
          emitted and all further records will be ignored.
        - Exceptions will only be raised when:
            - The ``create`` flag is specified, but the file already exists
            - The ``create`` flag is not specified but the file does not exist
            - The programmer makes a stupid error (see ``assert`` statements)
        """

    RECORD_TYPE_ITEM = "\x01"
    RECORD_TYPE_JOURNAL = "\x02"

    SERIALIZER = pickle

    def __init__(self, filename, create=False):
        self.filename = filename
        self._peeked = None
        self._file = self._open(create)
        self._initialize()

    def _open(self, create):
        exists = os.path.exists(self.filename)
        if create and exists:
            raise QueueError("refusing to create - file already exists: %r"
                             %(self.filename, ))
        elif not (create or exists):
            raise QueueError("file does not exist: %r" %(self.filename, ))
        mode = create and "w+b" or "r+b"
        return open(self.filename, mode)

    def _initialize(self):
        """ Initializes ``self._read_pos`` (the location of the record
            currently being read from), ``self._write_pos`` (the location where
            future writes should go) and ``self._item_count`` (the number of
            active items in this queue).
            """
        self._file.seek(0)
        self._read_pos = self._file.tell()
        self._write_pos = self._read_pos
        self._item_count = 0
        while True:
            record = self._read_one(self._write_pos)
            if record is None:
                break

            if record.error:
                log.warn("error encountered while loading journal; truncated "
                         "record will be overwritten on the next write "
                         "(error record: %r)", record)
                break

            if record.type == self.RECORD_TYPE_JOURNAL:
                self._read_pos = unpack_uint(record.data)
                self._item_count -= 1

            elif record.type == self.RECORD_TYPE_ITEM:
                self._item_count += 1

            else:
                assert False, "_read_one returned unexpected record type " \
                        "without an error: %r" %(record, )

            self._write_pos = record.end

    def _read_one(self, start):
        """ Reads one record from location ``start``.
            Returns either ``None`` (if ``start`` is the end of the file) or
            an instance of ``PQRecord``.
            If any error is encountered while reading the record (truncation
            or checksum failure), ``PQRecord.error`` will be set. Other fields
            of ``PQRecord`` may also be set, but their values should only
            be used for diagnostics and debugging.
            Note that ``self._read_pos`` is not modified.
            """

        HEADER_LEN = 5
        CHECKSUM_LEN = 4
        self._file.seek(start)
        header = self._file.read(HEADER_LEN)
        header_len = len(header)
        if header_len == 0:
            return None

        if header_len < HEADER_LEN:
            return PQRecord(self, start, None, header[0], header[1:],
                            "truncated header: %r" %(header, ))

        type = header[0]
        if not (type == self.RECORD_TYPE_ITEM or type == self.RECORD_TYPE_JOURNAL):
            return PQRecord(self, start, None, header[0], header[1:],
                            "unexpected record type: %r" %(header, ))

        data_checksum_len = unpack_uint(header[1:]) + CHECKSUM_LEN
        end = start + HEADER_LEN + data_checksum_len
        data_checksum = self._file.read(data_checksum_len)
        if len(data_checksum) != data_checksum_len:
            return PQRecord(self, start, end, type, None, "record truncated")

        data = data_checksum[:-CHECKSUM_LEN]
        checksum = data_checksum[-CHECKSUM_LEN:]
        actual_checksum = pack_int(zlib.crc32(header + data))
        if actual_checksum != checksum:
            return PQRecord(self, start, end, type, data,
                            "checksum failed (%r != %r)"
                            %(checksum, actual_checksum))

        return PQRecord(self, start, end, type, data, None)

    def _write_one(self, type, data, active=True):
        """ Writes one record to ``self._write_pos`` and updates
            ``self._write_pos`` to the end of the new record.
            """
        assert type in [self.RECORD_TYPE_ITEM, self.RECORD_TYPE_JOURNAL], \
                "invalid record type: %r" %(type, )
        self._file.seek(self._write_pos)
        data_len = pack_uint(len(data))
        to_write = type + data_len + data
        to_write += pack_int(zlib.crc32(to_write))
        self._file.write(to_write)
        self._file.flush()
        self._write_pos += len(to_write)

    def _peek(self):
        """ Reads and returns a ``(record, obj)`` tuple, where ``record`` is
            the next ``RECORD_TYPE_ITEM`` record (starting at
            ``self._read_pos``), and ``obj`` is the deserialized object stored
            in that record.
            Raises ``Empty`` if there are no ``RECORD_TYPE_ITEM`` records left
            in the file.
            If an error is encountered, a warning will be logged and further
            records in the file will be truncated.
            """
        if self._peeked is None:
            while True:
                record = self._read_one(self._read_pos)
                if record is None:
                    break
                if record.error:
                    log.warn("error encountered while reading from journal; "
                             "any subsequent records will be ignored: %r",
                             record)
                    self._write_pos = self._read_pos
                    self._item_count = 0
                    record = None
                    break
                if record.type == self.RECORD_TYPE_ITEM:
                    break
                self._read_pos = record.end
            obj = None
        else:
            record, obj = self._peeked

        if record is None:
            raise Empty

        if obj is None:
            obj = self.SERIALIZER.loads(record.data)

        self._peeked = (record, obj)
        return obj, record

    def put_nowait(self, obj):
        data = self.SERIALIZER.dumps(obj)
        self._write_one(self.RECORD_TYPE_ITEM, data)
        self._item_count += 1

    def get_nowait(self):
        obj, record = self._peek()
        self._read_pos = record.end
        self._write_one(self.RECORD_TYPE_JOURNAL, pack_uint(self._read_pos))
        self._item_count -= 1
        self._peeked = None
        return obj

    def peek_nowait(self):
        obj, _ = self._peek()
        return obj

    def qsize(self):
        return self._item_count

    def empty(self):
        return self._item_count == 0

    def filesize(self):
        """ Returns the end of the journal. Note that this will *almost* always
            be the end of the file, but it may be earlier in the file if the file
            contains invalid records.
            """
        return self._write_pos

    def close(self):
        self._file.close()

    def __repr__(self):
        return "<%s %r filesize=%r qsize=%r>" %(
            type(self).__name__, self.filename, self.filesize(), self.qsize(),
        )


class PersistentQueue(ThreadsafeQueueBase):
    """ A thread safe queue that will persist to multiple, rolling, journaled
        queues.
        Properties:
        - Thread safe.
        - Optimized for durability, not throughput.
        - Stores journal files as ``basedir/pq-data-%016x``.
        - Deletes journal files once they are no longer needed.
        - After a journal file has grown larger than ``max_filesize``, no new
          items will be written to it (subsequent writes will go to a new
          journal).
        - The ``qsize()`` will only return ``0`` (the queue is empty) or ``1``
          (the queue is not empty).
        """

    DATAFILE_PREFIX = "pq-data-"
    DATAFILE_TEMPLATE = DATAFILE_PREFIX + "%016x"

    def __init__(self, basedir, max_filesize=1024*1024,
                 queue_class=JournaledPersistentQueue):
        # Because our ``qsize()`` method doesn't return the total size of the
        # queue, setting a ``maxsize`` value here would be redundant.
        super(PersistentQueue, self).__init__(maxsize=0)
        self.basedir = basedir
        self.max_filesize = max_filesize
        self.queue_class = queue_class
        self._initialize()

    def _initialize(self):
        """ Initializes ``_reader`` and ``_writer`` queues, which are used
            by ``_get_reader`` and ``_get_writer`` to track which internal
            queue should be used to handle reads and writes. """
        if not os.path.exists(self.basedir):
            os.mkdir(self.basedir)

        self._load_data_files()

        if len(self._data_files) == 0:
            self._serial = 0
            self._writer = self._create_queue()
            self._reader = self._writer
        else:
            writer_filepath = self._data_files.pop()
            writer_filename = os.path.basename(writer_filepath)
            self._serial = int(writer_filename[len(self.DATAFILE_PREFIX):], 16)
            self._writer = self._load_queue(writer_filepath)
            if len(self._data_files) > 0:
                self._reader = self._load_queue(self._data_files.popleft())
            else:
                self._reader = self._writer

    def _load_data_files(self):
        """ Loads ``self._data_files``.
        
            ``self._data_files`` is an ordered deque of the available data
            files that are not currently being read from or written to.
            
            When ``self._writer`` fills up, the file it was writing to will be
            appended to ``self._data_files`` and a new writer will be created
            which will be backed by a new data file.
            When ``self._reader`` reaches the end of the file it is working
            with, the left-most file in ``self._data_files`` will be shifted
            off and read from.
            """
        data_files = glob.glob(self._path(self.DATAFILE_PREFIX + "*"))
        data_files.sort()
        self._data_files = deque(data_files)

    def _path(self, *parts):
        """ Returns a path relative to ``self.basedir``. """
        return os.path.join(self.basedir, *parts)

    def _load_queue(self, filename):
        """ Loads the queue from ``filename``. """
        return self.queue_class(filename)

    def _create_queue(self):
        """ Creates and returns a new queue. """
        self._serial += 1
        filename = self._path(self.DATAFILE_TEMPLATE %(self._serial, ))
        log.info("creating new queue at %r", filename)
        return self.queue_class(filename, create=True)

    def _get_reader(self):
        """ Returns the queue which should be read from. """
        while self._reader is not self._writer and self._reader.empty():
            self._reader.close()
            os.unlink(self._reader.filename)
            if len(self._data_files) > 0:
                self._reader = self._load_queue(self._data_files.popleft())
            else:
                self._reader = self._writer
        return self._reader

    def _get_writer(self):
        """ Returns the queue which should be written to. """
        if self._writer.filesize() > self.max_filesize:
            if self._reader is not self._writer:
                self._writer.close()
                self._data_files.append(self._writer.filename)
            self._writer = self._create_queue()
        return self._writer

    def _peek(self):
        return self._get_reader().peek_nowait()

    def _get(self):
        return self._get_reader().get_nowait()

    def _put(self, obj):
        return self._get_writer().put_nowait(obj)

    def _qsize(self):
        """ Returns ``0`` if a call to ``get`` will block, otherwise returns
            ``1``.
            This is done because it would be very slow to load and read all
            the data files, and ``qsize`` is normally only used to determine
            if the queue is empty.
            """
        return self._get_reader().qsize() > 0 and 1 or 0

    def close(self):
        self._reader.close()
        if self._reader is not self._writer:
            self._writer.close()
