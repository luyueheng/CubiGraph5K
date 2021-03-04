# CubiGraph5K

Code and dataset for **CubiGraph5K: Organizational Graph Generation for Structured Architectural Floor Plan Dataset** CAADRIA 2021

This dataset is a collection of graph representations generated by the proposed algorithms, using the floor plans in the popular CubiCasa5K dataset as inputs. The aim of this contribution is to provide a matching dataset that could be used to train neural networks on enhanced floor plan parsing, analysis and generation in future research.

### Requirements

- Python3
- BeautifulSoup
- Shapely

### Usage

### Dataset

You can download original CubiCasa5K dataset from [here] (https://zenodo.org/record/2613548) and extract the .zip file to `/cubicasa5k` folder.

The corresponding CubiGraph5K dataset is in `/dataset/data.json`. 

The file paths of floor plans with invalid Shapely geomety or multiple stories are listed in `/dataset/invalid.txt` and `dataset/multistory.txt` for reference.



