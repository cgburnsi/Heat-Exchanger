from abc import ABC, abstractmethod

class HeatTransferModel(ABC):
    @abstractmethod
    def calculate_Nu(self, *args, **kwargs):
        pass
