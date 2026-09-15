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

ENV PATH=/opt/conda/envs/naturebench-eval/bin:/opt/conda/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/naturebench

RUN python -c "import Bio, anndata, dgl, h5py, imageio, meeko, networkx, numpy, pandas, pyarrow, rdkit, scipy, skimage, sklearn, torch"

COPY naturebench_eval_service /opt/naturebench/naturebench_eval_service
COPY bin /opt/naturebench/bin
RUN chmod +x /opt/naturebench/bin/timerctl /opt/naturebench/bin/drain-and-finalize \
    && mkdir -p /state /run/naturebench

EXPOSE 8000
ENTRYPOINT ["python", "-m", "naturebench_eval_service.server"]
