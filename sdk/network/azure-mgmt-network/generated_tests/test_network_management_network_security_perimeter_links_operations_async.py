# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.network.aio import NetworkManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer
from devtools_testutils.aio import recorded_by_proxy_async

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestNetworkManagementNetworkSecurityPerimeterLinksOperationsAsync(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(NetworkManagementClient, is_async=True)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_network_security_perimeter_links_get(self, resource_group):
        response = await self.client.network_security_perimeter_links.get(
            resource_group_name=resource_group.name,
            network_security_perimeter_name="str",
            link_name="str",
            api_version="2024-07-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_network_security_perimeter_links_create_or_update(self, resource_group):
        response = await self.client.network_security_perimeter_links.create_or_update(
            resource_group_name=resource_group.name,
            network_security_perimeter_name="str",
            link_name="str",
            parameters={
                "autoApprovedRemotePerimeterResourceId": "str",
                "description": "str",
                "id": "str",
                "localInboundProfiles": ["str"],
                "localOutboundProfiles": ["str"],
                "name": "str",
                "provisioningState": "str",
                "remoteInboundProfiles": ["str"],
                "remoteOutboundProfiles": ["str"],
                "remotePerimeterGuid": "str",
                "remotePerimeterLocation": "str",
                "status": "str",
                "systemData": {
                    "createdAt": "2020-02-20 00:00:00",
                    "createdBy": "str",
                    "createdByType": "str",
                    "lastModifiedAt": "2020-02-20 00:00:00",
                    "lastModifiedBy": "str",
                    "lastModifiedByType": "str",
                },
                "type": "str",
            },
            api_version="2024-07-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_network_security_perimeter_links_begin_delete(self, resource_group):
        response = await (
            await self.client.network_security_perimeter_links.begin_delete(
                resource_group_name=resource_group.name,
                network_security_perimeter_name="str",
                link_name="str",
                api_version="2024-07-01",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_network_security_perimeter_links_list(self, resource_group):
        response = self.client.network_security_perimeter_links.list(
            resource_group_name=resource_group.name,
            network_security_perimeter_name="str",
            api_version="2024-07-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...
