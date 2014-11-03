class AbstractDisorderSeeker(object):
    def __new__(cls, *args, **kwargs):
        disorder_seeker = super(AbstractDisorderSeeker, cls).__new__(cls)
        disorder_seeker.observers = []
        return disorder_seeker

    def add_observer(self, observer, key):
        self.observers.append((observer, key))

    def state_disorder(self, is_disorder, disorder=None):
        if is_disorder is None:
            self.seeker_is_not_functional()
        if is_disorder is True:
            self.there_is_disorder(disorder)
        if is_disorder is False:
            self.there_is_no_disorder(disorder)

    def there_is_disorder(self, disorder):
        for observer, key in self.observers:
            observer.there_is_disorder(key, disorder)

    def there_is_no_disorder(self, disorder):
        for observer, key in self.observers:
            observer.there_is_no_disorder(key, disorder)

    def seeker_is_not_functional(self):
        for observer, key in self.observers:
            observer.seeker_is_not_functional(key)
