"""The link creation use case (story P1-01).

Collision handling lives here rather than in the generator because uniqueness is a
property of the *repository*, not of a generated value. Keeping them apart is what lets
Phase 4's custom-alias flow reuse this collision logic without a generator at all.
"""

from __future__ import annotations

from urlshortener.link_management.application.dto.create_link_command import (
    CreateLinkCommand,
)
from urlshortener.link_management.application.dto.link_view import LinkView
from urlshortener.link_management.domain.errors import (
    InvalidShortCode,
    ShortCodeGenerationExhausted,
)
from urlshortener.link_management.domain.model.link import Link
from urlshortener.link_management.domain.ports.link_repository import LinkRepository
from urlshortener.link_management.domain.ports.short_code_generator import (
    ShortCodeGenerator,
)
from urlshortener.link_management.domain.value_objects.destination_url import (
    DestinationUrl,
)
from urlshortener.link_management.domain.value_objects.short_code import ShortCode
from urlshortener.shared_kernel.logging.structured_logging import get_logger
from urlshortener.shared_kernel.time.clock import Clock

logger = get_logger(__name__)


class LinkCreationService:
    """Turns a destination URL into a persisted, uniquely addressable short link."""

    def __init__(
        self,
        link_repository: LinkRepository,
        short_code_generator: ShortCodeGenerator,
        clock: Clock,
        short_url_base: str,
        max_attempts: int,
    ) -> None:
        self._link_repository = link_repository
        self._short_code_generator = short_code_generator
        self._clock = clock
        self._short_url_base = short_url_base
        self._max_attempts = max_attempts

    async def create_link(self, command: CreateLinkCommand) -> LinkView:
        """Persist a new link and return its short code and full short URL.

        Raises ``InvalidDestinationUrl`` if the destination is not an absolute http(s)
        URL, and ``ShortCodeGenerationExhausted`` if every permitted attempt collided.
        """
        destination_url = DestinationUrl(command.long_url)
        for attempt in range(1, self._max_attempts + 1):
            link = await self._try_claim(destination_url, attempt)
            if link is not None:
                return self._to_view(link)
        raise ShortCodeGenerationExhausted(
            f"no free short code after {self._max_attempts} attempts"
        )

    async def _try_claim(
        self, destination_url: DestinationUrl, attempt: int
    ) -> Link | None:
        """Return the persisted link, or ``None`` if this attempt collided."""
        short_code = self._short_code_generator.generate()
        if await self._link_repository.exists_by_short_code(short_code):
            self._log_collision(short_code, attempt, "already_taken")
            return None
        link = Link(
            short_code=short_code,
            destination_url=destination_url,
            created_at=self._clock.now(),
        )
        try:
            await self._link_repository.add(link)
        except InvalidShortCode:
            # The check-then-insert window is not atomic: a concurrent creator can take
            # the code between exists_by_short_code() and add(). That is a collision,
            # not a caller error.
            self._log_collision(short_code, attempt, "lost_insert_race")
            return None
        return link

    def _log_collision(self, short_code: ShortCode, attempt: int, reason: str) -> None:
        logger.info(
            "short_code_collision",
            extra={
                "short_code": short_code.value,
                "attempt": attempt,
                "max_attempts": self._max_attempts,
                "reason": reason,
            },
        )

    def _to_view(self, link: Link) -> LinkView:
        code = link.short_code.value
        return LinkView(
            short_code=code,
            short_url=f"{self._short_url_base.rstrip('/')}/{code}",
        )
