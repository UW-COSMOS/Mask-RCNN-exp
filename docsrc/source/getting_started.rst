Getting Started
==================================

To get started with Cosmos, we highly suggest utilizing some of our prebuilt _Docker images.
These handle building dependencies and running your documents through the pipeline without
having to worry about installing things locally.

First, clone the Cosmos repository, and change into the root directory of the repository.
Open a file named .env in the directory, and populate it with the following:

.. code-block:: console

    BASE_IMAGE=uwcosmos/cosmos-base:latest
    DETECT_IMAGE=uwcosmos/cosmos-ingestion:latest
    WORKER_IMAGE=uwcosmos/cosmos-ingestion:latest
    UPLOAD_IMAGE=uwcosmos/cosmos-upload:latest
    RETRIEVAL_IMAGE=uwcosmos/cosmos-retrieval:latest
    EXTRACTION_IMAGE=ankurgos/cosmos-extraction:latest
    VISUALIZER_IMAGE=uwcosmos/visualizer_kb:latest
    API_IMAGE=uwcosmos/cosmos-api:latest
    DETECT_PROCS=1
    WORKER_PROCS=7
    DEVICE=cuda
    RERANKING_DEVICE=cuda
    INPUT_DIR=/path/to/input/dir
    TMP_DIR=/path/to/tmp/dir
    OUTPUT_DIR=/path/to/output/dir
    ELASTIC_DATA_PATH=/path/to/es/directory
    ELASTIC_ADDRESS=es01

The first seven lines in the file define which images to use. The default cosmos images assumes access to a CUDA
enabled GPU. To utilize a CPU, append to each image "-cpu". For example, change uwcosmos/cosmos-base:latest to
uwcosmos/cosmos-base-cpu:latest. If you use the CPU version, make sure to change all \*_DEVICE from 'cuda' to 'cpu'.

Depending on your machine, you can scale the process by setting DETECT_PROCS and WORKER_PROCS to the desired number of
processes.

Finally, make sure to set the final three directories, denoting the input directory pointing to your PDFs, a temporary
directory with sufficient hard drive space to write images and such, and an output directory to write information.

To process the images, run the following line:

.. code-block:: console

    docker-compose -f deployment/docker-compose-ingest.yml -p cosmos up

The output directory you defined will now be populated with a set of Parquet_ files, as well as an images directory
containing object specific images, and saved word embeddings over the input corpus.

Entity linking
--------------
Once the documents have been ingested, a separate process can be run to recognize named entities
within the extracted objects, linking them to the Unified Medical Language System (UMLS). Named
entity recognition and UMLS linking are accomplished via SciSpacy_. The parquet files will be
modified to include linked and unlinked entities, and an additional parquet file will be created
containing canonical information for the linked entities. To run the entity linking pipeline:

.. code-block:: console
    docker-compose -f deployment/docker-compose-link.yml -p cosmos up

Deploying the COSMOS search interface
-----------------------------------

To deploy the search interface over this processed dataset, run the following command:

.. code-block:: console

    docker-compose -f deployment/docker-compose-api.yml up

This will create an elasticsearch service for you. If you already have a ElasticSearch cluster online, see
:ref:`Existing ElasticSearch Cluster`. Its datapath is will be set to the environment variable set in the .env file.

Reading ingested data into ElasticSearch
----------------------------------------

The files outputted by ingestion must now be read into ElasticSearch indices. In a separate window, run:

.. code-block:: console

    docker-compose -f deployment/docker-compose-api-upload.yml up

This could take some time, depending on the size of your document stack.

Viewing output
--------------

You should now be able to navigate to localhost:8082 in your browser to access the search interface.

.. _Docker: https://www.docker.com/
.. _Parquet: https://parquet.apache.org/
.. _ElasticSearch: https://www.elastic.co/home
.. _SciSpacy: https://allenai.github.io/scispacy/
