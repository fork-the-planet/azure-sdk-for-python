# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) Python Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
# pylint: disable=wrong-import-position

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._patch import *  # pylint: disable=unused-wildcard-import

from ._operations import ModelsOperations  # type: ignore
from ._operations import Operations  # type: ignore
from ._operations import OrganizationsOperations  # type: ignore
from ._operations import ProjectsOperations  # type: ignore
from ._operations import BranchesOperations  # type: ignore
from ._operations import ComputesOperations  # type: ignore
from ._operations import NeonDatabasesOperations  # type: ignore
from ._operations import NeonRolesOperations  # type: ignore
from ._operations import EndpointsOperations  # type: ignore

from ._patch import __all__ as _patch_all
from ._patch import *
from ._patch import patch_sdk as _patch_sdk

__all__ = [
    "ModelsOperations",
    "Operations",
    "OrganizationsOperations",
    "ProjectsOperations",
    "BranchesOperations",
    "ComputesOperations",
    "NeonDatabasesOperations",
    "NeonRolesOperations",
    "EndpointsOperations",
]
__all__.extend([p for p in _patch_all if p not in __all__])  # pyright: ignore
_patch_sdk()
