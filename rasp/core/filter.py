from __future__ import unicode_literals
import inspect
from enum import Enum
from typing import List
from collections import defaultdict
from abc import ABCMeta, abstractmethod

from future.utils import with_metaclass

from rasp.utils.log import logger

from rasp.core.rule import RULE_MANAGER, AbstractRule
from rasp.common.config import DEFAULT_FILTER_DIR, Path


class FilterResult(Enum):
    """Filter result enumeration."""

    IGNORE = False
    ALERT = True
    DEFAULT = True


class FilterContext(Enum):
    """Filter context enumeration."""

    CODE = "code"
    COMMAND = "command"
    URL = "url"
    FILE = "file"
    SQL = "sql"
    VAR = "var"
    XXE = "xxe"
    ANY = "any"


class AbstractFilter(with_metaclass(ABCMeta)):
    """Base class for creating a filter."""

    rule = defaultdict(list)
    name = 'AbstractFilter'
    context = FilterContext.ANY
    rule_method = AbstractRule

    def __init__(self):
        logger.info("Filter '{}' is loaded.".format(self.name))
    
    def update_filter_rule(self):
        rule_list = RULE_MANAGER.get_rule_list(self.name)
        self.init_filter_rule(rule_list)
    
    @abstractmethod
    def init_filter_rule(self, rule_list: List[AbstractRule]):
        pass

    @abstractmethod
    def filter(self, message):
        return FilterResult.DEFAULT


class FilterManager(object):
    """Managing filters."""

    filters_context_dict = defaultdict(list)
    filters_name_dict = defaultdict(AbstractFilter)

    def __init__(self, filter_path=None):
        self.load_filters(filter_path)

    def get_filter_define_files(self, filter_paths: List[Path]):
        for filter_path in filter_paths:
            files = [filter_file for filter_file in filter_path.resolve().rglob('*.py')]
            yield from files

    def load_module_from_file(self, filter_file: Path):
        try:
            # Python3
            import importlib.util
            spec = importlib.util.spec_from_file_location(filter_file.stem, filter_file.as_posix())
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except ImportError:
            # Python2
            import imp
            module = imp.load_source(filter_file.stem, filter_file.as_posix())
        
        return module

    def is_filter(self, obj):
        return inspect.isclass(obj) and issubclass(obj, AbstractFilter) and obj is not AbstractFilter
    
    def init_filter(self, filter_class: AbstractFilter) -> AbstractFilter:
        return filter_class()

    def load_filter_from_module(self, module):
        for _, member_obj in inspect.getmembers(module):

            if not self.is_filter(member_obj):
                continue

            filter_instance = self.init_filter(member_obj)
            self.import_filters_dict(filter_instance)

    def import_filters_dict(self, filter_instance: AbstractFilter):
        self.filters_name_dict[filter_instance.name] = filter_instance
        self.filters_context_dict[filter_instance.context].append(filter_instance)

    def load_filters(self, path=None):
        modules = list()
        filter_paths = [DEFAULT_FILTER_DIR, ]

        if path is not None:
            filter_paths.append(path)

        for filter_file in self.get_filter_define_files(filter_paths):
            modules.append(self.load_module_from_file(filter_file))

        for module in modules:
            self.load_filter_from_module(module)
        
    def update_filter(self, filename: str) -> bool:
        module = self.load_module_from_file(Path(filename))
        self.load_filter_from_module(module)

    def get_filters(self, context):
        return self.filters_context_dict[FilterContext.ANY] + self.filters_context_dict[context]
    
    def filter(self, message):
        try:
            filters = self.get_filters(FilterContext(message['context']))
            result = [filter.filter(message).value for filter in filters]
        except Exception as e:
            logger.error("Failed to filter message: {}, due to {}".format(message, e))
            return FilterResult.DEFAULT.value

        return all(result)

FILTER_MANAGER = FilterManager()
