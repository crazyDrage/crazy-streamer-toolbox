from abc import ABC, abstractmethod


class MessageInbox(ABC):
    """Where a program's messages come IN to the toolbox (his round 95, Warudo): the program connects to

        ws://<toolbox>/connections/<connection id>/in/<type>?key=<key>

    and every text it sends there arrives in received(). The type is in the address so one program can keep
    several lines open at once, one per kind of message (his 11-21: "to keep it global"). A type that connected
    once, or that he added by hand (add_type: VNyan only connects when it sends, his 11-22), is known
    (known_types) until it is removed (forget); the trigger `<connection id>.message` offers the
    known ones. A connection that takes messages gives its inbox through Connection.inbox(); a plugin's
    connection can do the same."""

    @abstractmethod
    def refusal(self, key: str) -> str:
        """Why a line with this key is not let in (a wrong key, switched off); "" = welcome."""

    @abstractmethod
    def opened(self, kind: str) -> None:
        """A line of this type came in (from now on the type is known; the tab shows it as live)."""

    @abstractmethod
    def received(self, kind: str, text: str) -> None:
        """One message on a line of this type."""

    @abstractmethod
    def closed(self, kind: str) -> None:
        """A line of this type went away."""

    @abstractmethod
    def known_types(self) -> list[str]:
        """Every type that connected at least once and wasn't removed, sorted."""

    @abstractmethod
    def live_types(self) -> list[str]:
        """The types whose lines are open now, sorted."""

    @abstractmethod
    def add_type(self, kind: str) -> None:
        """Makes a type known before it ever connected (the tab's Add button)."""

    @abstractmethod
    def forget(self, kind: str) -> None:
        """Removes a known type (it comes back when it connects again)."""
