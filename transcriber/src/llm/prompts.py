import logging
from functools import lru_cache
from typing import Final, NamedTuple

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from config import load_config

logger = logging.getLogger(__name__)

_NAMES: Final[tuple[str, ...]] = ("summarize",)


class Prompt(BaseModel):
    """
    The system and user halves of one LLM step's prompt.
    """

    system: str
    user: str

    def to_template(self) -> ChatPromptTemplate:
        """
        Build the chat template this prompt describes.

        :return: The chat prompt template.
        """
        return ChatPromptTemplate.from_messages([("system", self.system), ("human", self.user)])


class PromptsConfig(BaseSettings):
    """
    Prompts for the LLM post-processing steps, read from the file the config names.

    Values are overridable per prompt without a rebuild, e.g.
    ``TRANSCRIBER_PROMPTS_SUMMARIZE__system=...``.
    """

    model_config = SettingsConfigDict(
        env_prefix="TRANSCRIBER_PROMPTS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    summarize: Prompt

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Read the prompts file the config names, and order it so environment variables win.

        :return: Ordered tuple of settings sources, earliest wins.
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=load_config().llm.prompts_file),
            file_secret_settings,
        )


class Prompts(NamedTuple):
    """
    Chat prompt templates for the LLM post-processing steps.
    """

    summarize: ChatPromptTemplate


@lru_cache
def load_prompts() -> Prompts:
    """
    Load the prompts and build their templates once.

    Templates are built eagerly so a broken prompt fails at worker startup rather than on
    the first job that happens to need it.

    :raises pydantic.ValidationError: If a prompt, or a half of one, is missing.
    :return: The prompt templates.
    """
    cfg = PromptsConfig()
    return Prompts(*(getattr(cfg, name).to_template() for name in _NAMES))
