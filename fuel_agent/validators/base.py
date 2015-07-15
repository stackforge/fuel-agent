import abc

import six

from fuel_agent import errors
from fuel_agent.openstack.common import log as logging

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseValidator(object):

    @abc.abstractmethod
    def validate(self, *args, **kwargs):
        pass

    def __init__(self, *args, **kwargs):
        self.validate(*args, **kwargs)

    @classmethod
    def raise_error(self, message):
        error = errors.WrongPartitionSchemeError(message)
        LOG.exception(error)
        raise error


class DummyValidator(object):

    def valdiate(self, *args, **kwargs):
        pass
