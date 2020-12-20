from re import L
from parsing.Parsers import ReceiptParser
from preprocessing.Processors import Eroder,Denoiser,Deskewer,ArtifactRemover,Dilater
from output.Printers import JsonPrinter
import cv2 
import sys
import os
import ntpath
import numpy as np
import json 
import math 

def parseReceipt(path,outPath):
    img = cv2.imread(path,0)     

    pre_processors=[
        Denoiser(lo_intensity_thresh=140),
        ArtifactRemover(text_area_frac_threshold_lo=0.0001,text_area_frac_threshold_hi=0.6),
        Deskewer(text_area_frac_threshold=0.03),
        Dilater(iterations=2,kernel_shape=(2,2)),
        Eroder(iterations=2,kernel_shape=(2,2)),
        Dilater(iterations=2,kernel_shape=(2,2)),

        ]

    if img is None:
        print("Could not find input image at:" + path)
        sys.exit(1)

    for p in pre_processors:
        img = p.process(img)  

    cv2.imwrite(os.path.splitext(outPath)[0]+".png",img)
    
    receipt = parser.parseReceipt(img)
    
    f = open(outPath,"w")
    printer.printOutput(receipt,f)


def word_distance(seq1,seq2):
    """ the error metric in analytics mode for comparing expected output to actual 
        https://stackabuse.com/levenshtein-distance-and-text-similarity-in-python/
    """
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = np.zeros ((size_x, size_y))
    for x in range(size_x):
        matrix [x, 0] = x
    for y in range(size_y):
        matrix [0, y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x-1] == seq2[y-1]:
                matrix [x,y] = min(
                    matrix[x-1, y] + 1,
                    matrix[x-1, y-1],
                    matrix[x, y-1] + 1
                )
            else:
                matrix [x,y] = min(
                    matrix[x-1,y] + 1,
                    matrix[x-1,y-1] + 1,
                    matrix[x,y-1] + 1
                )
    return (matrix[size_x - 1, size_y - 1])

def normalized_error(total_distance,total_label_characters):
    return total_distance / (total_label_characters + 1)


# utility for nested dictionary val extraction
def json_leaf_strings(json,leafs):
    for v in json.values():
        if isinstance(v,dict):
            json_leaf_strings(v,leafs)
        elif isinstance(v,list):
            for i in v:
                json_leaf_strings(i,leafs)
        else:
            leafs.append(v)
                
    return leafs

def analyzeResults(input_filepath,output_directory, label_directory, results_directory):
        # input will be a png input file
        basename = ntpath.basename(input_filepath).split(".")[0]
        label_data = json.load(open(os.path.join(label_directory,basename + ".json"),"r"))
        output_data = json.load(open(os.path.join(output_directory,basename + ".json"),"r"))
        # analysis results
        result_data_path = results_directory


        day_dist = word_distance(label_data["day"],output_data["day"])
        month_dist = word_distance(label_data["month"],output_data["month"])
        year_dist = word_distance(label_data["year"],output_data["year"])
        total_w_dist = word_distance(label_data["total_whole_part"],output_data["total_whole_part"])
        total_f_dist = word_distance(label_data["total_fractional_part"],output_data["total_fractional_part"])

        # match items based on word distance between label and output
        assignment = []
        assigned = set()
        for correct in label_data["items"]:

            min_output = None
            min_distance = math.inf

            for output in output_data["items"]:
                # don't assign more than once
                if output["name"] in assigned:
                    continue 

                # pick output best matching correct output by name of product
                distance = word_distance(correct["name"],output["name"])
                if distance < min_distance:
                    min_output = output
                    min_distance = distance

            if min_output is not None:
                assignment.append((correct,min_output))
                assigned.add(min_output["name"])
            else: 
                # no matching found
                assignment.append((correct,None)) 
        
        # compare based on this matching
        items_distance = 0
        for label_output_pair in assignment:
            label = label_output_pair[0]
            output = label_output_pair[-1]

            # if label is assigned to an output
            if output is not None:
                # count distances
                items_distance += word_distance(label["name"],output["name"])
                items_distance += word_distance(label["price_whole_part"],output["price_whole_part"])
                items_distance += word_distance(label["price_fractional_part"],output["price_fractional_part"])
            else:
                # add length of missed item and its fields to item distance
                items_distance += len(label["name"]) + len(label["price_whole_part"]) + len(label["price_fractional_part"])

        # now penalize additional found items, by adding their lengths to items distance
        for item in output_data["items"]:
            # skip assigned items which we compared above
            if item["name"] in assigned:
                continue 
            else:
                items_distance += len(item["name"] or "") + len(item["price_whole_part"] or "") + len(item["price_fractional_part"] or "")

        # output the data to argument 4
        chars_in_output = sum([len(x) for x in json_leaf_strings(label_data,[])])
        total_error = day_dist + month_dist + year_dist + total_w_dist + total_f_dist + items_distance
        result = {
            "date_dist":day_dist + month_dist + year_dist,
            "total_dist": total_w_dist + total_f_dist,
            "item_dist": items_distance,
            "total_word_distance": total_error,
            "total_characters_label": chars_in_output,
            "normalized_total_error": normalized_error(total_error,chars_in_output)
        }

        out = open(os.path.join(result_data_path,basename + ".json"),"w")
        json.dump(result,out,indent=4)
    

if __name__ == "__main__":

    # in bulk_mode first arg is the directory of images
    # and second is directory output
    # image names will form output names
    bulk_mode = "-b" in sys.argv

    # analytics mode takes in 2 additional argumens one pointing to a directory of labelled training output data
    # and will output score metrics in second additional argument directory
    analytics_mode = "-a" in sys.argv

    if bulk_mode:
        sys.argv.remove("-b")
    if analytics_mode:
        sys.argv.remove("-a")


    parser = ReceiptParser()
    printer = JsonPrinter()


    if bulk_mode or analytics_mode:
        dir = sys.argv[1]  
        out_dir = sys.argv[2]
        files = [os.path.join(dir,f) for f in os.listdir(dir) if os.path.isfile(os.path.join(dir,f))]

        for f in files:
            basename = ntpath.basename(f)
            out_path = os.path.join(out_dir,basename.split(".")[0] + ".json")
            parseReceipt(f,out_path)

            # additionally calculate error metrics
            if analytics_mode:
                analyzeResults(f,out_dir,sys.argv[3],sys.argv[4])
        
        # collate total error metric
        if analytics_mode:
            result_directory = sys.argv[4]

            average_error = 0
            for f in files:
                basename = ntpath.basename(f)
                result_file_path = os.path.join(sys.argv[4],basename.split(".")[0] + ".json")

                result = json.load(open(result_file_path,"r"))

                average_error += result["normalized_total_error"]

            average_error = average_error / len(files)
            print("the average normalized error is: " + str(average_error))
            # write to collated file
            collated_result_file = open(os.path.join(result_directory,"total.json"),"w")
            json.dump({"average_error":average_error},collated_result_file)

    else:
        input = sys.argv[1]
        output = sys.argv[2]
        parseReceipt(input,output)

