# Collect the information of APIs
## Get the reference of Pytorch
```
    python get_reference_torch.py
```
Then you will get two files: `api_description.json` and `apis_info.json`. 
The `api_description.json` records the description for all target APIs.
The `apis_info.json` records the variables's name and type for all target APIs.

If you want to get the reference of Tensorflow, you can just set the `file_path` in `get_reference_torch.py` as `./data/tf_apis.txt`.