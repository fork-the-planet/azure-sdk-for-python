# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from azure.identity import DefaultAzureCredential

from azure.mgmt.recoveryservicesbackup.activestamp import RecoveryServicesBackupClient

"""
# PREREQUISITES
    pip install azure-identity
    pip install azure-mgmt-recoveryservicesbackup
# USAGE
    python protection_policies_create_or_update_hardened.py

    Before run the sample, please set the values of the client ID, tenant ID and client secret
    of the AAD application as environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID,
    AZURE_CLIENT_SECRET. For more info about how to get the value, please see:
    https://docs.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal
"""


def main():
    client = RecoveryServicesBackupClient(
        credential=DefaultAzureCredential(),
        subscription_id="00000000-0000-0000-0000-000000000000",
    )

    response = client.protection_policies.create_or_update(
        vault_name="swaggertestvault",
        resource_group_name="SwaggerTestRg",
        policy_name="newPolicyV2",
        parameters={
            "properties": {
                "backupManagementType": "AzureStorage",
                "schedulePolicy": {
                    "schedulePolicyType": "SimpleSchedulePolicy",
                    "scheduleRunFrequency": "Daily",
                    "scheduleRunTimes": ["2023-07-18T09:30:00.000Z"],
                },
                "timeZone": "UTC",
                "vaultRetentionPolicy": {
                    "snapshotRetentionInDays": 5,
                    "vaultRetention": {
                        "dailySchedule": {
                            "retentionDuration": {"count": 30, "durationType": "Days"},
                            "retentionTimes": ["2023-07-18T09:30:00.000Z"],
                        },
                        "monthlySchedule": {
                            "retentionDuration": {"count": 60, "durationType": "Months"},
                            "retentionScheduleDaily": None,
                            "retentionScheduleFormatType": "Weekly",
                            "retentionScheduleWeekly": {"daysOfTheWeek": ["Sunday"], "weeksOfTheMonth": ["First"]},
                            "retentionTimes": ["2023-07-18T09:30:00.000Z"],
                        },
                        "retentionPolicyType": "LongTermRetentionPolicy",
                        "weeklySchedule": {
                            "daysOfTheWeek": ["Sunday"],
                            "retentionDuration": {"count": 12, "durationType": "Weeks"},
                            "retentionTimes": ["2023-07-18T09:30:00.000Z"],
                        },
                        "yearlySchedule": {
                            "monthsOfYear": ["January"],
                            "retentionDuration": {"count": 10, "durationType": "Years"},
                            "retentionScheduleDaily": None,
                            "retentionScheduleFormatType": "Weekly",
                            "retentionScheduleWeekly": {"daysOfTheWeek": ["Sunday"], "weeksOfTheMonth": ["First"]},
                            "retentionTimes": ["2023-07-18T09:30:00.000Z"],
                        },
                    },
                },
                "workLoadType": "AzureFileShare",
            }
        },
    )
    print(response)


# x-ms-original-file: specification/recoveryservicesbackup/resource-manager/Microsoft.RecoveryServices/stable/2025-02-01/examples/AzureStorage/ProtectionPolicies_CreateOrUpdate_Hardened.json
if __name__ == "__main__":
    main()
