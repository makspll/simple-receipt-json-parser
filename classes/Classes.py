class Item():
    """
    A receipt item
    """
    def __init__(self):
        self.name = None
        self.price_whole_part = None
        self.price_fractional_part = None
    
    def __repr__(self) -> str:
        return str(self.name) + ":" + str(self.price_whole_part) +"." + str(self.price_fractional_part)

class Receipt():
    """
    A receipt detailing a purchase of a list of items on a certain date
    """
    def __init__(self):
        self.items = []
        self.day = None
        self.month = None
        self.year = None

        self.total_whole_part = None
        self.total_fractional_part = None
