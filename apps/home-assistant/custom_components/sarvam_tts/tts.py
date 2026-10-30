"""Sarvam AI text-to-speech platform (Bulbul models)."""

from __future__ import annotations

import base64
import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.components.tts import PLATFORM_SCHEMA, Provider, TtsAudioType
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

API_URL = "https://api.sarvam.ai/text-to-speech"
MAX_CHARS = 2500
TIMEOUT = aiohttp.ClientTimeout(total=30)

CONF_LANGUAGE = "language"
CONF_MODEL = "model"
CONF_SPEAKER = "speaker"
CONF_PACE = "pace"
CONF_SAMPLE_RATE = "sample_rate"

SUPPORTED_LANGUAGES = [
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
]
SUPPORTED_OPTIONS = [CONF_MODEL, CONF_SPEAKER, CONF_PACE]
DEFAULTS: dict[str, Any] = {
    CONF_LANGUAGE: "kn-IN",
    CONF_MODEL: "bulbul:v4-flash",
    CONF_SPEAKER: "chaitra_kn_conversation",
    CONF_PACE: 1.0,
    CONF_SAMPLE_RATE: 24000,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),
        vol.Optional(CONF_MODEL): cv.string,
        vol.Optional(CONF_SPEAKER): cv.string,
        vol.Optional(CONF_PACE): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=2.0)
        ),
        vol.Optional(CONF_SAMPLE_RATE): vol.In(
            [8000, 16000, 22050, 24000, 32000, 44100, 48000]
        ),
    }
)


async def async_get_engine(
    hass: HomeAssistant, config: dict[str, Any], discovery_info: Any = None
) -> SarvamProvider:
    """Set up the Sarvam text-to-speech provider."""
    return SarvamProvider(hass, config)


def split_text(text: str, limit: int = MAX_CHARS) -> list[str]:
    """Split text at sentence ends so that each part fits in one API request."""
    parts: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?।])\s+", text.strip()):
        while len(sentence) > limit:
            parts.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


class SarvamProvider(Provider):
    """Text-to-speech provider that calls the Sarvam API."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self.hass = hass
        self.name = "Sarvam"
        settings = {key: config.get(key, value) for key, value in DEFAULTS.items()}
        self._api_key: str = config[CONF_API_KEY]
        self._language: str = settings[CONF_LANGUAGE]
        self._defaults = {key: settings[key] for key in SUPPORTED_OPTIONS}
        self._sample_rate: int = settings[CONF_SAMPLE_RATE]

    @property
    def default_language(self) -> str:
        return self._language

    @property
    def supported_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

    @property
    def supported_options(self) -> list[str]:
        return SUPPORTED_OPTIONS

    @property
    def default_options(self) -> dict[str, Any]:
        return self._defaults

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Return MP3 audio for the message, one API request for each part."""
        session = async_get_clientsession(self.hass)
        audio = b""
        for part in split_text(message):
            payload = {
                "text": part,
                "language_code": language,
                "model": options.get(CONF_MODEL, self._defaults[CONF_MODEL]),
                "speaker": options.get(CONF_SPEAKER, self._defaults[CONF_SPEAKER]),
                "pace": options.get(CONF_PACE, self._defaults[CONF_PACE]),
                "speech_sample_rate": self._sample_rate,
                "output_audio_codec": "mp3",
            }
            try:
                async with session.post(
                    API_URL,
                    json=payload,
                    headers={"api-subscription-key": self._api_key},
                    timeout=TIMEOUT,
                ) as response:
                    body = await response.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.error("Sarvam request failed: %s", err)
                return None, None
            if response.status != 200 or not body.get("audios"):
                _LOGGER.error(
                    "Sarvam returned HTTP %s: %s",
                    response.status,
                    str((body.get("error") or {}).get("message", body))[:200],
                )
                return None, None
            audio += base64.b64decode(body["audios"][0])
        return "mp3", audio
