# base of all exceptions related to this project
class FormatsError(Exception):
    ...


class StructClassError(FormatsError):
    ...


class BlockClassError(FormatsError):
    ...
