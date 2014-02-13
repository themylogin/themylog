class AbstractDisorderSeeker(object):
    def __new__(cls, *args, **kwargs):
        disorder_seeker = super(AbstractDisorderSeeker, cls).__new__(cls)
        disorder_seeker.observers = []
        return disorder_seeker

    def add_observer(self, observer, key):
        self.observers.append((observer, key))

    def there_is_disorder(self, reason):
        for observer, key in self.observers:
            observer.there_is_disorder(key, reason)

    def there_is_no_disorder(self, reason):
        for observer, key in self.observers:
            observer.there_is_no_disorder(key, reason)

    def seeker_is_not_functional(self):
        for observer, key in self.observers:
            observer.seeker_is_not_functional(key)
