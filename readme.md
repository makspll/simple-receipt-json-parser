# Simple-receipt-json-parser

# Description
This is a pretty basic skeleton for a receipt parser. The structure allows you to add your custom rule-based or perhaps neural network-based parsers as well as implement a custom pre-processing pipeline for your images. 

The `receipt_parser.py` script compiles the basic usage of the classes into a script which is designed to work with rather higher quality scans with 300 DPI ideally. For other uses you might want to modify the script or roll your own

# Requirements
- tesseract OCR: `sudo apt install tesseract-ocr`

- tesseract language pack: `sudo apt-get install tesseract-ocr-eng` (for `receipt_parser.py`, if you're rolling your own implementation in a different language, you will need the language pack in that language)

- OpenCV 2 (in pipfile)

- Rest of requirements can be installed from pipfile using `pipenv install`

# Structure

There are 4 basic modules making up this software:

- preprocessing: contains  `Processor` abstract class and a bunch of implementing classes, each one implements the `process(img)` method which performs some sort of pre-processing. The available ones currently are: Denoiser, ArtifactRemover,Deskewer,Dilater,Eroder.

- parsing: contains the Parser abstract class, and ReceiptParser implementation which performs rule-based parsing on the given pre-processed image, i.e. it picks the highest currency formated value becomes the total. This class has accepts a tesseract language code, a price regex and a date regex - the regexes have to capture certain parts of the price and date as detailed in the code (defaults work with UK receipts).

- output: contains the Printer abstract class, and JsonPrinter implementation of it, these as the name imply simply output the parsed receipts

- classes: contain the `Item` and `Receipt` classes which are parsing targets.

# Usage

Single receipt:

`python receipt_parser.py path-to-img.png path-to-output.json`

Multiple receipts:

`python receipt_parser.py -b path-to-img-dir path-to-output-dir`

Calibration (analytics mode), if you have a set of labelled data (expected json output files in the same format as printer):

`python receipt_parser.py -a path-to-img-dir path-to-output-dir path-to-training-labels path-to-analytics-output-dir`