import os

from ansible.plugins.lookup import LookupBase
from ansible.module_utils.six import string_types
import ansible_collections.cloud.common.plugins.module_utils.turbo.common
from ansible_collections.cloud.common.plugins.module_utils.turbo.exceptions import (
    EmbeddedModuleUnexpectedFailure,
)


def get_server_ttl(variables):
    # trying to retrieve first TTL from environment variable
    ttl = os.environ.get("ANSIBLE_TURBO_LOOKUP_TTL", None)
    if ttl is not None:
        return ttl
    # Read TTL from ansible environment
    for env_var in variables.get("environment", []):
        value = env_var.get("ANSIBLE_TURBO_LOOKUP_TTL", None)
        test_var_int = [
            isinstance(value, string_types) and value.isnumeric(),
            isinstance(value, int),
        ]
        if value is not None and any(test_var_int):
            ttl = value
    return ttl


class TurboLookupBase(LookupBase):
    def run_on_daemon(self, terms, variables=None, **kwargs):
        self._ttl = get_server_ttl(variables)
        return self.execute(terms=terms, variables=variables, **kwargs)

    @property
    def socket_path(self):
        if not hasattr(self, "__socket_path"):
            """
            Input:
                _load_name: ansible_collections.cloud.common.plugins.lookup.turbo_random_lookup
            Output:
                __socket_path: {HOME}/.ansible/tmp/turbo_mode_cloud.common.socket
            this will allow to have one socket per collection
            """
            name = self._load_name
            ansible_collections = "ansible_collections."
            if name.startswith(ansible_collections):
                name = name.replace(ansible_collections, "", 1)
                lookup_plugins = ".plugins.lookup."
                idx = name.find(lookup_plugins)
                if idx != -1:
                    name = name[:idx]
            self.__socket_path = os.environ[
                "HOME"
            ] + "/.ansible/tmp/turbo_lookup.{0}.socket".format(name)
        return self.__socket_path

    def execute(self, terms, variables=None, **kwargs):
        with ansible_collections.cloud.common.plugins.module_utils.turbo.common.connect(
            socket_path=self.socket_path, ttl=self._ttl, plugin="lookup"
        ) as turbo_socket:
            content = (self._load_name, terms, variables, kwargs)
            (result, errors) = turbo_socket.communicate(content)
            if errors:
                raise EmbeddedModuleUnexpectedFailure(errors)
            return result
