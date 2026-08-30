FROM quay.io/condaforge/miniforge3:26.3.2-3

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DGLBACKEND=pytorch \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY conda_env_eval.yml /tmp/conda_env_eval.yml
RUN /opt/conda/bin/conda env create --file /tmp/conda_env_eval.yml \
    && /opt/conda/bin/conda clean --all --yes \
    && rm /tmp/conda_env_eval.yml

ENV PATH=/opt/conda/envs/naturebench-eval/bin:/opt/conda/bin:$PATH

RUN python -c "import Bio, anndata, dgl, h5py, imageio, meeko, networkx, numpy, pandas, pyarrow, rdkit, scipy, skimage, sklearn, torch"

WORKDIR /opt/naturebench-eval
