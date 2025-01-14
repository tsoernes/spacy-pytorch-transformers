# Stubs for torch.nn.modules.padding (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from ..._jit_internal import weak_module, weak_script_method
from .module import Module
from .utils import _ntuple, _pair, _quadruple
from typing import Any

class _ConstantPadNd(Module):
    __constants__: Any = ...
    value: Any = ...
    def __init__(self, value: Any) -> None: ...
    def forward(self, input: Any): ...
    def extra_repr(self): ...

class ConstantPad1d(_ConstantPadNd):
    padding: Any = ...
    def __init__(self, padding: Any, value: Any) -> None: ...

class ConstantPad2d(_ConstantPadNd):
    __constants__: Any = ...
    padding: Any = ...
    def __init__(self, padding: Any, value: Any) -> None: ...

class ConstantPad3d(_ConstantPadNd):
    padding: Any = ...
    def __init__(self, padding: Any, value: Any) -> None: ...

class _ReflectionPadNd(Module):
    __constants__: Any = ...
    def forward(self, input: Any): ...
    def extra_repr(self): ...

class ReflectionPad1d(_ReflectionPadNd):
    padding: Any = ...
    def __init__(self, padding: Any) -> None: ...

class ReflectionPad2d(_ReflectionPadNd):
    padding: Any = ...
    def __init__(self, padding: Any) -> None: ...

class _ReplicationPadNd(Module):
    __constants__: Any = ...
    def forward(self, input: Any): ...
    def extra_repr(self): ...

class ReplicationPad1d(_ReplicationPadNd):
    padding: Any = ...
    def __init__(self, padding: Any) -> None: ...

class ReplicationPad2d(_ReplicationPadNd):
    padding: Any = ...
    def __init__(self, padding: Any) -> None: ...

class ReplicationPad3d(_ReplicationPadNd):
    padding: Any = ...
    def __init__(self, padding: Any) -> None: ...

class ZeroPad2d(ConstantPad2d):
    def __init__(self, padding: Any) -> None: ...
