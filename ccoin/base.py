from abc import ABC, abstractmethod, abstractclassmethod


class Serializable(ABC):

    @abstractmethod
    def to_dict(self):
        pass

    @classmethod
    @abstractclassmethod
    def from_dict(cls, data):
        pass