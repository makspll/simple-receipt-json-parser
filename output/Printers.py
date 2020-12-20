from classes.Classes import Item,Receipt
import json 
from abc import ABC, abstractmethod


class Printer(ABC):
    @abstractmethod
    def printOutput(self,receipt,file):
        pass


class JsonPrinter(Printer):

    def printOutput(self,receipt,file):

        items = [{
            "name": str(x.name),
            "price_whole_part": str(x.price_whole_part),
            "price_fractional_part": str(x.price_fractional_part)
        } for x in receipt.items]

        r = {
            "day":str(receipt.day),
            "month":str(receipt.month),
            "year":str(receipt.year),
            "total_whole_part": str(receipt.total_whole_part),
            "total_fractional_part": str(receipt.total_fractional_part),
            "items": items
        }

        json.dump(r, file,indent=4)

