# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class RankResponse(Model):
    """A resulting ordered list of actions that result from a rank request.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    :ivar ranking: The calculated ranking for the current request.
    :vartype ranking:
     list[~azure.cognitiveservices.personalizer.models.RankedAction]
    :ivar event_id: The eventId for the round trip from request to response.
    :vartype event_id: str
    :ivar reward_action_id: The action chosen by the Personalizer service.
     This is the action for which to report the reward. This might not be the
     first found in 'ranking' if an action in the request in first position was
     part of the excluded ids.
    :vartype reward_action_id: str
    """

    _validation = {
        "ranking": {"readonly": True},
        "event_id": {"readonly": True, "max_length": 256},
        "reward_action_id": {"readonly": True, "max_length": 256},
    }

    _attribute_map = {
        "ranking": {"key": "ranking", "type": "[RankedAction]"},
        "event_id": {"key": "eventId", "type": "str"},
        "reward_action_id": {"key": "rewardActionId", "type": "str"},
    }

    def __init__(self, **kwargs):
        super(RankResponse, self).__init__(**kwargs)
        self.ranking = None
        self.event_id = None
        self.reward_action_id = None
