class AbstractDisorderSeeker(object):
    def __new__(cls, *args, **kwargs):
        disorder_seeker = super(AbstractDisorderSeeker, cls).__new__(cls)
        disorder_seeker.observers = []
        return disorder_seeker

    def add_observer(self, observer):
        self.observers.append(observer)

    def there_is_disorder(self, record):
        for observer in self.observers:
            observer.there_is_disorder(record)

    def there_is_no_disorder(self, record):
        for observer in self.observers:
            observer.there_is_no_disorder(record)

    def seeker_is_not_functional(self):
        for observer in self.observers:
            observer.seeker_is_not_functional()
