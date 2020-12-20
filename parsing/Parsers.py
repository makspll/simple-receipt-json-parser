from datetime import date
import cv2
import numpy as np
import sys
from matplotlib import pyplot as plt
import pytesseract
from pytesseract import Output
from abc import ABC, abstractmethod
import re 
from classes.Classes import Item,Receipt

class Parser(ABC):
    
    @abstractmethod
    def parseReceipt(self,img):
        pass

class ReceiptParser(Parser):
    def __init__(self,
        lang="eng",
        price_regex= r".(?P<w>\b\d+)\.(?P<f>\d+)\b",
        date_regex=r"(?P<d>\d+)/(?P<m>\d+)/(?P<y>\d+)"):

        """ lang is the tesseract language code to use in OCR, price regex is a regex which matches any prices in the receipt and captures w,f as the whole and fractional parts respectively.
            Similarly the date regex catches the d,m,y for day month and years respectively.
        """
        self.lang = lang 
        self.price_regex = price_regex
        self.date_regex = date_regex

    def parseReceipt(self,img):
        
        # perform OCR 
        extracted_text = self.normalize_text(
            pytesseract.image_to_string(img,lang=self.lang))
            
        # extract data according to custom rules
        (total_w,total_f) = self.parseTotal(extracted_text) or ("","")
        d,m,y = self.parseDate(extracted_text) or ("","","")
        items = self.parseItems(extracted_text) or []

        # create receipt
        receipt = Receipt()
        receipt.total_whole_part = total_w
        receipt.total_fractional_part = total_f
        receipt.day = d 
        receipt.month = m
        receipt.year = y
        receipt.items = items

        # return
        return receipt 
        
    def normalize_text(self,text):
        return text.lower()

    def parseTotal(self,text):
        """ looks for the total price in the normalized text given, returns none if none found, or tuple of whole and fractional part of the total """
        
        # identify all prices
        prices = self.findPriceMatches(text)

        # if no prices found return no total
        if len(prices) == 0:
            return None

        # find biggest price    
        max = 0
        max_match = None
        for match in prices:
            if match["value"] > max:
                max = match["value"]
                max_match = match["match"]
        
        return (max_match.group("w"),max_match.group("f"))

        # we look for occurences of floating point formated numbers and 
    
    def parseDate(self,text):
        """ looks for the date in the normalized text given, returns none if none found and 3-ple (d,m,y) otherwise"""

        # attempt to find date in the expected format
        match = re.search(self.date_regex,text)

        if match is None:
            return None
        else:
            d,m,y = match.group("d"),match.group("m"),match.group("y")
            return (d,m,y)

    def parseItems(self,text):
        """ looks for the items in the normalized text given, returns none if none found """

        # find first line which contains a price and try to parse each line as an item,
        # exclude any lines with the word total or such, and try to ignore discount lines, or filler ones 
        prices = self.findPriceMatches(text)

        # if no prices, return none 
        if len(prices) == 0:
            return None
        else:
            first_price = prices[0]
            
            # find line containing first price
            line_no = self.findLineAtIndex(first_price["start"],text)
            lines = text.splitlines()

            items = []

            for idx,l in enumerate(lines):
                # check line contains word TOTAL, if so stop
                if "total" in l.lower():
                    break

                # otherwise keep interpreting price-item pairs
                prices = self.findPriceMatches(l)

                # if no price, skip line
                if len(prices) == 0:
                    continue
                else:
                    # otherwise pick last one (first one is likely price per kilo or similar)
                    price_match = prices[-1]
                    # take name to be everything in the line except price
                    name = l[0 : price_match["start"]] + l[price_match["end"] + 1:]
                    # clean up
                    name = name.strip()
                    
                    # create item and append
                    item = Item()
                    item.name = name
                    item.price_whole_part = price_match["match"].group("w")
                    item.price_fractional_part = price_match["match"].group("f")
                    
                    items.append(item)

            return items



    def findLineAtIndex(self,index,string):
        """ returns line number at the given index of the given string"""

        line = 0
        curr_line_start_idx = 0
        last_line = False

        for idx,c in enumerate(string):
            if c == '\n':
                if last_line == True:
                    # if we just ending this line, return
                    return line
                else:
                    line+= 1
                    curr_line_start_idx = idx
                    continue

            if idx == index:
                last_line = True


    def findPriceMatches(self,text):
        """ identifies the start-end positions of each possible price found in the receipt along with their values in a list of tuples"""
        

        # find matches for things starting with currency sign and some digits around a dot
        matches = re.finditer(self.price_regex, text)
        matches = [{"start":match.start(),
                    "end":match.end(),
                    "value":float(match.group("w")+"."+match.group("f")),
                    "match":match
                } for match in matches]
        return matches