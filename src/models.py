from abc import ABC, abstractmethod
import numpy as np
import math
import itertools


class HeatTransferModel(ABC):
    @abstractmethod
    def calculate_Nu(self, *args, **kwargs):
        pass


    