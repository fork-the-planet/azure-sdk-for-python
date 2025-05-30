# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from azure.identity import DefaultAzureCredential

from azure.mgmt.network import NetworkManagementClient

"""
# PREREQUISITES
    pip install azure-identity
    pip install azure-mgmt-network
# USAGE
    python network_watcher_connection_monitor_v2_create.py

    Before run the sample, please set the values of the client ID, tenant ID and client secret
    of the AAD application as environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID,
    AZURE_CLIENT_SECRET. For more info about how to get the value, please see:
    https://docs.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal
"""


def main():
    client = NetworkManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id="subid",
    )

    response = client.connection_monitors.begin_create_or_update(
        resource_group_name="rg1",
        network_watcher_name="nw1",
        connection_monitor_name="cm1",
        parameters={
            "properties": {
                "endpoints": [
                    {
                        "name": "vm1",
                        "resourceId": "/subscriptions/96e68903-0a56-4819-9987-8d08ad6a1f99/resourceGroups/NwRgIrinaCentralUSEUAP/providers/Microsoft.Compute/virtualMachines/vm1",
                    },
                    {
                        "filter": {"items": [{"address": "npmuser", "type": "AgentAddress"}], "type": "Include"},
                        "name": "CanaryWorkspaceVamshi",
                        "resourceId": "/subscriptions/96e68903-0a56-4819-9987-8d08ad6a1f99/resourceGroups/vasamudrRG/providers/Microsoft.OperationalInsights/workspaces/vasamudrWorkspace",
                    },
                    {"address": "bing.com", "name": "bing"},
                    {"address": "google.com", "name": "google"},
                ],
                "outputs": [],
                "testConfigurations": [
                    {
                        "name": "testConfig1",
                        "protocol": "Tcp",
                        "tcpConfiguration": {"disableTraceRoute": False, "port": 80},
                        "testFrequencySec": 60,
                    }
                ],
                "testGroups": [
                    {
                        "destinations": ["bing", "google"],
                        "disable": False,
                        "name": "test1",
                        "sources": ["vm1", "CanaryWorkspaceVamshi"],
                        "testConfigurations": ["testConfig1"],
                    }
                ],
            }
        },
    ).result()
    print(response)


# x-ms-original-file: specification/network/resource-manager/Microsoft.Network/stable/2024-07-01/examples/NetworkWatcherConnectionMonitorV2Create.json
if __name__ == "__main__":
    main()
