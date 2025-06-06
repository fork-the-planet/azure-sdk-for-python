# --------------------------------------------------------------------------
#
# Copyright (c) Microsoft Corporation. All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# --------------------------------------------------------------------------
"""Common functions shared by both the sync and the async decorators."""
from contextlib import contextmanager
from typing import Any, Optional, Callable, Type, Generator
import warnings

from ._abstract_span import AbstractSpan
from ..instrumentation import get_tracer
from ..settings import settings


__all__ = [
    "change_context",
    "with_current_context",
]


def get_function_and_class_name(func: Callable, *args: object) -> str:
    """
    Given a function and its unamed arguments, returns class_name.function_name. It assumes the first argument
    is `self`. If there are no arguments then it only returns the function name.

    :param func: the function passed in
    :type func: callable
    :param args: List of arguments passed into the function
    :type args: list
    :return: The function name with the class name
    :rtype: str
    """
    try:
        return func.__qualname__
    except AttributeError:
        if args:
            return "{}.{}".format(args[0].__class__.__name__, func.__name__)
        return func.__name__


@contextmanager
def change_context(span: Optional[AbstractSpan]) -> Generator:
    """Execute this block inside the given context and restore it afterwards.

    This does not start and ends the span, but just make sure all code is executed within
    that span.

    If span is None, no-op.

    :param span: A span
    :type span: AbstractSpan
    :rtype: contextmanager
    :return: A context manager that will run the given span in the new context
    """
    span_impl_type = settings.tracing_implementation()
    if span_impl_type is None or span is None:
        yield
    else:

        try:
            with span_impl_type.change_context(span):
                yield
        except AttributeError:
            # This plugin does not support "change_context"
            warnings.warn(
                'Your tracing plugin should be updated to support "change_context"',
                DeprecationWarning,
            )
            original_span = span_impl_type.get_current_span()
            try:
                span_impl_type.set_current_span(span)
                yield
            finally:
                span_impl_type.set_current_span(original_span)


def with_current_context(func: Callable) -> Any:
    """Passes the current spans to the new context the function will be run in.

    :param func: The function that will be run in the new context
    :type func: callable
    :return: The func wrapped with correct context
    :rtype: callable
    """
    if not settings.tracing_enabled():
        return func

    span_impl_type: Optional[Type[AbstractSpan]] = settings.tracing_implementation()
    if span_impl_type:
        return span_impl_type.with_current_context(func)

    tracer = get_tracer()
    if not tracer:
        return func
    return tracer.with_current_context(func)
