import abc


class BaseValidator(object):

    @abc.abstractmethod
    def validate(self, *args, **kwargs):
        pass

    def __init__(self, *args, **kwargs):
        self.validate(*args, **kwargs)


class DummyValidator(object):

    def valdiate(self, *args, **kwargs):
        pass
