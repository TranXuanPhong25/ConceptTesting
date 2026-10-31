# TRATTO Neural module

TRATTO neural module is a PyTorch model fine-tuned on the task of predicting the next token-class and the next token, given a partial oracle.
The model is fine-tuned using the pre-trained [CodeLlama](https://huggingface.co/codellama/CodeLlama-7b-hf) model (`7B-hf`).

# Setup

To set up and run the model, the following requirements must be satisfied:

* `Python 3.9`
* `Pip`

The model has been trained on a GPU `Nvidia A-100` with `80GB` of memory (vRAM) and `147GB` of RAM.

At inference time, the model requires a GPU with at least `24GB` of vRAM.

## 1. Environment

In order to set up the environment is not strictly necessary, but recommended to create a [_venv_](https://docs.python.org/3/library/venv.html)
or [_conda_](https://docs.conda.io/en/latest/) environment.
In the following section we will provide the general information to configure the environment.

### 1.A.1 Create and activate _venv_ environment

Follow the instructions to properly create and activate the environment

1. Open a terminal and move to the `ml-model` directory.
2. Create the _venv_ environment with `Python 3.9`:
   ```shell
   python3.9 -m venv .venv
   ```
   The command will generate a _venv_ environment within `ml-model/.venv`.
3. Activate the _venv_ environment:
   ```shell
   source .venv/bin/activate
   ```

### 1.A.2 Install the requirements

Install the dependencies within the active _venv_ environment, using the following command:

   ```shell
  python3.9 -m pip install --upgrade -r requirements.txt --target=[path_to_tratto_replication_package]/ml-model/.venv/lib/python3.9/site-packages
   ```

where:

   * `path_to_tratto_replication_package` must be substituted the absolute path to the replication package repository

### 1.B.1 Install Conda

The reader can find all the instructions to properly install and setup _conda_, on the official [user guide](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html).

We provide an example on how to install conda on Linux operating systems. The installation is relatively similar for
macOS and Windows systems.

1. Open a terminal and type the following command to download the installer:
    ```shell
    wget -P [path_to_destination_directory] [conda_download_http_link]
    ```
    * `path_to_destination_directory` - represents the destination path where the installer will be downloaded.
    * `conda_download_http_link` - is the link of the installer. You can choose the installer [here](https://docs.conda.io/en/latest/miniconda.html#linux-installers), copying the corresponding url.

2. Execute the installer:
    ```shell
    bash [fullname_of_the_installer]
    ```
   * `fullname_of_the_installer` - is the whole name of the downloaded installer (it is a _.sh_ file, like for example
     _Miniconda3-py39_23.3.1-0-Linux-aarch64.sh_)

3. Close and re-open the terminal at the end of the installation. Check _conda_ has been successfully installated typing the command:
    ```shell
    conda --version
    ```

### 1.B.2 Create and activate _conda_ environment

4. Create a new conda environment named "_tratto_" for the **TRATTO** project with Python version 3.9 and pip.
   ```bash
    conda create --name tratto python=3.9 pip
    ```

5. Activate the conda environment
    ```bash
    conda activate tratto
    ```

### 1.B.3 Install the requirements

6. Move to the `ml-model` folder of the `tratto` project
    ```bash
    cd [path_to_the_tratto_folder]/ml-model
    ```

7. Install all the required dependencies
    ```shell
    pip install -r requirements.txt
    ```

## 2. Models Checkpoints & Datasets

Execute the following command to download the datasets and/or the checkpoint of the final trained model.
   ```shell
   bash init.sh [--datasets] [--checkpoint]
   ```
where:
   * `--datasets`: if provided, the script will download the datasets to train the token classes and token values models.
   * `--checkpoint`: if provided, the script will download the checkpoints of the fine-tuned model.
The datasets and checkpoints will be saved within the `ml-model` root directory, with the homonym names
(`ml-model/datasets` and `ml-model/checkpoint`).

## 3. Training

### 3.1 Data pre-processing
Ensure to have downloaded the datasets (see previous section [2](#2.-models-checkpoints-&-datasets])) and they are present within the `datasets` directory.
Execute the following script to prepare the datasets for the training of the models.
   ```shell
   bash pre_processing.sh
   ```
The script generate a `dataset.csv` file within the `ml-model/datasets` of the processed datasets.

### 3.2 Training the model
Run the following command to replicate the training of the model.
   ```shell
   bash ./training.sh
   ```

If you want to run the training as a background process execute the following command:
   ```shell
   nohup bash ./training.sh > [log_filename].out 2>&1 & echo $! > [process_number_filename].pid
   ```
where:
* `log_filename` is the name of the textual file where the logs will be saved
* `process_number_filename` is the name of the textual file where the pid number of the generated process will be saved.

The bash scripts contain a list of different arguments that can be changed to fine-tune the model using
different values of the hyperparameters.

## 5. Server

To provide the model as a service and run it within a server to perform predictions on new data (for example, in combination with the main tratto program), 
execute the following command to setup and start the server:
   ```shell
   bash server.sh [port_number]
   ```
where:
   * `port_number` indicates the port where to run the server (`5000`, by default).

The command will instantiate the server, listening on the port printed within the terminal (`http://127.0.0.1:5000` by default).
The server implements a single REST API endpoint (`/api/next_token`) that receive as a single parameter the path to the file
where the dataset for the next token to compute is located (the file must be in `json` format):

   ```http request
   http://127.0.0.1:5000/api/next_token?filename=[path_to_file]/[filename].json
   ```
   * `path_to_file` - the absolute path to the directory where the dataset is located.
   * `filename` - the name of the json file containing the dataset.

The response to the request contains a string representing the next token class and token value of the oracle.

