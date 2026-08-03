from rocketlib import IGlobalBase, OPEN_MODE
from ai.common.config import Config


class IGlobal(IGlobalBase):
    config = None

    def beginGlobal(self):
        if self.IEndpoint.endpoint.openMode != OPEN_MODE.CONFIG:
            self.config = Config.getNodeConfig(self.glb.logicalType, self.glb.connConfig)

    def endGlobal(self):
        self.config = None
