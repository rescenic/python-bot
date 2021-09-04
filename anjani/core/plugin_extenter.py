import importlib
import inspect
from types import ModuleType as PluginType
from typing import TYPE_CHECKING, Any, Iterable, MutableMapping, Optional, Type

from anjani import custom_plugins, plugin, plugins, util
from anjani.error import ExistingPluginError

from .anjani_mixin_base import MixinBase

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class PluginExtender(MixinBase):
    # Initialized during instantiation
    plugins: MutableMapping[str, plugin.Plugin]

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        # Initialize plugin map
        self.plugins = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def load_plugin(
        self: "Anjani", cls: Type[plugin.Plugin], *, comment: Optional[str] = None
    ) -> None:
        self.log.info(f"Loading {cls.format_desc(comment)}")

        if cls.name in self.plugins:
            old = type(self.plugins[cls.name])
            raise ExistingPluginError(old, cls)

        plug = cls(self)
        plug.comment = comment
        self.register_listeners(plug)
        self.register_commands(plug)
        self.plugins[cls.name] = plug

    def unload_plugin(self: "Anjani", plug: plugin.Plugin) -> None:
        cls = type(plug)
        self.log.info(f"Unloading {plug.format_desc(plug.comment)}")

        self.unregister_listeners(plug)
        self.unregister_commands(plug)
        del self.plugins[cls.name]

    def _load_all_from_metaplug(
        self: "Anjani", subplugins: Iterable[PluginType], *, comment: str = None
    ) -> None:
        for plug in subplugins:
            for sym in dir(plug):
                cls = getattr(plug, sym)
                if inspect.isclass(cls) and issubclass(cls, plugin.Plugin) and not cls.disabled:
                    self.load_plugin(cls, comment=comment)

    # noinspection PyTypeChecker,PyTypeChecker
    def load_all_plugins(self: "Anjani") -> None:
        self.log.info("Loading plugins")
        self._load_all_from_metaplug(plugins.subplugins)
        self._load_all_from_metaplug(custom_plugins.subplugins, comment="custom")
        self.log.info("All plugins loaded.")

    def unload_all_pluginss(self: "Anjani") -> None:
        self.log.info("Unloading plugins...")

        # Can't modify while iterating, so collect a list first
        for plug in list(self.plugins.values()):
            self.unload_plugin(plug)

        self.log.info("All plugins unloaded.")

    async def reload_plugin_pkg(self: "Anjani") -> None:
        self.log.info("Reloading base plugin class...")
        await util.run_sync(importlib.reload, plugin)

        self.log.info("Reloading master plugin...")
        await util.run_sync(importlib.reload, plugins)

        self.log.info("Reloading custom master module...")
        await util.run_sync(importlib.reload, custom_plugins )
