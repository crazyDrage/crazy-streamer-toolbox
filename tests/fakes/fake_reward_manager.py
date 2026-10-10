from dataclasses import replace

from streamer_toolbox.connections.twitch.twitch_reward import TwitchReward
from streamer_toolbox.core.interfaces.reward_manager import RewardManager


class FakeRewardManager(RewardManager):
    """Rewards kept in a list. Like Twitch, only by_toolbox rewards can be changed or deleted."""

    def __init__(self, rewards: list[TwitchReward] | None = None) -> None:
        self.rewards = list(rewards or [])

    async def list_rewards(self) -> list[TwitchReward]:
        return list(self.rewards)

    async def save_reward(self, reward: TwitchReward) -> TwitchReward:
        if not reward.id:
            saved = replace(reward, id=f"r{len(self.rewards) + 1}", by_toolbox=True)
            self.rewards.append(saved)
            return saved
        index = next(i for i, r in enumerate(self.rewards) if r.id == reward.id)
        if not self.rewards[index].by_toolbox:
            raise PermissionError("The ID in id must be a reward created by client")
        self.rewards[index] = reward
        return reward

    async def delete_reward(self, reward_id: str) -> None:
        reward = next(r for r in self.rewards if r.id == reward_id)
        if not reward.by_toolbox:
            raise PermissionError("The ID in id must be a reward created by client")
        self.rewards.remove(reward)
