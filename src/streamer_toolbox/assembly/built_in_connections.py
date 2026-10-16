from collections.abc import Callable
from pathlib import Path
from typing import Any

from streamer_toolbox.connections.crowdcontrol_connection import CrowdControlConnection
from streamer_toolbox.connections.discord_connection import DiscordConnection
from streamer_toolbox.connections.firebot_connection import FirebotConnection
from streamer_toolbox.connections.heartrate.heart_rate import HeartRate
from streamer_toolbox.connections.hyperate_connection import HypeRateConnection
from streamer_toolbox.connections.keyboard.pynput_key_listener import PynputKeyListener
from streamer_toolbox.connections.keyboard_connection import KeyboardConnection
from streamer_toolbox.connections.lumia_connection import LumiaConnection
from streamer_toolbox.connections.mixitup_connection import MixItUpConnection
from streamer_toolbox.connections.oauth.oauth_token_store import OAuthTokenStore
from streamer_toolbox.connections.obs_connection import ObsConnection
from streamer_toolbox.connections.pulsoid_connection import PulsoidConnection
from streamer_toolbox.connections.rumble_connection import RumbleConnection
from streamer_toolbox.connections.sammi_connection import SammiConnection
from streamer_toolbox.connections.streamelements_connection import StreamElementsConnection
from streamer_toolbox.connections.streamerbot_connection import StreamerbotConnection
from streamer_toolbox.connections.streamlabs_connection import StreamlabsConnection
from streamer_toolbox.connections.streamsocket_connection import StreamSocketConnection
from streamer_toolbox.connections.tiltify_connection import TiltifyConnection
from streamer_toolbox.connections.tits_connection import TitsConnection
from streamer_toolbox.connections.twitch_connection import TwitchConnection
from streamer_toolbox.connections.veadotube_connection import VeadotubeConnection
from streamer_toolbox.connections.vnyan_connection import VNyanConnection
from streamer_toolbox.connections.voicemod_connection import VoicemodConnection
from streamer_toolbox.connections.vts_connection import VtsConnection
from streamer_toolbox.connections.vtube_studio.vts_position_store import VtsPositionStore
from streamer_toolbox.connections.warudo_connection import WarudoConnection
from streamer_toolbox.connections.youtube_connection import YouTubeConnection
from streamer_toolbox.core.connections.secrets_folder import SecretsFolder
from streamer_toolbox.core.config.obs_config import ObsConfig
from streamer_toolbox.core.events.event_bus import EventBus
from streamer_toolbox.core.files.move_once import move_once
from streamer_toolbox.core.media.mp4_header_probe import Mp4HeaderProbe


class BuiltInConnections:
    """The connections the toolbox brings itself, in the order of their tabs. Each gets its table of
    config/toolbox.toml (tables), the file that keeps its token or secret (in folder, never in git) and the
    EventBus it reports to. A plugin's own connections are added by assemble()."""

    def __init__(self, tables: dict[str, Any], obs: ObsConfig, folder: Path, events: EventBus,
                 secrets: SecretsFolder | None = None,
                 raw: Callable[[str, dict[str, Any]], None] | None = None) -> None:
        self._secrets = secrets or SecretsFolder(folder)
        self._tables = tables
        self._obs = obs
        self._folder = folder
        self._events = events
        self._raw = raw  # a platform's own message, for the event recording

    def build(self, probe: Mp4HeaderProbe, twitch: TwitchConnection, twitch_tokens: OAuthTokenStore,
              mixitup: MixItUpConnection, heart: HeartRate, wants_key: Callable[[str], bool],
              deck: Callable[[], Any]) -> list[Any]:
        """probe reads a video's size for OBS; twitch, mixitup and heart are made by assemble() because other
        parts use them too; wants_key says which keys a flow listens to; deck gives SAMMI the toolbox's deck."""
        tables, obs, folder, events = self._tables, self._obs, self._folder, self._events
        secret = self._secrets.path  # tokens, keys and logins: config/secrets/
        return [
            ObsConnection(obs, probe),
            SammiConnection(tables.get("sammi", {}), deck),
            mixitup,
            VtsConnection(tables.get("vtube_studio", {}), secret("vts_token.txt"),
                          VtsPositionStore(move_once(folder / "vts_positions.toml", folder / "boxes" / "vts"
                                                     / "position" / "positions.toml")), events=events),
            twitch,
            KeyboardConnection(tables.get("keyboard", {}), PynputKeyListener(), events, wants_key),
            StreamElementsConnection(tables.get("streamelements", {}),
                                     secret("streamelements_token.txt"), events),
            StreamlabsConnection(tables.get("streamlabs", {}), secret("streamlabs_token.txt"),
                                 events, raw=self._raw),
            RumbleConnection(tables.get("rumble", {}), secret("rumble_address.txt"), events),
            YouTubeConnection(tables.get("youtube", {}),
                              OAuthTokenStore(secret("youtube_token.json")), events),
            StreamSocketConnection(tables.get("streamsocket", {}), secret("streamsocket_secret.txt"),
                                   events, lambda: (twitch_tokens.load().user_id if twitch_tokens.load() else "")),
            VNyanConnection(tables.get("vnyan", {})),
            WarudoConnection(tables.get("warudo", {})),
            VeadotubeConnection(tables.get("veadotube", {}), events),
            TitsConnection(tables.get("tits", {}), events),
            StreamerbotConnection(tables.get("streamerbot", {}),
                                  secret("streamerbot_password.txt"), events),
            FirebotConnection(tables.get("firebot", {})),
            LumiaConnection(tables.get("lumia", {}), secret("lumia_token.txt"), events),
            VoicemodConnection(tables.get("voicemod", {}), secret("voicemod_key.txt")),
            PulsoidConnection(tables.get("pulsoid", {}), secret("pulsoid_token.txt"), heart),
            HypeRateConnection(tables.get("hyperate", {}), secret("hyperate_key.txt"), heart),
            DiscordConnection(tables.get("discord", {}), secret("discord_webhook.txt")),
            TiltifyConnection(tables.get("tiltify", {}), secret("tiltify_secret.txt"), events),
            CrowdControlConnection(tables.get("crowdcontrol", {}), events),
        ]
