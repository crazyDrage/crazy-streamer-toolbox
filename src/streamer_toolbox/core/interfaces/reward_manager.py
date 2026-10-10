from abc import ABC, abstractmethod

from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward


class RewardManager(ABC):
    """The channel point rewards, for the Twitch tool: list them, create or change one, delete one. Changing and
    deleting only work for rewards the toolbox made (Twitch's rule); the others fail with Twitch's message."""

    @abstractmethod
    async def list_rewards(self) -> list[TwitchReward]:
        """Every reward of the channel, with by_toolbox set."""

    @abstractmethod
    async def save_reward(self, reward: TwitchReward) -> TwitchReward:
        """Creates it (no id yet) or changes it (has an id); gives it back as Twitch has it now."""

    @abstractmethod
    async def delete_reward(self, reward_id: str) -> None:
        """Deletes it on Twitch (its waiting redeems get their points back)."""
